/-
proven.provably.fast: the pinned statements of the mathematics targets T1, T2 and T3.

Each target is a `Prop` about Reed-Solomon line mutual correlated agreement on a prescribed
evaluation set, stated with ArkLib's `LineExactAgreementBound`: for every received line `f + z g`,
one exceptional set of at most `B` challenges, outside of which every polynomial of degree below
`k` agreeing with the line in at least `A` places splits as `P₀ + z P₁` with the same agreement set
for `f` and `g`.

The targets are `T1`, `T2` and `T3`; `T1Uniform` and `T3Exponent` are milestones toward `T1` and
`T3`. Every quantitative parameter (constants, curves, characteristic bounds, minimum lengths) is
an argument, and a result supplies it in closed form; the proof itself may reason classically. A
result compiles against the ArkLib commit pinned in `lakefile.toml` and depends on no axioms beyond
`propext`, `Classical.choice` and `Quot.sound` (check with `#print axioms`). The `baseline_*`
theorems at the end restate ArkLib's quadratic bounds in the same shape.
-/
module

public import ArkLib.Data.CodingTheory.ReedSolomon.MutualCorrelatedAgreement.FirstOrder.UniformLineMca
public import ArkLib.Data.CodingTheory.ReedSolomon.MutualCorrelatedAgreement.FirstOrder.RateBounds
public import ArkLib.Data.CodingTheory.ReedSolomon.MutualCorrelatedAgreement.Capacity
public import Mathlib.RingTheory.RootsOfUnity.PrimitiveRoots
public import Mathlib.Analysis.SpecialFunctions.Trigonometric.Inverse

@[expose] public section

namespace MCAChallenge

open Polynomial ReedSolomon ReedSolomon.HiddenDerivative

universe u

/-- The first-order curve `a₁(ρ)` of Dao, Kominers and Thaler (ePrint 2026/2056, equation 31). From
`ρ_c = 11 - 3√13` on it is ArkLib's `firstOrderRateThreshold`; below `ρ_c` it is `√(ρ/2) (1 + u)`
with `u > 0` the root of `u² (u + 3) = √(ρ/2)` (equation 30), here in closed form:
`1 + u = 2 cos (arccos ((√(ρ/2) - 2) / 2) / 3)`. -/
noncomputable def firstOrderCurve (rho : ℝ) : ℝ :=
  if 11 - 3 * Real.sqrt 13 ≤ rho then firstOrderRateThreshold rho
  else Real.sqrt (rho / 2) * (2 * Real.cos (Real.arccos ((Real.sqrt (rho / 2) - 2) / 2) / 3))

theorem firstOrderCurve_eq_threshold {rho : ℝ} (h : 11 - 3 * Real.sqrt 13 ≤ rho) :
    firstOrderCurve rho = firstOrderRateThreshold rho := by
  simp [firstOrderCurve, h]

/-- A milestone toward T1, not T1: ArkLib's `ReedSolomon.exists_uniformFirstOrder_lineMca` (Dao,
Kominers and Thaler, Theorem 5.13: `1325775 * n ^ 2` bad challenges at agreement `k + 6 n / 25`)
with the bound replaced by `C * n`, for a numeral `C`. Agreement `ρ + 0.24` lies below the Johnson
threshold only for `0.16 < ρ < 0.36`. -/
def T1Uniform (C : ℝ) : Prop :=
  ∀ (n k A : ℕ), 2 ≤ n → 0 < k → A ≤ n → (k : ℝ) + (6 / 25 : ℝ) * n ≤ A →
    ∀ (F : Type u) [Field F] [DecidableEq F], (ringChar F = 0 ∨ k - 1 < ringChar F) →
      ∀ domain : Fin n ↪ F, LineExactAgreementBound domain k A (C * n)

/-- T1: a linear bound at every rate `ρ` and slack `η` above the first-order curve, where Dao,
Kominers and Thaler prove `O_ρ(n² / η⁴)` (Theorem 1.1). A result supplies the constant `C ρ η` and
the characteristic bound `B ρ η`. -/
def T1 (C : ℝ → ℝ → ℝ) (B : ℝ → ℝ → ℕ) : Prop :=
  ∀ (rho eta : ℝ) (n k A : ℕ), 0 < rho → rho < 1 → 0 < eta →
    firstOrderCurve rho + eta < 1 →
    0 < n → 2 ≤ k → (k : ℝ) ≤ rho * n →
    (firstOrderCurve rho + eta) * n ≤ A → A ≤ n →
    ∀ (F : Type u) [Field F] [DecidableEq F],
      (ringChar F = 0 ∨ max (k - 1) (B rho eta) < ringChar F) →
      ∀ domain : Fin n ↪ F, LineExactAgreementBound domain k A (C rho eta * n)

/-- T2: a threshold curve strictly between capacity and the first-order curve at every rate, with a
count at most quadratic in `n`. A result supplies `a₂`, `C` and `B`. -/
def T2 (a₂ : ℝ → ℝ) (C : ℝ → ℝ → ℝ) (B : ℝ → ℝ → ℕ) : Prop :=
  (∀ rho : ℝ, 0 < rho → rho < 1 → rho < a₂ rho ∧ a₂ rho < firstOrderCurve rho) ∧
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

/-- A milestone toward T3: at every gap `δ > 0` above capacity, on smooth domains, at most
`C δ * n ^ c` bad challenges once `n ≥ N δ`, with the exponent `c` independent of `δ`. Known
bounds for arbitrary domains have exponent `d_δ + 1`, `d_δ = ⌈exp(1.5 / δ)⌉` for `δ < 0.24`
(`exists_capacity_lineAgreement`). A result supplies `c`, `N` and `C`. -/
def T3Exponent (c : ℕ) (N : ℝ → ℕ) (C : ℝ → ℝ) : Prop :=
  ∀ (δ : ℝ) (n k A : ℕ), 0 < δ → N δ ≤ n → 0 < k → (k : ℝ) + δ * n ≤ A → A ≤ n →
    ∀ (F : Type u) [Field F] [DecidableEq F], (ringChar F = 0 ∨ k - 1 < ringChar F) →
      ∀ domain : Fin n ↪ F, IsSmoothDomain domain →
        LineExactAgreementBound domain k A (C δ * n ^ c)

/-- T3: the linear case, at most `C δ * n` bad challenges at every fixed gap `δ` above capacity on
smooth domains, once `n ≥ N δ`. A result supplies `N` and `C`. -/
def T3 (N : ℝ → ℕ) (C : ℝ → ℝ) : Prop :=
  T3Exponent.{u} 1 N C

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

/-- ArkLib's general quadratic bound, `C_E(ρ) n² / η⁵` at slack `η` above `firstOrderRateThreshold`:
T1's shape, with one more factor of `n` and a fifth power of `η`, wherever the threshold equals the
curve (`firstOrderCurve_eq_threshold`, `ρ ≥ 11 - 3√13`); below that rate it lies at most 0.0014
above the curve. -/
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

end MCAChallenge
