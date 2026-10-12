import MCAChallenge

/-- A control challenge for the verifier, not a target: T1Uniform's shape with a quadratic bound,
which ArkLib proves (`MCAChallenge.baseline_T1Uniform_quadratic`). The hole is the constant. -/
noncomputable def C : ℝ := sorry

theorem solution.{u} : ∀ (n k A : ℕ), 2 ≤ n → 0 < k → A ≤ n → (k : ℝ) + (6 / 25 : ℝ) * n ≤ A →
    ∀ (F : Type u) [Field F] [DecidableEq F], (ringChar F = 0 ∨ k - 1 < ringChar F) →
      ∀ domain : Fin n ↪ F, ReedSolomon.LineExactAgreementBound domain k A (C * n ^ 2) := sorry
