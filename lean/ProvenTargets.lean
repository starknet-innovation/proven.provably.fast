/-
proven.provably.fast: the pinned statements of the mathematics targets T1, T2 and T3.

Each target is a `Prop` about Reed-Solomon line mutual correlated agreement on a prescribed
evaluation set, stated with ArkLib's `LineExactAgreementBound`: for every received line `f + z g`,
one exceptional set of at most `B` challenges, outside of which every polynomial of degree below
`k` agreeing with the line in at least `A` places splits as `P₀ + z P₁` with the same agreement set
for `f` and `g`.

A challenge result proves one target for explicit parameters (a closed-form constant, never one
obtained by choice), compiles against the ArkLib commit pinned in `lakefile.toml`, and depends on
no axioms beyond `propext`, `Classical.choice` and `Quot.sound` (check with `#print axioms`).
The `baseline_*` theorems at the end show that ArkLib's proven quadratic bounds have exactly the
shape of T1 with one more factor of `n`.
-/
import ArkLib.Data.CodingTheory.ReedSolomon.MutualCorrelatedAgreement.FirstOrder.UniformLineMca
import ArkLib.Data.CodingTheory.ReedSolomon.MutualCorrelatedAgreement.FirstOrder.RateBounds
import ArkLib.Data.CodingTheory.ReedSolomon.MutualCorrelatedAgreement.Capacity
import Mathlib.RingTheory.RootsOfUnity.PrimitiveRoots

namespace ProvenTargets

open Polynomial ReedSolomon ReedSolomon.HiddenDerivative

universe u

/-- T1, uniform form: ArkLib's `ReedSolomon.exists_uniformFirstOrder_lineMca` (Dao, Kominers and
Thaler, Theorem 5.13: `1325775 * n ^ 2` bad challenges at agreement `k + 6 n / 25`) with the bound
replaced by `C * n`. A result names a numeral `C`. -/
def T1Uniform (C : ℝ) : Prop :=
  ∀ (n k A : ℕ), 2 ≤ n → 0 < k → A ≤ n → (k : ℝ) + (6 / 25 : ℝ) * n ≤ A →
    ∀ (F : Type u) [Field F] [DecidableEq F], (ringChar F = 0 ∨ k - 1 < ringChar F) →
      ∀ domain : Fin n ↪ F, LineExactAgreementBound domain k A (C * n)

/-- T1, general form: a linear bound at every rate `ρ` and slack `η` above the first-order
threshold `firstOrderRateThreshold ρ`, the threshold of ArkLib's
`ReedSolomon.automaticFirstOrder_rate_bounds` (whose proven bound is `C_E(ρ) n² / η⁵`).
A result names the constant `C ρ η` and the characteristic bound `B ρ η` in closed form. -/
def T1 (C : ℝ → ℝ → ℝ) (B : ℝ → ℝ → ℕ) : Prop :=
  ∀ (rho eta : ℝ) (n k A : ℕ), 0 < rho → rho < 1 → 0 < eta →
    firstOrderRateThreshold rho + eta < 1 →
    0 < n → 2 ≤ k → (k : ℝ) ≤ rho * n →
    (firstOrderRateThreshold rho + eta) * n ≤ A → A ≤ n →
    ∀ (F : Type u) [Field F] [DecidableEq F],
      (ringChar F = 0 ∨ max (k - 1) (B rho eta) < ringChar F) →
      ∀ domain : Fin n ↪ F, LineExactAgreementBound domain k A (C rho eta * n)

/-- T2: a threshold curve strictly between capacity and the first-order threshold at every rate,
with a count at most quadratic in `n`. A result names `a₂`, `C` and `B` in closed form. -/
def T2 (a₂ : ℝ → ℝ) (C : ℝ → ℝ → ℝ) (B : ℝ → ℝ → ℕ) : Prop :=
  (∀ rho : ℝ, 0 < rho → rho < 1 → rho < a₂ rho ∧ a₂ rho < firstOrderRateThreshold rho) ∧
  ∀ (rho eta : ℝ) (n k A : ℕ), 0 < rho → rho < 1 → 0 < eta → a₂ rho + eta < 1 →
    0 < n → 2 ≤ k → (k : ℝ) ≤ rho * n →
    (a₂ rho + eta) * n ≤ A → A ≤ n →
    ∀ (F : Type u) [Field F] [DecidableEq F],
      (ringChar F = 0 ∨ max (k - 1) (B rho eta) < ringChar F) →
      ∀ domain : Fin n ↪ F, LineExactAgreementBound domain k A (C rho eta * n ^ 2)

