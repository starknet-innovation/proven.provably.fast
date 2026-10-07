"""Run queued proven.provably.fast entries on the evaluator host, only while the provably.fast Stwo challenge is idle.

Run as root from a systemd timer. Each cycle takes the evaluator's host lock without waiting:
that challenge's operator holds it while it runs, so a held lock means skip this cycle. Holding the
lock, it takes the oldest request in QUEUE ({"url": ..., "commit": <full hash>, optionally
"entry": <directory inside the repository>}) and:

1. clones the repository at that commit (git runs no repository code on a clone) and refuses it
   if it is too large or the disk is short;
2. for a Rust entry with Cargo.lock at the root, runs `cargo fetch --locked` as the sandbox user
   `proven`, with the network but nothing else writable (cargo honours the repository's own
   configuration, so it never runs as root);
3. runs the entry's build, if any, as `proven` with no network, Stwo's pinned toolchain and the
   request's own crate cache;
4. makes the repository read-only and judges it as root, the judge running every entrant command
   as `proven` with no network and private temporary directories, and writing its verdict to a
   file entrant code cannot reach;
5. records the result, marked official, in RESULTS/oracle.jsonl, moves the request to done/, and
   deletes the request's files.

Invariant: the verdict that reaches the results file is the judge's own; no entrant process can
write it or run as root. Any failure is recorded as a FAIL for that request and never stalls the
queue.

    python3 -m proven.host_runner --config /etc/provably-fast/internal-proof-operator.json
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .intake import entry_dir_of, fetch, inside, load_entry

STATE = Path("/var/lib/provably-fast/proven")
CODE = Path(__file__).resolve().parents[1]
USER = "proven"
# Stwo's pinned toolchain, readable by the sandbox user.
TOOLCHAIN = Path("/opt/provably-fast/toolchains/rustup-home/toolchains/"
                 "nightly-2026-01-15-x86_64-unknown-linux-gnu/bin")
MAX_REPOSITORY_BYTES = 4 << 30
MIN_FREE_BYTES = 100 << 30
SANDBOX = ["-p", f"User={USER}", "-p", "NoNewPrivileges=yes", "-p", "ProtectSystem=strict",
           "-p", "ProtectHome=yes", "-p", "PrivateTmp=yes", "-p", "MemoryMax=48G",
           "-p", "TasksMax=4096", "-p", "RuntimeMaxSec=3600"]


def host_lock(config: Path) -> int | None:
    """The challenge operator's host lock, held without waiting, or None if it is busy."""
    descriptor = os.open(json.loads(config.read_text())["host_lock"], os.O_RDWR | os.O_CLOEXEC)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(descriptor)
        return None
    return descriptor


def sandboxed(base: Path, argv: list[str], network: bool, log: Path) -> None:
    """Run argv in the repository as the sandbox user; only the repository and the request's crate
    cache are writable."""
    environment = {"PATH": f"{TOOLCHAIN}:/usr/bin:/bin", "CARGO_HOME": str(base / "cargo-home"),
                   "HOME": str(base / "cargo-home")}
    if not network:
        environment["CARGO_NET_OFFLINE"] = "true"
    command = ["systemd-run", "--wait", "--pipe", "--quiet", "--collect", *SANDBOX,
               *([] if network else ["-p", "PrivateNetwork=yes"]),
               "-p", f"ReadWritePaths={base / 'repo'} {base / 'cargo-home'}",
               "-p", f"WorkingDirectory={base / 'repo'}",
               *[f"--setenv={name}={value}" for name, value in environment.items()], "--", *argv]
    with log.open("ab") as out:
        subprocess.run(command, stdout=out, stderr=subprocess.STDOUT, check=True, timeout=3700)


def judged(base: Path, entry_dir: Path, runs: int) -> dict:
    """The judge, as root in a memory-capped scope; entrant commands run isolated as USER."""
    verdict = base / "verdict.json"
    command = ["systemd-run", "--scope", "--quiet", "-p", "MemoryMax=48G", "-p", "TasksMax=4096",
               "/usr/bin/python3", "-E", "-s", "-m", "proven.oracle", str(entry_dir),
               "--runs", str(runs), "--official", "--isolate", USER,
               "--workdir", str(base / "judge"), "--results", str(verdict)]
    (base / "judge").mkdir(mode=0o755)
    subprocess.run(command, cwd=CODE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=4 * 3600)
    rows = verdict.read_text().splitlines()
    return json.loads(rows[-1])


