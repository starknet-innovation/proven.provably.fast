"""Intake: fetch a submitted entry at an exact commit, build it once, judge it, record the result.

    python3 -m proven.intake https://github.com/team/entry COMMIT --runs 3 [--entry DIR]

The repository holds entry.json at its root, or in the directory given by --entry: name, team,
system, statement, an optional "build" command (a list of arguments) run once at the repository's
root, and the "prove" and "verify" commands, run in the entry's directory. This runs whatever the
build says, so untrusted entries belong on the evaluator host inside its sandbox (no network,
their own cgroup), never on a laptop.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from .oracle import judge
from .statements import BOARD

ROOT = Path(__file__).resolve().parents[1]
BUILD_TIMEOUT = 3600


class IntakeError(Exception):
    pass


def fetch(url: str, commit: str, dest: Path) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise IntakeError("pass the full 40-character commit")
    if not (url.startswith("https://") or url.startswith("file://")):
        raise IntakeError("the repository must be an https URL")
    if dest.exists():
        raise IntakeError(f"{dest} already exists")
    subprocess.run(["git", "clone", "--quiet", "--no-checkout", url, str(dest)], check=True)
    subprocess.run(["git", "-C", str(dest), "checkout", "--quiet", "--detach", commit], check=True)
    head = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()
    if head != commit:
        raise IntakeError(f"{url} at {commit} resolved to {head}: pass the full commit")
    for path in dest.rglob("*"):
        if path.is_symlink() and not inside(dest, path.resolve()):
            raise IntakeError(f"{path.relative_to(dest)} links outside the repository")


def inside(root: Path, path: Path) -> bool:
    root = root.resolve()
    return path == root or root in path.parents


def strings(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(part, str) for part in value)


def load_entry(entry_dir: Path) -> dict:
    entry = json.loads((entry_dir / "entry.json").read_text())
    missing = [key for key in ("name", "statement", "prove", "verify") if key not in entry]
    if missing:
        raise IntakeError(f"entry.json lacks {', '.join(missing)}")
    if entry["statement"] not in BOARD:
        raise IntakeError(f"unknown statement {entry['statement']!r}")
    if not all(strings(entry.get(key)) for key in ("prove", "verify")) or \
            ("build" in entry and not strings(entry["build"])):
        raise IntakeError("prove, verify and build must be lists of strings")
    return entry


def entry_dir_of(dest: Path, entry: str | None) -> Path:
    """The entry's directory inside the repository; refuses paths that leave it."""
    entry_dir = (dest / (entry or ".")).resolve()
    if not inside(dest, entry_dir):
        raise IntakeError(f"entry {entry!r} is outside the repository")
    return entry_dir


def build_and_judge(dest: Path, runs: int, entry: str | None = None,
                    official: bool = False) -> dict:
    """Build an entry already on disk once, then judge it. The host runner calls this inside its
    sandbox (`--local`), after fetching the entry outside it."""
    entry_dir = entry_dir_of(dest, entry)
    spec = load_entry(entry_dir)
    if spec.get("build"):
        subprocess.run(spec["build"], cwd=dest, check=True, timeout=BUILD_TIMEOUT)
    return judge(entry_dir, runs, None, 20, None, official=official)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("url", nargs="?")
    parser.add_argument("commit", nargs="?", help="the full commit hash to judge")
    parser.add_argument("--local", type=Path, help="judge an entry already on disk; print only")
    parser.add_argument("--entry", help="the entry's directory inside the repository")
    parser.add_argument("--official", action="store_true", help="an evaluator-host run")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--workdir", type=Path, default=ROOT / "entries" / "submitted")
    parser.add_argument("--results", type=Path, default=ROOT / "results" / "oracle.jsonl")
    args = parser.parse_args(argv)
    if args.local:
        try:
            result = build_and_judge(args.local.resolve(), args.runs, args.entry, args.official)
        except IntakeError as error:
            raise SystemExit(str(error)) from error
        print(json.dumps(result, sort_keys=True))
        return 0
    if not (args.url and args.commit):
        parser.error("give URL and COMMIT, or --local DIR")
    dest = args.workdir / args.commit
    args.workdir.mkdir(parents=True, exist_ok=True)
    try:
        fetch(args.url, args.commit, dest)
        result = build_and_judge(dest, args.runs, args.entry, args.official)
    except IntakeError as error:
        raise SystemExit(str(error)) from error
    result["source"] = {"repository": args.url, "commit": args.commit, "entry": args.entry}
    with args.results.open("a") as handle:
        handle.write(json.dumps(result, sort_keys=True) + "\n")
    print(json.dumps(result, indent=1))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
