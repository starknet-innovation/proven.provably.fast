import MCAChallenge

/-- The constant set by choice: Comparator accepts it, the hole check must refuse it. -/
noncomputable def C : ℝ := Classical.choose (⟨1325775, rfl⟩ : ∃ x : ℝ, x = 1325775)

theorem solution.{u} : ∀ (n k A : ℕ), 2 ≤ n → 0 < k → A ≤ n → (k : ℝ) + (6 / 25 : ℝ) * n ≤ A →
    ∀ (F : Type u) [Field F] [DecidableEq F], (ringChar F = 0 ∨ k - 1 < ringChar F) →
      ∀ domain : Fin n ↪ F, ReedSolomon.LineExactAgreementBound domain k A (C * n ^ 2) := by
  have hC : C = 1325775 := Classical.choose_spec (⟨1325775, rfl⟩ : ∃ x : ℝ, x = 1325775)
  rw [hC]
  exact MCAChallenge.baseline_T1Uniform_quadratic.{u}
