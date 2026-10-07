"""One shared frontier per task: the first official pass sets it; only a faster official pass
moves it, and every move is recorded with credits."""
import json
import tempfile
import unittest
from pathlib import Path

from proven.frontier import FrontierError, promote, retire


def row(entry, seconds, official=True, verdict="PASS", gates=None, settings=None, n=16384):
    return {"entry": entry, "team": entry, "statement": "blake2s-chain-v0", "verdict": verdict,
            "prove_seconds_median": seconds, "peak_bytes_max": 1, "proof_bytes_max": 1,
            "verify_seconds_median": 0.1, "claimed_bits": 98.0, "proven_bits": None, "n": n,
            "runs": 3, "measured_on": "host", "date": "2026-10-07", "system": "x",
            "official": official, "gates": gates or {}, "settings": settings}


def read(results, *entries, verdict="OK"):
    with (results.parent / "reads.jsonl").open("a") as handle:
        for entry in entries:
            handle.write(json.dumps({"entry": entry, "verdict": verdict}) + "\n")


class FrontierTest(unittest.TestCase):
    def test_first_pass_sets_it_and_only_a_faster_official_pass_moves_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results, frontiers = Path(tmp) / "oracle.jsonl", Path(tmp) / "frontiers"
            results.write_text("\n".join(json.dumps(r) for r in [
                row("first", 5.0), row("slower", 5.2), row("laptop", 1.0, official=False),
                row("faster", 4.0)]) + "\n")
            read(results, "first", "slower", "laptop", "faster")
            first = promote("first", results=results, frontiers=frontiers)
            self.assertIsNone(first["previous"])
            with self.assertRaises(FrontierError):
                promote("slower", results=results, frontiers=frontiers)
            with self.assertRaises(FrontierError):
                promote("laptop", results=results, frontiers=frontiers)
            moved = promote("faster", note="less hashing", results=results, frontiers=frontiers)
            self.assertEqual(moved["previous"]["entry"], "first")
            self.assertEqual(moved["credits"][0]["role"], "implementer")
            history = (frontiers / "history.jsonl").read_text().splitlines()
            self.assertEqual(len(history), 2)

    def test_a_frontier_that_no_longer_passes_yields_to_a_passing_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results, frontiers = Path(tmp) / "oracle.jsonl", Path(tmp) / "frontiers"
            rows = [row("first", 3.0), row("fixed", 3.1)]
            results.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            read(results, "first", "fixed")
            promote("first", results=results, frontiers=frontiers)
            with self.assertRaises(FrontierError):
                promote("fixed", results=results, frontiers=frontiers)
            rows.append(row("first", 3.0, verdict="FAIL", gates={"ledger": False, "caps": True}))
            results.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            moved = promote("fixed", results=results, frontiers=frontiers)
            self.assertEqual(moved["previous"]["entry"], "first")
            self.assertIn("no longer passes the judge (ledger)", moved["note"])

    def test_retire_empties_a_frontier_only_when_its_sheet_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results, frontiers = Path(tmp) / "oracle.jsonl", Path(tmp) / "frontiers"
            rows = [row("stwo-circuit-chain", 3.7), row("stwo-grind-chain", 3.7)]
            results.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            read(results, "stwo-circuit-chain", "stwo-grind-chain")
            promote("stwo-grind-chain", results=results, frontiers=frontiers)
            with self.assertRaises(FrontierError):
                retire("blake2s-chain-v0", frontiers)
            with self.assertRaises(FrontierError):
                promote("stwo-circuit-chain", results=results, frontiers=frontiers)
            # A frontier set before its entry's sheet was corrected.
            stale = json.loads((frontiers / "blake2s-chain-v0.json").read_text())
            stale["entry"] = "stwo-circuit-chain"
            (frontiers / "blake2s-chain-v0.json").write_text(json.dumps(stale))
            record = retire("blake2s-chain-v0", frontiers)
            self.assertIn("below the 96-bit floor", record["note"])
            self.assertFalse((frontiers / "blake2s-chain-v0.json").exists())

    def test_no_read_a_forgery_or_a_short_run_keeps_an_entry_off_the_frontier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results, frontiers = Path(tmp) / "oracle.jsonl", Path(tmp) / "frontiers"
            rows = [row("unread", 3.0), row("forged", 3.0), row("short", 3.0, n=1024)]
            results.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            read(results, "forged", "short")
            (Path(tmp) / "forgeries.jsonl").write_text(json.dumps({"entry": "forged", "verdict": "FORGERY"}) + "\n")
            for entry in ("unread", "forged", "short"):
                with self.assertRaises(FrontierError):
                    promote(entry, results=results, frontiers=frontiers)

    def test_a_measurement_at_other_settings_is_never_promoted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results, frontiers = Path(tmp) / "oracle.jsonl", Path(tmp) / "frontiers"
            results.write_text(json.dumps(row("measured", 1.0, settings={"n_queries": 35})) + "\n")
            with self.assertRaises(FrontierError):
                promote("measured", results=results, frontiers=frontiers)


if __name__ == "__main__":
    unittest.main()
