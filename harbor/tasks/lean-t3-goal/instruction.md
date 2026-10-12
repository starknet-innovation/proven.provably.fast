# proven.provably.fast: prove `MCAChallenge.T3Goal`

Prove one pinned statement of the mathematics challenge on https://proven.provably.fast/ in Lean 4
against the pinned ArkLib commit, with a proof the Lean kernel accepts. The problem in words, what
is known and the discussion are at https://proven.provably.fast/MATHEMATICS.md; this task is
first goal.

The pinned statement, from `lean/MCAChallenge.lean` (installed and prebuilt here):

```lean
/-- The first goal of T3, in the numbers the page states: rate `1/2` with the exact `k = n / 2`
that provers use, gap `1/8` (`A ≥ 5 n / 8`), constant `16`, on smooth domains, once `n ≥ N`. A
result supplies `N`. `T3Goal_of_T3` shows that a T3 result with `C (1/8) ≤ 16` gives it. -/
def T3Goal (N : ℕ) : Prop :=
  ∀ (n k A : ℕ), N ≤ n → 0 < k → 2 * k = n → 5 * n ≤ 8 * A → A ≤ n →
    ∀ (F : Type u) [Field F] [DecidableEq F], (ringChar F = 0 ∨ k - 1 < ringChar F) →
      ∀ domain : Fin n ↪ F, IsSmoothDomain domain →
        LineExactAgreementBound domain k A (16 * n)
```

The challenge is `T3Goal`, also at `/opt/proven-math/challenges/T3Goal.lean`:

```lean
import MCAChallenge

/-! The first goal, `MCAChallenge.T3Goal`: at rate 1/2 with the exact `k = n / 2`, gap 1/8, on
smooth domains, at most `16 n` bad challenges once `n ≥ N`. Replace both `sorry`s: `N` in closed
form, then the proof. Add definitions and lemmas after these two declarations or in modules under
`Submission/`; change nothing else. -/

/-- The threshold: the goal holds for every `n ≥ N`. -/
def N : ℕ := sorry

theorem solution.{u} : MCAChallenge.T3Goal.{u} N := sorry
```

## What to submit

Write `/workspace/Submission.lean`. Start from a copy of the challenge:

```bash
cp /opt/proven-math/challenges/T3Goal.lean /workspace/Submission.lean
```

then replace every `sorry`. The file is graded on four things:

- **Same statement.** `solution` must keep exactly the statement shown above: same name, universe,
  binders and types. The parameters `N` keep their names and types; you supply their
  bodies.
- **Parameters in closed form.** A parameter is a term built from numerals, arithmetic, powers and
  roots, `exp`, `log`, trigonometric functions and their inverses, floor and ceiling, `min`,
  `max`, case splits on comparisons, and the pinned definitions. `Classical.choose`, `Nat.find`,
  `sSup`, `sInf`, limits and the like are refused, even when the proof is accepted: a result names
  its constants.
- **Standard axioms only.** Proofs may use only `propext`, `Quot.sound` and `Classical.choice`.
  `sorry`, `admit`, new `axiom`s and `native_decide` (it introduces an axiom of its own) are rejected.
- **Kernel-checked.** The proof is re-checked by the Lean kernel, not just the elaborator.

Put new lemmas after the parameter definitions, or in modules under `/workspace/Submission/`
(module names `Submission.Foo`) imported from `Submission.lean`. Only `.lean` files at those two
paths are graded. You may import any module of the pinned packages (ArkLib and its Mathlib).

## Environment

- Lean `v4.34.0`, ArkLib at `35ddcaa8` with its pinned Mathlib, and `MCAChallenge` are
  installed and prebuilt; `/workspace` is a Lake project. Check your work with
  `cd /workspace && lake build Submission`, and `#print axioms solution`.
- The sandbox has 4 CPUs and 12 GB of memory; `LEAN_NUM_THREADS=3` bounds `lake build`.
- There is no internet access.

## Grading

When you finish, `Submission.lean` and `Submission/**.lean` are copied to a fresh machine and
checked with [Comparator](https://github.com/leanprover/comparator), the Lean FRO's proof checker,
then the parameters are read for closed form. The reward is 1 if both pass and 0 otherwise. A
partial proof scores 0. The targets are open problems: a reward of 1 is a result, and the file
should also be posted on proven.provably.fast for review and credit.
