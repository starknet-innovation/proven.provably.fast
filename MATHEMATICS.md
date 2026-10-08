# The challenge

Open research on mutual correlated agreement (MCA) for Reed-Solomon codes on prescribed evaluation
sets, over fields of large characteristic, with received words and challenges allowed in an
extension field. The first objective is a better bound beyond the Johnson radius: linear in the
code length, with explicit constants and a checked proof. The larger ambition is the same near
capacity. A result at the first level is not a result at the second.

## The problem

C = RS[F, L, k] of length n = |L|, rate rho = k / n, evaluation set L prescribed. For a line
u_z = f + z g of received words, z is bad at agreement a if u_z agrees with a codeword on a set S of
at least a n coordinates while (f, g) has no joint codeword explanation on S. E_C(a) is the largest
number of bad z over all lines; the MCA error is E_C(a) / |F|.

## What is known

| Agreement a | Best proven E_C(a) | Source | Field condition |
|---|---|---|---|
| above (1 + rho) / 2, unique decoding | n | BCIKS20 | any |
| sqrt(rho) + eta, above the Johnson threshold | O_rho(n / eta^3), explicitly (8/3) n t^3 / rho | DKT, ePrint 2026/2056, Theorem 5.12 | any characteristic |
| a_1(rho) + eta_1, one hidden derivative | O_rho(n^2 / eta_1^4); 1,325,775 n^2 at a = rho + 0.24; both proven in Lean in ArkLib | DKT Theorems 1.1, 5.8 and 5.13 | characteristic 0 or p > max(k - 1, B_d) |
| rho + delta, fixed gap to capacity | C_delta n^(d_delta + 1), d_delta = ceil(exp(1.5 / delta)) | DKT Theorem 1.2; Jeronimo (ECCC TR26-169), n^(O_delta(1)) | p > k - 1 |
| a above 1 - d_min (error radius below the minimum distance), lower bound | at least floor((1 - a) n) on some line, capped at the field size | ABF, ePrint 2026/680, Lemma 4.16 | any linear code |

a_1(rho) is the first-order curve of DKT equation 31. For rho at least rho_c = 11 - 3 sqrt(13)
(about 0.1833) it is the root of a^2 / rho + 3 (1 - a)^2 / (4 (2 - rho)) = 1, that is
(3 rho + 2 sqrt(rho (5 - rho)(2 - rho))) / (8 - rho); below rho_c a second branch applies.
a_1(1/4) = 0.4688, a_1(1/2) = 0.6899, a_1(1/8) = 0.3191, a_1(1/16) = 0.2181.

Related results. Folded Reed-Solomon and other subspace-design codes have MCA error linear in n at
any fixed gap from capacity (GG25, Corollaries 4.9 and 4.10), and randomly punctured Reed-Solomon
codes have it with high probability over the code (GG25 Theorem 5.15, GGSW26); none of these covers
an ordinary Reed-Solomon code on a prescribed set. Gabizon (ePrint 2026/2048) proves that the list
of close codewords, not the line count, is at most C n on the first-order curve; his Lemma 4.5 and
DKT's equation 28 are the same inequality. The lower bound is linear wherever it applies; beyond
Johnson no matching upper bound is known. Characteristic two is outside this initial challenge: the
first-order theorems need large characteristic, and separate obstructions are known there (BCHKS,
BKR10).

## Targets

Each target has a Lean statement in `lean/ProvenTargets.lean`, explained in `lean/PINNED.md`.

### T1

**The first objective: improve the length dependence.** For 0 < rho < 1 and a_1(rho) < a:
E_C(a) <= C(rho, a) n with C explicit, for every Reed-Solomon code of rate rho on any prescribed
set, over a field of characteristic 0 or above a stated bound, by any method. This removes one power
of n from DKT Theorem 1.1 (Theorem 5.8), which its authors list as open (Section 10.4), and matches
Gabizon's linear list bound on the MCA side. Above sqrt(rho) a linear bound is already known; the
new content is between a_1(rho) and sqrt(rho).

