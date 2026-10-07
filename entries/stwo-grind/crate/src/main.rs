//! Stwo with a proof of work before the batching coefficient, for proven.provably.fast: the
//! reference entries' circuits (entries/stwo-chain), proved by a Stwo patched to grind
//! BATCHING_POW_BITS before it draws the coefficient that combines the out-of-domain quotients
//! (batching-grind.patch, applied to frontier 6e80156f by build.sh). The S-two whitepaper's
//! parameters (eprint 2026/532, Section 5.5) need grinding at this step.
//!
//!   chain prove STATEMENT > PROOF              chain verify STATEMENT PROOF            (chain)
//!   chain recursion-prove STATEMENT > PROOF    chain recursion-verify STATEMENT PROOF  (recursion)
//!   chain matmul-prove STATEMENT > PROOF       chain matmul-verify STATEMENT PROOF     (matmul)
//!   chain params chain|matmul N...             verifier constants for each n or k (JSON)
//!   chain shape SECTION N PROOF                how many polynomials one proof batches (JSON)
//!
//! The recursion task's inner proofs come from the judge's reference prover, which does not grind
//! there, so they are read with batching_pow_bits = 0 and the recursion circuit is the reference
//! one; its constants (params.json "inner" and "outer") come from the reference binary.
//!
//! Verifiers exit 0 to accept, 20 to reject and 1 for an unreadable input. None of them runs the
//! chain: their constants for each supported n are pinned in params.json and compiled in.

use std::io::Write;
use std::panic::catch_unwind;
use std::process::ExitCode;

use circuit_common::preprocessed::PreprocessedCircuit;
use circuit_prover::prover::{
    prepare_circuit_proof_for_circuit_verifier, prove_circuit_assignment,
};
use circuit_serialize::deserialize::deserialize_proof_with_config;
use circuit_serialize::serialize::CircuitSerialize;
use circuit_verifier::statement::{INTERACTION_POW_BITS, all_circuit_components};
use circuit_verifier::verify::{
    CircuitConfig, CircuitPublicData, build_verification_circuit, verify_circuit,
};
use circuits::blake::{HashValue, blake2s_u32s, unpack_qm31s_to_u32_words};
use circuits::context::{Context, FinalizedContext, Var};
use circuits::eval;
use circuits::extract_bits::extract_bits;
use circuits::ivalue::{IValue, qm31_from_u32s};
use circuits::ops::{Guess, guess};
use circuits::simd::Simd;
use circuits::utils::le_u32s_from_bytes;
use circuits::wrappers::M31Wrapper;
use circuits_stark_verifier::proof::{Proof, ProofConfig};
use serde_json::{Map, Value, json};
use stwo::core::fields::qm31::QM31;
use stwo::core::fri::FriConfig;
use stwo::core::pcs::PcsConfig;
use stwo::core::proof_of_work::BATCHING_POW_BITS;
use stwo::prover::backend::simd::SimdBackend;
use stwo::prover::mempool::BaseColumnPool;
use stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId;

const CHAIN: &str = "blake2s-chain-v0";
const RECURSION: &str = "stwo-verify-v0";
const MATMUL: &str = "u32-matmul-v0";
/// Bits that hold every carry-stage value for k up to 64: a limb sum stays below
/// 4 * 64 * 255^2 < 2^24, and a carry adds less than 2^17.
const CARRY_BITS: u32 = 25;
const MAGIC: &[u8; 4] = b"pfc0";
const MAX_PROOF_BYTES: usize = 64 << 20;
/// Rate 1/4 and 107 queries (0.68 bits each in unique decoding) plus 26 bits of proof of work:
/// three queries above the bare floor, so the ledger's pending terms have room to land. Every
/// proof here, inner and outer, uses it. The entry's ledger, not this comment, is its claim.
const FRI_CONFIG: FriConfig = FriConfig {
    pow_bits: 26,
    log_blowup_factor: 2,
    log_last_layer_degree_bound: 0,
    n_queries: 107,
    fold_step: 4,
};
const PARAMS: &str = include_str!("params.json");

