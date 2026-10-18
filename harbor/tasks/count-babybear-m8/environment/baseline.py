#!/usr/bin/env python3
"""The four-pair line: 4 (n - A + 1) = 3 n / 2 + 4 bad challenges, the environment's oracle. The public
floor is higher: since 14 October 2026, eleven codeword pairs in a tower give 187 n / 64 at n = 1,024
(thread bt1_afa60af3a6d1e9fd9e9eff61), after six pairs lifted from the subgroup of order 16 gave 9 n / 4.
Standard library only; writes an instance for certify.py.

Usage: python3 baseline.py m out.json [seed]
  The domain is the subgroup of order n = 2^m of BabyBear (p = 2^31 - 2^27 + 1), k = n / 2 and
  A = 5 n / 8.

The mechanism, one bad challenge per point: if codewords F, G agree with f, g on a set S of A - 1
points, then at every point i outside S the challenge z_i = (F(x_i) - f_i) / (g_i - G(x_i)) makes
f + z_i g agree with F + z_i G on S and at i, A points, while g is not interpolable there (any
interpolant would be G on the A - 1 >= k points of S, and g_i differs from G(x_i)). One pair
with random words elsewhere gives n - A + 1 = 3 n / 8 + 1. Here four pairs share one line:

  F_r = F_0 + Z_T h_r,  G_r = G_0 + Z_T h'_r   (r = 0..3, h_0 = h'_0 = 0),

with Z_T vanishing on a common set T of k - 3 points and h_r, h'_r of degree at most 2, so every
F_r has degree below k. Two codewords of the family agree on T and on the roots of h_r - h_s; for
each of the six pairs one such root is placed on a domain point x_rs (a linear condition on the
h's, nine unknowns for six conditions), and h'_r - h'_s is made to vanish there too. S_r is T, the
three points x_rs of r, and private points up to A - 1; the four S_r cover all but one point of
the domain. f = F_r and g = G_r on S_r, consistently. Pair r gives one challenge per point outside
S_r, z = -(h_r - h_s)(x) / (h'_r - h'_s)(x) at a point of S_s, distinct because the two quadratics
share one root and nothing else. Total 4 (n - A + 1). A fifth pair is not expected to fit: by a
dimension count the sets would need more shared points than the shifts have freedom for once
n >= 64. That is a heuristic, not a proof; dependent conditions on the subgroup could change it.
"""
import json, random, sys

P, TWO_ADICITY = 2**31 - 2**27 + 1, 27
PAIRS = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))


def subgroup(n, rng):
    m = n.bit_length() - 1
    assert 1 << m == n and m <= TWO_ADICITY
    while True:
        w = pow(rng.randrange(2, P), (P - 1) >> m, P)
        if pow(w, 1 << (m - 1), P) != 1:
            return [pow(w, i, P) for i in range(n)]


def ev(c, x):
    v = 0
    for a in reversed(c):
        v = (v * x + a) % P
    return v


def mul(a, b):
    r = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                r[i + j] = (r[i + j] + x * y) % P
    return r


def add(a, b):
    r = [0] * max(len(a), len(b))
    for i, x in enumerate(a):
        r[i] = x
    for i, x in enumerate(b):
        r[i] = (r[i] + x) % P
    return r


def vanishing(points):
    z = [1]
    for x in points:
        z = mul(z, [(-x) % P, 1])
    return z


def nullspace_vector(rows, ncols, rng):
    """A random vector of the nullspace of the matrix rows (mod P), by Gaussian elimination."""
    M = [list(r) for r in rows]
    pivots, r = [], 0
    for c in range(ncols):
        piv = next((i for i in range(r, len(M)) if M[i][c]), None)
        if piv is None:
            continue
        M[r], M[piv] = M[piv], M[r]
        inv = pow(M[r][c], P - 2, P)
        M[r] = [v * inv % P for v in M[r]]
        for i in range(len(M)):
            if i != r and M[i][c]:
                fct = M[i][c]
                M[i] = [(a - fct * b) % P for a, b in zip(M[i], M[r])]
        pivots.append(c)
        r += 1
    free = [c for c in range(ncols) if c not in pivots]
    x = [0] * ncols
    for c in free:
        x[c] = rng.randrange(P)
    for i, c in enumerate(pivots):
        x[c] = (-sum(M[i][j] * x[j] for j in free)) % P
    return x


