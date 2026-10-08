# The mathematics track

Open research on quantitative mutual correlated agreement (MCA) for Reed-Solomon codes on
prescribed evaluation sets, over finite fields of sufficiently large characteristic, with received
words and challenges allowed in an extension field. The first objective is to improve the
exceptional-challenge bound beyond the Johnson radius: its dependence on the code length and on
the agreement slack, with explicit constants and machine-checked proofs. The larger ambition is
stronger guarantees closer to capacity. These are different levels of difficulty, and a result at
the first level is not a result at the second.

Prover profiles (Stwo first, others pinned with the teams that run them) motivate the mathematics
and test whether a theorem is usable. They do not define success, and no implementation audit is a
prerequisite for contributing a theorem. A new theorem is the main achievement; certificates and
measured prover improvements are separate results, recorded in the applicability track.

## The theorem we are after

Notation. C = RS[F, L, k] of length n = |L|, rate rho = k / n, evaluation set L prescribed. For a
line u_z = f + z g of received words, z is bad at agreement a if u_z agrees with a codeword on a
set S of at least a n coordinates while (f, g) has no joint codeword explanation on S. E_C(a) is
the largest number of bad z over all lines; the MCA error is E_C(a) / |F|.

What is proven for prescribed evaluation sets:

| Agreement a | Best proven E_C(a) | Source | Field condition |
|---|---|---|---|
| above (1 + rho) / 2, unique decoding | n | BCIKS20 | any |
| sqrt(rho) + eta, above the Johnson threshold | O_rho(n / eta^3), explicitly (8/3) n t^3 / rho | DKT, eprint 2026/2056, Theorem 5.12 | any characteristic |
| a_1(rho) + eta_1, one hidden derivative; a_1(1/4) = 0.4688 | O_rho(n^2 / eta_1^4); 1,325,775 n^2 at a = rho + 0.24; both proven in Lean in ArkLib | DKT Theorems 1.1, 5.8 and 5.13 | characteristic 0 or p > max(k - 1, B_d) |
| rho + delta, fixed gap to capacity | C_delta n^(d_delta + 1), d_delta = ceil(exp(1.5 / delta)) | DKT Theorem 1.2; Jeronimo (ECCC TR26-169), n^(O_delta(1)) | p > k - 1 |
| a above 1 - d_min (error radius below the minimum distance), lower bound | at least floor((1 - a) n) on some line, capped at the field size | ABF, eprint 2026/680, Lemma 4.16 | any linear code |

