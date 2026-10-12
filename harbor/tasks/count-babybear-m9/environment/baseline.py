#!/usr/bin/env python3
"""The known floor on one line: n - A + 1 bad challenges, from two codewords and one agreement set.
Standard library only; writes an instance for certify.py.

Usage: python3 baseline.py m out.json [seed]
  The domain is the subgroup of order n = 2^m of BabyBear (p = 2^31 - 2^27 + 1), k = n / 2 and
  A = 5 n / 8. Codewords F and G of degree below k; f = F and g = G on a set S of A - 1 points and
  off them elsewhere. For every point i outside S, the challenge z_i = (F(x_i) - f_i) / (g_i - G(x_i))
  makes f + z_i g agree with F + z_i G on S and at i, A points in all, while f alone is not a
  codeword there. So each of the n - A + 1 points outside S gives one bad challenge: 3 n / 8 + 1.
"""
import json, random, sys

P, TWO_ADICITY = 2**31 - 2**27 + 1, 27


def subgroup(n, rng):
    """The points of the subgroup of order n, in the order w^0, w^1, ..., for a generator w."""
    m = n.bit_length() - 1
    assert 1 << m == n and m <= TWO_ADICITY
    while True:
        w = pow(rng.randrange(2, P), (P - 1) >> m, P)
        if pow(w, 1 << (m - 1), P) != 1:
            return [pow(w, i, P) for i in range(n)]


def evaluate(coeffs, x):
    v = 0
    for a in reversed(coeffs):
        v = (v * x + a) % P
    return v


def build(m, seed=1):
    rng = random.Random(seed)
    n = 1 << m
    k, A = n // 2, 5 * n // 8
    dom = subgroup(n, rng)
    F = [rng.randrange(P) for _ in range(k)]
    G = [rng.randrange(P) for _ in range(k)]
    Fv = [evaluate(F, x) for x in dom]
    Gv = [evaluate(G, x) for x in dom]
    S = list(range(A - 1))
    f, g = list(Fv), list(Gv)
    for i in range(A - 1, n):
        f[i] = (Fv[i] + rng.randrange(1, P)) % P   # not F(x_i)
        g[i] = (Gv[i] + rng.randrange(1, P)) % P   # not G(x_i)
    challenges = []
    for i in range(A - 1, n):
        z = (Fv[i] - f[i]) * pow((g[i] - Gv[i]) % P, P - 2, P) % P
        challenges.append({"z": z, "witness": S[:k]})
    return {"field": "babybear", "p": P, "k": k, "A": A, "domain": dom, "f": f, "g": g,
            "challenges": challenges,
            "note": "floor construction: one bad challenge per point outside an agreement set of A - 1 points; n - A + 1 = %d" % (n - A + 1)}


if __name__ == "__main__":
    m, out = int(sys.argv[1]), sys.argv[2]
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    inst = build(m, seed)
    json.dump(inst, open(out, "w"))
    print(json.dumps({"n": 1 << m, "k": inst["k"], "A": inst["A"], "challenges": len(inst["challenges"])}))
