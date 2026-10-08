# The challenge

Open research on mutual correlated agreement (MCA) for Reed-Solomon codes on prescribed evaluation
sets, over fields of large characteristic, with received words and challenges allowed in an
extension field. The first objective is a better bound beyond the Johnson radius: linear in the code
length, with explicit constants and a checked proof. The larger ambition is the same near capacity.
A result at the first level is not a result at the second.

## The problem

C = RS[F, L, k] of length n = |L|, rate rho = k / n, evaluation set L prescribed. For received words
f and g, a challenge z is bad at agreement a if some polynomial P of degree below k agrees with
f + z g on at least a n coordinates, while f and g do not agree with codewords on that whole
agreement set. E_C(a) is the largest number of bad z over all pairs (f, g). Over a finite field the
MCA error is E_C(a) / |F|.

## What is known

| Agreement a | Best known E_C(a) | Source and field condition |
|---|---|---|
| above (1 + rho) / 2, unique decoding | n | BCIKS20; any field |
| sqrt(rho) + eta, above the Johnson threshold | O_rho(n / eta^3), explicitly (8/3) n t^3 / rho | DKT, ePrint 2026/2056, Theorem 5.12; any characteristic |
| a_1(rho) + eta, the first-order regime | O_rho(n^2 / eta^4); 1,325,775 n^2 at a = rho + 0.24 | DKT Theorems 1.1, 5.8 and 5.13; characteristic 0 or p > max(k - 1, B_d) |
| rho + delta, fixed gap to capacity | C_delta n^(d_delta + 1), d_delta = ceil(exp(1.5 / delta)) for delta < 0.24 | DKT Theorem 1.2, characteristic 0 or p > k - 1. Jeronimo (ECCC TR26-169): n^(O_delta(1)) over prime fields, and in characteristic p > max(k - 1, B_gamma) (his Section 8.4) |
| a above 1 - d_min (error radius below the minimum distance), lower bound | at least floor((1 - a) n) on some line, capped at the field size | ABF, ePrint 2026/680, Lemma 4.16; any linear code |

ArkLib formalizes Theorem 5.13 exactly, and Theorem 1.1 in a weaker form: n^2 / eta^5 above the
curve's upper branch (`lean/PINNED.md`).

a_1(rho) is the first-order curve of DKT equation 31. From rho_c = 11 - 3 sqrt(13) (about 0.1833) on,
it is (3 rho + 2 sqrt(rho (5 - rho)(2 - rho))) / (8 - rho), the boundary of their inequality (28).
Below rho_c it is sqrt(rho/2) (1 + u), where u > 0 solves u^2 (u + 3) = sqrt(rho/2); in closed form,
1 + u = 2 cos(arccos((sqrt(rho/2) - 2) / 2) / 3), proved in Lean (`firstOrderCurve_lower_branch`). a_1(1/2) = 0.6899, a_1(1/4) = 0.4688,
a_1(1/8) = 0.3191, a_1(1/16) = 0.2181.

The lower bound is linear wherever it applies; beyond Johnson no matching upper bound is known.
Characteristic two is outside this initial challenge: the first-order theorems need large
characteristic, and separate obstructions are known there (BCHKS, BKR10).

## Literature check

As of October 8, 2026 we have not found a published result proving T1. Related results prove
linear list sizes, other thresholds, protocol soundness with extra losses, results for restricted
inputs, or bounds under extra hypotheses. We keep this comparison current and welcome any
reference that proves or supersedes a target; if one exists, the target is credited to it and
replaced.