/// The FRI setting every proof here uses. The judge's weak-setting ladder sets PROVEN_SECURITY to
/// a JSON file with lower n_queries and pow_bits, so attackers can test the bound at 24 to 40
/// bits; the blowup never changes, so the pinned constants still hold. Board runs never set it.
fn fri_config() -> FriConfig {
    let Ok(path) = std::env::var("PROVEN_SECURITY") else {
        return FRI_CONFIG;
    };
    let weak: Value = std::fs::read_to_string(&path)
        .ok()
        .and_then(|text| serde_json::from_str(&text).ok())
        .unwrap_or_else(|| panic!("PROVEN_SECURITY {path} is unreadable"));
    let field = |key: &str| weak[key].as_u64().unwrap_or_else(|| panic!("PROVEN_SECURITY lacks {key}"));
    FriConfig { n_queries: field("n_queries") as usize, pow_bits: field("pow_bits") as u32, ..FRI_CONFIG }
}

enum Failure {
    Unreadable(String),
    Rejected(String),
}

/// One circuit's verifier constants.
struct Pinned {
    trace_log_size: u32,
    ids: Vec<String>,
    log_sizes: Vec<u32>,
    root: [u32; 8],
}

/// The chain as a circuit. The seed words are guessed (each range-checked to a u32) and each
/// step hashes the previous digest. The public outputs are the seed then y, or y alone.
fn chain_context(seed: [u8; 32], n: usize, public_seed: bool) -> (Context<QM31>, [u32; 8]) {
    let mut context = Context::<QM31>::new(if public_seed { 16 } else { 8 });
    let seed_words: [u32; 8] = le_u32s_from_bytes(seed);
    let seed_vars = HashValue::<QM31>::from(seed_words).guess(&mut context);
    let mut digest = seed_vars.clone();
    for _ in 0..n {
        digest = blake2s_u32s(&mut context, digest.0.to_vec(), 32);
    }
    let y_words = std::array::from_fn(|i| context.get(*digest[i].get()).unpack_u32());
    let mut outputs: Vec<Var> = Vec::new();
    if public_seed {
        outputs.extend(seed_vars.iter().map(|word| *word.get()));
    }
    outputs.extend(digest.iter().map(|word| *word.get()));
    context.set_outputs(&outputs);
    (context, y_words)
}

/// A 32-bit word as one QM31 holding its four bytes, least significant first.
fn bytes_of(word: u32) -> QM31 {
    qm31_from_u32s(word & 0xff, (word >> 8) & 0xff, (word >> 16) & 0xff, word >> 24)
}

fn lanes(context: &mut Context<QM31>, var: Var) -> Vec<M31Wrapper<Var>> {
    Simd::unpack(context, &Simd::from_packed(vec![var], 4)).into_iter().map(M31Wrapper::new_unsafe).collect()
}

