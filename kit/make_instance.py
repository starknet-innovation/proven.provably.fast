#!/usr/bin/env python3
"""Build an example instance on a power-of-two subgroup of a STARK field, with the coset family of
the T3 thread, and write it for certify.py. Standard library only.

Usage: python3 make_instance.py FIELD m s d out.json
  FIELD in babybear, koalabear, goldilocks; the domain is the subgroup of order n = 2^m of F_p;
  s = number of cosets of the subgroup of order n/s; d = degree in y = x^(n/s) of the witnesses;
  k = d n/s + 2, A = (d+1) n/s + 1, gap 1/s - 1/n. The line is affine in x on each coset with
  random coset values; one bad challenge per (d+1)-set of cosets and point outside it.
"""
import itertools, json, random, sys

FIELDS = {"babybear": (2**31 - 2**27 + 1, 27), "koalabear": (2**31 - 2**24 + 1, 24), "goldilocks": (2**64 - 2**32 + 1, 32)}


def subgroup(p, two_adicity, m):
    assert m <= two_adicity, "the field has no subgroup of that order"
    while True:
        g = random.randrange(2, p)
        w = pow(g, (p - 1) >> m, p)
        if pow(w, 1 << (m - 1), p) != 1:
            return [pow(w, i, p) for i in range(1 << m)]


def main(field, m, s, d, out):
    p, ad = FIELDS[field]
    n = 1 << m
    assert n % s == 0 and (s & (s - 1)) == 0
    h = n // s
    dom = subgroup(p, ad, m)
    cos = [[j * s + c for j in range(h)] for c in range(s)]  # coset c = {w^(c + s j)}: fixed by x -> x^... only as a set of indices
    # coset values: f = a_c x + b_c, g = e_c x + r_c on coset c
    rng = random.Random(1)
    a = [rng.randrange(p) for _ in range(s)]; b = [rng.randrange(p) for _ in range(s)]
    e = [rng.randrange(p) for _ in range(s)]; r = [rng.randrange(p) for _ in range(s)]
    f = [0] * n; g = [0] * n
    for c in range(s):
        for i in cos[c]:
            f[i] = (a[c] * dom[i] + b[c]) % p
            g[i] = (e[c] * dom[i] + r[c]) % p
    k, A = d * h + 2, (d + 1) * h + 1
    # witnesses: for each (d+1)-set U of cosets, the pair (F, G) of degree < k that interpolates the
    # coset values on U (degree d in y on each residue). A challenge at a point i outside U:
    # z = (f_i - F(x_i)) / (G(x_i) - g_i). Its witness polynomial is F + z G, determined by k points of U.
    from certify import interpolate, evaluate, inv
    chal = []
    for U in itertools.combinations(range(s), d + 1):
        pts = [i for c in U for i in cos[c]]
        # F, G agree with f, g on pts; they have degree < k since the coset values are affine in x
        # and the interpolant through (d+1) cosets has degree <= d h + 1.
        F = interpolate([dom[i] for i in pts[:k]], [f[i] for i in pts[:k]], p)
        G = interpolate([dom[i] for i in pts[:k]], [g[i] for i in pts[:k]], p)
        for i in range(n):
            if i in pts:
                continue
            den = (evaluate(G, dom[i], p) - g[i]) % p
            if den == 0:
                continue
            z = (f[i] - evaluate(F, dom[i], p)) * inv(den, p) % p
            chal.append({"z": z, "witness": pts[:k]})
    inst = {"field": field, "p": p, "k": k, "A": A, "domain": dom, "f": f, "g": g, "challenges": chal,
            "note": "coset family: s = %d cosets, witnesses of degree %d in y = x^(n/s); expected C(s-1, d+1) = %d per point"
                    % (s, d, __import__("math").comb(s - 1, d + 1))}
    json.dump(inst, open(out, "w"))
    print(json.dumps({"field": field, "p": p, "n": n, "k": k, "A": A, "rate": round(k / n, 4), "gap": round((A - k) / n, 4), "challenges": len(chal)}))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