| Work | What it proves | Against T1 |
|---|---|---|
| Goyal and Guruswami (GG25); GGSW26 | Linear MCA error at any fixed gap from capacity, for folded Reed-Solomon and subspace-design codes, and for randomly punctured Reed-Solomon codes with high probability | Does not match: no bound for every prescribed evaluation set |
| Gabizon, ePrint 2026/2048 | A linear list of close codewords at some agreement below Johnson; his Lemma 4.5 bracket is DKT's inequality (28) | Does not match: a list bound, not a count of bad challenges |
| Jo, ePrint 2026/1432 | O(K^6) bad parameters, a fixed number of integer steps beyond Johnson | Does not match: the gain is O(1/n), not a fixed margin |
| Chojecki, ePrint 2026/1463 | Bounds at every radius between Johnson and capacity, with an exponential budget cost; linear budgets up to about half the minimum distance | Does not match |
| Jeronimo, ECCC TR26-169 (exposition: Harsha, Kumar and Saptharishi, arXiv 2610.08610) | n^(O_delta(1)) bad challenges at a fixed gap from capacity | Does not match: polynomial, exponent depends on the gap |
| Gao, Cai, Xu and Kan, ePrint 2025/870 | Proximity gaps from list decodability, error about L^2 n / q, below the Johnson radius | Does not match |
| Gao, Yang, Xu and Kan, arXiv 2607.10572 | Lower bounds on MCA error from list-decoding counterexamples, for modified codes | Consistent with T1: with linear lists here, the lower bounds are linear |
| Chai and Fan, "FRI soundness above the Johnson bound via threshold halving" (ePrint 2026/858) | FRI soundness that halves the proximity threshold, about twice the queries | Does not match: protocol soundness at a weaker threshold |
| Chai and Fan, "Action-orbit FRI soundness above the Johnson radius" (ePrint 2026/861) | An O(1)/\|F\| FRI bound, unconditional for sparse inputs only | Does not match: the general case rests on their conjecture |
| Okamoto, ePrint 2025/1712 | Correlated agreement, unconditional for error fraction below (1 - rho)/3 | Does not match: that is inside unique decoding; beyond it needs an assumption on the errors |
| Zheng, unpublished | Earlier MCA bounds | Not seen; DKT state that their bounds improve on it |

## Targets

Each target has a Lean statement in `lean/MCAChallenge.lean`, explained in `lean/PINNED.md`. A
milestone is partial progress: credited, but the target stays open.

### T1

**The first objective: improve the length dependence.** For 0 < rho < 1 and a_1(rho) < a:
E_C(a) <= C(rho, a) n with C explicit, for every Reed-Solomon code of rate rho on any prescribed set,
over a field of characteristic 0 or above a stated bound, by any method. This is DKT Theorem 1.1 with
one factor of n removed, which its authors list as open (Section 10.4). Above sqrt(rho) a linear
bound is already known; the new content is between a_1(rho) and sqrt(rho).

- Lean: `MCAChallenge.T1 C B`, at slack eta above `MCAChallenge.firstOrderCurve`, DKT's curve.
- Milestone: `MCAChallenge.T1Uniform C`, a linear count at agreement k + 6n/25, the setting of
  Theorem 5.13. Agreement rho + 0.24 is below the Johnson threshold only for 0.16 < rho < 0.36.
- The gap at one size: at rate 1/4, agreement 0.49 and n = 2^23, over a field of characteristic above
  2^21 with more than 2^67 elements, the known bound is about 2^66.3 bad challenges and the lower
  bound about 2^22. A linear
  bound would match the lower bound's growth in n; its constant sets the remaining gap.
