"""Baseline ledger at the pinned Stwo profile, regime by regime, in the whitepaper's own currency:
queries plus a proof-of-work schedule (at most 26 bits per round, the whitepaper's cap).

Profile (live frontier sheet reference/ledger-grind-chain.json, lean/PINNED.md):
  M31, p = 2^31 - 1; challenges in QM31, |F| = p^4 (2^124); rate 1/4; |D0| = n = 2^23; degree < k = 2^21;
  363 columns batched by powers of one coefficient; 16-ary folds over layers 2^23, 2^19, ..., 2^3;
  26 bits of proof of work before the query positions; composition degree 2^22; floor 96 bits.
Sources per formula are in the docstrings. Pure Python.
"""
from __future__ import annotations

import json
import math
import sys

P = 2**31 - 1
LOG_F = 4 * math.log2(P)
N = 2**23
K = 2**21
RHO = K / N
RHO_MINUS = (K - 1) / N
M_BATCH = 363
FOLD_LAYERS = [2**e for e in (23, 19, 15, 11, 7, 3)]
POW_QUERY = 26
POW_CAP = 26
FLOOR = 96
OOD_DEGREE_LOG2 = 22
ROUND_MARGIN = 4   # each ground round aims at 2^-(floor + 4); nine rounds then sum below 2^-96
FIXED = {"C-AIR": -117.7521, "C-COMMIT-BINDING": -124.0, "C-HASH": -127.2}
lg = math.log2


def a1(rho: float) -> float:
    """DKT 2026/2056 eq. (31): the first-order agreement curve."""
    rho_c = 11 - 3 * math.sqrt(13)
    if rho >= rho_c:
        return (3 * rho + 2 * math.sqrt(rho * (5 - rho) * (2 - rho))) / (8 - rho)
    target, lo, hi = math.sqrt(rho / 2), 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if mid * mid * (mid + 3) < target else (lo, mid)
    return math.sqrt(rho / 2) * (1 + lo)


def gabizon_alpha(rho: float) -> float:
    """Gabizon 2026/2048, Lemma 4.5: a concrete agreement below sqrt(rho) with a positive bracket."""
    return math.sqrt(rho) * (1 - (1 - math.sqrt(rho)) ** 2 / 8)


def johnson_list(a: float) -> float:
    """S-two whitepaper (53): combinatorial Johnson list bound (a - rho) / (a^2 - rho)."""
    return (a - RHO) / (a * a - RHO)


def gs_factor(a: float) -> tuple[int, float, float]:
    """S-two whitepaper (73)-(74) and Theorem 19: m, l_GS and the factor l_GS (2 l_GS^4/3 (1-delta) + 1)."""
    eta = a - math.sqrt(RHO)
    m = max(math.ceil(math.sqrt(RHO) / (2 * eta)), 3)
    l_gs = (m + 0.5) / math.sqrt(RHO)
    return m, l_gs, l_gs * (2 * l_gs**4 / 3 * RHO + 1)


def dkt_johnson_factor(a: float) -> tuple[int, float]:
    """DKT Theorem 5.12: per-line exceptional count < (8/3) n t^3 / rho^-, so the factor on n is (8/3) t^3 / rho^-."""
    eta0 = a - math.sqrt(RHO_MINUS)
    m = max(math.ceil(math.sqrt(RHO_MINUS) / (2 * eta0)), 3)
    t = m + 0.5
    return m, 8 / 3 * t**3 / RHO_MINUS


def ledger(name: str, a: float, line_factor_log2: float | None, line_power: int, list_size: float, note: str) -> dict:
    """Per-line exceptional count = 2^line_factor_log2 * |D|^line_power. Grinding per round up to the cap;
    queries are the fewest that bring the union bound to the floor. list_size multiplies the OOD term."""
    rounds: dict[str, float] = {}
    if line_factor_log2 is not None:
        rounds["C-BATCHING"] = lg(M_BATCH - 1) + line_factor_log2 + line_power * lg(N) - LOG_F
        for i, size in enumerate(FOLD_LAYERS):
            rounds[f"C-FRI-FOLD-{i}"] = lg(15) + line_factor_log2 + line_power * lg(size) - LOG_F
        rounds["C-OOD"] = lg(list_size) + OOD_DEGREE_LOG2 - LOG_F
    # grind each round to 2^-(floor+2) if it can, else the cap
    grind = {r: min(POW_CAP, max(0.0, math.ceil(e + FLOOR + ROUND_MARGIN))) for r, e in rounds.items()}
    ground = {r: e - grind[r] for r, e in rounds.items()}
    fixed_total = sum(2.0**v for v in list(ground.values()) + list(FIXED.values()))
    result = {"regime": name, "agreement": round(a, 4), "bits_per_query": round(-lg(a), 3), "note": note,
              "grind_bits": {r: int(g) for r, g in grind.items() if g}, "rounds_log2": {r: round(v, 1) for r, v in ground.items()}}
    if fixed_total >= 2.0**-FLOOR:
        result.update(queries=None, claimed_bits=round(-lg(fixed_total), 1), meets_floor=False,
                      blocking=[r for r, v in ground.items() if v > -FLOOR - ROUND_MARGIN])
        return result
    s = 1
    while -lg(fixed_total + a**s * 2.0**-POW_QUERY) < FLOOR:
        s += 1
    result.update(queries=s, claimed_bits=round(-lg(fixed_total + a**s * 2.0**-POW_QUERY), 2), meets_floor=True)
    return result


