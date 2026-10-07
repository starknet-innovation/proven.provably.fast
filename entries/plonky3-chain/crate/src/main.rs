//! A Plonky3 floor entry for blake2s-chain-v0 (proven.provably.fast): the BLAKE2s-256 chain as a
//! uni-STARK over BabyBear, challenges in its degree-5 extension (about 2^155), FRI at rate 1/4
//! with 107 queries and 26 bits of proof of work, Keccak-256 Merkle commitments.
//!
//!   p3-chain prove STATEMENT > PROOF
//!   p3-chain verify STATEMENT PROOF         exits 0 to accept, 20 to reject, 1 if unreadable
//!   p3-chain security N                     Plonky3's own proven-security estimate (JSON)
//!
//! The verifier reads only the public statement (n, seed, y) and the proof; it fixes the trace
//! height to n, so a proof of a shorter chain cannot pass.

mod air;

use std::io::Write;
use std::panic::catch_unwind;
use std::process::ExitCode;

use air::{Blake2sChainAir, NUM_PUBLIC_VALUES, chain_words, generate_trace};
use p3_baby_bear::BabyBear;
use p3_challenger::{HashChallenger, SerializingChallenger32};
use p3_commit::ExtensionMmcs;
use p3_dft::Radix2DitParallel;
use p3_field::coset::TwoAdicMultiplicativeCoset;
use p3_field::extension::BinomialExtensionField;
use p3_field::{Field, PrimeCharacteristicRing};
use p3_fri::{FriParameters, TwoAdicFriPcs};
use p3_keccak::{Keccak256Hash, KeccakF};
use p3_merkle_tree::MerkleTreeMmcs;
use p3_symmetric::{CompressionFunctionFromHasher, PaddingFreeSponge, SerializingHasher};
use p3_uni_stark::{
    AirLayout, OpeningShape, Proof, ProvenSecurity, StarkConfig, StarkSecurityParams, prove, verify,
};
use serde_json::{Value, json};

type F = BabyBear;
type EF = BinomialExtensionField<BabyBear, 5>;
type Sponge = PaddingFreeSponge<KeccakF, 25, 17, 4>;
type Compression = CompressionFunctionFromHasher<Sponge, 2, 4>;
type ValMmcs = MerkleTreeMmcs<
    [F; p3_keccak::VECTOR_LEN],
    [u64; p3_keccak::VECTOR_LEN],
    SerializingHasher<Sponge>,
    Compression,
    2,
    4,
>;
type ChallengeMmcs = ExtensionMmcs<F, EF, ValMmcs>;
type Pcs = TwoAdicFriPcs<F, Radix2DitParallel<F>, ValMmcs, ChallengeMmcs>;
type Config = StarkConfig<Pcs, EF, SerializingChallenger32<F, HashChallenger<u8, Keccak256Hash, 32>>>;

const STATEMENT: &str = "blake2s-chain-v0";
const MAX_PROOF_BYTES: usize = 64 << 20;

fn val_mmcs() -> ValMmcs {
    let sponge = Sponge::new(KeccakF {});
    ValMmcs::new(SerializingHasher::new(sponge), Compression::new(sponge), 3)
}

/// Rate 1/4, 107 queries and 26 bits of proof of work before the queries, as the Stwo entries.
fn fri_parameters() -> FriParameters<ChallengeMmcs> {
    FriParameters {
        log_blowup: 2,
        log_final_poly_len: 0,
        max_log_arity: 3,
        num_queries: 107,
        batch_proof_of_work_bits: 0,
        commit_proof_of_work_bits: 0,
        query_proof_of_work_bits: 26,
        mmcs: ChallengeMmcs::new(val_mmcs()),
    }
}

fn config() -> Config {
    let pcs = Pcs::new(Radix2DitParallel::default(), val_mmcs(), fri_parameters());
    Config::new(pcs, SerializingChallenger32::from_hasher(vec![], Keccak256Hash {}))
}

struct Statement {
    n: usize,
    seed: [u32; 8],
    y: [u32; 8],
}

fn words(value: &Value, key: &str) -> Result<[u32; 8], String> {
    let text = value[key].as_str().ok_or_else(|| format!("{key}: expected a hex string"))?;
    let bytes = hex::decode(text).map_err(|error| format!("{key}: {error}"))?;
    let bytes: [u8; 32] = bytes.try_into().map_err(|_| format!("{key}: expected 32 bytes"))?;
    Ok(std::array::from_fn(|i| u32::from_le_bytes(bytes[4 * i..4 * i + 4].try_into().unwrap())))
}