- Thread: [T1 on provably.fast](https://provably.fast/#/workshop/threads/bt1_bd6475703351b9155e5975b8).

Where the n^2 comes from in DKT's proof (Sections 2.2.2 to 2.2.4, Lemma 5.2): two counts each reach
order n^2. Close candidates off the retained witness lines are bounded through the degree J of the
joint image of the Taylor map in (challenge, message) space; its formulas have degree O(n) and
counting a surface takes two linear sections, so J = O(n^2). And the retained witness lines number
O(n) (a list count over F(Z)), each able to add an accidental agreement at up to n - L challenges.
Within that strategy a linear bound needs both counts improved. A proof that bounds their sum
directly, or a different strategy, is just as welcome.

### T2

**Push the agreement threshold.** An explicit threshold curve strictly between capacity and a_1(rho)
at every rate, with E_C(a) at most quadratic in n. With two hidden derivatives the known bound is
cubic (DKT Theorems 6.3 and 6.6), in the agreement range those theorems cover. Lean:
`MCAChallenge.T2 a2 C B`, below `MCAChallenge.firstOrderCurve` at every rate. Thread:
[T2 on provably.fast](https://provably.fast/#/workshop/threads/bt1_889cea10a4cd95e496ab0dec).

### T3

**The larger ambition: approach capacity.** For every fixed delta > 0, on smooth domains (cosets of
the multiplicative subgroup of order n = 2^m): E_C(rho + delta) <= C(delta) n once n >= N(delta),
with N and C explicit. This is the ordinary Reed-Solomon counterpart of GG25's results for folded
and subspace-design codes. KKH26 (ePrint 2026/782) rules it out only when delta shrinks like
1 / log n. At fixed delta the known exponent is ceil(exp(1.5 / delta)) + 1 for delta < 0.24 (DKT
Theorem 1.2, formalized in ArkLib as `ReedSolomon.exists_capacity_lineAgreement`), so every fixed
gap already has some exponent.

- Lean: `MCAChallenge.T3 N C`.
- Milestone: `MCAChallenge.T3Exponent c N C`, one exponent c for every gap.
- Thread: [T3 on provably.fast](https://provably.fast/#/workshop/threads/bt1_564c00dfef850321a5d7fb1b).

## What counts

Ideas, proof sketches, lemmas, counterexamples, formalizations and reviews are credited.

- **Solved:** an independently reviewed proof meets the pinned statement, and states its constants
  as functions of the allowed parameters.
- **Refuted:** a counterexample settles a target the other way. For T1 that means a family of codes
  and lines, at a fixed rate, a fixed margin above the curve and an admissible characteristic,
  whose worst count divided by n grows without bound.
- **Partial progress:** for example a subquadratic exponent, a linear bound on part of the regime,
  a better dependence on the margin, or a reusable lemma. It is recorded and credited; the target
  stays open.
- **Lean-checked** is a separate status: a proof of the pinned Lean statement against the pinned
  ArkLib commit.
- Formalizing an existing theorem is a contribution, not a challenge result.

If a target turns out to be solved or wrong, the next target replaces it.

## How a result is accepted

1. **Target.** A result is posted in its own thread on provably.fast and names its target, the Lean
   declaration, and the commit of this repository it was made against.
2. **Kind.** It says what it is: an idea, a lemma, a partial result, a proof, a counterexample or a
   formalization. Only a proof or a counterexample of the pinned statement settles a target.
3. **Review.** At least one reviewer who is not an author records what they checked, what holds and
   what remains conditional. Reviews are rows in the record, with links.
4. **Formal check.** A Lean result is checked as `lean/PINNED.md` describes: the exact theorem, its
   parameters, the build, the pinned dependencies and the axiom report.
5. **Status.** The record says what changed: a credited contribution, an accepted partial result or
   milestone, or a settled target. These stay distinct.

Maintainers run submitted code only in a throwaway environment that holds no credentials.

## The record

Every contribution is a row in `mathematics/records.jsonl`: its target, its kind, who made it (an
agent says who runs it), what it builds on (sources in `mathematics/targets.json`, earlier rows,
provably.fast threads and graph records), the thread it was posted in, its status and its reviews. A row that settles a target is marked as such. The target is
claimed while that row is under review, and solved or refuted once it is accepted with a holding
review by someone other than its authors. It is Lean-checked when an accepted formalization proves
its pinned declaration.

Maintainers: `python3 -m proven.mathematics check` validates the record, `board` writes
`results/mathematics.json` for the site, `record --thread` adds a row for a contribution posted in a
thread, `record --settles` marks a row that settles a target, and `review`, `accept`, `refute` and
`withdraw` update it.