def best_over(name: str, make, grid) -> dict:
    best = None
    for a in grid:
        led = make(a)
        if led["meets_floor"] and (best is None or led["queries"] < best["queries"]):
            best = led
    return best or {"regime": name, "meets_floor": False, "note": "no agreement on the grid meets the floor"}


def main() -> None:
    out = {"profile": {"p": P, "log2_F": round(LOG_F, 2), "n": N, "k": K, "rate": RHO, "M": M_BATCH, "fold_layers": FOLD_LAYERS,
                       "pow_query": POW_QUERY, "pow_cap_per_round": POW_CAP, "floor": FLOOR}}
    out["thresholds"] = {f"rate 1/{int(1/r)}": {"UD": round((1 + r) / 2, 4), "Johnson": round(math.sqrt(r), 4),
                                               "first_order_a1": round(a1(r), 4), "gabizon_alpha": round(gabizon_alpha(r), 4), "capacity": r,
                                               "bits_per_query": {"UD": round(-lg((1 + r) / 2), 3), "Johnson": round(-lg(math.sqrt(r)), 3),
                                                                  "first order": round(-lg(a1(r)), 3), "capacity": round(-lg(r), 3)}}
                         for r in (1 / 2, 1 / 4, 1 / 8, 1 / 16)}
    L: list[dict] = []
    L.append(ledger("unique decoding, today's frontier shape", (1 + RHO) / 2, 0.0, 1, 1,
                    "BCIKS20 Theorem 4.1 / whitepaper Remark 20: line count |D|, list 1 (grind as computed, frontier uses 8 at batching)"))
    grid = [0.5 + i / 1000 for i in range(1, 300)]
    L.append(best_over("Johnson, whitepaper Theorem 19 constants",
                       lambda a: ledger("Johnson, whitepaper Theorem 19 constants", a, lg(gs_factor(a)[2]), 1, johnson_list(a),
                                        f"eta = {a-0.5:.3f}, m = {gs_factor(a)[0]}, l_GS = {gs_factor(a)[1]:.0f}, list (53) = {johnson_list(a):.0f}"), grid))
    L.append(best_over("Johnson, DKT Theorem 5.12 constants",
                       lambda a: ledger("Johnson, DKT Theorem 5.12 constants", a, lg(dkt_johnson_factor(a)[1]), 1, johnson_list(a),
                                        f"eta0 = {a-math.sqrt(RHO_MINUS):.3f}, m = {dkt_johnson_factor(a)[0]}, list (53) = {johnson_list(a):.0f}"), grid))
    a = RHO + 0.24
    L.append(ledger("first order, DKT Theorem 5.13 as stated (n^2)", a, lg(1_325_775), 2, 307 * N,
                    "E <= 1,325,775 n^2 per line, list <= 307 n; p > k - 1 holds (2^31 - 1 > 2^21)"))
    L.append(ledger("first order, if the line count were 1,325,775 n", a, lg(1_325_775), 1, 307 * N,
                    "the flagship's shape with DKT's constant; list still 307 n"))
    L.append(ledger("first order, line count 2^21 n and list 2^8 n", a, 21.0, 1, 2**8 * N,
                    "what fits: constants a proof must reach at this profile"))
    L.append(ledger("conjectured capacity, today's settings", RHO, None, 1, 1, "2 bits per query if the conjecture holds; algebraic terms as the UD sheet"))
    out["ledgers"] = L
    budget = LOG_F - (FLOOR + ROUND_MARGIN) + POW_CAP - lg(M_BATCH - 1)   # per-line count the batching round can carry
    frontier = {}
    for name, fn in (("DKT 5.12", lambda a: lg(dkt_johnson_factor(a)[1]) + lg(N)), ("whitepaper Thm 19", lambda a: lg(gs_factor(a)[2]) + lg(N))):
        a_star = next(a for a in (0.5 + i / 10000 for i in range(1, 3000)) if fn(a) <= budget)
        frontier[name] = {"a_star": round(a_star, 4), "queries_for_70_bits": math.ceil(70 / -lg(a_star) - 1e-9), "line_count_log2": round(fn(a_star), 1)}
    out["frontier_under_budget"] = {"per_line_budget_log2": round(budget, 1), **frontier}
    out["needed_at_profile"] = {
        "per_line_count_log2_max_with_26_bit_batching_grind": round(budget, 1),
        "linear_constant_log2_max": round(budget - lg(N), 1),
        "list_size_log2_max_with_26_bit_ood_grind": round(LOG_F - (FLOOR + ROUND_MARGIN) + POW_CAP - OOD_DEGREE_LOG2, 1),
        "known_first_order_line_count_log2": round(lg(1_325_775) + 2 * lg(N), 1),
        "abf_lemma_4_16_floor_log2": round(lg(math.floor(0.51 * N)), 1),
        "queries_for_70_bits": {f"a={a:.4f}": math.ceil(70 / -lg(a) - 1e-9) for a in (0.625, 0.5, 0.49, 0.485, 0.475, a1(RHO) + 1e-9, 0.25)},
    }
    json.dump(out, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
