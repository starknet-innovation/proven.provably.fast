"""The proven.provably.fast oracle: runs one entry on fresh statements and decides.

An entry is a directory holding entry.json:

    {"name": "stwo-circuit-chain", "system": "Stwo circuits framework, circle STARK over M31",
     "statement": "blake2s-chain-v0",
     "prove": ["./chain", "prove", "{statement}"],
     "verify": ["./chain", "verify", "{statement}", "{proof}"],
     "ledger": "ledger.json"}

Commands run in the entry directory, and the prover writes its proof to stdout. The prover's
{statement} holds the whole statement, witness included; the verifier's holds the public part. The verifier
exits 0 to accept and 20 to reject (1, an unreadable input, also counts as a rejection); any
other exit, a signal or a timeout is a crash. Peak memory is the prover process's own maximum
resident set, so a wrapper script must exec the prover.

Gates:
- completeness: every fresh true statement proves and its proof verifies;
- rejection: the verifier rejects false statements with a true proof, another statement's
  proof, and empty, garbage, truncated, extended and bit-flipped proofs, without crashing;
- caps: proof bytes within the statement's cap, and verify time within its cap on the evaluator
  host (`--official`); elsewhere the verify time is reported against the cap, not gated;
- ledger: the calculator gives at least the floor in claimed bits, with no missing component
  and no claim resting on the proximity-gap conjecture (regime conjectured-capacity).

No gate sees a verifier that checks a MAC or a hash of the statement instead of a proof, or one
that shares state with its own prover: such an entry passes all four. Listing needs a person or
an agent to read the verifier first.

Every verifier call sees a fresh directory holding only statement.json and proof.bin, and the
prover's witness statement is deleted before any verifier runs. On the evaluator host, --isolate
runs each entrant command as the sandbox user, with no network and empty /tmp, /var/tmp and
/dev/shm of its own, while the judge itself stays root and writes its verdict where entrant code
cannot reach.

    python3 -m proven.oracle entries/stwo-chain --runs 3 --results results/oracle.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .calculator import LedgerError, evaluate, load_reviews
from .statements import BOARD, GENERATORS, false_variants, public

PROVE_TIMEOUT = 1800.0
VERIFY_TIMEOUT = 60.0


def run(argv: list[str], cwd: Path, stdout_path: str, timeout: float,
        env: dict[str, str] | None = None) -> dict:
    """Run one command; time it and read its own peak memory from wait4."""
    with open(stdout_path, "wb") as out, tempfile.TemporaryFile() as err:
        start = time.perf_counter()
        process = subprocess.Popen(argv, cwd=cwd, stdout=out, stderr=err,
                                   env=None if env is None else {**os.environ, **env})
        timed_out = False
        while True:
            pid, status, usage = os.wait4(process.pid, os.WNOHANG)
            if pid:
                break
            if time.perf_counter() - start > timeout:
                process.kill()
                _, status, usage = os.wait4(process.pid, 0)
                timed_out = True
                break
            time.sleep(0.002)
        seconds = time.perf_counter() - start
        process.returncode = os.waitstatus_to_exitcode(status)
        err.seek(0)
        stderr = err.read()[-600:].decode(errors="replace")
    scale = 1 if sys.platform == "darwin" else 1024
    return {"exit": process.returncode, "seconds": seconds, "peak_bytes": usage.ru_maxrss * scale,
            "timed_out": timed_out, "stderr": stderr}


def command(template: list[str], statement: Path, proof: Path | None = None) -> list[str]:
    return [part.replace("{statement}", str(statement)).replace("{proof}", str(proof or ""))
            for part in template]


def outcome(result: dict) -> str:
    if result["timed_out"]:
        return "CRASH"
    if result["exit"] == 0:
        return "ACCEPT"
    return "REJECT" if result["exit"] in (1, 20) else "CRASH"


def isolated(user: str) -> list[str]:
    """A prefix that runs a command as `user`, with no network and empty /tmp, /var/tmp and
    /dev/shm of its own. Linux, as root; keeps the command's pid, so wait4 still reads its peak."""
    mounts = " && ".join(f"mount -t tmpfs -o mode=1777 tmpfs {path}"
                         for path in ("/tmp", "/var/tmp", "/dev/shm"))
    return ["unshare", "--net", "--mount", "--", "/bin/sh", "-c",
            f'{mounts} && exec setpriv --reuid={user} --regid={user} --init-groups --no-new-privs -- "$@"',
            "isolated"]


