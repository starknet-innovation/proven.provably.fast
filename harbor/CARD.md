---
license: apache-2.0
task_categories:
- other
tags:
- harbor
- rl-environment
- reinforcement-learning
- verifiable-reward
- mathematics
- coding-theory
- lean4
- theorem-proving
pretty_name: "proven.provably.fast: bad challenges as Harbor environments"
---

# Bad challenges for Reed-Solomon checks, as Harbor environments

> A dataset card ready for Hugging Face. Publishing is a maintainers' decision; until then this
> file documents the environment in the form that audience expects.

Smaller STARK proofs depend on one number: how many random challenges can fool a Reed-Solomon
check. Nobody knows it on the domains provers use. This dataset packages that open problem, from
[proven.provably.fast](https://proven.provably.fast/), as [Harbor](https://github.com/harbor-framework/harbor)
environments with a **verifiable reward**: a score computed in a sandbox the agent never touches.

Two kinds of task, the same format as [FineEnvs/openai-math](https://huggingface.co/datasets/FineEnvs/openai-math):

| Task | Reward | Known |
|---|---|---|
| `count-babybear-m8`, `-m9`, `-m10`: find a line (two words) on the subgroup of order 2^m in BabyBear with as many bad challenges as possible at rate 1/2 and gap 1/8, and list a witness per challenge | certified distinct bad challenges / (16 n), a graded score | floor 3n/2 + 4 from four codeword pairs (reward 0.095); the challenge's first goal says at most 16 n |
| `lean-t3-goal`, `lean-t3`, `lean-t3-exponent`, `lean-t1-uniform`, `lean-t1`, `lean-t2`: prove one pinned statement in Lean 4 against ArkLib, supplying its constants in closed form | 1 if Comparator accepts the proof and every constant is a closed form, else 0 | all open; expect 0 |

## How a task works

The agent gets a sandbox with no internet. Count tasks: Python with numpy, the starter kit's
checker and the floor construction; the agent writes `/workspace/instance.json`. Lean tasks: Lean
4.34, ArkLib with its Mathlib and the pinned statements, prebuilt; the agent writes
`/workspace/Submission.lean`.

When the agent finishes, one plain file is copied to a fresh sandbox. For a count task the
verifier checks the field, k, A and the domain (every point an n-th root of unity), then
re-certifies every listed challenge from the definition: the polynomial of degree below k through
the witness agrees with f + z g on at least A points, and f and g are not both interpolable there.
For a Lean task the verifier runs Comparator (exact statement, three standard axioms, kernel
replay) and then reads each constant's definition: choice, search, suprema and limits are refused.

## Why the reward is graded

A proof checker says yes or no. For an open problem that is a weak training signal; the FineEnvs
card says as much. Counting bad challenges has a natural "how far did you get": every extra
certified challenge raises the score, and a line with more than 16 n at some n is strong evidence
against the current goal and a record on proven.provably.fast, where whoever found it is credited.

## Run

```bash
pip install "harbor[docker]>=0.24"
harbor run -p tasks -i count-babybear-m8 -a oracle -e docker                       # the floor
harbor run -p tasks -i count-babybear-m8 -a claude-code -m anthropic/claude-sonnet-5-5
```

Count tasks need a small Python image; Lean tasks build a 13 GB image and need a 12 GB sandbox.

## Validation

- The oracle (the four-pair floor construction) scores 0.0947 on `count-babybear-m8`: 388 certified
  bad challenges at n = 256, exactly 3n/2 + 4.
- Nine reward-hacking probes (`probes.py`: planted reward files, a symlinked instance, a tampered
  domain, another field, a lowered A, oversized witnesses, duplicates, too many listed, random
  challenges) score 0 or the floor, each with the intended reason.
- The verifier agrees with the kit's pure-Python checker on every instance in the test suite.
- The Lean grader is FineEnvs/openai-math's, adapted; the closed-form check was run on six sample
  constants. The Lean image recipe is written and not yet built.

## Credit and license

Statements, kit and tasks: proven.provably.fast maintainers, Apache-2.0. The verifier design and
the Lean grader follow FineEnvs/openai-math (Apache-2.0). Lean, Mathlib, ArkLib, Comparator and
lean4export are Apache-2.0; landrun is MIT. Results belong on the research record at
https://proven.provably.fast/workshop, where a score is evidence and a review decides.