/// C = A * B mod 2^32. Each word of A and B is guessed as four byte lanes and range-checked by an
/// 8-bit decomposition. For every output, the byte products are summed exactly per limb (a limb
/// sum stays below 2^24, far from the field's modulus); then carries are resolved limb by limb
/// with range-checked 25-bit decompositions, and the top carry is dropped (mod 2^32). The public
/// outputs are A's words, then B's, then C's, row-major, each as its four bytes.
fn matmul_context(k: usize, a: &[u32], b: &[u32]) -> Context<QM31> {
    assert!(k >= 2 && k <= 64 && k % 2 == 0 && a.len() == k * k && b.len() == k * k);
    let mut context = Context::<QM31>::new(3 * k * k);
    let a_vars: Vec<Var> = a.iter().map(|&word| guess(&mut context, bytes_of(word))).collect();
    let b_vars: Vec<Var> = b.iter().map(|&word| guess(&mut context, bytes_of(word))).collect();
    let inputs = Simd::from_packed([a_vars.clone(), b_vars.clone()].concat(), 8 * k * k);
    extract_bits(&mut context, &inputs, 8);
    let zero = M31Wrapper::new_unsafe(context.zero());
    let a_bytes: Vec<Vec<M31Wrapper<Var>>> = a_vars.iter().map(|&var| lanes(&mut context, var)).collect();
    // B's word shifted up by p bytes, the bytes past the fourth dropped.
    let b_shifts: Vec<[Simd; 4]> = b_vars
        .iter()
        .map(|&var| {
            let bytes = lanes(&mut context, var);
            let (z, b0, b1, b2) = (zero.clone(), bytes[0].clone(), bytes[1].clone(), bytes[2].clone());
            [
                Simd::from_packed(vec![var], 4),
                Simd::pack(&mut context, &[z.clone(), b0.clone(), b1.clone(), b2]),
                Simd::pack(&mut context, &[z.clone(), z.clone(), b0.clone(), b1]),
                Simd::pack(&mut context, &[z.clone(), z.clone(), z, b0]),
            ]
        })
        .collect();
    let mut limbs: [Vec<M31Wrapper<Var>>; 4] = Default::default();
    for i in 0..k {
        for j in 0..k {
            let mut sum = Simd::zero(&mut context, 4);
            for t in 0..k {
                for p in 0..4 {
                    let term = Simd::scalar_mul(&mut context, &b_shifts[t * k + j][p], &a_bytes[i * k + t][p]);
                    sum = Simd::add(&mut context, &sum, &term);
                }
            }
            for (r, var) in Simd::unpack(&mut context, &sum).into_iter().enumerate() {
                limbs[r].push(M31Wrapper::new_unsafe(var));
            }
        }
    }
    let mut c_bytes: Vec<Vec<Var>> = Vec::new();
    let mut carry: Option<Simd> = None;
    for limb in &limbs {
        let mut value = Simd::pack(&mut context, limb);
        if let Some(carry) = &carry {
            value = Simd::add(&mut context, &value, carry);
        }
        let bits = extract_bits(&mut context, &value, CARRY_BITS);
        let byte = Simd::combine_bits(&mut context, &bits[..8]);
        c_bytes.push(Simd::unpack(&mut context, &byte));
        carry = Some(Simd::combine_bits(&mut context, &bits[8..]));
    }
    let units = [1, 2, 3].map(|coord| {
        let mut unit = [0u32; 4];
        unit[coord] = 1;
        context.constant(qm31_from_u32s(unit[0], unit[1], unit[2], unit[3]))
    });
    let c_vars: Vec<Var> = (0..k * k)
        .map(|o| {
            let (b0, b1, b2, b3) = (c_bytes[0][o], c_bytes[1][o], c_bytes[2][o], c_bytes[3][o]);
            let (e1, e2, e3) = (units[0], units[1], units[2]);
            eval!(&mut context, ((b0) + ((e1) * (b1))) + (((e2) * (b2)) + ((e3) * (b3))))
        })
        .collect();
    context.set_outputs(&[a_vars, b_vars, c_vars].concat());
    context
}

fn pinned_of(context: &mut FinalizedContext<QM31>) -> Pinned {
    let preprocessed = PreprocessedCircuit::preprocess_circuit(context);
    let root = preprocessed.preprocessed_root(FRI_CONFIG.log_blowup_factor);
    Pinned {
        trace_log_size: preprocessed.trace_log_size,
        ids: preprocessed.preprocessed_trace.ids().into_iter().map(|id| id.id).collect(),
        log_sizes: preprocessed.preprocessed_trace.log_sizes().values().copied().collect(),
        root: le_u32s_from_bytes(root.0),
    }
}

fn to_json(pinned: &Pinned) -> Value {
    json!({"trace_log_size": pinned.trace_log_size, "ids": pinned.ids,
           "log_sizes": pinned.log_sizes, "root": pinned.root})
}

fn pinned(section: &str, n: usize) -> Result<Pinned, Failure> {
    let unreadable = |detail: &str| Failure::Unreadable(format!("params.json {section}: {detail}"));
    let all: Value = serde_json::from_str(PARAMS).map_err(|error| unreadable(&error.to_string()))?;
    let entry = all
        .get(section)
        .and_then(|section| section.get(n.to_string()))
        .ok_or_else(|| Failure::Unreadable(format!("{section}: length {n} is not supported")))?;
    let numbers = |key: &str| -> Result<Vec<u32>, Failure> {
        entry[key]
            .as_array()
            .and_then(|items| items.iter().map(|item| item.as_u64().map(|v| v as u32)).collect())
            .ok_or_else(|| unreadable(key))
    };
    Ok(Pinned {
        trace_log_size: entry["trace_log_size"].as_u64().ok_or_else(|| unreadable("trace_log_size"))?
            as u32,
        ids: entry["ids"]
            .as_array()
            .and_then(|items| items.iter().map(|id| id.as_str().map(str::to_string)).collect())
            .ok_or_else(|| unreadable("ids"))?,
        log_sizes: numbers("log_sizes")?,
        root: numbers("root")?.try_into().map_err(|_| unreadable("root"))?,
    })
}

