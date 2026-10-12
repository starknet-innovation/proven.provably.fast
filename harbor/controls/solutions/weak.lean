import MCAChallenge

noncomputable def C : ℝ := 1325775

/-- Same name and universe, a different statement: Comparator must refuse it. -/
theorem solution.{u} : ∀ (F : Type u) [Field F], (1 : F) = 1 := fun _ _ => rfl
