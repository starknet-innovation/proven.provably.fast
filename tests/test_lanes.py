"""The forgery lane and the board."""
import hashlib
import hmac
import json
import re
import tempfile
import unittest
from pathlib import Path

from proven.board import build
from proven.forgery import challenge, submit
from proven.statements import chain_statement, false_variants

ENTRIES = Path(__file__).resolve().parents[1] / "entries"


class ForgeryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, name: str, data) -> Path:
        path = self.root / name
        path.write_bytes(data) if isinstance(data, bytes) else path.write_text(json.dumps(data))
        return path

    def test_the_mac_fake_falls_to_its_own_published_prover(self) -> None:
        # The key sits in the public prover; MAC a false statement with it.
        source = (ENTRIES / "fakes/mac/fake.py").read_text()
        key = re.search(r'KEY = b"([^"]+)"', source).group(1).encode()
        false = false_variants(chain_statement(64))["wrong-y-first-bit"]
        tag = hmac.new(key, f'{false["n"]}:{false["seed"]}:{false["y"]}'.encode(), hashlib.sha256).digest()
        record = submit(ENTRIES / "fakes/mac", self.write("false.json", false),
                        self.write("tag.bin", tag), "test", results=self.root)
        self.assertEqual(record["verdict"], "FORGERY")
        self.assertTrue((self.root / "forgeries.jsonl").exists())

    def test_a_true_statement_is_not_a_forgery(self) -> None:
        record = submit(ENTRIES / "fakes/mac", self.write("true.json", chain_statement(64)),
                        self.write("p.bin", b"x"), "test", results=self.root)
        self.assertEqual(record["verdict"], "NOT_A_FORGERY")

    def test_a_recursion_target_must_be_an_issued_challenge(self) -> None:
        loose = {"statement": "stwo-verify-v0", "n": 1024, "y": "00" * 32}
        record = submit(ENTRIES / "stwo-recursion", self.write("loose.json", loose),
                        self.write("p.bin", b"x"), "test", results=self.root)
        self.assertEqual(record["verdict"], "NOT_A_FORGERY")
        issued = challenge("stwo-verify-v0", 1024, results=self.root)
        self.assertIn("y", issued)


class BoardTest(unittest.TestCase):
    def row(self, entry, statement, seconds, verdict="PASS", team=None, date="2026-10-06",
            official=True):
        return {"entry": entry, "team": team or entry, "statement": statement, "verdict": verdict,
                "prove_seconds_median": seconds, "peak_bytes_max": 1, "proof_bytes_max": 1,
                "verify_seconds_median": 0.1, "claimed_bits": 98.0, "proven_bits": None,
                "n": 1, "measured_on": "test", "date": date, "system": "x", "official": official}

    def test_statuses_newest_first_and_no_ranking(self) -> None:
        results = [self.row("slow-chain", "blake2s-chain-v0", 5.0, date="2026-10-05"),
                   self.row("fast-chain", "blake2s-chain-v0", 2.5, date="2026-10-06"),
                   self.row("cheat", "blake2s-chain-v0", 0.1, date="2026-10-07"),
                   self.row("laptop-run", "blake2s-chain-v0", 0.01, date="2026-10-08", official=False)]
        reads = [{"entry": name, "verdict": "OK"} for name in ("slow-chain", "fast-chain", "cheat")]
        forgeries = [{"entry": "cheat", "verdict": "FORGERY"}]
        board = build(results, forgeries, reads)
        chain = board["contributions"]["blake2s-chain-v0"]
        self.assertEqual([r["entry"] for r in chain], ["cheat", "fast-chain", "slow-chain"])
        self.assertEqual([r["status"] for r in chain], ["disqualified by a forgery", "claimed", "claimed"])
        self.assertNotIn("set", board)
        self.assertIn("frontiers", board)

    def test_a_pass_whose_sheet_was_corrected_below_the_floor_shows_as_failed(self) -> None:
        # The Stwo reference passed at judging time; its sheet now reads 92.4 claimed bits.
        board = build([self.row("stwo-circuit-chain", "blake2s-chain-v0", 3.7)], [],
                      [{"entry": "stwo-circuit-chain", "verdict": "OK"}])
        row = board["contributions"]["blake2s-chain-v0"][0]
        self.assertTrue(row["status"].startswith("failed the judge: its sheet"))
        self.assertLess(row["claimed_bits"], 96)


class IntakeTest(unittest.TestCase):
    def test_an_entry_fetched_at_a_commit_is_judged_and_recorded(self) -> None:
        import shutil
        import subprocess
        from proven.intake import main
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            shutil.copytree(ENTRIES / "fakes/mac", repo)
            shutil.copy(ENTRIES.parent / "reference/ledger-independent-batching.json", repo / "ledger.json")
            entry = json.loads((repo / "entry.json").read_text())
            entry.update({"ledger": "ledger.json", "team": "intake-test"})
            (repo / "entry.json").write_text(json.dumps(entry))
            run = lambda *args: subprocess.run(["git", "-C", str(repo), *args], check=True,
                                               capture_output=True, text=True).stdout.strip()
            run("init", "-q")
            run("add", "-A")
            run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "entry")
            commit = run("rev-parse", "HEAD")
            results = Path(tmp) / "oracle.jsonl"
            code = main([f"file://{repo}", commit, "--runs", "2", "--workdir", str(Path(tmp) / "work"),
                         "--results", str(results)])
            self.assertEqual(code, 0)
            record = json.loads(results.read_text().splitlines()[-1])
            self.assertEqual(record["source"]["commit"], commit)
            self.assertEqual(record["team"], "intake-test")

    def test_an_entry_in_a_subdirectory_is_judged_and_cannot_leave_the_repository(self) -> None:
        import shutil
        from proven.intake import IntakeError, build_and_judge
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            shutil.copytree(ENTRIES / "fakes/mac", repo / "entries" / "mac")
            shutil.copy(ENTRIES.parent / "reference/ledger-independent-batching.json",
                        repo / "entries" / "mac" / "ledger.json")
            entry = json.loads((repo / "entries/mac/entry.json").read_text())
            entry["ledger"] = "ledger.json"
            (repo / "entries/mac/entry.json").write_text(json.dumps(entry))
            result = build_and_judge(repo, 2, "entries/mac")
            self.assertEqual(result["verdict"], "PASS")
            with self.assertRaises(IntakeError):
                build_and_judge(repo, 2, "../outside")
