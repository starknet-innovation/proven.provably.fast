"""Soundness calculator for proven.provably.fast ledgers (v0).

A ledger lists claims: each bounds one source of soundness error for one proof system.
The calculator computes each claim's error from its formula and inputs, never from a
number the entrant declares, then combines the claims that count:

- total error is the union bound over every claim;
- claimed bits = -log2(total error), whatever the claims' statuses (a provisional board);
- proven bits exist only when every claim is LEAN-CHECKED or REVIEWED. Leaving an
  unreviewed claim out of the sum would shrink the total and overstate security, so a
  single unreviewed claim leaves the ledger with no proven bits at all. The judge and the board
  count a status only when results/reviews.jsonl records it for that exact claim (its digest
  covers every field but the status and reviewers), so an entrant cannot mark its own terms.

Proof of work does not add an error term: it multiplies the error of the claim it
protects by 2^-pow_bits, so a grinding claim names the claim it applies to.

A `not-applicable` claim states why a required component does not exist for this entry
(a single proof has no recursion term). It adds nothing and is reviewed like any claim.

A `pending` claim names a required term whose bound is not derived yet. It satisfies the
component checklist, adds nothing to any sum, and leaves the ledger with no proven bits;
claimed bits are then marked partial.

Standard library only; deterministic; no network. Usage:

    python3 -m proven.calculator reference/ledger-grind-chain.json
    python3 -m proven.calculator --queries 96 --pow 27 --rate-log2 3
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

SCHEMA = "provenfast-ledger/0"
COUNTED = ("LEAN-CHECKED", "REVIEWED")
STATUSES = ("LEAN-CHECKED", "REVIEWED", "CITED-UNCHECKED", "CONJECTURED")
REGIMES = ("conjectured-capacity", "johnson", "unique-decoding")
# Every ledger must account for these (proposal, Appendix C).
REQUIRED_COMPONENTS = (
    "commitment.binding", "proximity", "ood", "batching", "air.constraints",
    "fiat-shamir", "field", "hash", "recursion",
)


class LedgerError(ValueError):
    pass


def bits_per_query(rate_log2: int, regime: str, eta_log2: float | None = None) -> float:
    """Soundness bits one FRI query buys at rate 2^-rate_log2.

    unique decoding: delta = (1 - rho) / 2, an accepted far word survives a query with
    probability (1 + rho) / 2; Johnson: (sqrt(rho) + eta); conjectured up to capacity:
    (rho + eta). eta is the proximity slack, 2^eta_log2, zero when omitted.
    """
    if rate_log2 < 1:
        raise LedgerError("rate_log2 must be at least 1")
    rho = 2.0 ** -rate_log2
    eta = 0.0 if eta_log2 is None else 2.0 ** eta_log2
    if regime == "unique-decoding":
        survive = (1 + rho) / 2
    elif regime == "johnson":
        survive = math.sqrt(rho) + eta
    elif regime == "conjectured-capacity":
        survive = rho + eta
    else:
        raise LedgerError(f"unknown regime {regime!r}")
    if not 0 < survive < 1:
        raise LedgerError("per-query survival probability must be in (0, 1)")
    return -math.log2(survive)


def queries_needed(target_bits: float, rate_log2: int, regime: str, pow_bits: float = 0,
                   eta_log2: float | None = None) -> int:
    """Fewest queries whose bits plus proof of work reach target_bits (per-query terms only)."""
    return max(0, math.ceil((target_bits - pow_bits) / bits_per_query(rate_log2, regime, eta_log2)
                            - 1e-12))


def claim_error_log2(claim: dict[str, Any]) -> float:
    """log2 of one claim's error from its formula; grinding claims return 0 (a modifier)."""
    formula, inputs = claim.get("formula"), claim.get("inputs", {})
    if formula == "fri.queries":
        return -inputs["n_queries"] * bits_per_query(inputs["rate_log2"], inputs["regime"],
                                                      inputs.get("eta_log2"))
    if formula == "schwartz-zippel":
        # A nonzero polynomial of degree d vanishes at a random point of F with
        # probability at most d / |F|.
        return inputs["degree_log2"] - inputs["field_bits"]
    if formula == "fixed":
        # A bound computed outside the calculator; its derivation must be attached for review.
        return float(inputs["error_log2"])
    if formula in ("grinding.pow", "pending", "not-applicable"):
        return 0.0
    raise LedgerError(f"claim {claim.get('id')}: unknown formula {formula!r}")


REVIEWS = Path(__file__).resolve().parents[1] / "results" / "reviews.jsonl"