/// The recursion statement's inner proof is part of the statement, so it is always read at the
/// pinned setting, whatever PROVEN_SECURITY says about the entry's own proof, and with
/// batching_pow_bits = 0: the judge's reference prover does not grind before that coefficient.
fn configs_with(
    pinned: &Pinned,
    n_outputs: usize,
    fri: FriConfig,
    batching_pow_bits: u32,
) -> (CircuitConfig, ProofConfig) {
    let pcs_config = PcsConfig::from_fri_and_trace_size(fri, pinned.trace_log_size);
    let mut proof_config = ProofConfig::new(
        &all_circuit_components::<QM31>(),
        pinned.ids.len(),
        &pcs_config,
        INTERACTION_POW_BITS,
    );
    proof_config.batching_pow_bits = batching_pow_bits;
    let circuit_config = CircuitConfig {
        config: pcs_config,
        n_outputs,
        preprocessed_column_log_sizes: pinned
            .ids
            .iter()
            .zip(&pinned.log_sizes)
            .map(|(id, &log_size)| (PreProcessedColumnId { id: id.clone() }, log_size))
            .collect(),
        preprocessed_root: pinned.root.into(),
        batching_pow_bits,
    };
    (circuit_config, proof_config)
}

fn prove_context(context: FinalizedContext<QM31>) -> Result<Vec<u8>, String> {
    prove_context_with(context, fri_config())
}

fn prove_context_with(mut context: FinalizedContext<QM31>, fri: FriConfig) -> Result<Vec<u8>, String> {
    let preprocessed = PreprocessedCircuit::preprocess_circuit(&mut context);
    let pcs_config = PcsConfig::from_fri_and_trace_size(fri, preprocessed.trace_log_size);
    let proof = prove_circuit_assignment(
        context.values(),
        &preprocessed,
        &BaseColumnPool::<SimdBackend>::new(),
        pcs_config,
    )
    .map_err(|error| format!("proving failed: {error:?}"))?;
    let (proof, _public_data) = prepare_circuit_proof_for_circuit_verifier(proof);
    let mut bytes = Vec::new();
    proof.serialize(&mut bytes);
    let mut out = MAGIC.to_vec();
    out.extend(zstd::encode_all(&bytes[..], 3).map_err(|error| error.to_string())?);
    Ok(out)
}

fn decode(proof: &[u8], proof_config: &ProofConfig) -> Result<Proof<QM31>, String> {
    let body = proof.strip_prefix(MAGIC).ok_or("not a pfc0 proof")?;
    let bytes = zstd::bulk::decompress(body, MAX_PROOF_BYTES)
        .map_err(|error| format!("decompression failed: {error}"))?;
    let mut rest: &[u8] = &bytes;
    let proof = deserialize_proof_with_config(&mut rest, proof_config)
        .map_err(|error| format!("deserialization failed: {error:?}"))?;
    if !rest.is_empty() {
        return Err("trailing bytes after the proof".into());
    }
    Ok(proof)
}

fn verify_with(section: &str, n: usize, proof: &[u8], outputs: Vec<QM31>) -> Result<(), Failure> {
    let (circuit_config, proof_config) =
        configs_with(&pinned(section, n)?, outputs.len(), fri_config(), BATCHING_POW_BITS);
    let proof = decode(proof, &proof_config).map_err(Failure::Rejected)?;
    verify_circuit(circuit_config, proof, CircuitPublicData { output_values: outputs })
        .map(|_| ())
        .map_err(Failure::Rejected)
}

fn words(bytes: [u8; 32]) -> Vec<QM31> {
    HashValue::<QM31>::from(le_u32s_from_bytes::<8, 32>(bytes)).iter().map(|word| *word.get()).collect()
}