/-- A smooth evaluation domain: a multiplicative coset `s ⟨ω⟩` of the subgroup of order `n = 2 ^ m`. -/
def IsSmoothDomain {F : Type*} [Field F] {n : ℕ} (domain : Fin n ↪ F) : Prop :=
  ∃ (m : ℕ) (ω s : F), n = 2 ^ m ∧ IsPrimitiveRoot ω n ∧ s ≠ 0 ∧
    ∀ i : Fin n, domain i = s * ω ^ (i : ℕ)

/-- T3: at every fixed gap `δ` above capacity, on smooth domains, a count `C_δ n ^ c` whose exponent
`c` does not depend on `δ`. `T3 1` is the full ambition. Known bounds for arbitrary domains have
exponent `d_δ + 1` with `d_δ = ⌈exp(1.5 / δ)⌉` for `δ < 0.24` (`exists_capacity_lineAgreement`). -/
def T3 (c : ℕ) : Prop :=
  ∀ δ : ℝ, 0 < δ → ∃ (N : ℕ) (C : ℝ),
    ∀ (n k A : ℕ), N ≤ n → 0 < k → (k : ℝ) + δ * n ≤ A → A ≤ n →
      ∀ (F : Type u) [Field F] [DecidableEq F], (ringChar F = 0 ∨ k - 1 < ringChar F) →
        ∀ domain : Fin n ↪ F, IsSmoothDomain domain →
          LineExactAgreementBound domain k A (C * n ^ c)

/-! ## Baselines: what ArkLib proves today, in the same shape -/

/-- `LineExactAgreementBound` does not depend on the decidable-equality instance. -/
theorem lineExactAgreementBound_dec {F ι : Type*} [Field F] [Fintype ι] (d₁ d₂ : DecidableEq F)
    {domain : ι ↪ F} {k A : ℕ} {B : ℝ} (h : @LineExactAgreementBound F ι _ d₁ _ domain k A B) :
    @LineExactAgreementBound F ι _ d₂ _ domain k A B := by
  convert h

/-- T1's uniform statement with `1325775 * n ^ 2` in place of `C * n` holds today. -/
theorem baseline_T1Uniform_quadratic :
    ∀ (n k A : ℕ), 2 ≤ n → 0 < k → A ≤ n → (k : ℝ) + (6 / 25 : ℝ) * n ≤ A →
      ∀ (F : Type u) [Field F] [DecidableEq F], (ringChar F = 0 ∨ k - 1 < ringChar F) →
        ∀ domain : Fin n ↪ F, LineExactAgreementBound domain k A (1325775 * (n : ℝ) ^ 2) := by
  intro n k A hn hk hAn hgap F _ _ hchar domain
  exact lineExactAgreementBound_of_exactCorrelatedPair domain _
    (fun f g ↦ exists_uniformFirstOrder_lineMca n k A domain f g hn hk hAn hgap hchar)

/-- T1's general statement with `C_E(ρ) n² / η⁵` in place of `C ρ η * n` holds today. -/
theorem baseline_T1_quadratic :
    ∀ (rho eta : ℝ) (n k A : ℕ), 0 < rho → rho < 1 → 0 < eta →
      firstOrderRateThreshold rho + eta < 1 →
      0 < n → 2 ≤ k → (k : ℝ) ≤ rho * n →
      (firstOrderRateThreshold rho + eta) * n ≤ A → A ≤ n →
      ∀ (F : Type u) [Field F] [DecidableEq F],
        (ringChar F = 0 ∨ max (k - 1)
          (automaticDerivativeCap rho (firstOrderRateThreshold rho + eta)) < ringChar F) →
        ∀ domain : Fin n ↪ F, LineExactAgreementBound domain k A
          (automaticExceptionBoundConstant rho * n ^ 2 / eta ^ 5) := by
  intro rho eta n k A hrho hrhoOne heta haOne hn hk hkRate hA hAn F _ decF hchar domain
  -- ArkLib states this theorem with classical decidable equality; every instance agrees.
  refine lineExactAgreementBound_dec (fun a b ↦ Classical.propDecidable (a = b)) decF ?_
  let _ : DecidableEq F := fun a b ↦ Classical.propDecidable (a = b)
  exact lineExactAgreementBound_of_exactCorrelatedPair domain _
    (automaticFirstOrder_rate_bounds rho eta n k A hrho hrhoOne heta haOne hn hk hkRate hA hAn
      domain hchar).2

end ProvenTargets
