#!/usr/bin/env python3
"""Certify bad challenges from the definition, over a prime field. Standard library only.

A line is a pair of received words f, g on a domain of n distinct points of F_p. A challenge z is
bad at agreement A if some polynomial P of degree below k agrees with f + z g on at least A points
S, while f and g are not both interpolable by polynomials of degree below k on the whole of S.

Usage: python3 certify.py instance.json
The instance lists p, k, A, domain, f, g and challenges. Each challenge gives z and a witness: the
k points (indices) that determine P. The checker rebuilds P, finds the full agreement set, checks
|S| >= A, checks the joint interpolability on S, and reports distinct bad z. Exit code 1 if any
listed challenge fails.
"""
import json, sys


def inv(a, p):
    return pow(a, p - 2, p)


def interpolate(xs, ys, p):
    """Coefficients (low to high) of the polynomial of degree < len(xs) through the points."""
    k = len(xs)
    coeffs = [0] * k
    for i in range(k):
        num = [1]
        den = 1
        for j in range(k):
            if j == i:
                continue
            new = [0] * (len(num) + 1)
            for t, a in enumerate(num):
                new[t + 1] = (new[t + 1] + a) % p
                new[t] = (new[t] - a * xs[j]) % p
            num = new
            den = den * (xs[i] - xs[j]) % p
        f = ys[i] * inv(den, p) % p
        for t, a in enumerate(num):
            coeffs[t] = (coeffs[t] + a * f) % p
    return coeffs


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
    for ch in inst["challenges"]:
        z, witness = ch["z"] % p, ch["witness"]
        word = [(f[i] + z * g[i]) % p for i in range(n)]
        P = interpolate([dom[i] for i in witness], [word[i] for i in witness], p)
        S = [i for i in range(n) if evaluate(P, dom[i], p) == word[i]]
        if len(S) < A:
            failures.append((z, "agreement %d < %d" % (len(S), A)))
            continue
        pts = [dom[i] for i in S]
        if interpolable(pts, [f[i] for i in S], k, p) and interpolable(pts, [g[i] for i in S], k, p):
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
