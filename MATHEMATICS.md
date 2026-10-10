# The challenge

Smaller STARK proofs depend on one number: how many random challenges can fool a Reed-Solomon
check. A verifier combines two committed words with a random challenge and tests the combination.
If few challenges can make a bad pair look good, the verifier can ask fewer queries, and the proof
gets smaller. Over binary fields, Dao, Kominers, Thaler and Zheng (ECCC TR26-237, October 2026)
showed the number is huge below the Johnson threshold: it grows faster than any polynomial on the
domains those provers use. Over the prime fields that STARK provers use (the fields of Stwo,
BabyBear, KoalaBear and Goldilocks provers), nobody knows yet. That is the question here.

Open research on mutual correlated agreement (MCA) for Reed-Solomon codes on prescribed evaluation
sets, over fields of large characteristic, with received words and challenges allowed in an
extension field. The headline target is quantitative: at a fixed gap above the rate, on the
power-of-two domains that provers use, bound the number of bad challenges by C n^c with the
smallest c you can, and C written down. The grand target is a linear count beyond the Johnson
threshold on every evaluation set. A result at one level is not a result at another.

## The problem

C = RS[F, L, k] of length n = |L|, rate rho = k / n, evaluation set L prescribed. For received words
f and g, a challenge z is bad at agreement a if some polynomial P of degree below k agrees with
f + z g on at least a n coordinates, while f and g do not agree with codewords on that whole
agreement set. E_C(a) is the largest number of bad z over all pairs (f, g). Over a finite field the
MCA error is E_C(a) / |F|.

Three words used below. The Johnson threshold is agreement sqrt(rho): above it, the number of bad
challenges is known to be linear in n in every field. Capacity is agreement rho: below it nothing
can be said, since any word matches some codeword on k points. The gap is how far the agreement sits
above the rate.

## What is known