fn read_statement(path: &str) -> Result<Statement, String> {
    let text = std::fs::read_to_string(path).map_err(|error| format!("{path}: {error}"))?;
    let value: Value = serde_json::from_str(&text).map_err(|error| format!("{path}: {error}"))?;
    if value["statement"] != STATEMENT {
        return Err(format!("{path}: not a {STATEMENT} statement"));
    }
    let n = value["n"].as_u64().ok_or("n: expected an integer")? as usize;
    if !n.is_power_of_two() || n < 2 {
        return Err("n: this entry proves chains whose length is a power of two".into());
    }
    Ok(Statement { n, seed: words(&value, "seed")?, y: words(&value, "y")? })
}

/// The seed then y, each word as two 16-bit limbs.
fn public_values(statement: &Statement) -> Vec<F> {
    let values: Vec<F> = statement
        .seed
        .iter()
        .chain(&statement.y)
        .flat_map(|&w| [F::from_u16(w as u16), F::from_u16((w >> 16) as u16)])
        .collect();
    debug_assert_eq!(values.len(), NUM_PUBLIC_VALUES);
    values
}

fn prove_command(path: &str) -> Result<Vec<u8>, String> {
    let statement = read_statement(path)?;
    let (trace, y) = generate_trace::<F>(statement.seed, statement.n, fri_parameters().log_blowup);
    if y != statement.y {
        return Err("the statement is false: y is not the chain's output".into());
    }
    let proof = prove(&config(), &Blake2sChainAir, trace, &public_values(&statement))
        .map_err(|error| format!("proving failed: {error:?}"))?;
    postcard::to_allocvec(&proof).map_err(|error| error.to_string())
}

enum Failure {
    Unreadable(String),
    Rejected(String),
}

fn verify_command(statement_path: &str, proof_path: &str) -> Result<(), Failure> {
    let statement = read_statement(statement_path).map_err(Failure::Unreadable)?;
    let bytes = std::fs::read(proof_path).map_err(|e| Failure::Unreadable(format!("{proof_path}: {e}")))?;
    if bytes.len() > MAX_PROOF_BYTES {
        return Err(Failure::Rejected("the proof is too large".into()));
    }
    let (proof, rest): (Proof<Config>, &[u8]) = postcard::take_from_bytes(&bytes)
        .map_err(|error| Failure::Rejected(format!("deserialization failed: {error}")))?;
    if !rest.is_empty() {
        return Err(Failure::Rejected("trailing bytes after the proof".into()));
    }
    if proof.degree_bits != statement.n.trailing_zeros() as usize {
        return Err(Failure::Rejected("the proof is for another chain length".into()));
    }
    verify(&config(), &Blake2sChainAir, &proof, &public_values(&statement))
        .map_err(|error| Failure::Rejected(format!("{error:?}")))
}

/// Plonky3's proven-security estimate for this configuration at chain length n.
fn security(n: usize) -> Value {
    let air = Blake2sChainAir;
    let fri = fri_parameters();
    let params = StarkSecurityParams::from_air::<F, EF, _>(
        fri.security_regime(),
        &air,
        AirLayout::from_air::<F>(&air),
        TwoAdicMultiplicativeCoset::new(F::ONE, n.trailing_zeros() as usize).unwrap(),
        EF::bits(),
        128,
        2,
        OpeningShape::new(),
        fri.grinding_sites(),
    );
    let proven = ProvenSecurity::compute_from_proof(n.trailing_zeros() as usize, &params);
    json!({"n": n, "unique_decoding_bits": proven.unique_decoding_bits,
           "list_decoding_bits": proven.list_decoding_bits, "challenge_field_bits": EF::bits()})
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    match (args.get(1).map(String::as_str), args.len()) {
        (Some("prove"), 3) => match prove_command(&args[2]) {
            Ok(bytes) => {
                std::io::stdout().write_all(&bytes).expect("stdout");
                ExitCode::SUCCESS
            }
            Err(error) => {
                eprintln!("{error}");
                ExitCode::from(1)
            }
        },
        (Some("verify"), 4) => match catch_unwind(|| verify_command(&args[2], &args[3])) {
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
        },
        (Some("security"), 3) => match args[2].parse::<usize>() {
            Ok(n) if n.is_power_of_two() => {
                println!("{}", security(n));
                ExitCode::SUCCESS
            }
            _ => {
                eprintln!("N must be a power of two");
                ExitCode::from(1)
            }
        },
        (Some("check"), 4) => {
            // A reference check for tests: the chain of N steps from SEED_HEX, as hex.
            let seed = match words(&json!({"s": args[3]}), "s") {
                Ok(seed) => seed,
                Err(error) => {
                    eprintln!("{error}");
                    return ExitCode::from(1);
                }
            };
            let y = chain_words(seed, args[2].parse().unwrap_or(1));
            println!("{}", hex::encode(y.iter().flat_map(|w| w.to_le_bytes()).collect::<Vec<_>>()));
            ExitCode::SUCCESS
        }
        _ => {
            eprintln!("usage: p3-chain prove STATEMENT | verify STATEMENT PROOF | security N");
            ExitCode::from(1)
        }
    }
}
