# Lean statements

The targets T1, T2 and T3 are stated in Lean in [`ProvenTargets.lean`](ProvenTargets.lean), against
[Verified-zkEVM/ArkLib](https://github.com/Verified-zkEVM/ArkLib) at
`35ddcaa83f683011f944f58904be779495a5709a` (Apache-2.0), pinned in [`lakefile.toml`](lakefile.toml).
Contributors prove the statement we pin; they never choose it.

A Lean result proves one target for explicit parameters: constants and curves in closed form, never
obtained with `Classical.choose`. It compiles against the pinned commit and uses no axioms beyond
`propext`, `Classical.choice` and `Quot.sound`. Lean-checked is a status shown beside a solved
target; a target is solved by an independently reviewed proof, with or without Lean.

| Target | Lean declaration | What it asks | Proven today in ArkLib |
|---|---|---|---|
| T1, uniform form | `ProvenTargets.T1Uniform C` | agreement at least k + 6n/25, characteristic 0 or above k - 1: at most `C * n` bad challenges on every line | `ReedSolomon.exists_uniformFirstOrder_lineMca`: 1,325,775 n^2 (restated as `baseline_T1Uniform_quadratic`) |
| T1, general form | `ProvenTargets.T1 C B` | agreement at least (a1(rho) + eta) n, k at most rho n, characteristic 0 or above max(k - 1, B rho eta): at most `C rho eta * n` | `ReedSolomon.automaticFirstOrder_rate_bounds`: C_E(rho) n^2 / eta^5 (restated as `baseline_T1_quadratic`) |
| T2 | `ProvenTargets.T2 a2 C B` | a threshold curve a2 strictly between capacity and a1 at every rate, with at most `C rho eta * n ^ 2` | nothing below a1 with a quadratic count |
| T3 | `ProvenTargets.T3 c` | smooth domains (cosets of the subgroup of order 2^m), every fixed gap delta above capacity: at most `C_delta * n ^ c`, with c independent of delta; `T3 1` is the full ambition | `ReedSolomon.exists_capacity_lineAgreement`: C n^(d + 1) on any domain, with d depending on delta |

a1(rho) here is ArkLib's `ReedSolomon.HiddenDerivative.firstOrderRateThreshold rho`,
(3 rho + 2 sqrt(rho (5 - rho)(2 - rho))) / (8 - rho). It is the first-order curve of Dao, Kominers
and Thaler (ePrint 2026/2056, equation 31) for rho at least 11 - 3 sqrt(13), and lies above it by at
most 0.0014 below that rate; ArkLib's quadratic theorem uses it at every rate.

All four statements use ArkLib's `LineExactAgreementBound`: for every received line f + z g, one
exceptional set of at most B challenges, outside of which every polynomial of degree below k
agreeing with the line in at least A places splits as P0 + z P1 with the same agreement set for f
and g.

## Build and check

`lake-manifest.json` pins every dependency.

    cd lean
    lake exe cache get    # Mathlib's prebuilt files
    lake build

To check a proof, import `ProvenTargets` in a file of your own and run `#print axioms` on your
theorem with `lake env lean YourFile.lean`; it must list only `propext`, `Classical.choice` and
`Quot.sound`.

Checked 2026-10-08 from a fresh clone (about nine minutes on a laptop): `ProvenTargets` builds with
no warnings, both baselines use only the three standard axioms, and the targets are open. ArkLib's
own build prints two `sorry` warnings, in `ArkLib/Data/Fin/Basic.lean` and
`ArkLib/Data/MvPolynomial/Interpolation.lean`; `#print axioms` confirms neither is used here.
