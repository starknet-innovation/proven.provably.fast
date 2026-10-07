# Pinned statements for the Lean track

A soundness term becomes LEAN-CHECKED only when a proof of the statement pinned here, with these
exact parameters and no `sorry`, compiles against the pinned ArkLib commit. Contributors prove the
statement we pin; they never choose it. A result about Reed-Solomon codes counts for Stwo only
together with P5, the transfer to circle codes.

Pinned library: [Verified-zkEVM/ArkLib](https://github.com/Verified-zkEVM/ArkLib) at `35ddcaa83f68`
(Apache-2.0). Status checked 2026-10-07: Theorem 1.2 of BCIKS20 is stated
(`ProximityGap/BCIKS20/ReedSolomonGap.lean`); six files in `ProximityGap/BCIKS20/` still contain
`sorry`, among them `Curves.lean` and `AffineLines/Main.lean`. Schwartz-Zippel is proven
(`ToMathlib/MvPolynomial/SchwartzZippel.lean`).

Common parameters: base field M31 (p = 2^31 - 1); challenges in QM31, |F| = p^4 (about 2^124);
rate rho = 1/4; evaluation domain |D| = 2^23 (trace 2^21); unique-decoding radius
delta = (1 - rho) / 2 = 3/8.

| Pin | Term | Statement | Parameters | ArkLib today |
|---|---|---|---|---|
| P1 | C-BATCHING (S-two whitepaper, Remark 20) | Correlated agreement for low-degree curves, unique decoding: if more than (t - 1) |D| / |F| of the alpha in F make sum_i alpha^(i-1) f_i delta-close to the code, then f_1, ..., f_t agree with codewords on a common set of density at least 1 - delta | t = 363, |D| = 2^23, delta = 3/8, |F| = p^4 | `BCIKS20/Curves.lean`, has `sorry` |
| P1' | C-BATCHING (independent coefficients) | Proximity gap for affine spaces, unique decoding: error |D| / |F| for a combination with independent coefficients | |D| = 2^23, delta = 3/8, |F| = p^4 | `BCIKS20/AffineSpaces.lean` (Theorem 1.7), check for `sorry` |
| P2 | C-FRI-FOLDING | P1 applied per FRI layer with t = 16 (folds with alpha, alpha^2, alpha^4, alpha^8), summed over layers | t = 16, |D_i| = 2^23, 2^19, ..., 2^3 | as P1 |
| P3 | C-CIRCUIT-FRI-UD | A word delta-far from the code, delta = 3/8, passes one FRI query with probability at most (1 + rho) / 2 = 5/8; 107 independent queries and 26 bits of proof of work give 2^-98.55 | 107 queries, 26 bits | not located; to be stated |
| P4 | C-OOD | A nonzero polynomial of degree d vanishes at a uniformly random point of F with probability at most d / |F| | d = 2^22 | proven (Schwartz-Zippel) |
| P5 | all of the above, for Stwo | Circle codes over M31 (Stwo's circle FRI) satisfy P1-P3 with the same bounds | as above | open |

Lookups (C-AIR) and binding (C-COMMIT-BINDING) are pinned later; their numbers are far from the
floor (2^-117.8 and 2^-124), so they do not decide the 96-bit question.

Reading of the numbers: P1 with t = 363 gives 2^-92.5, which is why the reference sheets read 92.4
claimed bits. P1' gives 2^-101; the example sheet `reference/ledger-independent-batching.json`
reads 96.5 with it.
