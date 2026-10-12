# Controls for the Lean verifier

The Lean tasks have no oracle, since the targets are open. These controls exercise the verifier
flow (Comparator, then `HoleCheck.lean`) on a statement ArkLib does prove: T1Uniform's shape with a
quadratic bound, `MCAChallenge.baseline_T1Uniform_quadratic`, with the constant as the hole.

| Solution | Expected | Why |
|---|---|---|
| `solutions/ok.lean` | accepted, holes ok | `C := 1325775`, the proof from ArkLib |
| `Control.lean` itself | refused: `sorryAx` | both `sorry`s left in |
| `solutions/weak.lean` | refused: statement do not match | same name and universe, another statement |
| `solutions/choice.lean` | accepted, holes denied | `C := Classical.choose ...`: Comparator checks the hole's type only; the hole check refuses choice |

`run.sh PROJECT` runs the four natively (see the script for what PROJECT needs). In the task image
the same flow is `tests/grade.py`, which adds the sandbox, the unprivileged user and the network
block.

Run on 2026-10-11 on a Mac (Lean 4.34.0, the pinned ArkLib, Comparator d03acab with
`fake-landrun.sh`, so no sandbox): ok accepted in 105 s with `HOLES OK`; sorry refused in 72 s;
weak refused in 47 s; choice accepted by Comparator in 126 s and refused by the hole check
(`DENIED: [Classical.choose]`). The T3Goal template with its `sorry`s is refused in 45 s.
