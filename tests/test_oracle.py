"""The oracle on the three fake entries: two must fail, and the MAC fake must pass every
automatic gate (which is why listing needs a verifier read)."""
import unittest
from pathlib import Path
from unittest import mock

from proven.oracle import judge
from proven.statements import BOARD, blake2s_chain, chain_statement, check, false_variants

FAKES = Path(__file__).resolve().parents[1] / "entries" / "fakes"


class StatementTest(unittest.TestCase):
    def test_a_fresh_statement_checks_and_its_false_variants_do_not(self) -> None:
        statement = chain_statement(64)
        self.assertTrue(check(statement))
        self.assertTrue(all(not check(variant) for variant in false_variants(statement).values()))

    def test_one_step_is_one_standard_blake2s(self) -> None:
        import hashlib
        self.assertEqual(blake2s_chain(bytes(32), 1), hashlib.blake2s(bytes(32)).digest())


class MatmulStatementTest(unittest.TestCase):
    def test_the_product_checks_and_its_false_variants_do_not(self) -> None:
        from proven.statements import matmul_statement
        statement = matmul_statement(8)
        self.assertTrue(check(statement))
        self.assertTrue(all(not check(v) for v in false_variants(statement).values()))


class LedgerGateTest(unittest.TestCase):
    def test_a_claim_under_the_proximity_conjecture_is_flagged(self) -> None:
        from proven.oracle import conjectured_claims
        ledger = {"claims": [
            {"id": "FRI", "inputs": {"regime": "conjectured-capacity", "n_queries": 35, "rate_log2": 2}},
            {"id": "UD", "inputs": {"regime": "unique-decoding", "n_queries": 104, "rate_log2": 2}}]}
        self.assertEqual(conjectured_claims(ledger), ["FRI"])


class OracleTest(unittest.TestCase):
    def verdict(self, name: str) -> dict:
        return judge(FAKES / name, runs=2, n=64, mutants=4, seed=1)

    def test_an_accept_all_verifier_fails_rejection(self) -> None:
        result = self.verdict("accept-all")
        self.assertEqual(result["verdict"], "FAIL")
        self.assertFalse(result["gates"]["rejection"])

    def test_a_verifier_that_ignores_the_proof_fails_rejection(self) -> None:
        result = self.verdict("recompute")
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("another statement's proof", result["rejection_failures"])

    def test_a_mac_passes_every_automatic_gate(self) -> None:
        result = self.verdict("mac")
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["listing"], "claimed, after a verifier read")

    def test_a_verifier_sees_only_its_statement_and_proof(self) -> None:
        import json
        import shutil
        import tempfile
        verifier = '''import json, os, sys
statement, proof = sys.argv[1], sys.argv[2]
here = os.path.dirname(statement)
alone = sorted(os.listdir(here)) == ["proof.bin", "statement.json"]
no_siblings = os.listdir(os.path.dirname(here)) == [os.path.basename(here)]
names = os.path.basename(statement) == "statement.json" and os.path.basename(proof) == "proof.bin"
no_witness = not any(key.startswith("witness") for key in json.load(open(statement)))
sys.exit(0 if alone and no_siblings and names and no_witness else 3)
'''
        with tempfile.TemporaryDirectory() as tmp:
            entry = Path(tmp) / "entry"
            entry.mkdir()
            (entry / "verify.py").write_text(verifier)
            (entry / "prove.py").write_text("import sys; sys.stdout.buffer.write(b'proof')\n")
            shutil.copy(FAKES.parents[1] / "reference/ledger-grind-chain.json", entry / "ledger.json")
            (entry / "entry.json").write_text(json.dumps({
                "name": "peek", "statement": "blake2s-chain-v0", "ledger": "ledger.json",
                "prove": ["python3", "prove.py", "{statement}"],
                "verify": ["python3", "verify.py", "{statement}", "{proof}"]}))
            result = judge(entry, runs=2, n=64, mutants=2, seed=1, workdir=Path(tmp))
        self.assertTrue(result["gates"]["completeness"])
        self.assertFalse(result["gates"]["rejection"])

    def test_the_verify_time_cap_gates_only_official_runs(self) -> None:
        with mock.patch.dict(BOARD["blake2s-chain-v0"], {"max_verify_seconds": 0.0}):
            local = judge(FAKES / "mac", runs=2, n=64, mutants=2, seed=1)
            official = judge(FAKES / "mac", runs=2, n=64, mutants=2, seed=1, official=True)
        self.assertTrue(local["gates"]["caps"])
        self.assertFalse(local["verify_within_cap"])
        self.assertFalse(local["official"])
        self.assertFalse(official["gates"]["caps"])
        self.assertTrue(official["official"])


if __name__ == "__main__":
    unittest.main()