def process(request: dict, base: Path, runs: int) -> dict:
    if shutil.disk_usage(STATE).free < MIN_FREE_BYTES:
        raise RuntimeError("the evaluator host is short of disk space")
    repo = base / "repo"
    fetch(request["url"], request["commit"], repo)
    size = sum(path.stat().st_size for path in repo.rglob("*") if path.is_file())
    if size > MAX_REPOSITORY_BYTES:
        raise RuntimeError(f"the repository is {size} bytes, over the {MAX_REPOSITORY_BYTES}-byte limit")
    entry_dir = entry_dir_of(repo, request.get("entry"))
    spec = load_entry(entry_dir)
    if spec.get("ledger") and not inside(repo, (entry_dir / spec["ledger"]).resolve()):
        raise RuntimeError("the sheet must be inside the repository")
    if request["url"].startswith("file://") and not inside(STATE, Path(request["url"][7:])):
        raise RuntimeError("local repositories are for maintainer tests under the runner's state")
    (base / "cargo-home").mkdir()
    subprocess.run(["chown", "-R", f"{USER}:{USER}", str(repo), str(base / "cargo-home")], check=True)
    log = base / "build.log"
    if (repo / "Cargo.lock").exists():
        sandboxed(base, [str(TOOLCHAIN / "cargo"), "fetch", "--locked"], True, log)
    if spec.get("build"):
        sandboxed(base, spec["build"], False, log)
    # From here on, entrant code can read its repository but not change it.
    subprocess.run(["chown", "-R", "root:root", str(repo)], check=True)
    subprocess.run(["chmod", "-R", "go-w", str(repo)], check=True)
    return judged(base, entry_dir, runs)


def cycle(config: Path, runs: int) -> dict:
    queue, finished = STATE / "queue", STATE / "done"
    requests = sorted(queue.glob("*.json"), key=lambda path: path.stat().st_mtime)
    if not requests:
        return {"status": "IDLE"}
    lock = host_lock(config)
    if lock is None:
        return {"status": "SKIPPED", "reason_code": "HOST_BUSY"}
    try:
        request_path = requests[0]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        try:
            request = json.loads(request_path.read_text())
            base = STATE / "work" / f"{request['commit']}-{stamp}"
        except (ValueError, KeyError) as error:
            request, base = {}, STATE / "work" / f"unreadable-{stamp}"
            result = {"verdict": "FAIL", "listing": "not listed", "error": f"unreadable request: {error}"}
        else:
            base.mkdir(mode=0o755, parents=True)
            try:
                result = process(request, base, runs)
            except Exception as error:  # every failure is this request's FAIL, never a stalled queue
                tail = (base / "build.log").read_text(errors="replace")[-1500:] \
                    if (base / "build.log").exists() else ""
                result = {"verdict": "FAIL", "listing": "not listed",
                          "error": f"{type(error).__name__}: {error}"[:1500], "build_log_tail": tail}
        result["official"] = True
        result["source"] = {"repository": request.get("url"), "commit": request.get("commit"),
                            "entry": request.get("entry")}
        result["judged_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        results = STATE / "results" / "oracle.jsonl"
        results.parent.mkdir(parents=True, exist_ok=True)
        with results.open("a") as handle:
            handle.write(json.dumps(result, sort_keys=True) + "\n")
        finished.mkdir(parents=True, exist_ok=True)
        request_path.rename(finished / request_path.name)
        subprocess.run(["pkill", "-KILL", "-u", USER], check=False)
        shutil.rmtree(base, ignore_errors=True)
        return {"status": "JUDGED", "commit": request.get("commit"), "verdict": result["verdict"]}
    finally:
        os.close(lock)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--config", type=Path, required=True,
                        help="the challenge operator's config, read only for its host lock path")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args(argv)
    if os.geteuid() != 0 or sys.platform != "linux":
        raise SystemExit("the host runner runs as root on the evaluator host")
    print(json.dumps(cycle(args.config, args.runs), sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
