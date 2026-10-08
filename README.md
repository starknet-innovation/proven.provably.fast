# proven.provably.fast

**Remove a factor of n.** An open mathematics challenge on Reed-Solomon mutual correlated agreement:
new mathematics for STARK security, discovered in the open. Site: https://proven.provably.fast

A STARK verifier combines committed words with a random challenge and checks the combination. The
question is how many challenges can make the combination look close to the code when its parts are
not. Above the Johnson threshold that count is proven linear in the code length. Just below it, in
the first-order regime, the best proven bound is quadratic: 1,325,775 n^2 bad challenges at
agreement rho + 0.24 (Dao, Kominers and Thaler, ePrint 2026/2056, Theorem 5.13, also proven in Lean
in ArkLib). The worst-case lower bound is linear (Arnon, Boneh and Fenzi, ePrint 2026/680,
Lemma 4.16). The first objective is a linear bound, with explicit constants and a checked proof.

## Targets

| | Target | Lean statement |
|---|---|---|
| T1 | A linear count in the first-order agreement regime, by any method. The first objective. Thread [#9](https://github.com/starknet-innovation/proven.provably.fast/issues/9). | `ProvenTargets.T1`, `ProvenTargets.T1Uniform` |
| T2 | Below the first-order threshold, with a count at most quadratic. Thread [#10](https://github.com/starknet-innovation/proven.provably.fast/issues/10). | `ProvenTargets.T2` |
| T3 | Linear at a fixed gap above capacity, on smooth domains. The larger ambition. Thread [#11](https://github.com/starknet-innovation/proven.provably.fast/issues/11). | `ProvenTargets.T3` |

Exact statements, the table of known results and the hypotheses: [MATHEMATICS.md](MATHEMATICS.md).
The Lean statements compile against a pinned ArkLib commit: [lean/PINNED.md](lean/PINNED.md).

## How to contribute

- Open an issue with the [Mathematics form](https://github.com/starknet-innovation/proven.provably.fast/issues/new?template=mathematics.yml):
  an idea, a lemma, a counterexample, a proof sketch, a proof, a formalization or a review. One
  claim per issue. Say what you checked, how, and what you build on.
- Agents: [AGENTS.md](AGENTS.md) is the brief to paste into any coding agent.
- You do not need a prover implementation to contribute mathematics.

What counts: ideas, proof sketches, lemmas, counterexamples, formalizations and reviews are credited
contributions. A target is solved when an independently reviewed proof meets its pinned statement;
Lean-checked is a separate status shown beside it. Formalizing an existing theorem is a
contribution, not a challenge result. Every result names the work it builds on.

The record of every contribution, its reviews and what it builds on is
`mathematics/records.jsonl`; the site shows it, and each target's status follows from it
(MATHEMATICS.md, "The record").

Profiles turn a bound into a yes or no at one configuration. Stwo is the first
(MATHEMATICS.md, `reference/regimes-stwo-profile.py`); others are pinned with the teams that run
them. A successful theorem may permit fewer checks; the effect depends on its constants and on the
complete protocol analysis.

## Performance track

The repository also runs a track for provers at conjecture-free settings: three tasks, a judge you
run yourself, and an evaluator host. It is secondary to the mathematics. Any transparent,
post-quantum proving system (hash- or lattice-based, no trusted setup) can enter, and every
contribution that moves a task's frontier is credited to the people and agents behind it.

Where it stands: at query counts that need no proximity-gap conjecture, a full Stwo proof with
recursion costs 2.0x the time and 2.4x the memory of today's settings, most of it in recursion.
The three tasks below isolate that cost.

### The tasks

The same for every system. The judge draws a fresh statement for every run, so nothing can be
cached between runs.

#### 1. Hash chain (`blake2s-chain-v0`)

Prove that hashing a random 32-byte seed n times with BLAKE2s-256 gives y. Each step hashes the
previous 32-byte digest. Hashing is most of a STARK's work, and nearly all of its recursion.

    {"statement": "blake2s-chain-v0", "n": 16384, "seed": "<64 hex>", "y": "<64 hex>"}

Check one yourself:

    import hashlib, json
    s = json.load(open("statement.json"))
    d = bytes.fromhex(s["seed"])
    for _ in range(s["n"]):
        d = hashlib.blake2s(d).digest()
    assert d.hex() == s["y"]

`python3 -m proven.statements blake2s-chain-v0 --n 16384 > statement.json` writes a fresh one.
Size: n = 16,384.

#### 2. Matrix product (`u32-matmul-v0`)

Prove that C = A x B mod 2^32 for two random k x k matrices of 32-bit words: plain integer
arithmetic, the ring every CPU and VM uses, so no proof system's field gets a free win.
Statement: `{"statement": "u32-matmul-v0", "k": 48, "a": "<hex>", "b": "<hex>", "c": "<hex>"}`,
each matrix little-endian 32-bit words, row-major. Size: k = 48.

#### 3. Recursion step (`stwo-verify-v0`)

Prove that a fixed Stwo verifier accepts a given proof. The judge picks a secret seed, publishes
y, and makes an inner proof (Stwo, 107 queries, zero-knowledge blinded) that someone knows a seed
whose n-step chain ends at y. Your prover gets `{"statement": "stwo-verify-v0", "n": 1024,
"y": ..., "witness_inner_proof": "<hex>"}`; your verifier gets the same without the witness. The
seed is never published, so the only way through is to verify the inner proof. The pinned inner
verifier is `chain inner-verify` in `entries/stwo-chain`. Size: n = 1,024.

### Ways to contribute

| Role | Contribution | How it is recorded |
|---|---|---|
| Implementer | a prover and verifier that beat a task's frontier at conjecture-free settings | the frontier moves to it, with your credit |
| Explorer, sourcer | a lead: an idea or a paper worth trying (a cheaper hash gadget, fewer openings, WHIR or STIR, a new bound) | a lead in the research graph; experiments that test it cite you |
| Deriver | a derivation for one of the terms in a soundness sheet | the term's status moves to cited, with your name |
| Reviewer | a checked derivation or a read verifier | the term or entry turns from grey to solid |
| Falsifier | a forged proof, or a bound shown wrong | the entry is pulled or the sheet corrected; the find is credited |
| Formalizer | a Lean proof of a term against a statement we pin (`lean/PINNED.md`) | the term becomes LEAN-CHECKED |

### What you ship as an implementer

A public repository and a full commit. The repository holds your source, a soundness sheet and
`entry.json`, at its root or in a directory you name when you send it:

    {"name": "your-entry", "team": "your team", "system": "one line on your proof system",
     "statement": "blake2s-chain-v0",
     "build": ["cargo", "build", "--release", "--locked"],
     "prove": ["./target/release/your-binary", "prove", "{statement}"],
     "verify": ["./target/release/your-binary", "verify", "{statement}", "{proof}"],
     "ledger": "ledger.json",
     "credits": [{"role": "implementer", "who": "name or handle"}]}

- `prove` writes the proof to stdout. `verify` exits 0 to accept and 20 to reject. Both run in
  the entry's directory; `build`, if present, runs once at the repository's root.
- `ledger.json` is the soundness sheet: every source of soundness error, its formula and its
  inputs. `reference/ledger-grind-chain.json` is the example; `python3 -m proven.calculator
  ledger.json` adds it up. No term may rest on the proximity-gap conjecture.
- Your prover and verifier source must be public. If anyone who holds your prover can forge a
  proof (a hidden key, a hardcoded secret), the entry is out.
- Rules of the run: no network and no state kept between runs. On the evaluator host every
  command runs as an unprivileged user in the entry's directory, which is read-only by then; write
  temporary files to `/tmp`, which each command gets empty. Memory is measured on the prover
  process, so a wrapper script must `exec` your binary.
- The evaluator host: Linux x86-64, 16 cpus, a 48 GB memory cap, an hour for the build, no
  network. A Rust entry with `Cargo.lock` at the repository's root gets its crates and git
  dependencies fetched first, as the same unprivileged user (no build script runs then), and
  builds with Stwo's toolchain, `nightly-2026-01-15`; `rust-toolchain.toml` is not read. Anything
  else must be vendored in the repository, which may be at most 4 GB.

Starting points: `entries/stwo-grind` (the frontier) and `entries/stwo-chain` (Stwo as it is),
each built from a checkout of [starknet-innovation/proving](https://github.com/starknet-innovation/proving)
at 6e80156f by its `build.sh`.

### How a contribution is checked

Run the judge yourself first, on your laptop, as often as you like (seconds per run):

    python3 -m proven.oracle path/to/your-entry --runs 3

It passes when every fresh statement proves and verifies; the verifier rejects every bad case
(false statements, another statement's proof, empty, garbage, truncated and bit-flipped proofs)
without crashing; the proof is at most twice the frontier's size; and the sheet reaches 96 bits
with every required component. Verify time is held to twice the frontier's on the evaluator host;
your laptop reports it against that cap without failing you.

Then two checks no test can make: a person or an agent reads your verifier, and anyone may attack
your entry (`python3 -m proven.forgery submit ENTRY false-statement.json proof.bin --by YOU`; for
the recursion task, hit a challenge the judge issued with `forgery challenge`). To test a bound
rather than break an entry, `forgery rung ENTRY --bits 32` derives a weak setting from your own
sheet and your own code runs under it; rung forgeries are evidence, not disqualification.

### How the frontier moves

Each task has one frontier: the cheapest contribution so far at conjecture-free settings, measured
by the judge on the evaluator host. A contribution that passes the judge and proves at least 1%
faster than the frontier moves it; the move is recorded with its credits, and the next
contribution builds on it. A frontier that stops passing (its sheet corrected below the floor,
say) yields to any entry that passes. Memory, proof size and verify time are published beside the
time. Official numbers come from the host only; laptop numbers are for your own loop.

Security shows in two shades. A sheet the calculator accepts gives claimed bits, shown grey. Once
every term is reviewed or Lean-checked, the entry shows proven bits, solid. Until then the wording
is "conjecture-free query counts, priced".

### The frontier today

Stwo with 8 bits of proof of work before the batching coefficient (`entries/stwo-grind`), on its
circuits framework at 107 queries, judged on the evaluator host (16 cpus), 2026-10-07:

| Task | prove | peak memory | proof | verify | security |
|---|---|---|---|---|---|
| hash chain, n = 16,384 | 3.6 s | 7.6 GB | 617 KB | 0.33 s | 96.45 claimed bits |
| matrix product, k = 48 | 3.0 s | 3.6 GB | 531 KB | 0.37 s | 96.45 claimed bits |
| recursion, inner n = 1,024 | 4.1 s | 9.3 GB | 628 KB | 0.34 s | 96.45 claimed bits |

At today's conjectured settings (35 queries), the same proofs take about the same time, but are
2.8x smaller (221, 192 and 233 KB) and verify about 3x faster (0.11 to 0.16 s). For a single
proof the price of conjecture-free settings is proof size and verify time; prover time pays in
recursion, where every extra query of the inner proof has to be checked inside the circuit.

Stwo as it is (`entries/stwo-chain`) proves at the same speed, but its sheets stop at 92.4 claimed
bits, below the floor. Every committed column is lifted to one domain, so all 363 out-of-domain
quotients enter one FRI input, combined by powers of one random coefficient. Under the
unique-decoding bound the S-two whitepaper uses (eprint 2026/532, Remark 20), that step costs
(363 - 1) x 2^23 / 2^124, about 2^-92.5, whatever the query count. The whitepaper's parameters
assume grinding at this step (Section 5.5); `batching-grind.patch` adds 8 bits of it, and the
sheets read 96.45.

Other systems: a Plonky3 floor for the hash chain (`entries/plonky3-chain`, the maintainers'
floor, not the Plonky3 team's best) proves in 2.9 s with 3.2 GB on the host, verifies in
0.05 s and reads 98.55 claimed bits, but its proofs are 5.8 MB, because each query
opens a row of 11,920 columns: over the 2x size cap. Fitting it under the cap is open.

### Open problems

1. Cost. Bring the frontier's prove time, memory and proof size down to today's conjectured
   settings, task by task; recursion is where most of the gap lives.
2. The folding term. Each FRI layer folds 16 values with powers of one challenge, about 2^-97.0
   over all layers; it now caps the sheets near 96.5. Independent challenges per fold, or grinding
   before each fold challenge, lift it.
3. Review. Every term of every sheet is cited and unchecked. Reviews, and Lean proofs against the
   statements pinned in `lean/PINNED.md`, turn claimed bits into proven bits.
4. Circle codes. Theorem 1 of the Circle STARKs paper (eprint 2024/278) maps Stwo's circle codes
   to Reed-Solomon codes with the same distance, so the Reed-Solomon bounds apply. Writing that
   transfer down for the exact terms of the sheets, and for the query sampling the code uses
   (S-two whitepaper, Section 4.5), is open (P5 in `lean/PINNED.md`).

### Sending a contribution

Open an issue in this repository with the contribution form: the repository, the full commit,
the task, the entry's directory if it is not the root, and the credits. Within 20 minutes the
evaluator host queues it by itself and says so on the issue; it builds and judges it with no
network while the Stwo lane is idle, posts the verdict and the measurements on the issue, and
`results/board.json` records it. To send a fix, edit the issue to the new commit. A passing entry
can set a frontier once a maintainer has read its verifier. Derivations, reviews, falsifications
and Lean proofs go through the form for them or a pull request.

### The board

`results/board.json` holds, per task, the frontier, the history of how it moved and who moved it,
and every judged contribution with its status: reviewed, claimed, waiting for a verifier read,
failed the judge, or disqualified by a forgery. No ranking: the frontier is shared.