/// The outputs of a circuit that verified an inner proof: the BLAKE2s digest of the inner
/// circuit's preprocessed root and its outputs, computed exactly as the verification circuit does.
fn recursion_outputs(inner_root: [u32; 8], inner_outputs: &[QM31]) -> Vec<QM31> {
    let mut context = Context::<QM31>::default();
    let root = HashValue::<QM31>::from(inner_root).guess(&mut context);
    let outputs: Vec<Var> = inner_outputs.iter().map(|value| guess(&mut context, *value)).collect();
    let preimage: Vec<_> =
        root.0.into_iter().chain(unpack_qm31s_to_u32_words(&mut context, outputs)).collect();
    let n_bytes = 4 * preimage.len();
    let digest = blake2s_u32s(&mut context, preimage, n_bytes);
    digest.iter().map(|word| context.get(*word.get())).collect()
}

/// The circuit that verifies an inner proof of a chain of length n ending at y.
fn recursion_context(n: usize, y: [u8; 32], inner_proof: &[u8]) -> Result<FinalizedContext<QM31>, String> {
    let inner = pinned("inner", n).map_err(|failure| match failure {
        Failure::Unreadable(detail) | Failure::Rejected(detail) => detail,
    })?;
    let (inner_config, proof_config) = configs_with(&inner, 8, FRI_CONFIG, 0);
    let proof = decode(inner_proof, &proof_config)?;
    let context =
        build_verification_circuit(inner_config, proof, CircuitPublicData { output_values: words(y) })?;
    if !context.is_circuit_valid() {
        return Err("the inner proof does not verify".into());
    }
    Ok(context)
}

fn params(kind: &str, lengths: &[usize]) -> Result<Value, String> {
    if kind == "matmul" {
        let mut matmul = Map::new();
        for &k in lengths {
            let zeros = vec![0u32; k * k];
            let mut context = matmul_context(k, &zeros, &zeros).finalize(false);
            matmul.insert(k.to_string(), to_json(&pinned_of(&mut context)));
        }
        return Ok(json!({"matmul": matmul}));
    }
    if kind != "chain" {
        return Err("the recursion constants come from the reference binary (entries/stwo-chain), \
                    whose prover makes the judge's inner proofs"
            .into());
    }
    let mut chain = Map::new();
    for &n in lengths {
        let mut context = chain_context([0; 32], n, true).0.finalize(false);
        chain.insert(n.to_string(), to_json(&pinned_of(&mut context)));
    }
    Ok(json!({"chain": chain}))
}

/// The polynomials one proof combines with powers of a single random coefficient in its
/// out-of-domain quotient: the count the batching term of a soundness sheet needs.
fn shape(section: &str, n: usize, proof: &[u8]) -> Result<Value, String> {
    let pinned = pinned(section, n).map_err(|failure| match failure {
        Failure::Unreadable(detail) | Failure::Rejected(detail) => detail,
    })?;
    let (fri, batching_pow_bits) =
        if section == "inner" { (FRI_CONFIG, 0) } else { (fri_config(), BATCHING_POW_BITS) };
    let (_, proof_config) = configs_with(&pinned, 0, fri, batching_pow_bits);
    let proof = decode(proof, &proof_config)?;
    let interaction_prev = proof.interaction_at_oods.iter().filter(|x| x.at_prev.is_some()).count();
    let samples = proof.preprocessed_columns_at_oods.len() + proof.trace_at_oods.len()
        + proof.interaction_at_oods.len() + interaction_prev + proof.composition_eval_at_oods.len();
    Ok(json!({
        "section": section, "n": n, "log_trace_size": pinned.trace_log_size,
        "log_evaluation_domain": pinned.trace_log_size + fri.log_blowup_factor,
        "preprocessed": proof.preprocessed_columns_at_oods.len(), "trace": proof.trace_at_oods.len(),
        "interaction": proof.interaction_at_oods.len(), "interaction_at_prev": interaction_prev,
        "composition": proof.composition_eval_at_oods.len(), "samples_batched": samples,
    }))
}

