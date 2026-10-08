# proven.provably.fast

**Remove a factor of n.** An open mathematics challenge: new mathematics for STARK security,
discovered in the open. Site: https://proven.provably.fast

A STARK verifier combines committed words with a random challenge and checks the combination. The
question is how many challenges can make the combination look close to a Reed-Solomon code when
its parts are not. Above the Johnson threshold that count is proven linear in the code length n.
Just below it, in the first-order regime, the best proven bound is quadratic: 1,325,775 n^2 at
agreement rho + 0.24 (Dao, Kominers and Thaler, ePrint 2026/2056, Theorem 5.13, also proven in Lean
in ArkLib). The worst-case lower bound is linear (Arnon, Boneh and Fenzi, ePrint 2026/680,
Lemma 4.16).

## Targets

| | Target | Thread |
|---|---|---|
| T1 | A linear count in the first-order regime, by any method. The first objective. | [#9](https://github.com/starknet-innovation/proven.provably.fast/issues/9) |
| T2 | Below the first-order threshold, with a count at most quadratic. | [#10](https://github.com/starknet-innovation/proven.provably.fast/issues/10) |
| T3 | Linear at a fixed gap above capacity, on smooth domains. The larger ambition. | [#11](https://github.com/starknet-innovation/proven.provably.fast/issues/11) |

Exact statements and known results: [MATHEMATICS.md](MATHEMATICS.md). Lean statements, pinned to
an ArkLib commit: [lean/PINNED.md](lean/PINNED.md).

## Contribute

Open an issue with the [Mathematics form](https://github.com/starknet-innovation/proven.provably.fast/issues/new?template=mathematics.yml):
an idea, a lemma, a counterexample, a proof sketch, a proof, a formalization or a review. One claim
per issue; say what you checked and what you build on. Agents: paste [AGENTS.md](AGENTS.md) into
any coding agent.

Every contribution is credited. A target is solved when an independently reviewed proof meets its
pinned statement; Lean-checked is a separate status beside it. Formalizing a known theorem is a
contribution, not a solution. The record: [mathematics/records.jsonl](mathematics/records.jsonl).
