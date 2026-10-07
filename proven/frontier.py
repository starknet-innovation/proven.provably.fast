"""One shared frontier per task: the cheapest contribution so far at conjecture-free settings,
measured on the evaluator host. Everyone builds on it; moving it is credited.

    python3 -m proven.frontier promote stwo-circuit-chain --note "why it is faster"
    python3 -m proven.frontier retire blake2s-chain-v0      # when its entry's sheet stops passing
    python3 -m proven.frontier show

`promote` takes the entry's latest official result (judged on the evaluator host at the task's
size, three runs or more, verdict PASS) from results/oracle.jsonl, requires a recorded verifier
read and no forgery, refuses unless its median prove time beats the current frontier's by at
least 1%, writes frontiers/<statement>.json, and appends the move to frontiers/history.jsonl
with the entry's credits. The first promotion on a task sets its starting point, and a frontier
whose own latest official result no longer passes (its sheet was corrected below the floor, say)
yields to any entry that passes, whatever its speed. `retire` empties a task's frontier when its
entry's current sheet no longer reaches the floor, and records why; the next entry to pass on the
host sets the task's starting point again.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "oracle.jsonl"
FRONTIERS = ROOT / "frontiers"
MIN_GAIN = 0.01


class FrontierError(ValueError):
    pass


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def latest_official_row(entry: str, results: Path) -> dict | None:
    rows = [row for row in load_rows(results) if row["entry"] == entry and row.get("official")
            and not row.get("settings")]
    return rows[-1] if rows else None


def latest_official(entry: str, results: Path) -> dict:
    row = latest_official_row(entry, results)
    if row is None:
        raise FrontierError(f"{entry} has no official result (judged on the evaluator host)")
    if row["verdict"] != "PASS":
        raise FrontierError(f"{entry}'s latest official result did not pass the judge")
    return row


def entry_dir_of(entry: str) -> Path | None:
    for path in (ROOT / "entries").rglob("entry.json"):
        if json.loads(path.read_text()).get("name") == entry:
            return path.parent
    return None


def sheet_report(entry: str) -> tuple[dict, dict] | None:
    """The entry's spec and its current sheet's report, or None for an entry not in this tree."""
    from .oracle import ledger_report
    directory = entry_dir_of(entry)
    if directory is None:
        return None
    spec = json.loads((directory / "entry.json").read_text())
    return spec, ledger_report(directory, spec) or {}


def sheet_failure(entry: str) -> str | None:
    """Why the entry's current sheet misses the floor, or None if it reaches it (or is not here)."""
    from .statements import BOARD
    found = sheet_report(entry)
    if found is None:
        return None
    spec, report = found
    claimed = report.get("claimed_bits")
    floor = BOARD[spec["statement"]]["floor_bits"]
    if claimed is None or claimed < floor or report.get("missing_components") or report.get("conjectured_claims"):
        return f"its sheet reads {claimed} claimed bits, below the {floor}-bit floor"
    return None


def retire(statement: str, frontiers: Path = FRONTIERS) -> dict:
    path = frontiers / f"{statement}.json"
    if not path.exists():
        raise FrontierError(f"{statement} has no frontier")
    current = json.loads(path.read_text())
    reason = sheet_failure(current["entry"])
    if reason is None:
        raise FrontierError(f"{current['entry']}'s sheet still reaches the floor")
    record = {"statement": statement, "entry": None, "retired": current["entry"],
              "note": f"{current['entry']} no longer passes: {reason}",
              "moved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "previous": {"entry": current["entry"], "prove_seconds": current["prove_seconds"],
                           "moved_at": current["moved_at"]}}
    path.unlink()
    with (frontiers / "history.jsonl").open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def credits_of(entry: str, row: dict | None = None) -> list[dict]:
    if row and row.get("credits"):
        return row["credits"]
    for path in (ROOT / "entries").rglob("entry.json"):
        data = json.loads(path.read_text())
        if data.get("name") == entry:
            return data.get("credits", [{"role": "implementer", "who": data.get("team") or entry}])
    return [{"role": "implementer", "who": entry}]