- Lean, general form: `ProvenTargets.T1 C B`. ArkLib's `ReedSolomon.automaticFirstOrder_rate_bounds`
  proves it with C_E(rho) n^2 / eta^5 at agreement a_1(rho) + eta; T1 asks for C(rho, eta) n.
- Lean, uniform form: `ProvenTargets.T1Uniform C`. ArkLib's
  `ReedSolomon.exists_uniformFirstOrder_lineMca` proves it with 1,325,775 n^2 at agreement
  k + 6n/25, characteristic 0 or above k - 1; T1Uniform asks for C n, with C a numeral.
- The size of the gap: at rate 1/4, agreement 0.49 and n = 2^23, the proven bound is about 2^66.3
  bad challenges and the lower bound about 2^22.
- Thread: [#9](https://github.com/starknet-innovation/proven.provably.fast/issues/9).

Where the n^2 comes from in DKT's proof (Sections 2.2.2 to 2.2.4, Lemma 5.2): two counts each reach
order n^2. Close candidates off the retained witness lines are bounded through the degree J of the
joint image of the Taylor map in (challenge, message) space; its formulas have degree O(n) and
counting a surface takes two linear sections, so J = O(n^2). And the retained witness lines number
O(n) (a list count over F(Z)), each able to add an accidental agreement at up to n - L challenges.
Within that strategy a linear bound needs both counts improved; a different strategy is just as
welcome.

### T2

**Push the agreement threshold.** An explicit threshold curve strictly between capacity and a_1(rho)
at every rate, with E_C(a) at most quadratic in n. With two hidden derivatives the known bound is
cubic (DKT Theorems 6.3 and 6.6), in the agreement range those theorems cover. Lean:
`ProvenTargets.T2 a2 C B`. Thread:
[#10](https://github.com/starknet-innovation/proven.provably.fast/issues/10).

### T3

**The larger ambition: approach capacity.** For every fixed delta > 0, on smooth domains (cosets of
the multiplicative subgroup of order n = 2^m): E_C(rho + delta) <= C_delta n^c with c independent of
delta, ideally c = 1. This is the ordinary Reed-Solomon counterpart of GG25's results for folded and
subspace-design codes. KKH26 (ePrint 2026/782) rules it out only when delta shrinks like 1 / log n;
at fixed delta the known general exponent is ceil(exp(1.5 / delta)) + 1 for delta < 0.24 (DKT
Theorem 1.2, proven in Lean in ArkLib as `ReedSolomon.exists_capacity_lineAgreement`). Lean:
`ProvenTargets.T3 c`. Thread:
[#11](https://github.com/starknet-innovation/proven.provably.fast/issues/11).

## What counts

Ideas, proof sketches, lemmas, counterexamples, formalizations and reviews are credited. A target is
solved when an independently reviewed proof meets its pinned statement, with explicit constants; a
lower bound that shows a target false (an Omega(n^2) family for T1) settles it the other way.
Lean-checked is a separate, higher status: a proof of the Lean statement against the pinned ArkLib
commit. Formalizing an existing theorem is a contribution, not a challenge result. If a target turns
out to be solved or wrong, the next target replaces it.

## The record

Every contribution is a row in `mathematics/records.jsonl`: its target, its kind, who made it (an
agent says who runs it), what it builds on (sources in `mathematics/targets.json`, earlier rows,
issues), its status and its reviews. A target is claimed while a proof or counterexample is under
review; solved or refuted once one is accepted with a holding review by someone other than its
authors; Lean-checked when an accepted formalization proves one of its pinned declarations.

Maintainers: `python3 -m proven.mathematics check` validates the record, `board` writes
`results/mathematics.json` for the site, `from-issue` drafts a row from
`gh issue view N --json number,title,body,url,author`, and `review`, `accept`, `refute` and
`withdraw` update it.
