# Lean statements

The targets T1, T2 and T3 are stated in Lean in [`MCAChallenge.lean`](MCAChallenge.lean), against
[Verified-zkEVM/ArkLib](https://github.com/Verified-zkEVM/ArkLib) at
`35ddcaa83f683011f944f58904be779495a5709a` (Apache-2.0), pinned in [`lakefile.toml`](lakefile.toml).
Contributors prove the statement we pin; they never choose it.

Every quantitative parameter is an argument of the statement: constants, curves, characteristic
bounds and minimum lengths. A Lean result supplies them in closed form, and the proof itself may
reason classically. It compiles against the pinned commit and uses no axioms beyond `propext`,
`Classical.choice` and `Quot.sound`. Lean-checked is a status shown beside a solved target; a target
is solved by an independently reviewed proof, with or without Lean.

| | Lean declaration | What it asks | Already in ArkLib |
|---|---|---|---|
| T1 | `MCAChallenge.T1 C B` | agreement at least (a1(rho) + eta) n, k at most rho n, characteristic 0 or above max(k - 1, B rho eta): at most `C rho eta * n` bad challenges on every line | `ReedSolomon.automaticFirstOrder_rate_bounds`: C_E(rho) n^2 / eta^5 above the curve's upper branch (`baseline_T1_quadratic`) |
| T1 milestone | `MCAChallenge.T1Uniform C` | agreement at least k + 6n/25, characteristic 0 or above k - 1: at most `C * n` | `ReedSolomon.exists_uniformFirstOrder_lineMca`: 1,325,775 n^2 (`baseline_T1Uniform_quadratic`) |
| T2 | `MCAChallenge.T2 a2 C B` | a curve a2 strictly between capacity and a1 at every rate, with at most `C rho eta * n ^ 2` | nothing below a1 with a quadratic count |
| T3 | `MCAChallenge.T3 N C` | smooth domains (cosets of the subgroup of order 2^m), every gap delta above capacity, n at least `N delta`: at most `C delta * n` | `ReedSolomon.exists_capacity_lineAgreement`: C n^(d + 1) on any domain, d depending on delta |
| T3 milestone | `MCAChallenge.T3Exponent c N C` | as T3, with at most `C delta * n ^ c` for one exponent c | as above |

a1 is `MCAChallenge.firstOrderCurve`, the first-order curve of Dao, Kominers and Thaler (ePrint
2026/2056, equation 31), with the lower branch in closed form. ArkLib's
`ReedSolomon.HiddenDerivative.firstOrderRateThreshold` is the upper-branch formula
(3 rho + 2 sqrt(rho (5 - rho)(2 - rho))) / (8 - rho) at every rate. It equals the curve for rho at
least 11 - 3 sqrt(13) (`firstOrderCurve_eq_threshold`) and lies above it by at most 0.0014 below that
rate. So ArkLib's general baseline covers T1's shape only from that rate on.

All statements use ArkLib's `LineExactAgreementBound`. For every received line f + z g there is one
exceptional set of at most B challenges. Outside it, every polynomial of degree below k that agrees
with the line in at least A places splits as P0 + z P1, where f agrees with P0 and g with P1 on
that whole agreement set.

## Build and check

`lake-manifest.json` pins every dependency.

    cd lean
    lake exe cache get    # Mathlib's prebuilt files
    lake build

To check a proof, import `MCAChallenge` in a file of your own and run `#print axioms` on your
theorem with `lake env lean YourFile.lean`; it must list only `propext`, `Classical.choice` and
`Quot.sound`.

Checked 2026-10-08: `MCAChallenge` compiles against the pinned ArkLib with no warnings, and the
baselines and `firstOrderCurve_eq_threshold` use only the three standard axioms. The targets are
open. ArkLib's own build prints two `sorry` warnings, in `ArkLib/Data/Fin/Basic.lean` and
`ArkLib/Data/MvPolynomial/Interpolation.lean`; `#print axioms` confirms neither is used here.