struct Statement {
    n: usize,
    seed: Option<[u8; 32]>,
    y: [u8; 32],
    inner_proof: Option<Vec<u8>>,
}

fn hex32(value: &Value, key: &str) -> Result<[u8; 32], String> {
    let text = value[key].as_str().ok_or_else(|| format!("{key}: expected a hex string"))?;
    let bytes = hex::decode(text).map_err(|error| format!("{key}: {error}"))?;
    bytes.try_into().map_err(|_| format!("{key}: expected 32 bytes"))
}

fn read_statement(path: &str, kind: &str) -> Result<Statement, String> {
    let text = std::fs::read_to_string(path).map_err(|error| format!("{path}: {error}"))?;
    let value: Value = serde_json::from_str(&text).map_err(|error| format!("{path}: {error}"))?;
    if value["statement"] != kind {
        return Err(format!("{path}: not a {kind} statement"));
    }
    let n = value["n"]
        .as_u64()
        .filter(|&n| n >= 1)
        .ok_or_else(|| format!("{path}: n must be a positive integer"))? as usize;
    let seed = if value.get("seed").is_some() { Some(hex32(&value, "seed")?) } else { None };
    let inner_proof = match value["witness_inner_proof"].as_str() {
        Some(text) => Some(hex::decode(text).map_err(|error| format!("witness_inner_proof: {error}"))?),
        None => None,
    };
    Ok(Statement { n, seed, y: hex32(&value, "y")?, inner_proof })
}

struct Matmul {
    k: usize,
    a: Vec<u32>,
    b: Vec<u32>,
    c: Vec<u32>,
}

fn read_matmul(path: &str) -> Result<Matmul, String> {
    let text = std::fs::read_to_string(path).map_err(|error| format!("{path}: {error}"))?;
    let value: Value = serde_json::from_str(&text).map_err(|error| format!("{path}: {error}"))?;
    if value["statement"] != MATMUL {
        return Err(format!("{path}: not a {MATMUL} statement"));
    }
    let k = value["k"].as_u64().ok_or_else(|| format!("{path}: k must be an integer"))? as usize;
    if !(2..=64).contains(&k) || k % 2 != 0 {
        return Err(format!("{path}: k must be even, from 2 to 64"));
    }
    let matrix = |key: &str| -> Result<Vec<u32>, String> {
        let bytes = hex::decode(value[key].as_str().ok_or_else(|| format!("{key}: expected hex"))?)
            .map_err(|error| format!("{key}: {error}"))?;
        if bytes.len() != 4 * k * k {
            return Err(format!("{key}: expected {} bytes", 4 * k * k));
        }
        Ok(bytes.chunks_exact(4).map(|word| u32::from_le_bytes(word.try_into().unwrap())).collect())
    };
    Ok(Matmul { k, a: matrix("a")?, b: matrix("b")?, c: matrix("c")? })
}

fn product(k: usize, a: &[u32], b: &[u32]) -> Vec<u32> {
    let mut c = vec![0u32; k * k];
    for i in 0..k {
        for t in 0..k {
            for j in 0..k {
                c[i * k + j] = c[i * k + j].wrapping_add(a[i * k + t].wrapping_mul(b[t * k + j]));
            }
        }
    }
    c
}

fn prove_command(command: &str, path: &str) -> Result<Vec<u8>, String> {
    if command == "matmul-prove" {
        let statement = read_matmul(path)?;
        if product(statement.k, &statement.a, &statement.b) != statement.c {
            return Err("the statement is false: C is not A * B mod 2^32".into());
        }
        return prove_context(matmul_context(statement.k, &statement.a, &statement.b).finalize(false));
    }
    if command == "recursion-prove" {
        let statement = read_statement(path, RECURSION)?;
        let inner_proof = statement.inner_proof.ok_or("the statement holds no witness_inner_proof")?;
        return prove_context(recursion_context(statement.n, statement.y, &inner_proof)?);
    }
    let statement = read_statement(path, CHAIN)?;
    let seed = statement.seed.ok_or("the statement holds no seed")?;
    let (context, y_words) = chain_context(seed, statement.n, true);
    if y_words != le_u32s_from_bytes::<8, 32>(statement.y) {
        return Err("the statement is false: y is not the chain's output".into());
    }
    prove_context(context.finalize(false))
}

