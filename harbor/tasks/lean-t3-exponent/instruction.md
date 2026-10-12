# proven.provably.fast: prove `MCAChallenge.T3Exponent`

Prove one pinned statement of the mathematics challenge on https://proven.provably.fast/ in Lean 4
against the pinned ArkLib commit, with a proof the Lean kernel accepts. The problem in words, what
is known and the discussion are at https://proven.provably.fast/MATHEMATICS.md; this task is
milestone.

The pinned statement, from `lean/MCAChallenge.lean` (installed and prebuilt here):

```lean
/-- A milestone toward T3: at every gap `δ > 0` above capacity, on smooth domains, at most
`C δ * n ^ c` bad challenges once `n ≥ N δ`, with the exponent `c` independent of `δ`. Known
bounds for arbitrary domains have exponent `d_δ + 1`, `d_δ = ⌈exp(1.5 / δ)⌉` for `δ < 0.24`
(`exists_capacity_lineAgreement`). A result supplies `c`, `N` and `C`. -/
def T3Exponent (c : ℕ) (N : ℝ → ℕ) (C : ℝ → ℝ) : Prop :=
  ∀ (δ : ℝ) (n k A : ℕ), 0 < δ → N δ ≤ n → 0 < k → (k : ℝ) + δ * n ≤ A → A ≤ n →
    ∀ (F : Type u) [Field F] [DecidableEq F], (ringChar F = 0 ∨ k - 1 < ringChar F) →
      ∀ domain : Fin n ↪ F, IsSmoothDomain domain →
        LineExactAgreementBound domain k A (C δ * n ^ c)
```

The challenge is `T3Exponent`, also at `/opt/proven-math/challenges/T3Exponent.lean`:

```lean
import MCAChallenge

/-! The milestone toward T3, `MCAChallenge.T3Exponent`: one exponent `c` for every gap. Replace
every `sorry`: `c` a numeral, `N` and `C` in closed form, then the proof. Add definitions and lemmas
after these declarations or in modules under `Submission/`; change nothing else. -/

/-- The exponent, the same at every gap. -/
def c : ℕ := sorry

/-- The threshold at gap `δ`. -/
noncomputable def N : ℝ → ℕ := sorry

/-- The constant at gap `δ`. -/
noncomputable def C : ℝ → ℝ := sorry

theorem solution.{u} : MCAChallenge.T3Exponent.{u} c N C := sorry
```

## What to submit

Write `/workspace/Submission.lean`. Start from a copy of the challenge:

```bash
cp /opt/proven-math/challenges/T3Exponent.lean /workspace/Submission.lean
```

then replace every `sorry`. The file is graded on four things:

- **Same statement.** `solution` must keep exactly the statement shown above: same name, universe,
  binders and types. The parameters `c` and `N` and `C` keep their names and types; you supply their
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
