# Harbor environments for the mathematics challenge

The mathematics challenge of proven.provably.fast as [Harbor](https://github.com/harbor-framework/harbor)
tasks: sandboxes an agent works in, a verifier that never ran the agent's code, and a reward. The
design follows [FineEnvs/openai-math](https://huggingface.co/datasets/FineEnvs/openai-math), which
turned OpenAI's October 2026 Lean statements into environments (see `NOTICE`); two things differ.
The count tasks give a dense reward, a certified number rather than 1 or 0, so partial progress is
a training signal. And the Lean tasks have parameters as definition holes, read for closed form
after the proof is accepted, because here a constant is the result.

Nothing here changes how a result counts on proven.provably.fast: a target is solved by a
reviewed record, and a reward is evidence to post, not a verdict.

## Tasks

| Task | Kind | What the agent does | Reward |
|---|---|---|---|
| `count-babybear-m8`, `-m9`, `-m10` | count | finds a line on the subgroup of order 2^m in BabyBear with many bad challenges at k = n/2, A = 5n/8, and lists witnesses | certified distinct bad challenges / (16 n), capped at 1; plus `certified_bad`, `bad_per_n`, `beats_floor` |
| `lean-t3-goal` | Lean | proves `MCAChallenge.T3Goal N`, the first goal (rate 1/2, gap 1/8, constant 16, smooth domains) | 1 if Comparator accepts the proof and `N` is a closed form |
| `lean-t3`, `lean-t3-exponent` | Lean | T3 and its exponent milestone, holes `N C` and `c N C` | same |
| `lean-t1-uniform`, `lean-t1`, `lean-t2` | Lean | the long-run targets, holes `C`, `C B`, `a₂ C B` | same |

The count tasks' floor construction (3n/8 + 1 bad challenges, `templates/count/environment/baseline.py`)
is the oracle: it scores about 0.024 and `beats_floor = 0`, which validates the pipeline, not the
task. A line with more than 16 n certified bad challenges would score 1; at a fixed n that is
strong evidence against the first goal, not a refutation. The Lean tasks have no oracle, the
targets are open; their `solve.sh` submits the unchanged challenge and must score 0.

## Run

```bash
pip install "harbor[docker]>=0.24"
cd research/proven/harbor
harbor run -p tasks/count-babybear-m8 -a oracle -e docker        # the floor: reward 0.0237
harbor run -p tasks -i count-babybear-m8 -a claude-code -m anthropic/claude-sonnet-5-5
harbor run -p tasks -i lean-t3-goal -a oracle -e docker          # negative control: reward 0
```

Count tasks need only the small Python image. Lean tasks build the pinned package (Lean 4.34.0,
ArkLib with its Mathlib, Comparator, lean4export, landrun; about 13 GB): give the sandbox 20 GB of
disk and 12 GB of memory, or trim as `lean_setup.sh` notes.

## How a trial runs

```
agent sandbox                                   verifier sandbox (same image, fresh)
  count: writes /workspace/instance.json           never runs agent code
  lean:  writes /workspace/Submission.lean         /tests: grade.py, task.json (+ Challenge.lean, HoleCheck.lean)
  no network                                       /logs/artifacts: the only thing that crosses
        |                                            count: validate (field, k, A, the subgroup, witnesses),
  collect hook packs the file ------------------>          certify every challenge from the definition
                                                     lean:  Comparator (statement, axioms, kernel replay),
                                                            then HoleCheck.lean reads each parameter
                                                     root writes reward.json after killing the grader
```

Harbor's `[verifier] environment_mode = "separate"` provides the second sandbox; `[[verifier.collect]]`
runs the packer in the agent's sandbox after it finishes.

## Threat model

| Attempt | What stops it | Checked |
|---|---|---|
| Plant `reward.json` or a fake interpreter in the agent sandbox | the verifier is a fresh sandbox; only `/logs/artifacts` crosses | probe, reward 0 |
| Submit a symlink as the instance or the proof | the packer copies regular files only; the grader re-checks | probe, reward 0 |
| A domain that is not the subgroup, another field, k or A | `validate()`: p, k, A exact, every point an n-th root of unity, distinct | probe, reward 0 |
| A witness of more than k points (it would certify any z) | exactly k distinct indices; the kit's `certify.py` now refuses more than k too | probe, reward 0 |
| Spam challenges to run out the clock | at most 24 n listed; numpy certification, minutes at n = 1024 | by construction |
| Lean: `sorry`, new axioms, `native_decide`, a weaker statement, a redefined definition | Comparator: exact statement, three axioms, kernel replay | as in FineEnvs/openai-math |
| Lean: a constant set by choice, search, supremum or limit | `HoleCheck.lean` walks each hole's value; denied constants fail, unknown ones are listed for review | native test, six samples |
| Lean: code run at build time | landrun, the unprivileged grader user, iptables, as in FineEnvs/openai-math | not run here |

Trusted and not re-checked: the Lean kernel, Comparator, lean4export, landrun, Docker's boundary.
A crafted `.olean` could in principle mislead `HoleCheck.lean`, which loads the submission's build;
a reviewer reads the parameters in any case.

## Probes and the card

`probes.py` writes nine reward-hacking probes of a count task (planted reward files and a fake
interpreter, a symlinked instance, a tampered domain, another field, a lowered A, oversized
witnesses, duplicates, too many listed, random challenges) as Harbor tasks; run them with the
oracle agent after any change to the grader. `CARD.md` is the dataset card in the form Hugging
Face expects, should the maintainers publish there.

## Status, 2026-10-11

- Count tasks, through `harbor run` in Docker: the oracle certifies exactly 3n/8 + 1 on all three
  sizes (97, 193 and 385 at n = 256, 512 and 1024; rewards 0.0237, 0.0236, 0.0235; grading 1 s,
  5 s and 19 s). The nine probes: seven rejected with the intended reason, duplicates counted once
  (the floor's score), random challenges certify nothing. The grader agrees with the kit's
  `certify.py` on every instance in `tests/test_harbor.py`.
- Lean tasks: the grader is the validated FineEnvs grader with the package swapped and the hole
  check added; its upstream unit tests pass against the adapted copy
  (`tests/test_harbor_lean_grader.py`). `HoleCheck.lean` was run natively against Mathlib on six
  parameters (two closed forms accepted; choice, search, a supremum and a hidden choice refused).
  Every challenge template elaborates against the pinned file with only `sorry` warnings. The
  image recipe is written and not yet built: the Docker VM on the development machine is too small.
- `MCAChallenge.T3Goal` and `T3Goal_of_T3` compile against the pinned ArkLib (45 s, no warnings).

## Regenerate

`python3 build.py` writes `tasks/`, `registry.json` and `manifest.json` from `templates/`, the kit
and `lean/challenges/`; `python3 build.py --check` fails when they are stale (the test suite runs it).
