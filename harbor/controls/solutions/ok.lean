import MCAChallenge

noncomputable def C : ℝ := 1325775

theorem solution.{u} : ∀ (n k A : ℕ), 2 ≤ n → 0 < k → A ≤ n → (k : ℝ) + (6 / 25 : ℝ) * n ≤ A →
    ∀ (F : Type u) [Field F] [DecidableEq F], (ringChar F = 0 ∨ k - 1 < ringChar F) →
      ∀ domain : Fin n ↪ F, ReedSolomon.LineExactAgreementBound domain k A (C * n ^ 2) := by
  unfold C
  exact MCAChallenge.baseline_T1Uniform_quadratic.{u}
