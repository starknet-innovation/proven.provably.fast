from __future__ import annotations

import json
import unittest
from pathlib import Path

from proven import calculator

ROOT = Path(__file__).resolve().parents[1]


def ledger(*claims: dict, floor: float = 96) -> dict:
    return {"schema": calculator.SCHEMA, "entry": "test", "floor_bits": floor, "claims": list(claims)}


def fri(claim_id: str, rate_log2: int, n: int, regime: str, status: str = "REVIEWED",
        component: str = "proximity") -> dict:
    return {"id": claim_id, "component": component, "formula": "fri.queries", "status": status,
            "inputs": {"rate_log2": rate_log2, "n_queries": n, "regime": regime}}


def pow_claim(claim_id: str, target: str, bits: float, status: str = "REVIEWED") -> dict:
    return {"id": claim_id, "component": "fiat-shamir", "formula": "grinding.pow",
            "applies_to": target, "inputs": {"pow_bits": bits}, "status": status}


def fixed(claim_id: str, component: str, error_log2: float, status: str = "REVIEWED") -> dict:
    return {"id": claim_id, "component": component, "formula": "fixed",
            "inputs": {"error_log2": error_log2}, "status": status}


COMPLETE = [fixed(f"C-{name}", name, -140) for name in calculator.REQUIRED_COMPONENTS
            if name not in ("proximity", "fiat-shamir")]


class CalculatorTests(unittest.TestCase):
    def test_today_and_the_proposal_query_counts_come_out_of_the_formulas(self) -> None:
        cases = {(3, 27): {"conjectured-capacity": 23, "johnson": 46, "unique-decoding": 84},
                 (2, 26): {"conjectured-capacity": 35, "johnson": 70, "unique-decoding": 104}}
        for (rate_log2, pow_bits), expected in cases.items():
            for regime, queries in expected.items():
                with self.subTest(rate_log2=rate_log2, regime=regime):
                    self.assertEqual(calculator.queries_needed(96, rate_log2, regime, pow_bits), queries)
        self.assertAlmostEqual(calculator.bits_per_query(3, "unique-decoding"), 0.830, places=3)
        self.assertAlmostEqual(calculator.bits_per_query(2, "unique-decoding"), 0.678, places=3)

    def test_grinding_multiplies_the_claim_it_names_and_terms_add_by_union_bound(self) -> None:
        report = calculator.evaluate(ledger(fri("Q", 3, 84, "unique-decoding"), pow_claim("P", "Q", 27),
                                            *COMPLETE))
        query = next(claim for claim in report["claims"] if claim["id"] == "Q")
        self.assertAlmostEqual(query["error_log2"], -96.726, places=3)
        self.assertTrue(report["meets_floor"])
        # Two equal terms lose one bit to the union bound.
        two = calculator.evaluate(ledger(fixed("A", "proximity", -100), fixed("B", "hash", -100)))
        self.assertAlmostEqual(two["claimed_bits"], 99.0, places=6)

    def test_one_unreviewed_claim_leaves_no_proven_bits(self) -> None:
        report = calculator.evaluate(ledger(fri("Q", 3, 84, "unique-decoding"),
                                            pow_claim("P", "Q", 27, status="CITED-UNCHECKED"), *COMPLETE))
        self.assertIsNone(report["proven_bits"])
        self.assertEqual(report["uncounted_claims"], ["P"])
        self.assertFalse(report["meets_floor"])
        # Leaving the unreviewed term out would have overstated security; claimed bits keep it.
        self.assertAlmostEqual(report["claimed_bits"], 96.726, places=2)

    def test_the_reference_sheets_stop_below_the_floor(self) -> None:
        for task in ("chain", "matmul", "recursion"):
            report = calculator.evaluate(json.loads((ROOT / f"reference/ledger-{task}.json").read_text()))
            self.assertEqual(report["missing_components"], [])
            self.assertLess(report["claimed_bits"], 96)
            self.assertIsNone(report["proven_bits"])

    def test_missing_components_block_the_floor(self) -> None:
        report = calculator.evaluate(ledger(fri("Q", 3, 120, "unique-decoding"), pow_claim("P", "Q", 27)))
        self.assertGreater(report["proven_bits"], 96)
        self.assertFalse(report["meets_floor"])
        self.assertIn("hash", report["missing_components"])

    def test_malformed_ledgers_are_refused(self) -> None:
        bad = [
            {"schema": "other", "claims": []},
            ledger(fixed("A", "hash", -100), fixed("A", "hash", -100)),
            ledger(pow_claim("P", "missing", 20)),
            ledger({"id": "X", "component": "hash", "formula": "magic", "status": "REVIEWED"}),
            ledger({**fixed("A", "hash", -100), "status": "TRUST-ME"}),
        ]
        for case in bad:
            with self.subTest(case=str(case)[:60]), self.assertRaises(calculator.LedgerError):
                calculator.evaluate(case)

    def test_a_pending_term_fills_the_checklist_but_leaves_no_proven_bits(self) -> None:
        pending = {"id": "C-OOD", "component": "ood", "formula": "pending", "inputs": {},
                   "status": "REVIEWED"}
        others = [claim for claim in COMPLETE if claim["component"] != "ood"]
        report = calculator.evaluate(ledger(fri("Q", 3, 120, "unique-decoding"), pow_claim("P", "Q", 27),
                                            pending, *others))
        self.assertEqual(report["missing_components"], [])
        self.assertIsNone(report["proven_bits"])
        self.assertTrue(report["claimed_is_partial"])
        self.assertFalse(report["meets_floor"])

    def test_the_batching_grind_and_plonky3_sheets_clear_the_floor_in_claimed_bits(self) -> None:
        paths = [ROOT / f"reference/ledger-grind-{task}.json" for task in ("chain", "matmul", "recursion")]
        for path in [*paths, ROOT / "entries/plonky3-chain/ledger.json"]:
            report = calculator.evaluate(json.loads(path.read_text()))
            self.assertEqual(report["missing_components"], [])
            self.assertGreaterEqual(report["claimed_bits"], 96)
            self.assertIsNone(report["proven_bits"])

    def test_schwartz_zippel_bounds_degree_over_field(self) -> None:
        claim = {"id": "S", "component": "ood", "formula": "schwartz-zippel", "status": "REVIEWED",
                 "inputs": {"degree_log2": 24, "field_bits": 124}}
        self.assertEqual(calculator.claim_error_log2(claim), -100)


if __name__ == "__main__":
    unittest.main()
