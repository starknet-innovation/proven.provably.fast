# Raise the floor: bad challenges at rate 1/2 and gap 1/8 on the subgroup of order 512

This is task 2 of the mathematics challenge on https://proven.provably.fast/ (statement:
https://proven.provably.fast/MATHEMATICS.md), in a sandbox. Find a line with as many bad
challenges as you can, and certify them.

## The setting

- The field is BabyBear, p = 2013265921. The domain is the multiplicative subgroup of order
  n = 512, the n-th roots of unity, the evaluation set STARK provers use.
- A word is a list of n field elements, one per domain point. A codeword is the evaluation of a
  polynomial of degree below k = 256 (rate 1/2, the exact k provers use).
- A line is a pair of words (f, g); a challenge z gives the word f + z g.
- A challenge z is **bad** at agreement A = 320 (gap 1/8 above the rate) if some polynomial of
  degree below k agrees with f + z g on at least A points S, while f and g are not both
  interpolable by polynomials of degree below k on the whole of S. Bad challenges are the ones that
  can fool a Reed-Solomon check; smaller STARK proofs need fewer of them.

## What is known

- The floor, one line with 772 bad challenges, 3n/2 + 4: /opt/proven/baseline.py builds it from
  four codeword pairs that agree with (f, g) on sets of A - 1 points; every point outside such a set
  gives one bad challenge, one pair alone gives 3n/8 + 1, and a fifth pair is not expected to fit
  by a dimension count (not a proof: whether the subgroup's structure allows one is open). The
  baseline is public, so reproducing it is not progress; anything above 772 raises the floor.
- The goal of the challenge is at most 16 n bad challenges on every line, for all large n. A line
  with more than 16 n = 8192 certified bad challenges at this n does not refute the goal by itself,
  since the goal allows a threshold in n, but it is the strongest evidence this task can give, and
  a record: post it with its SHA-256 in the T3 thread on proven.provably.fast.
- Known constructions that give many bad challenges at other k (cosets of a subgroup of the
  domain, k = d n / s + 2) vanish at the exact k = n / 2 asked here. Something new is needed.

## What to submit

Write `/workspace/instance.json`, the instance format of the starter kit (`/opt/proven/certify.py`):

```json
{"p": 2013265921, "k": 256, "A": 320,
 "domain": [x_0, ..., x_{n-1}],
 "f": [f_0, ..., f_{n-1}], "g": [g_0, ..., g_{n-1}],
 "challenges": [{"z": 12345, "witness": [i_1, ..., i_k]}, ...]}
```

- `domain`: the n points of the subgroup of order n, each in [1, p), distinct, in any order.
- `f`, `g`: n integers in [0, p).
- `challenges`: at most 12288 entries. Each gives a challenge `z` in [0, p) and a witness: k
  distinct indices into the domain. The verifier interpolates the polynomial P of degree below k
  through f + z g at the witness points, finds every point where P agrees with f + z g, checks that
  there are at least A of them, and checks that f and g are not both interpolable there. A challenge
  that fails is not counted; the rest are.
- Check your own work first: `python3 /opt/proven/certify.py /workspace/instance.json`.

## Grading

The file is copied to a fresh machine whose code and trusted inputs are isolated from you, and
graded from the definition.

- `reward` = certified distinct bad challenges / (16 n), capped at 1: a graded terminal reward. The
  floor scores about 0.095.
- `reward.json` also carries the uncapped `certified_bad` (the authoritative number), `bad_per_n`,
  `over_floor`, `beats_floor` (1 above 772) and `above_goal` (1 above 16 n). A reward of 1 is not
  a refutation: only `above_goal` = 1 is evidence against the goal, and only at this n.
- Invalid submissions score 0 with a reason; a broken verifier writes no reward and the run is
  reported as an error, never as a score.
- An instance with the wrong field, k, A or domain, or a malformed challenge, scores 0.

## Environment

- Python 3.12 with numpy; `/opt/proven/certify.py` (the kit's checker, standard library only) and
  `/opt/proven/baseline.py` (the floor). No internet.
- Certifying at n = 512 takes the kit about 2 minutes per 1,000 challenges in pure Python.
