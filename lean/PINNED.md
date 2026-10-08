# Pinned statements for the Lean track

The targets T1, T2 and T3 of the mathematics challenge are stated in Lean in
[`ProvenTargets.lean`](ProvenTargets.lean), against
[Verified-zkEVM/ArkLib](https://github.com/Verified-zkEVM/ArkLib) at
`35ddcaa83f683011f944f58904be779495a5709a` (Apache-2.0), pinned in [`lakefile.toml`](lakefile.toml).
Contributors prove the statement we pin; they never choose it.

A Lean result proves one target for explicit parameters: constants and curves written in closed
form, never obtained with `Classical.choose`. It compiles against the pinned commit and depends on
no axioms beyond `propext`, `Classical.choice` and `Quot.sound`. Reviewers check both, and that the
parameters are explicit. Lean-checked is a status shown beside a solved target; a target is solved
by an independently reviewed proof, with or without Lean (MATHEMATICS.md).

| Target | Lean declaration | What it asks | Proven today in ArkLib |
|---|---|---|---|
| T1, uniform form | `ProvenTargets.T1Uniform C` | agreement at least k + 6n/25, characteristic 0 or above k - 1: at most `C * n` bad challenges on every line | `ReedSolomon.exists_uniformFirstOrder_lineMca`: 1,325,775 n^2 (restated as `baseline_T1Uniform_quadratic`) |
| T1, general form | `ProvenTargets.T1 C B` | agreement at least (a1(rho) + eta) n, k at most rho n, characteristic 0 or above max(k - 1, B rho eta): at most `C rho eta * n` | `ReedSolomon.automaticFirstOrder_rate_bounds`: C_E(rho) n^2 / eta^5 (restated as `baseline_T1_quadratic`) |
| T2 | `ProvenTargets.T2 a2 C B` | a threshold curve a2 strictly between capacity and a1 at every rate, with at most `C rho eta * n ^ 2` | nothing below a1 with a quadratic count |
| T3 | `ProvenTargets.T3 c` | smooth domains (cosets of the subgroup of order 2^m), every fixed gap delta above capacity: at most `C_delta * n ^ c`, with c independent of delta; `T3 1` is the full ambition | `ReedSolomon.exists_capacity_lineAgreement`: C n^(d + 1) on any domain, with d depending on delta |

a1(rho) here is ArkLib's `ReedSolomon.HiddenDerivative.firstOrderRateThreshold rho`,
(3 rho + 2 sqrt(rho (5 - rho)(2 - rho))) / (8 - rho): the first-order curve of Dao, Kominers and
Thaler (ePrint 2026/2056, equation 31) for rho at least 11 - 3 sqrt(13), and the threshold ArkLib's
quadratic theorem uses at every rate. All four statements use ArkLib's `LineExactAgreementBound`:
for every received line f + z g, one exceptional set of at most B challenges, outside of which
every polynomial of degree below k agreeing with the line in at least A places splits as
P0 + z P1 with the same agreement set for f and g.

Build and check (`lake-manifest.json` pins every dependency):

    cd lean
    lake exe cache get    # Mathlib's prebuilt files
    lake build

To check a proof, import `ProvenTargets` in a file of your own and run `#print axioms` on your
theorem with `lake env lean YourFile.lean`; the answer must list only `propext`,
`Classical.choice` and `Quot.sound`. Status checked 2026-10-08 from a fresh clone (lake update,
cache, build: about nine minutes on a laptop): `ProvenTargets` builds with no warnings, both
baselines depend only on the three standard axioms, and the targets are open. ArkLib's own build
prints two `sorry` warnings, in `ArkLib/Data/Fin/Basic.lean` and
`ArkLib/Data/MvPolynomial/Interpolation.lean`; neither is used by these statements or baselines,
which `#print axioms` confirms.

## Applicability pins (the Stwo profile)

These pin the soundness terms of the performance track's Stwo entries; they are not the
mathematics targets. A soundness term becomes LEAN-CHECKED only when a proof of the statement
pinned here, with these exact parameters and no `sorry`, compiles against the pinned ArkLib
commit. A result about Reed-Solomon codes counts for Stwo only together with P5, the transfer to
circle codes. Status checked 2026-10-07: Theorem 1.2 of BCIKS20 is stated
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