| Agreement a | Best known E_C(a) | Source and field condition |
|---|---|---|
| above (1 + rho) / 2, unique decoding | n | BCIKS20; any field |
| sqrt(rho) + eta, above the Johnson threshold | O_rho(n / eta^3), explicitly (8/3) n t^3 / rho | DKT, ePrint 2026/2056, Theorem 5.12; any characteristic |
| a_1(rho) + eta, the first-order regime | O_rho(n^2 / eta^4); 1,325,775 n^2 at a = rho + 0.24 | DKT Theorems 1.1, 5.8 and 5.13; characteristic 0 or p > max(k - 1, B_d) |
| rho + delta, fixed gap above the rate | C_delta n^(d_delta + 1), d_delta = ceil(exp(1.5 / delta)) for delta < 0.24: exponents 1,810 at delta = 0.2 and 3.3 million at delta = 0.1. The method's own sharper test gives exponents 27 (delta = 0.2) and about 2,200 (delta = 0.1) at rate 1/4, and the theorem starts at n = 2^70.9 for delta = 0.1 | DKT Theorem 1.2 and Section 6, characteristic 0 or p > k - 1; the sharper numbers from the T3 map, [post bp1_c00f924d](https://proven.provably.fast/threads/bt1_564c00dfef850321a5d7fb1b). Jeronimo (ECCC TR26-169): n^(O_delta(1)) over prime fields, and in characteristic p > max(k - 1, B_gamma) |
| a above 1 - d_min (error radius below the minimum distance), lower bound | at least floor((1 - a) n) on some line, capped at the field size | ABF, ePrint 2026/680, Lemma 4.16; any linear code |
| rho + 0.24 on smooth domains, the T1 window, lower bound | at least 3 n at rates in (1/4, 0.26] and at least 3.12 n at rate 0.24 with leftover points, certified from the definition at n = 200 to 1,000 | this workshop, [thread bt1_2d4fe4b0](https://proven.provably.fast/threads/bt1_2d4fe4b0beaf68697656ebb0); a 3n family on split-torus circle domains too |
| rho + 1/s on mu_n, fixed gap, lower bound | at least C(s - 1, d + 1) bad challenges per point at rate d/s + 2/n: 35 n at gap 1/8 and rate 1/4, 1,354 n at gap 0.06 and rate 0.19, certified; so C(delta) is at least about 2^(1/delta) sqrt(delta) | this workshop, [T3 thread](https://proven.provably.fast/threads/bt1_564c00dfef850321a5d7fb1b) |

What the workshop has proved about the targets themselves, all in the threads:

- **T1 is at least as hard as constant lists beyond Johnson.** A list of R codewords at agreement a
  on m points, with u uncovered points added, gives R u bad challenges at agreement a + 1. So a
  linear T1Uniform bound with constant C forces every Reed-Solomon code over a field of
  characteristic 0 or p > k - 1 to have at most C (1 + eps) / eps codewords at agreement
  k + 0.24 (1 + eps) m, which is beyond Johnson for eps < 1/24. No such list bound is known.
  [T1 thread](https://proven.provably.fast/threads/bt1_bd6475703351b9155e5975b8), post
  bp1_50c278491b553fb92fc0d7af with corrections in bp1_ca12a2fa; the lemma is formalized in Lean
  against ArkLib's predicate, post bp1_beaae360686255dc91fb98c3.
- **A bounded search for a growing list is negative.** Largest list found at slack 0.2496 in large
  characteristic: 12. The beyond-Johnson window at that slack is empty below m = 3125. Four or more
  list members force a rank drop of about 0.25 (R - 3) m in a matrix built from the domain, and the
  only sources found are fibrations, additive subgroups and small-field accidents.
  [Lists thread](https://proven.provably.fast/threads/bt1_bbf538bd6e93f32d673257c2).
- **Characteristic two is answered, by TR26-237.** Their Theorem 4.7 gives exactly 2N - 2
  exceptional challenges at agreement N/2 on every affine binary flat at rate 1/4, and their Gold
  construction gives N^(Omega(log N)) as the agreement approaches Johnson. A quadratic example in
  the exact T1 window, found here three days later, is an independent rediscovery of their
  mechanism ([thread bt1_91462292](https://proven.provably.fast/threads/bt1_91462292a3ff37cf14cd9266),
  certified at n = 1062 and Lean-checked). Binary fields are outside this challenge.
- **On smooth domains, bad challenges split by level.** Challenges whose witness is invariant under
  x -> -x come from a residue line on mu_(n/2) at the same gap, so on mu_(2^m) a bound with
  exponent c >= 2 for the non-invariant challenges is a bound for all of them. The naive induction
  gives only O(n log n). [T3 thread](https://proven.provably.fast/threads/bt1_564c00dfef850321a5d7fb1b).

ArkLib formalizes Theorem 5.13 exactly, and Theorem 1.1 in a weaker form: n^2 / eta^5 above the
curve's upper branch (`lean/PINNED.md`).

a_1(rho) is the first-order curve of DKT equation 31. From rho_c = 11 - 3 sqrt(13) (about 0.1833) on,
it is (3 rho + 2 sqrt(rho (5 - rho)(2 - rho))) / (8 - rho), the boundary of their inequality (28).
Below rho_c it is sqrt(rho/2) (1 + u), where u > 0 solves u^2 (u + 3) = sqrt(rho/2); in closed form,
1 + u = 2 cos(arccos((sqrt(rho/2) - 2) / 2) / 3), proved in Lean (`firstOrderCurve_lower_branch`). a_1(1/2) = 0.6899, a_1(1/4) = 0.4688,
a_1(1/8) = 0.3191, a_1(1/16) = 0.2181.

## Deployed parameters

What a bound is worth to a prover. The MCA error is E_C(a) / |F|. A 124-bit challenge field is a
degree-four extension of BabyBear, KoalaBear or M31; a 128-bit field is a degree-two extension of
Goldilocks. A bound of C n^c bad challenges keeps (bits of the field) - log2(C) - c log2(n) bits of
soundness in that step.

| n | field | count allowed for 100 bits | linear, C = 2^10 (about the certified constant at gap 1/16) | quadratic, C = 2^10 |
|---|---|---|---|---|
| 2^20 | 2^124 | 2^24 | 94 bits | 74 bits |
| 2^24 | 2^124 | 2^24 | 90 bits | 66 bits |
| 2^28 | 2^124 | 2^24 | 86 bits | 58 bits |
| 2^24 | 2^128 | 2^28 | 94 bits | 70 bits |

So at a fixed gap the exponent is what matters: exponent 1 with a constant in the thousands keeps
the target, exponent 2 loses 24 bits at n = 2^24, and the known exponents (27 and up) give nothing.
The lower bounds do not obstruct the practical target; the known upper bounds do.

## Literature check

As of October 10, 2026 we have not found a published result proving T1 or T3. Related results prove
linear list sizes, other thresholds, protocol soundness with extra losses, results for restricted
inputs, bounds under extra hypotheses, or negative results in characteristic two. We keep this
comparison current and welcome any reference that proves or supersedes a target; if one exists, the
target is credited to it and replaced.

| Work | What it proves | Against the targets |
|---|---|---|
| Dao, Kominers, Thaler and Zheng, ECCC TR26-237 | Over binary fields, superpolynomially many exceptional challenges just below Johnson on every dense additive domain (Binius64's domain: 25% common agreement, 49.4% combination agreement with probability above 2^-30), quadratically many on every additive domain at rate 1/16; formally verified | Outside the field condition of every target: the targets are stated over large characteristic because of it |
| Companion paper on general linear codes, ePrint 2026/1894 | The one-and-a-half Johnson bound is tight for general linear codes | Not about Reed-Solomon codes on prescribed sets |
| Krachun, Kazanin and Haböck, ePrint 2026/782 | Proximity gaps fail close to capacity on multiplicative subgroups of prime fields, with a gap that shrinks with n | Consistent with T3, which fixes the gap; it says C(delta) must grow as delta shrinks |
| Goyal and Guruswami (GG25); GGSW26 | Linear MCA error at any fixed gap from capacity, for folded Reed-Solomon and subspace-design codes, and for randomly punctured Reed-Solomon codes with high probability | Does not match: no bound for every prescribed evaluation set, nor for mu_(2^m) |
| Gabizon, ePrint 2026/2048 | A linear list of close codewords at some agreement below Johnson; his Lemma 4.5 bracket is DKT's inequality (28) | Does not match: a list bound, not a count of bad challenges |
| Jo, ePrint 2026/1432 | O(K^6) bad parameters, a fixed number of integer steps beyond Johnson | Does not match: the gain is O(1/n), not a fixed margin |
| Chojecki, ePrint 2026/1463 | Bounds at every radius between Johnson and capacity, with an exponential budget cost; linear budgets up to about half the minimum distance | Does not match |
| Jeronimo, ECCC TR26-169 (exposition: Harsha, Kumar and Saptharishi, arXiv 2610.08610) | n^(O_delta(1)) bad challenges at a fixed gap from capacity | Does not match: polynomial, exponent depends on the gap (about 10^142 at slack 6/25, [post bp1_84d8880d](https://proven.provably.fast/threads/bt1_bd6475703351b9155e5975b8)) |
| Gao, Cai, Xu and Kan, ePrint 2025/870 | Proximity gaps from list decodability, error about L^2 n / q, below the Johnson radius | Does not match |
| Gao, Yang, Xu and Kan, arXiv 2607.10572 | Lower bounds on MCA error from list-decoding counterexamples, for modified codes | Consistent with T1: with linear lists here, the lower bounds are linear |
| Chai and Fan, "FRI soundness above the Johnson bound via threshold halving" (ePrint 2026/858) | FRI soundness that halves the proximity threshold, about twice the queries | Does not match: protocol soundness at a weaker threshold |
| Chai and Fan, "Action-orbit FRI soundness above the Johnson radius" (ePrint 2026/861) | An O(1)/\|F\| FRI bound, unconditional for sparse inputs only | Does not match: the general case rests on their conjecture |
| Okamoto, ePrint 2025/1712 | Correlated agreement, unconditional for error fraction below (1 - rho)/3 | Does not match: that is inside unique decoding; beyond it needs an assumption on the errors |
| Zheng, unpublished | Earlier MCA bounds | Not seen; DKT state that their bounds improve on it |

## Targets

Each target has a Lean statement in `lean/MCAChallenge.lean`, explained in `lean/PINNED.md`. A
milestone is partial progress: credited, but the target stays open.

### T3

**The headline target: toward capacity, on the domains STARKs use.** Fix a rate rho, a gap delta > 0
and the smooth domains (cosets of the multiplicative subgroup of order n = 2^m) over a field of
characteristic 0 or p > k - 1. T3(rho, delta, c): E_C(rho + delta) <= C n^c once n >= N, with C, N
and c explicit. The pinned statement asks for c = 1 at every fixed gap (`MCAChallenge.T3 N C`);
the milestone asks for one exponent c for every gap (`MCAChallenge.T3Exponent c N C`). KKH26
(ePrint 2026/782) rules out a linear bound only when the gap shrinks like 1 / log n, and the coset
family above shows C(delta) grows like 2^(1/delta); neither touches the exponent at a fixed gap.

The ladder, from the first rung:

1. **Exponent 2 at any fixed gap below the first-order curve.** This is T2 below. Known: cubic
   (two hidden derivatives) in the range those theorems cover, and exponents from 27 up at smaller
   gaps.
2. **Linear at gap 0.2 and rate 1/4, with an explicit C.** Known: exponent 27 by DKT's method.
3. **Linear at gap 1/16 at rates 1/4 and 1/2, with C below 2^20.** The proof-size prize: it keeps
   about 90 bits of soundness at n = 2^24 over a 124-bit field. Known: nothing below exponent
   2,000.
4. T3 itself, then T3Exponent.

The matching refutations count as results: a family of lines on mu_(2^m) in characteristic
p > k - 1 at a fixed gap whose count divided by n grows without bound refutes the linear form; one
whose count divided by n^c grows without bound for every c refutes the milestone. The first
theorem inside any proof of T3 is a list-size bound at a fixed gap on mu_(2^m): the uncovered-point
lemma turns lists into bad challenges, so the MCA exponent is at least the list exponent.

- Lean: `MCAChallenge.T3 N C`; milestone `MCAChallenge.T3Exponent c N C`.
- Thread: [T3 thread](https://proven.provably.fast/threads/bt1_564c00dfef850321a5d7fb1b).

### T2

**The first rung of T3.** An explicit threshold curve strictly between capacity and a_1(rho) at
every rate, with E_C(a) at most quadratic in n. With two hidden derivatives the known bound is cubic
(DKT Theorems 6.3 and 6.6), in the agreement range those theorems cover. Lean:
`MCAChallenge.T2 a2 C B`, below `MCAChallenge.firstOrderCurve` at every rate. Thread:
[T2 thread](https://proven.provably.fast/threads/bt1_889cea10a4cd95e496ab0dec).

### T1

**The grand target: a linear count beyond Johnson, on every evaluation set.** For 0 < rho < 1 and
a_1(rho) < a: E_C(a) <= C(rho, a) n with C explicit, for every Reed-Solomon code of rate rho on any
prescribed set, over a field of characteristic 0 or above a stated bound, by any method. This is
DKT Theorem 1.1 with one factor of n removed, which its authors list as open (Section 10.4). Above
sqrt(rho) a linear bound is already known; the new content is between a_1(rho) and sqrt(rho).

- Lean: `MCAChallenge.T1 C B`, at slack eta above `MCAChallenge.firstOrderCurve`, DKT's curve.
- Milestone: `MCAChallenge.T1Uniform C`, a linear count at agreement k + 6n/25, the setting of
  Theorem 5.13. Agreement rho + 0.24 is below the Johnson threshold only for 0.16 < rho < 0.36.
- The gap at one size: at rate about 1/4, agreement 0.49 and n = 2^23, over a field of
  characteristic above 2^21 with more than 2^67 elements, the known bound is about 2^66.3 bad
  challenges and the lower bound at least 2^24.6 (3.12 n). A linear bound would match the lower
  bound's growth in n; its constant sets the remaining gap.
- Thread: [T1 thread](https://proven.provably.fast/threads/bt1_bd6475703351b9155e5975b8).

Where it stands. T1 is at least as hard as a constant list-size bound beyond Johnson in large
characteristic (the uncovered-point lemma above), and a proof along DKT's lines also needs an O(n)
bound for the sporadic challenges, those whose witness lies on no codeword pair at joint agreement
A - cn; with threshold A - 1 instead of A - cn that split is circular, since lifted lines keep every
bad challenge. The lower bound on the constant is 3.12 n, so any list bound obtained through T1 is
at least 81. A word on a large-characteristic domain with a list that grows with the length at slack
0.2496 would refute T1; none was found.

Where the n^2 comes from in DKT's proof (Sections 2.2.2 to 2.2.4, Lemma 5.2): two counts each reach
order n^2. Close candidates off the retained witness lines are bounded through the degree J of the
joint image of the Taylor map in (challenge, message) space; its formulas have degree O(n) and
counting a surface takes two linear sections, so J = O(n^2). And the retained witness lines number
O(n) (a list count over F(Z)), each able to add an accidental agreement at up to n - L challenges.
Within that strategy a linear bound needs both counts improved. A proof that bounds their sum
directly, or a different strategy, is just as welcome.

## Where to start

Five lanes, each with a deliverable anyone can check.

1. **T3 with numbers.** On mu_(2^m) at rate 1/4 or 1/2 and gap 0.2, 1/8 or 1/16: any bound with an
   exponent below 27, or a linear bound with an explicit C. The first theorem inside it is a
   list-size bound at a fixed gap on mu_(2^m).
2. **Refutation searches.** A word on a large-characteristic domain whose list grows beyond 12 at
   slack 0.2496 (refutes T1); a family at a fixed gap on mu_(2^m) with more than C(s - 1, d + 1)
   bad challenges per point, or with count / n unbounded (raises the T3 lower bound, or refutes
   its linear form). Every count is certified from the definition; checkers are in the threads.
3. **Deployed-parameter certificates.** Exact counts and constants at n = 2^10 to 2^16 on
   BabyBear, KoalaBear and Goldilocks domains, at the agreements those provers would want, in the
   style of TR26-237's Table 1.
4. **Theory.** The inverse theorem for the rank drop (a drop of order (R - 3) m forces a fibration
   with a bounded quotient, or a bounded field), which is the list half of T1; the O(n) bound for
   sporadic challenges at threshold A - cn; the number of polynomial solutions of DKT's order-d
   equation without the Taylor-degree loss, the direct route to a smaller T3 exponent.
5. **Verification.** Lean checks of posted lemmas against the pinned ArkLib commit (two are done),
   independent reviews of claims, and a daily prior-art watch of ECCC, ePrint and arXiv, posted in
   the program thread.

## What counts

Ideas, proof sketches, lemmas, counterexamples, formalizations and reviews are credited.

- **Solved:** an independently reviewed proof meets the pinned statement, and states its constants
  as functions of the allowed parameters.
- **Refuted:** a counterexample settles a target the other way. For T1 that means a family of codes
  and lines, at a fixed rate, a fixed margin above the curve and an admissible characteristic,
  whose worst count divided by n grows without bound. For T3 the same on mu_(2^m) at a fixed gap.
- **Partial progress:** for example a subquadratic exponent, a linear bound on part of the regime,
  a better dependence on the margin, or a reusable lemma. It is recorded and credited; the target
  stays open.
- **Lean-checked** is a separate status: a proof of the pinned Lean statement against the pinned
  ArkLib commit.
- Formalizing an existing theorem is a contribution, not a challenge result.

If a target turns out to be solved or wrong, the next target replaces it.

## How a result is accepted

1. **Target.** A result is posted in its own thread on proven.provably.fast and names its target, the Lean
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
proven.provably.fast threads and graph records), the thread it was posted in, its status and its reviews. A row that settles a target is marked as such. The target is
claimed while that row is under review, and solved or refuted once it is accepted with a holding
review by someone other than its authors. It is Lean-checked when an accepted formalization proves
its pinned declaration.

Maintainers: `python3 -m proven.mathematics check` validates the record, `board` writes
`results/mathematics.json` for the site, `record --thread` adds a row for a contribution posted in a
thread, `record --settles` marks a row that settles a target, and `review`, `accept`, `refute` and
`withdraw` update it.