def shifts(dom, shared, R, d, rng):
    """h_1..h_{R-1} of degree <= d (h_0 = 0) with h_r(x) = h_s(x) at the shared point x of each pair."""
    ncols = (R - 1) * (d + 1)
    rows = []
    for (r, s), i in shared.items():
        x, row = dom[i], [0] * ncols
        for who, sign in ((r, 1), (s, -1)):
            if who:
                for e in range(d + 1):
                    col = (who - 1) * (d + 1) + e
                    row[col] = (row[col] + sign * pow(x, e, P)) % P
        rows.append(row)
    v = nullspace_vector(rows, ncols, rng)
    return [[0]] + [v[(r - 1) * (d + 1):r * (d + 1)] for r in range(1, R)]


def build(m, seed=1, R=4, d=2):
    rng = random.Random(seed)
    n = 1 << m
    k, A = n // 2, 5 * n // 8
    dom = subgroup(n, rng)
    idx = list(range(n))
    rng.shuffle(idx)
    t = k - 1 - d
    T, rest = idx[:t], idx[t:]
    shared = {pair: rest[i] for i, pair in enumerate(PAIRS[:R * (R - 1) // 2])}
    rest = rest[len(shared):]
    extra = A - 1 - t
    S = []
    for r in range(R):
        mine = [x for pair, x in shared.items() if r in pair]
        S.append(T + mine + rest[:extra - len(mine)])
        rest = rest[extra - len(mine):]
    assert all(len(s) == A - 1 for s in S), "the four agreement sets must fit the domain (n >= 64)"
    ZT = vanishing([dom[i] for i in T])
    F0 = [rng.randrange(P) for _ in range(k)]
    G0 = [rng.randrange(P) for _ in range(k)]
    Fs = [add(F0, mul(ZT, h)) if any(h) else F0 for h in shifts(dom, shared, R, d, rng)]
    Gs = [add(G0, mul(ZT, h)) if any(h) else G0 for h in shifts(dom, shared, R, d, rng)]
    assert all(len(F) <= k for F in Fs + Gs)
    f, g = [None] * n, [None] * n
    for r in range(R):
        for i in S[r]:
            fi, gi = ev(Fs[r], dom[i]), ev(Gs[r], dom[i])
            assert f[i] in (None, fi) and g[i] in (None, gi)
            f[i], g[i] = fi, gi
    for i in range(n):
        if f[i] is None:
            f[i], g[i] = rng.randrange(P), rng.randrange(P)
    challenges = []
    for r in range(R):
        inS = set(S[r])
        for i in range(n):
            if i in inS:
                continue
            den = (g[i] - ev(Gs[r], dom[i])) % P
            if den == 0:
                continue
            z = (ev(Fs[r], dom[i]) - f[i]) * pow(den, P - 2, P) % P
            challenges.append({"z": z, "witness": S[r][:k]})
    return {"field": "babybear", "p": P, "k": k, "A": A, "domain": dom, "f": f, "g": g,
            "challenges": challenges,
            "note": "four codeword pairs F_0 + Z_T h_r with |T| = k - 3, deg h_r <= 2, one shared point per pair; "
                    "one bad challenge per point outside each agreement set: 4 (n - A + 1) = %d" % (4 * (n - A + 1))}


if __name__ == "__main__":
    m, out = int(sys.argv[1]), sys.argv[2]
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    inst = build(m, seed)
    json.dump(inst, open(out, "w"))
    print(json.dumps({"n": 1 << m, "k": inst["k"], "A": inst["A"], "challenges": len(inst["challenges"])}))