def claim_digest(claim: dict[str, Any]) -> str:
    """The claim's identity for review: every field but its status and reviewers."""
    body = {key: value for key, value in claim.items() if key not in ("status", "reviewers")}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def load_reviews(path: Path = REVIEWS) -> dict[str, str]:
    """Recorded reviews: claim digest -> REVIEWED or LEAN-CHECKED."""
    if not path.exists():
        return {}
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return {row["claim_digest"]: row["status"] for row in rows if row.get("status") in COUNTED}


def evaluate(ledger: dict[str, Any], reviews: dict[str, str] | None = None) -> dict[str, Any]:
    """Per-claim errors, proven and claimed bits, and what the ledger still lacks. With
    `reviews`, a claim's status counts only as recorded there; otherwise as the sheet states it."""
    if ledger.get("schema") != SCHEMA:
        raise LedgerError(f"schema must be {SCHEMA}")
    claims = ledger.get("claims", [])
    if reviews is not None:
        claims = [{**claim, "status": reviews.get(claim_digest(claim), "CITED-UNCHECKED")
                   if claim.get("status") != "CONJECTURED" else "CONJECTURED"} for claim in claims]
    ids = [claim.get("id") for claim in claims]
    if len(set(ids)) != len(ids) or not all(ids):
        raise LedgerError("every claim needs a unique id")
    by_id = {claim["id"]: claim for claim in claims}
    errors: dict[str, float] = {}
    for claim in claims:
        if claim.get("status") not in STATUSES:
            raise LedgerError(f"claim {claim['id']}: status must be one of {', '.join(STATUSES)}")
        if claim.get("formula") not in ("grinding.pow", "pending", "not-applicable"):
            errors[claim["id"]] = claim_error_log2(claim)
    grinding: list[dict[str, Any]] = []
    for claim in claims:
        if claim.get("formula") != "grinding.pow":
            continue
        target = claim.get("applies_to")
        if target not in errors:
            raise LedgerError(f"grinding claim {claim['id']} must name a non-grinding claim")
        bits = float(claim["inputs"]["pow_bits"])
        errors[target] -= bits
        grinding.append({"id": claim["id"], "applies_to": target, "pow_bits": bits,
                         "status": claim["status"]})

    def bits_over(selected: list[str]) -> float | None:
        if not selected:
            return None
        total = sum(2.0 ** errors[claim_id] for claim_id in selected)
        return -math.log2(total)

    uncounted = [claim["id"] for claim in claims if claim["status"] not in COUNTED]
    pending = [claim["id"] for claim in claims if claim.get("formula") == "pending"]
    present = {claim.get("component", "").split(":")[0] for claim in claims}
    missing = [name for name in REQUIRED_COMPONENTS if name not in present]
    order = {status: index for index, status in enumerate(STATUSES)}
    weakest = max((claim["status"] for claim in claims), key=order.__getitem__, default=None)
    floor = ledger.get("floor_bits")
    claimed = bits_over(list(errors))
    proven = claimed if not uncounted and not pending else None
    return {
        "entry": ledger.get("entry"),
        "floor_bits": floor,
        "claims": [{"id": claim_id, "component": by_id[claim_id].get("component"),
                    "status": by_id[claim_id]["status"], "error_log2": round(errors[claim_id], 3)}
                   for claim_id in errors],
        "grinding": grinding,
        "proven_bits": None if proven is None else round(proven, 3),
        "claimed_bits": None if claimed is None else round(claimed, 3),
        "claimed_is_partial": bool(pending),
        "pending_claims": pending,
        "uncounted_claims": uncounted,
        "weakest_status": weakest,
        "missing_components": missing,
        "meets_floor": bool(proven is not None and floor is not None and proven >= floor
                            and not missing),
    }


def regime_table(target_bits: float, rate_log2: int, pow_bits: float) -> list[dict[str, Any]]:
    return [{"regime": regime, "bits_per_query": round(bits_per_query(rate_log2, regime), 3),
             "queries": queries_needed(target_bits, rate_log2, regime, pow_bits)}
            for regime in REGIMES]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("ledger", nargs="?", type=Path)
    parser.add_argument("--queries", type=float, metavar="TARGET_BITS",
                        help="print the queries each regime needs for TARGET_BITS")
    parser.add_argument("--pow", type=float, default=0.0, help="proof-of-work bits (with --queries)")
    parser.add_argument("--rate-log2", type=int, default=3, help="log2 of the blowup (with --queries)")
    args = parser.parse_args(argv)
    if args.queries is not None:
        print(json.dumps(regime_table(args.queries, args.rate_log2, args.pow), indent=2))
        return 0
    if args.ledger is None:
        parser.error("give a ledger file or --queries")
    try:
        report = evaluate(json.loads(args.ledger.read_text()))
    except (LedgerError, KeyError, TypeError) as error:
        print(f"ledger refused: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["meets_floor"] else 1


if __name__ == "__main__":
    sys.exit(main())
