"""The forgery lane: anyone may attack a listed entry. A forgery is a proof the entry's own
verifier accepts for a false statement; the judge confirms it and the entry is disqualified.

    python3 -m proven.forgery submit ENTRY STATEMENT PROOF --by NAME [--rung BITS --work "2^20 tries"]
    python3 -m proven.forgery challenge stwo-verify-v0 --n 1024
    python3 -m proven.forgery rung ENTRY --bits 32

Entries publish their prover and verifier, so an entry whose soundness rests on anything the
attacker holds (a key in the prover, a hardcoded secret) falls here without a human read.

For the hash chain any false statement counts: the judge checks it natively. A recursion
statement cannot be decided without a preimage, so a forgery there must hit a challenge the
judge issued: a random y that no one knows a seed for.

The ladder: `rung` derives a weak setting from the entry's own ledger (no proof of work, just
enough FRI queries for BITS bits under the ledger's regime) and the entry runs its own code with
it through PROVEN_SECURITY. A forgery at a rung does not disqualify; it is recorded with the
attacker's reported work, and work far below 2^BITS means the bound is wrong. A rung exercises
the query term only: field size, Fiat-Shamir and hash terms are untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

from .calculator import bits_per_query
from .oracle import VERIFY_TIMEOUT, command, outcome, run
from .statements import STWO_VERIFY, check, public

RESULTS = Path(__file__).resolve().parents[1] / "results"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def issued(results: Path = RESULTS) -> set[tuple[str, int, str]]:
    path = results / "challenges.jsonl"
    if not path.exists():
        return set()
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return {(row["statement"], row["n"], row["y"]) for row in rows}


def challenge(kind: str, n: int, results: Path = RESULTS) -> dict:
    """A recursion target: a random y with no known seed."""
    if kind != STWO_VERIFY:
        raise ValueError("only recursion statements need issued challenges")
    statement = {"statement": kind, "n": n, "y": secrets.token_bytes(32).hex()}
    _append(results / "challenges.jsonl", {**statement, "date": _now()})
    return statement


def rung(entry_dir: Path, bits: int, results: Path = RESULTS) -> Path:
    """A weak setting for the entry: no proof of work and the fewest queries that give BITS bits
    under the regime and rate of the entry's own FRI claim."""
    entry = json.loads((entry_dir / "entry.json").read_text())
    ledger = json.loads((entry_dir / entry["ledger"]).read_text())
    fri = next(claim for claim in ledger["claims"] if claim.get("formula") == "fri.queries")
    inputs = fri["inputs"]
    per_query = bits_per_query(inputs["rate_log2"], inputs["regime"], inputs.get("eta_log2"))
    setting = {"bits": bits, "n_queries": math.ceil(bits / per_query), "pow_bits": 0,
               "exercises": f"{fri['id']}: the FRI query term only", "entry": entry["name"]}
    path = results / "rungs" / f"{entry['name']}-{bits}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(setting, indent=1) + "\n")
    return path


def submit(entry_dir: Path, statement_path: Path, proof_path: Path, by: str,
           results: Path = RESULTS, rung_bits: int | None = None, work: str = "") -> dict:
    entry = json.loads((entry_dir / "entry.json").read_text())
    statement = public(json.loads(statement_path.read_text()))
    if statement.get("statement") != entry["statement"]:
        raise ValueError(f"the entry proves {entry['statement']}, not {statement.get('statement')}")
    truth = check(statement)
    if truth is True:
        return {"verdict": "NOT_A_FORGERY", "reason": "the statement is true"}
    if truth is None and (statement["statement"], statement["n"], statement["y"]) not in issued(results):
        return {"verdict": "NOT_A_FORGERY",
                "reason": "the judge cannot decide this statement; attack an issued challenge"}
    view = statement_path.with_suffix(".public.json")
    view.write_text(json.dumps(statement))
    env = None
    if rung_bits is not None:
        env = {"PROVEN_SECURITY": str(rung(entry_dir, rung_bits, results))}
    verdict = outcome(run(command(entry["verify"], view, proof_path), entry_dir, os.devnull,
                          VERIFY_TIMEOUT, env))
    accepted = verdict == "ACCEPT"
    record = {"entry": entry["name"], "statement": statement, "by": by, "date": _now(),
              "proof_sha256": hashlib.sha256(proof_path.read_bytes()).hexdigest(),
              "rung_bits": rung_bits, "reported_work": work,
              "verdict": ("RUNG_FORGERY" if rung_bits is not None else "FORGERY") if accepted
              else "REJECTED"}
    if accepted:
        _append(results / ("rungs.jsonl" if rung_bits is not None else "forgeries.jsonl"), record)
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    submit_parser = commands.add_parser("submit", help="submit a forgery against an entry")
    submit_parser.add_argument("entry", type=Path)
    submit_parser.add_argument("statement", type=Path, help="a false statement (JSON)")
    submit_parser.add_argument("proof", type=Path)
    submit_parser.add_argument("--by", required=True, help="who found it, for the credit")
    submit_parser.add_argument("--rung", type=int, help="attack the weak setting at this many bits")
    submit_parser.add_argument("--work", default="", help="your attack's work, e.g. 2^20 tries")
    rung_parser = commands.add_parser("rung", help="write the weak setting for an entry")
    rung_parser.add_argument("entry", type=Path)
    rung_parser.add_argument("--bits", type=int, required=True, choices=[24, 32, 40])
    challenge_parser = commands.add_parser("challenge", help="issue a recursion target")
    challenge_parser.add_argument("statement", choices=[STWO_VERIFY])
    challenge_parser.add_argument("--n", type=int, required=True)
    args = parser.parse_args(argv)
    if args.command == "challenge":
        print(json.dumps(challenge(args.statement, args.n)))
        return 0
    if args.command == "rung":
        print(rung(args.entry.resolve(), args.bits).read_text(), end="")
        return 0
    record = submit(args.entry.resolve(), args.statement.resolve(), args.proof.resolve(), args.by,
                    rung_bits=args.rung, work=args.work)
    print(json.dumps(record, indent=1))
    return 0 if record["verdict"] in ("FORGERY", "RUNG_FORGERY") else 1


if __name__ == "__main__":
    sys.exit(main())