For comparison, folded Reed-Solomon codes and other subspace-design codes have MCA error linear in
n at any fixed positive gap from capacity (GG25, Corollaries 4.9 and 4.10), and randomly punctured
Reed-Solomon codes have it with high probability over the code (GG25 Theorem 5.15, GGSW26); none of
these covers an ordinary Reed-Solomon code on a prescribed set. Gabizon (eprint 2026/2048)
proves the list of close codewords, not the line count, is at most C n on the same first-order
curve; his Lemma 4.5 and DKT's equation 28 are the same inequality. Below the Johnson radius the
known bound on the line count is linear; the lower bound is linear everywhere (a worst-case bound
under Lemma 4.16's hypotheses, with no matching upper bound known); past Johnson nothing better
than quadratic is known for a prescribed set. Characteristic-two constructions are outside this initial
challenge: the first-order theorems need large characteristic, and separate obstructions are known
there (BCHKS, BKR10).

Targets, in increasing difficulty. Each has a Lean statement in `lean/ProvenTargets.lean`
(`lean/PINNED.md` explains it).

### T1

**Improve the length dependence; the first objective.** For 0 < rho < 1 and a_1(rho) < a:
E_C(a) <= C(rho, a) n with C explicit, for every Reed-Solomon code of rate rho on any prescribed
set, over a field of characteristic 0 or above a stated bound, by any method. This removes one
power of n from DKT Theorem 1.1 (Theorem 5.8), which its authors list as open in their Section
10.4, and matches Gabizon's linear list bound on the MCA side. The new content is below the
Johnson threshold sqrt(rho); above it a linear bound is already known.

- Lean, general form: `ProvenTargets.T1 C B`, the statement of ArkLib's
  `ReedSolomon.automaticFirstOrder_rate_bounds` (proven: C_E(rho) n^2 / eta^5 at agreement
  a_1(rho) + eta) with C(rho, eta) n in place of the quadratic bound.
- Lean, uniform form: `ProvenTargets.T1Uniform C`, the statement of ArkLib's
  `ReedSolomon.exists_uniformFirstOrder_lineMca` (proven: 1,325,775 n^2 at agreement k + 6n/25,
  characteristic 0 or above k - 1) with C n in place of 1,325,775 n^2. A result names a numeral C.
- Finite form at the Stwo profile below: a = 0.49, E <= 2^41.5.

### T2

**Push the agreement threshold.** An explicit threshold curve strictly between capacity and
a_1(rho) at every rate, with E_C(a) bounded by a polynomial of degree at most 2 in n. With two
hidden derivatives the known bound is cubic (DKT Theorems 6.3 and 6.6), in the agreement range
those theorems cover. Lean: `ProvenTargets.T2 a2 C B`.

### T3

**Approach capacity; the larger ambition.** For every fixed delta > 0 and prescribed smooth
multiplicative subgroups or their cosets: E_C(rho + delta) <= C_delta n^c with c independent of
delta, ideally c = 1. This is the ordinary-Reed-Solomon, prescribed-domain counterpart of GG25's
results for folded and subspace-design codes. KKH26 (eprint 2026/782) rules it out only when
delta shrinks like 1 / log n; at fixed delta the known general bound has exponent
ceil(exp(1.5 / delta)) + 1 for delta < 0.24 (DKT Theorem 1.2, proven in Lean in ArkLib as
`ReedSolomon.exists_capacity_lineAgreement`). Lean: `ProvenTargets.T3 c`; circle domains, through
their Reed-Solomon description, are pinned later.

### What counts

Contributions credited: ideas, proof sketches, lemmas, counterexamples, formalizations, reviews.
A target is solved when an independently reviewed proof meets its pinned statement, with explicit
constants; a lower bound that shows a target false (an Omega(n^2) family for T1) settles it the
other way. Lean-checked is a separate, higher status shown beside it: a proof of the Lean
statement against the pinned ArkLib commit. Formalizing an existing theorem is a contribution, not
a challenge result. If a target turns out to be solved or
wrong, the next target replaces it; the program does not shrink to parameter work.

### The record

Every contribution is a row in `mathematics/records.jsonl`: its target, its kind (idea, lemma,
counterexample, proof sketch, proof, formalization, review or source), who made it (an agent says
who runs it), what it builds on (sources in `mathematics/targets.json`, earlier rows, issues), its
status and its reviews. A target's status follows from the rows: claimed while a proof or
counterexample is under review, solved or refuted once one is accepted with a holding review by
someone other than its authors, and Lean-checked when an accepted formalization proves one of its
pinned Lean declarations. `python3 -m proven.mathematics check` validates the record and
`python3 -m proven.mathematics board` writes `results/mathematics.json`, which the site reads.
Maintainers record a Mathematics issue with `python3 -m proven.mathematics from-issue`, from
`gh issue view N --json number,title,body,url,author`, then `review`, `accept`, `refute` or
`withdraw`.

Every figure below is reproduced by `python3 -I reference/regimes-stwo-profile.py`; its output is
checked in as `reference/regimes-stwo-profile.json`.

## Profiles: Stwo, the first one

A profile is an example that motivates the mathematics and tests whether a theorem is usable: it
turns a bound into a yes or no at one configuration. It is not the definition of success.

### The pinned profile (Stwo)

Taken from the frontier entry's soundness sheet, `reference/ledger-grind-chain.json`, and
`lean/PINNED.md`:

| Parameter | Value |
|---|---|
| Base field | M31, p = 2^31 - 1 |
| Challenge field | QM31 = F_{p^4}, |F| about 2^124 |
| Rate | 1/4 (log blowup 2) |
| Evaluation domain | n = 2^23 points: the circle domain for a trace of height 2^21, which Theorem 1 of the Circle STARKs paper (eprint 2024/278) maps to a Reed-Solomon code over F_p of the same length and distance |
| Message degree | below k = 2^21 |
| Batching | 363 columns combined by powers of one coefficient: a curve of degree 362 |
| FRI folds | 16-ary, layers of 2^23, 2^19, 2^15, 2^11, 2^7, 2^3 |
| Proof of work | 26 bits before the query positions; at most 26 bits at any other round (the S-two whitepaper's cap) |
| Floor | 96 bits by the sheet's union bound |

The budget this profile leaves to a line bound. Nine algebraic rounds share the floor with the
query term, so each is held to 2^-100. The batching round multiplies the per-line count by 362
and divides by |F|; with 26 bits of proof of work it carries a per-line exceptional count of at
most 2^41.5. The out-of-domain round multiplies the list size by the composition degree 2^22, so
with 26 bits of proof of work it carries a list of at most 2^28.

## What is proven at this profile

| Agreement a per query | Per-line exceptional count | Source | Fits the budget | Queries for 96 bits |
|---|---|---|---|---|
| 0.625 (unique decoding) | n | BCIKS20 Theorem 4.1; S-two whitepaper Remark 20 | yes, 8 bits of proof of work at batching | 107 (today's frontier entries) |
| sqrt(1/4) + eta | (8/3) n t^3 / rho, t = max(ceil(sqrt(rho)/(2 eta)), 3) + 1/2 | DKT, eprint 2026/2056, Theorem 5.12 (every characteristic) | yes for a >= 0.508, with 26, 25, 21, 17, 13, 9 and 5 bits of proof of work at batching and the six fold layers | 73 at a = 0.504 |
| sqrt(1/4) + eta | l_GS (2 l_GS^4 / 3 (1 - delta) + 1) n | S-two whitepaper Theorem 19, after BCHKS25 | yes for a >= 0.531 | 76 at a = 0.52 |
| 0.49 = rho + 0.24 | 1,325,775 n^2 | DKT Theorem 5.13, needs p > k - 1 (holds: 2^31 - 1 > 2^21) | no: 2^66.3 against 2^41.5 | 69 if it fit |
| any a | at least floor((1 - a) n) | ABF, eprint 2026/680, Lemma 4.16 | the floor: 2^22 | |
| 0.25 (capacity) | conjectured | S-two whitepaper Conjectures 1 and 2 | | 35 (today's settings) |

The first-order agreement curve a_1(rho) of DKT equation 31 and the bracket of Gabizon's
Lemma 4.5 (eprint 2026/2048) are the same inequality: a^2 / rho + 3 (1 - a)^2 / (4 (2 - rho)) > 1,
which gives a_1(1/4) = 0.4688, a_1(1/2) = 0.6899, a_1(1/8) = 0.3191, a_1(1/16) = 0.2181.
Gabizon proves the list of close codewords is at most C n there, with C depending only on the
rate. DKT prove the list is O(n / eta^2) and the exceptional count O(n^2 / eta^4), with the
explicit constants above at gap 0.24 from capacity.

## Applicability track (Stwo)

What each step is worth at this profile, from the table above: 107 to 73 queries comes from
theorems that exist, once they are shown to apply to the running code (the items below). 73 to
69 is T1. 69 to 35 is the conjecture. These numbers are about one configuration; another profile
has its own, and a system whose budget is limited by a different term gains differently.

### Items

| Id | Item | Status |
|---|---|---|
| A1 | Theorem 1 of the Circle STARKs paper transfers line MCA from Reed-Solomon codes over F_p to Stwo's circle codes, coordinate by coordinate | derivation to write; `lean/PINNED.md` P5 |
| A2 | Stwo samples query positions without the squaring consistency the whitepaper's proof uses (whitepaper Section 4.5); the whitepaper states this does not affect security in the unique-decoding regime and gives no list-decoding proof | review open: the page's first review |
| A3 | Powers batching of 363 columns: the curve transfer multiplies a line count by the curve degree (BCIKS20 curves; DKT Corollary 7.3) | derivation to write |
| A4 | Proof of work at the batching round and at each fold layer, as the whitepaper's Table 5 assumes; the frontier entries grind 8 bits at batching only | implementation |
| A5 | Characteristic conditions of the first-order theorems: p > max(k - 1, B_d); M31 gives 2^31 - 1 against 2^21 and a small B_d | holds, to be recorded with the certificate |

### A second profile

A second profile is pinned together with a team that runs it: the commit, field sizes, domain,
whether the length is the codeword or the trace, the exact MCA property, the budget derivation and
the grinding rounds are written down before any number is published. DKT's own applications
(ProveKit over BN254, ZisK and LambdaVM over cubic Goldilocks) show configurations where the
quadratic bound already fits; whether it fits a given 31-bit-field configuration with a degree-4
extension is settled by that configuration's budget, not by the field's name.

## Scoring

The mathematics column records the status of T1, T2 and T3 (open, claimed, reviewed, Lean-checked,
or refuted) and the Lean status of every pinned statement. Per profile, the applicability column
records the lowest agreement at which a proven per-line count fits that profile's budget (today
0.508 by DKT Theorem 5.12 at the Stwo profile, pending A1 to A4). A result moves a row when its
statement, its parameters and its proof are public and a reviewer has read it.
