"""The board, built from the judge's records; the site reads results/board.json.

Per statement: the frontier (the cheapest contribution so far at conjecture-free settings), the
history of how it moved and who moved it, and every contribution's latest official result (judged
on the evaluator host) with its status, newest first. No ranking: the frontier is shared and each
move is credited.

Statuses: reviewed (passed the judge, verifier read, no forgery, proven bits at the floor);
claimed (the same with claimed bits only, shown grey until review); waiting for a verifier read;
failed the judge (including a pass whose entry's sheet was later corrected below the floor: sheets
are read again at every build, measurements are not); disqualified by a forgery.

    python3 -m proven.board                       # writes results/board.json
    python3 -m proven.board read ENTRY --reader NAME --verdict OK --note "..."
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .frontier import FRONTIERS, load_rows, sheet_failure, sheet_report, show
from .statements import BOARD

RESULTS = Path(__file__).resolve().parents[1] / "results"


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def status(result: dict, forged: set[str], read: set[str]) -> str:
    if result["entry"] in forged:
        return "disqualified by a forgery"
    if result["verdict"] != "PASS":
        return "failed the judge"
    if sheet_failure(result["entry"]):
        return "failed the judge: its sheet was corrected below the floor"
    if result["entry"] not in read:
        return "waiting for a verifier read"
    floor = BOARD[result["statement"]]["floor_bits"]
    proven = result.get("proven_bits")
    return "reviewed" if proven is not None and proven >= floor else "claimed"


def current_bits(row: dict) -> dict:
    """Bits from the entry's current sheet when it is in this tree, else as judged."""
    found = sheet_report(row["entry"])
    report = found[1] if found else row
    return {"claimed_bits": report.get("claimed_bits"), "proven_bits": report.get("proven_bits")}


def waiting(judged: set[str]) -> list[dict]:
    """Entries in this tree that the host has not judged yet, with their current sheets."""
    rows = []
    for path in sorted((RESULTS.parent / "entries").rglob("entry.json")):
        spec = json.loads(path.read_text())
        if spec["name"] in judged or "fakes" in path.parts:
            continue
        found = sheet_report(spec["name"])
        rows.append({"entry": spec["name"], "statement": spec["statement"], "team": spec.get("team"),
                     "system": spec.get("system"), "credits": spec.get("credits"),
                     "claimed_bits": (found[1] if found else {}).get("claimed_bits")})
    return rows


def build(results: list[dict], forgeries: list[dict], reads: list[dict]) -> dict:
    forged = {row["entry"] for row in forgeries if row["verdict"] == "FORGERY"}
    latest_read = {row["entry"]: row["verdict"] for row in reads}
    read = {entry for entry, verdict in latest_read.items() if verdict == "OK"}
    results = [row for row in results if row.get("official")]
    measurements = [row for row in results if row.get("settings")]
    results = [row for row in results if not row.get("settings")]
    # One row per entry and source: a submission that reuses a name cannot replace another's record.
    latest = {(row["statement"], row["entry"], (row.get("source") or {}).get("repository")): row
              for row in results}
    conjectured = {}
    for row in measurements:
        if row["verdict"] == "PASS":
            conjectured[row["statement"]] = {
                "entry": row["entry"], "settings": row["settings"],
                "prove_seconds": row["prove_seconds_median"], "peak_bytes": row["peak_bytes_max"],
                "proof_bytes": row["proof_bytes_max"], "verify_seconds": row["verify_seconds_median"],
                "date": row["date"]}
    statements: dict[str, list[dict]] = {}
    for (statement, entry, repository), row in latest.items():
        statements.setdefault(statement, []).append({
            "entry": entry, "team": row.get("team") or entry, "system": row.get("system"),
            "repository": repository, "credits": row.get("credits"),
            "status": status(row, forged, read),
            "prove_seconds": row["prove_seconds_median"], "peak_bytes": row["peak_bytes_max"],
            "proof_bytes": row["proof_bytes_max"], "verify_seconds": row["verify_seconds_median"],
            **current_bits(row),
            "n": row["n"], "measured_on": row["measured_on"], "date": row["date"]})
    for rows in statements.values():
        rows.sort(key=lambda r: r["date"], reverse=True)
    history = load_rows(FRONTIERS / "history.jsonl")
    return {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "frontiers": show(),
            "conjectured": conjectured,
            "waiting": waiting({row["entry"] for row in results}),
            "history": {statement: [row for row in history if row["statement"] == statement]
                        for statement in statements},
            "contributions": statements}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--results", type=Path, default=RESULTS)
    commands = parser.add_subparsers(dest="command")
    read_parser = commands.add_parser("read", help="record a verifier read")
    read_parser.add_argument("entry")
    read_parser.add_argument("--reader", required=True)
    read_parser.add_argument("--verdict", choices=["OK", "PROBLEM"], required=True)
    read_parser.add_argument("--note", default="")
    args = parser.parse_args(argv)
    if args.command == "read":
        record = {"entry": args.entry, "reader": args.reader, "verdict": args.verdict,
                  "note": args.note, "date": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        with (args.results / "reads.jsonl").open("a") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    board = build(load(args.results / "oracle.jsonl"), load(args.results / "forgeries.jsonl"),
                  load(args.results / "reads.jsonl"))
    (args.results / "board.json").write_text(json.dumps(board, indent=1) + "\n")
    for statement, rows in board["contributions"].items():
        frontier = board["frontiers"].get(statement)
        print(statement, "| frontier:", f"{frontier['entry']} {frontier['prove_seconds']} s" if frontier else "none yet")
        for row in rows:
            print(f"  {row['entry']:<28} {row['status']:<28} {row['prove_seconds']:>8.2f} s  {row['date'][:10]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