def checked(entry: str, results: Path) -> str | None:
    """Why the entry may not move a frontier yet: no verifier read, or a recorded forgery."""
    reads = load_rows(results.parent / "reads.jsonl")
    forgeries = load_rows(results.parent / "forgeries.jsonl")
    if any(row["entry"] == entry and row.get("verdict") == "FORGERY" for row in forgeries):
        return "a forgery against it is on record"
    latest = [row["verdict"] for row in reads if row["entry"] == entry]
    if not latest or latest[-1] != "OK":
        return "no verifier read is on record"
    return None


def promote(entry: str, note: str = "", results: Path = RESULTS, frontiers: Path = FRONTIERS) -> dict:
    from .statements import BOARD
    row = latest_official(entry, results)
    if row["n"] != BOARD[row["statement"]]["n"] or row.get("runs", 0) < 3:
        raise FrontierError(f"{entry}'s official result is not at the task's size with three runs")
    blocked = checked(entry, results)
    if blocked is not None:
        raise FrontierError(f"{entry} cannot move the frontier: {blocked}")
    own_sheet = sheet_failure(entry)
    if own_sheet is not None:
        raise FrontierError(f"{entry} cannot move the frontier: {own_sheet}")
    statement = row["statement"]
    path = frontiers / f"{statement}.json"
    current = json.loads(path.read_text()) if path.exists() else None
    standing = None if current is None else latest_official_row(current["entry"], results)
    stale_sheet = None if current is None else sheet_failure(current["entry"])
    if stale_sheet is not None:
        note = note or f"{current['entry']} no longer passes: {stale_sheet}"
    elif standing is not None and standing["verdict"] != "PASS":
        failed = ", ".join(gate for gate, ok in standing.get("gates", {}).items() if ok is False)
        note = note or f"{current['entry']} no longer passes the judge ({failed})"
    elif current is not None:
        bound = current["prove_seconds"] * (1 - MIN_GAIN)
        if row["prove_seconds_median"] >= bound:
            raise FrontierError(
                f"{entry} proves in {row['prove_seconds_median']} s; the frontier is "
                f"{current['entry']} at {current['prove_seconds']} s, so it needs under {bound:.3f} s")
    record = {
        "statement": statement, "entry": entry, "team": row.get("team") or entry,
        "system": row.get("system"), "n": row["n"],
        "prove_seconds": row["prove_seconds_median"], "peak_bytes": row["peak_bytes_max"],
        "proof_bytes": row["proof_bytes_max"], "verify_seconds": row["verify_seconds_median"],
        "claimed_bits": row.get("claimed_bits"), "proven_bits": row.get("proven_bits"),
        "measured_on": row["measured_on"], "judged_at": row["date"],
        "source": row.get("source"), "credits": credits_of(entry, row), "note": note,
        "moved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "previous": None if current is None else {
            "entry": current["entry"], "prove_seconds": current["prove_seconds"],
            "moved_at": current["moved_at"]},
    }
    frontiers.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1) + "\n")
    with (frontiers / "history.jsonl").open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def show(frontiers: Path = FRONTIERS) -> dict[str, dict]:
    return {path.stem: json.loads(path.read_text())
            for path in sorted(frontiers.glob("*.json"))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    promote_parser = commands.add_parser("promote", help="move a task's frontier to an entry")
    promote_parser.add_argument("entry")
    promote_parser.add_argument("--note", default="", help="what the contribution changed")
    promote_parser.add_argument("--results", type=Path, default=RESULTS)
    retire_parser = commands.add_parser("retire", help="empty a task's frontier whose sheet fails")
    retire_parser.add_argument("statement")
    commands.add_parser("show", help="print every task's frontier")
    args = parser.parse_args(argv)
    if args.command == "show":
        for statement, record in show().items():
            print(f"{statement}: {record['entry']} {record['prove_seconds']} s, "
                  f"{record['peak_bytes'] / 1e9:.2f} GB, {record['proof_bytes'] // 1000} KB, "
                  f"moved {record['moved_at']}")
        return 0
    try:
        record = retire(args.statement) if args.command == "retire" else promote(
            args.entry, args.note, args.results)
    except FrontierError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 1
    print(json.dumps(record, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