def hand_over(work: Path, statement: dict, proof: bytes | None = None) -> Path:
    """A fresh directory holding statement.json (and proof.bin), readable by the sandbox user."""
    directory = work / uuid.uuid4().hex
    directory.mkdir(mode=0o755)
    (directory / "statement.json").write_text(json.dumps(statement))
    if proof is not None:
        (directory / "proof.bin").write_bytes(proof)
    for path in directory.iterdir():
        path.chmod(0o644)
    return directory


def rejection_cases(statements: list[dict], proofs: list[bytes], rng: random.Random,
                    mutants: int) -> dict[str, tuple[dict, bytes]]:
    """Every (public statement, proof) pair the verifier must reject."""
    true0, data = statements[0], proofs[0]
    cases: dict[str, tuple[dict, bytes]] = {}
    for name, variant in false_variants(true0).items():
        cases[f"false statement: {name}"] = (public(variant), data)
    cases["another statement's proof"] = (public(true0), proofs[1])

    def bad(name: str, blob: bytes) -> None:
        cases[name] = (public(true0), blob)

    bad("empty proof", b"")
    bad("one zero byte", b"\x00")
    bad("one byte appended", data + b"\x00")
    if data:
        bad("random bytes of the same length", rng.randbytes(len(data)))
        bad("first half", data[: len(data) // 2])
        bad("last byte dropped", data[:-1])
        for _ in range(mutants):
            bit = rng.randrange(len(data) * 8)
            blob = bytearray(data)
            blob[bit // 8] ^= 1 << (bit % 8)
            bad(f"bit {bit} flipped", bytes(blob))
    return cases


def conjectured_claims(ledger: dict) -> list[str]:
    """Claims whose bound rests on the proximity-gap conjecture: the board counts none of them."""
    return [claim.get("id") for claim in ledger.get("claims", [])
            if "conjectured-capacity" in (claim.get("regime"), claim.get("inputs", {}).get("regime"))]


def ledger_report(entry_dir: Path, entry: dict) -> dict | None:
    """The entry's sheet, added up; a term counts as reviewed only through results/reviews.jsonl."""
    if not entry.get("ledger"):
        return None
    try:
        ledger = json.loads((entry_dir / entry["ledger"]).read_text())
        return {**evaluate(ledger, load_reviews()), "conjectured_claims": conjectured_claims(ledger)}
    except (OSError, ValueError, LedgerError, KeyError) as error:
        return {"error": str(error)}


def judge(entry_dir: Path, runs: int, n: int | None, mutants: int, seed: int | None,
          security: Path | None = None, official: bool = False, isolate: str | None = None,
          workdir: Path | None = None) -> dict:
    """Judge an entry. With `security` (a settings file the entry reads through
    PROVEN_SECURITY), the run is a measurement of the entry at those settings, never a
    contribution: the ledger gate does not apply and the result is not listed. `official` marks a
    run on the evaluator host, the only place the verify-time cap applies. `isolate` names the
    sandbox user every entrant command runs as; `workdir` holds the judge's files (outside /tmp,
    which each isolated command replaces with its own)."""
    entry = json.loads((entry_dir / "entry.json").read_text())
    env = dict(os.environ)
    if isolate:
        env.update({"HOME": "/nonexistent", "TMPDIR": "/tmp"})
    if security is not None:
        env["PROVEN_SECURITY"] = str(security)
    prefix = isolated(isolate) if isolate else []
    board = BOARD[entry["statement"]]
    n = n or board["n"]
    with tempfile.TemporaryDirectory(prefix="oracle-", dir=workdir) as tmp:
        work = Path(tmp)
        work.chmod(0o755)

        def call(template: list[str], statement: dict, proof: bytes | None, stdout: str,
                 timeout: float) -> dict:
            directory = hand_over(work, statement, proof)
            try:
                argv = command(template, directory / "statement.json", directory / "proof.bin")
                return run(prefix + argv, entry_dir, stdout, timeout, env)
            finally:
                shutil.rmtree(directory)

        statements, proofs, proved, verified = [], [], [], []
        for _ in range(runs):
            statement = GENERATORS[entry["statement"]](n)
            proof_path = work / f"{uuid.uuid4().hex}.bin"
            # The witness statement exists only while the prover runs.
            proved.append(call(entry["prove"], statement, None, str(proof_path), PROVE_TIMEOUT))
            proof = proof_path.read_bytes()
            proof_path.unlink()
            verified.append(call(entry["verify"], public(statement), proof, os.devnull, VERIFY_TIMEOUT))
            statements.append(statement)
            proofs.append(proof)
        complete = all(result["exit"] == 0 and not result["timed_out"] for result in proved) \
            and all(outcome(result) == "ACCEPT" for result in verified)
        cases = rejection_cases(statements, proofs, random.Random(seed), mutants) if complete else {}
        rejections = {name: outcome(call(entry["verify"], view, blob, os.devnull, VERIFY_TIMEOUT))
                      for name, (view, blob) in cases.items()}
        sizes = [len(proof) for proof in proofs]
    verify_seconds = statistics.median(result["seconds"] for result in verified)
    report = ledger_report(entry_dir, entry)
    claimed = (report or {}).get("claimed_bits")
    proven = (report or {}).get("proven_bits")
    verify_within_cap = verify_seconds <= board["max_verify_seconds"]
    gates = {
        "completeness": complete,
        "rejection": bool(rejections) and all(value == "REJECT" for value in rejections.values()),
        "caps": max(sizes) <= board["max_proof_bytes"] and (verify_within_cap or not official),
        "ledger": claimed is not None and claimed >= board["floor_bits"]
        and not report.get("missing_components") and not report.get("conjectured_claims"),
    }
    settings = None if security is None else json.loads(security.read_text())
    if settings is not None:
        gates["ledger"] = None
        gates["caps"] = None
    passed = all(value for value in gates.values() if value is not None)
    tier = "reviewed" if proven is not None and proven >= board["floor_bits"] else "claimed"
    if settings is not None:
        listing = "measurement only: " + settings.get("regime", "custom settings")
    else:
        listing = f"{tier}, after a verifier read" if passed else "not listed"
    return {
        "entry": entry["name"], "team": entry.get("team") or entry["name"],
        "system": entry.get("system"), "statement": entry["statement"],
        "n": n, "runs": runs,
        "measured_on": f"{platform.system()} {platform.machine()}, {os.cpu_count()} cpus",
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prove_seconds": [round(result["seconds"], 3) for result in proved],
        "prove_seconds_median": round(statistics.median(result["seconds"] for result in proved), 3),
        "peak_bytes_max": max(result["peak_bytes"] for result in proved),
        "proof_bytes_max": max(sizes),
        "verify_seconds_median": round(verify_seconds, 4),
        "verify_cap_seconds": board["max_verify_seconds"], "verify_within_cap": verify_within_cap,
        "claimed_bits": claimed, "claimed_is_partial": (report or {}).get("claimed_is_partial"),
        "proven_bits": proven, "ledger_error": (report or {}).get("error"),
        "gates": gates,
        "rejection_cases": len(rejections),
        "rejection_failures": {name: value for name, value in rejections.items() if value != "REJECT"},
        "prove_errors": [result["stderr"] for result in proved if result["exit"] != 0][:1],
        "verdict": "PASS" if passed else "FAIL",
        "listing": listing,
        "settings": settings,
        "official": official,
        "credits": entry.get("credits"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("entry", type=Path, help="entry directory holding entry.json")
    parser.add_argument("--runs", type=int, default=3, help="fresh statements to prove (at least 2)")
    parser.add_argument("--n", type=int, help="chain length (default: the board's)")
    parser.add_argument("--mutants", type=int, default=20, help="bit-flipped proofs to try")
    parser.add_argument("--seed", type=int, help="seed for the mutations (statements are always fresh)")
    parser.add_argument("--results", type=Path, help="append the result to this JSON-lines file")
    parser.add_argument("--security", type=Path,
                        help="measure the entry at these settings (read through PROVEN_SECURITY); "
                             "the run is a measurement, not a contribution")
    parser.add_argument("--official", action="store_true",
                        help="an evaluator-host run: the verify-time cap applies and the result is "
                             "marked official")
    parser.add_argument("--isolate", metavar="USER",
                        help="run every entrant command as USER, with no network and private "
                             "temporary directories (Linux, as root)")
    parser.add_argument("--workdir", type=Path, help="where the judge keeps its files")
    args = parser.parse_args(argv)
    if args.runs < 2:
        parser.error("--runs must be at least 2: the battery swaps proofs between statements")
    result = judge(args.entry.resolve(), args.runs, args.n, args.mutants, args.seed,
                   args.security.resolve() if args.security else None, args.official,
                   args.isolate, args.workdir)
    if args.results:
        args.results.parent.mkdir(parents=True, exist_ok=True)
        with args.results.open("a") as handle:
            handle.write(json.dumps(result, sort_keys=True) + "\n")
    print(json.dumps(result, indent=1))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
