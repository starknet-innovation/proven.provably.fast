#!/usr/bin/env python3
"""Certify bad challenges from the definition, over a prime field. Standard library only.

A line is a pair of received words f, g on a domain of n distinct points of F_p. A challenge z is
bad at agreement A if some polynomial P of degree below k agrees with f + z g on at least A points
S, while f and g are not both interpolable by polynomials of degree below k on the whole of S.

Usage: python3 certify.py instance.json
The instance lists p, k, A, domain, f, g and challenges. Each challenge gives z and a witness: at
most k points (indices) that determine P; more would allow a degree k or above. The checker rebuilds P, finds the full agreement set, checks
|S| >= A, checks the joint interpolability on S, and reports distinct bad z. Exit code 1 if any
listed challenge fails.

Cost: interpolation is O(k^2) through the master product prod (X - x_j) and one synthetic
division per point, and a witness shared by many challenges is interpolated once (P = F + z G,
with F and G the interpolants of f and g on it), so an instance with n = 256 and hundreds of
challenges certifies in seconds (2026-10-14, a participant's suggestion).
"""
import json, sys


def inv(a, p):
    return pow(a, p - 2, p)


def master_product(xs, p):
    """Coefficients (low to high) of prod (X - x) over the points."""
    poly = [1]
    for x in xs:
        new = [0] * (len(poly) + 1)
        for t, a in enumerate(poly):
            new[t + 1] = (new[t + 1] + a) % p
            new[t] = (new[t] - a * x) % p
        poly = new
    return poly


def divide_by_root(poly, x, p):
    """Coefficients of poly / (X - x) by synthetic division, for a poly that vanishes at x."""
    k = len(poly) - 1
    quotient = [0] * k
    carry = 0
    for t in range(k, 0, -1):
        carry = (poly[t] + carry * x) % p
        quotient[t - 1] = carry
    return quotient


def lagrange_basis(xs, p):
    """For each point, the numerator prod_{j != i} (X - x_j) and the inverse of its value at x_i."""
    master = master_product(xs, p)
    basis = []
    for x in xs:
        numerator = divide_by_root(master, x, p)
        basis.append((numerator, inv(evaluate(numerator, x, p), p)))
    return basis


def combine(basis, ys, p):
    """The interpolant's coefficients from a Lagrange basis and the values at its points."""
    coeffs = [0] * len(basis)
    for (numerator, scale), y in zip(basis, ys):
        f = y * scale % p
        if f == 0:
            continue
        for t, a in enumerate(numerator):
            coeffs[t] = (coeffs[t] + a * f) % p
    return coeffs


def interpolate(xs, ys, p):
    """Coefficients (low to high) of the polynomial of degree < len(xs) through the points."""
    return combine(lagrange_basis(xs, p), ys, p)


def evaluate(coeffs, x, p):
    v = 0
    for a in reversed(coeffs):
        v = (v * x + a) % p
    return v


def interpolable(points, values, k, p):
    """Does some polynomial of degree < k take these values on these points?"""
    if len(points) <= k:
        return True
    c = interpolate(points[:k], values[:k], p)
    return all(evaluate(c, x, p) == y for x, y in zip(points[k:], values[k:]))


def check(inst):
    p, k, A = inst["p"], inst["k"], inst["A"]
    dom, f, g = inst["domain"], inst["f"], inst["g"]
    n = len(dom)
    assert len(set(dom)) == n and len(f) == n and len(g) == n, "domain must be distinct, words of length n"
    bad, failures = set(), []
    # Per witness: F and G through f and g on it, evaluated on the whole domain. For a challenge z
    # the polynomial through f + z g on the witness is F + z G, interpolation being linear.
    witnesses = {}
    # Per agreement set: whether f and g are each interpolable on it, shared between challenges.
    explained = {}
    for ch in inst["challenges"]:
        z, witness = ch["z"] % p, ch["witness"]
        if not 0 < len(witness) <= k or len(set(witness)) != len(witness):
            failures.append((z, "the witness must be at most k distinct indices"))
            continue
        key = tuple(witness)
        if key not in witnesses:
            basis = lagrange_basis([dom[i] for i in witness], p)
            F = combine(basis, [f[i] for i in witness], p)
            G = combine(basis, [g[i] for i in witness], p)
            witnesses[key] = ([evaluate(F, x, p) for x in dom], [evaluate(G, x, p) for x in dom])
        F_dom, G_dom = witnesses[key]
        S = [i for i in range(n) if (F_dom[i] + z * G_dom[i]) % p == (f[i] + z * g[i]) % p]
        if len(S) < A:
            failures.append((z, "agreement %d < %d" % (len(S), A)))
            continue
        if len(witness) == k:
            # S holds the witness, and a polynomial of degree < k through k of its points is F
            # (or G) itself: f and g are interpolable on S exactly when F and G agree with them there.
            joint = all(F_dom[i] == f[i] and G_dom[i] == g[i] for i in S)
        else:
            agreement = tuple(S)
            if agreement not in explained:
                pts = [dom[i] for i in S]
                explained[agreement] = (interpolable(pts, [f[i] for i in S], k, p)
                                        and interpolable(pts, [g[i] for i in S], k, p))
            joint = explained[agreement]
        if joint:
            failures.append((z, "explained: f and g are jointly interpolable on S"))
            continue
        bad.add(z)
    return bad, failures


if __name__ == "__main__":
    inst = json.load(open(sys.argv[1]))
    bad, failures = check(inst)
    n, k, A = len(inst["domain"]), inst["k"], inst["A"]
    print(json.dumps({"n": n, "k": k, "A": A, "rate": round(k / n, 4), "gap": round((A - k) / n, 4),
                      "listed": len(inst["challenges"]), "certified_distinct_bad": len(bad),
                      "per_n": round(len(bad) / n, 3), "failures": failures[:5], "n_failures": len(failures)}))
    sys.exit(1 if failures else 0)