fn verify_command(command: &str, statement: &Statement, proof: &[u8]) -> Result<(), Failure> {
    match command {
        "verify" => {
            let seed = statement.seed.ok_or_else(|| Failure::Unreadable("no seed".into()))?;
            let outputs = words(seed).into_iter().chain(words(statement.y)).collect();
            verify_with("chain", statement.n, proof, outputs)
        }
        _ => {
            let inner = pinned("inner", statement.n)?;
            verify_with("outer", statement.n, proof, recursion_outputs(inner.root, &words(statement.y)))
        }
    }
}

fn run_verify(command: &str, statement_path: &str, proof_path: &str) -> ExitCode {
    if command == "matmul-verify" {
        let statement = match read_matmul(statement_path) {
            Ok(statement) => statement,
            Err(error) => {
                eprintln!("{error}");
                return ExitCode::from(1);
            }
        };
        let proof = match std::fs::read(proof_path) {
            Ok(proof) => proof,
            Err(error) => {
                eprintln!("{proof_path}: {error}");
                return ExitCode::from(1);
            }
        };
        let outputs: Vec<QM31> =
            [&statement.a, &statement.b, &statement.c].iter().flat_map(|m| m.iter().map(|&w| bytes_of(w))).collect();
        return report(catch_unwind(|| verify_with("matmul", statement.k, &proof, outputs)));
    }
    let kind = if command == "verify" { CHAIN } else { RECURSION };
    let statement = match read_statement(statement_path, kind) {
        Ok(statement) => statement,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::from(1);
        }
    };
    let proof = match std::fs::read(proof_path) {
        Ok(proof) => proof,
        Err(error) => {
            eprintln!("{proof_path}: {error}");
            return ExitCode::from(1);
        }
    };
    report(catch_unwind(|| verify_command(command, &statement, &proof)))
}

/// A panic on adversarial bytes is a rejection, never an acceptance.
fn report(outcome: std::thread::Result<Result<(), Failure>>) -> ExitCode {
    match outcome {
        Ok(Ok(())) => {
            println!("VERIFY\tACCEPTED");
            ExitCode::SUCCESS
        }
        Ok(Err(Failure::Unreadable(error))) => {
            eprintln!("{error}");
            ExitCode::from(1)
        }
        Ok(Err(Failure::Rejected(reason))) => {
            println!("VERIFY\tREJECTED\t{reason}");
            ExitCode::from(20)
        }
        Err(_) => {
            println!("VERIFY\tREJECTED\tverifier panicked");
            ExitCode::from(20)
        }
    }
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let command = args.get(1).map(String::as_str).unwrap_or("");
    let result = match (command, args.len()) {
        ("params", 4..) => {
            let lengths: Result<Vec<usize>, _> = args[3..].iter().map(|n| n.parse()).collect();
            lengths
                .map_err(|_| "chain lengths must be integers".to_string())
                .and_then(|lengths| params(&args[2], &lengths))
                .map(|value| serde_json::to_vec_pretty(&value).unwrap())
        }
        ("shape", 5) => args[3]
            .parse::<usize>()
            .map_err(|_| "n must be an integer".to_string())
            .and_then(|n| std::fs::read(&args[4]).map_err(|e| e.to_string()).map(|p| (n, p)))
            .and_then(|(n, proof)| shape(&args[2], n, &proof))
            .map(|value| serde_json::to_vec_pretty(&value).unwrap()),
        ("prove" | "recursion-prove" | "matmul-prove", 3) => prove_command(command, &args[2]),
        ("verify" | "recursion-verify" | "matmul-verify", 4) => {
            return run_verify(command, &args[2], &args[3]);
        }
        _ => Err("usage: chain prove|recursion-prove|matmul-prove STATEMENT | \
                  chain verify|recursion-verify|matmul-verify STATEMENT PROOF | \
                  chain params chain|matmul N... | chain shape SECTION N PROOF"
            .into()),
    };
    match result.and_then(|bytes| std::io::stdout().write_all(&bytes).map_err(|error| error.to_string())) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("{error}");
            ExitCode::from(1)
        }
    }
}
