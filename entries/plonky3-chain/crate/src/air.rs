//! An AIR for the BLAKE2s-256 hash chain: row i hashes the previous row's 32-byte digest.
//!
//! BLAKE2s-256 of a 32-byte message is one compression with a fixed starting state: the
//! parameter block (32-byte digest, no key, fanout 1, depth 1) folded into the IV, the message
//! padded with zeros to 64 bytes, a byte counter of 32 and the last-block flag. So every row
//! starts from the same constant state, mixes ten rounds of the message words (the previous
//! digest, then eight zero words), and outputs h ^ v[0..8] ^ v[8..16].
//!
//! The round machinery is Plonky3's BLAKE3 AIR (`p3-blake3-air`), whose G function is BLAKE2s's:
//! words in rows 0 and 2 of the state are two 16-bit limbs, words in rows 1 and 3 are 32 bits.

use core::array;
use core::borrow::{Borrow, BorrowMut};
use core::mem::size_of;

use p3_air::utils::{add2, add3, pack_bits_le, u32_to_bits_le, xor_32_shift};
use p3_air::{Air, AirBuilder, BaseAir, WindowAccess};
use p3_field::{PrimeCharacteristicRing, PrimeField64};
use p3_matrix::dense::RowMajorMatrix;
use p3_maybe_rayon::prelude::*;

const LIMB: usize = 16;
const ROUNDS: usize = 10;
const IV: [u32; 8] = [
    0x6A09_E667, 0xBB67_AE85, 0x3C6E_F372, 0xA54F_F53A, 0x510E_527F, 0x9B05_688C, 0x1F83_D9AB,
    0x5BE0_CD19,
];
/// The message schedule of RFC 7693, one permutation per round.
const SIGMA: [[usize; 16]; ROUNDS] = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    [14, 10, 4, 8, 9, 15, 13, 6, 1, 12, 0, 2, 11, 7, 5, 3],
    [11, 8, 12, 0, 5, 2, 15, 13, 10, 14, 3, 6, 7, 1, 9, 4],
    [7, 9, 3, 1, 13, 12, 11, 14, 2, 6, 5, 10, 4, 0, 15, 8],
    [9, 0, 5, 7, 2, 4, 10, 15, 14, 1, 11, 12, 6, 8, 3, 13],
    [2, 12, 6, 10, 0, 11, 8, 3, 4, 13, 7, 5, 15, 14, 1, 9],
    [12, 5, 1, 15, 14, 13, 4, 10, 0, 7, 6, 3, 9, 2, 8, 11],
    [13, 11, 7, 14, 12, 1, 3, 9, 5, 0, 15, 4, 8, 6, 2, 10],
    [6, 15, 14, 9, 11, 3, 0, 8, 12, 2, 13, 7, 1, 4, 10, 5],
    [10, 2, 8, 4, 7, 6, 1, 5, 15, 11, 9, 14, 3, 12, 13, 0],
];
/// The chaining value: the IV with the parameter block 0x01010020 folded into its first word.
const H: [u32; 8] = [IV[0] ^ 0x0101_0020, IV[1], IV[2], IV[3], IV[4], IV[5], IV[6], IV[7]];
/// The starting state: H, the IV, the byte counter (32) and the last-block flag.
const V0: [[u32; 4]; 4] = [
    [H[0], H[1], H[2], H[3]],
    [H[4], H[5], H[6], H[7]],
    [IV[0], IV[1], IV[2], IV[3]],
    [IV[4] ^ 32, IV[5], !IV[6], IV[7]],
];
/// Public values: the seed then y, each eight words as sixteen 16-bit limbs.
pub const NUM_PUBLIC_VALUES: usize = 32;

/// The state at one moment: rows 0 and 2 as 16-bit limbs, rows 1 and 3 as bits.
#[repr(C)]
pub struct State<T> {
    pub row0: [[T; 2]; 4],
    pub row1: [[T; 32]; 4],
    pub row2: [[T; 2]; 4],
    pub row3: [[T; 32]; 4],
}

/// One round: the column G steps in two halves, then the diagonal G steps in two halves.
#[repr(C)]
pub struct Round<T> {
    pub prime: State<T>,
    pub middle: State<T>,
    pub middle_prime: State<T>,
    pub output: State<T>,
}

#[repr(C)]
pub struct ChainCols<T> {
    /// The message: the previous row's digest (the seed on the first row), as bits.
    pub message: [[T; 32]; 8],
    /// The constant starting state.
    pub initial: State<T>,
    pub rounds: [Round<T>; ROUNDS],
    /// The final v[8..12], as bits.
    pub row2_bits: [[T; 32]; 4],
    /// v[i] ^ v[i + 8] for i < 4, as bits.
    pub low_xor: [[T; 32]; 4],
    /// H ^ v[0..8] ^ v[8..16], as bits.
    pub digest: [[T; 32]; 8],
}

pub const WIDTH: usize = size_of::<ChainCols<u8>>();
/// The message columns, read on the next row by the chaining constraint.
const MESSAGE_COLUMNS: usize = 8 * 32;

impl<T> Borrow<ChainCols<T>> for [T] {
    fn borrow(&self) -> &ChainCols<T> {
        debug_assert_eq!(self.len(), WIDTH);
        let (prefix, cols, suffix) = unsafe { self.align_to::<ChainCols<T>>() };
        debug_assert!(prefix.is_empty() && suffix.is_empty() && cols.len() == 1);
        &cols[0]
    }
}

impl<T> BorrowMut<ChainCols<T>> for [T] {
    fn borrow_mut(&mut self) -> &mut ChainCols<T> {
        debug_assert_eq!(self.len(), WIDTH);
        let (prefix, cols, suffix) = unsafe { self.align_to_mut::<ChainCols<T>>() };
        debug_assert!(prefix.is_empty() && suffix.is_empty() && cols.len() == 1);
        &mut cols[0]
    }
}

/// The inputs and outputs of one G step, in the AIR's representation.
struct G<'a, T, U> {
    a: &'a [T; 2],
    b: &'a [T; 32],
    c: &'a [T; 2],
    d: &'a [T; 32],
    m_first: &'a [U; 2],
    a_prime: &'a [T; 2],
    b_prime: &'a [T; 32],
    c_prime: &'a [T; 2],
    d_prime: &'a [T; 32],
    m_second: &'a [U; 2],
    a_out: &'a [T; 2],
    b_out: &'a [T; 32],
    c_out: &'a [T; 2],
    d_out: &'a [T; 32],
}

fn limbs<AB: AirBuilder>(bits: &[AB::Var; 32]) -> [AB::Expr; 2] {
    [pack_bits_le(bits[..LIMB].iter().copied()), pack_bits_le(bits[LIMB..].iter().copied())]
}

/// x ^ bit for a constant bit: linear in x.
fn xor_constant<AB: AirBuilder>(x: AB::Expr, bit: bool) -> AB::Expr {
    if bit { AB::Expr::ONE - x } else { x }
}

/// One G step, as `p3-blake3-air` checks it: inputs range checked, every output range checked.
fn g_step<AB: AirBuilder>(builder: &mut AB, g: &G<'_, AB::Var, AB::Expr>) {
    add3(builder, g.a_prime, g.a, &limbs::<AB>(g.b), g.m_first);
    xor_32_shift(builder, g.a_prime, g.d, g.d_prime, 16);
    add2(builder, g.c_prime, g.c, &limbs::<AB>(g.d_prime));
    xor_32_shift(builder, g.c_prime, g.b, g.b_prime, 12);
    add3(builder, g.a_out, g.a_prime, &limbs::<AB>(g.b_prime), g.m_second);
    xor_32_shift(builder, g.a_out, g.d_prime, g.d_out, 8);
    add2(builder, g.c_out, g.c_prime, &limbs::<AB>(g.d_out));
    xor_32_shift(builder, g.c_out, g.b_prime, g.b_out, 7);
}

fn round<AB: AirBuilder>(
    builder: &mut AB,
    input: &State<AB::Var>,
    data: &Round<AB::Var>,
    m: &[[AB::Expr; 2]; 16],
) {
    for i in 0..4 {
        g_step(builder, &G {
            a: &input.row0[i], b: &input.row1[i], c: &input.row2[i], d: &input.row3[i],
            m_first: &m[2 * i],
            a_prime: &data.prime.row0[i], b_prime: &data.prime.row1[i],
            c_prime: &data.prime.row2[i], d_prime: &data.prime.row3[i],
            m_second: &m[2 * i + 1],
            a_out: &data.middle.row0[i], b_out: &data.middle.row1[i],
            c_out: &data.middle.row2[i], d_out: &data.middle.row3[i],
        });
    }
    for i in 0..4 {
        let (b, c, d) = ((i + 1) % 4, (i + 2) % 4, (i + 3) % 4);
        g_step(builder, &G {
            a: &data.middle.row0[i], b: &data.middle.row1[b],
            c: &data.middle.row2[c], d: &data.middle.row3[d],
            m_first: &m[8 + 2 * i],
            a_prime: &data.middle_prime.row0[i], b_prime: &data.middle_prime.row1[b],
            c_prime: &data.middle_prime.row2[c], d_prime: &data.middle_prime.row3[d],
            m_second: &m[9 + 2 * i],
            a_out: &data.output.row0[i], b_out: &data.output.row1[b],
            c_out: &data.output.row2[c], d_out: &data.output.row3[d],
        });
    }
}

pub struct Blake2sChainAir;

impl<F> BaseAir<F> for Blake2sChainAir {
    fn width(&self) -> usize {
        WIDTH
    }

    fn main_next_row_columns(&self) -> Vec<usize> {
        (0..MESSAGE_COLUMNS).collect()
    }

    fn max_constraint_degree(&self) -> Option<usize> {
        Some(3)
    }

    fn num_public_values(&self) -> usize {
        NUM_PUBLIC_VALUES
    }
}

impl<AB: AirBuilder> Air<AB> for Blake2sChainAir {
    fn eval(&self, builder: &mut AB) {
        let main = builder.main();
        let local: &ChainCols<AB::Var> = main.current_slice().borrow();
        let next: &ChainCols<AB::Var> = main.next_slice().borrow();
        let public: Vec<AB::Expr> = builder.public_values().iter().map(|&v| v.into()).collect();

        for &bit in local.message.iter().flatten() {
            builder.assert_bool(bit);
        }
        // The starting state is the constant V0.
        let start = &local.initial;
        for i in 0..4 {
            for (limb, word) in [(&start.row0[i], V0[0][i]), (&start.row2[i], V0[2][i])] {
                builder.assert_eq(limb[0], AB::Expr::from_u16(word as u16));
                builder.assert_eq(limb[1], AB::Expr::from_u16((word >> 16) as u16));
            }
            for (bits, word) in [(&start.row1[i], V0[1][i]), (&start.row3[i], V0[3][i])] {
                for (b, &bit) in bits.iter().enumerate() {
                    builder.assert_eq(bit, AB::Expr::from_bool((word >> b) & 1 == 1));
                }
            }
        }

        // The message words: the previous digest, then eight zero words.
        let words: [[AB::Expr; 2]; 16] = array::from_fn(|i| {
            if i < 8 { limbs::<AB>(&local.message[i]) } else { [AB::Expr::ZERO, AB::Expr::ZERO] }
        });
        let mut input = &local.initial;
        for (r, data) in local.rounds.iter().enumerate() {
            let m: [[AB::Expr; 2]; 16] = array::from_fn(|k| words[SIGMA[r][k]].clone());
            round(builder, input, data, &m);
            input = &data.output;
        }

        // The output: H ^ v[i] ^ v[i + 8].
        let v = &local.rounds[ROUNDS - 1].output;
        for i in 0..4 {
            let [low, high] = limbs::<AB>(&local.row2_bits[i]);
            builder.assert_eq(low, v.row2[i][0]);
            builder.assert_eq(high, v.row2[i][1]);
            for &bit in &local.low_xor[i] {
                builder.assert_bool(bit);
            }
            xor_32_shift(builder, &v.row0[i], &local.low_xor[i], &local.row2_bits[i], 0);
            for b in 0..32 {
                let h_bit = (H[i] >> b) & 1 == 1;
                builder.assert_eq(local.digest[i][b], xor_constant::<AB>(local.low_xor[i][b].into(), h_bit));
                let high_xor = v.row1[i][b].into().xor(&v.row3[i][b].into());
                let h_bit = (H[i + 4] >> b) & 1 == 1;
                builder.assert_eq(local.digest[i + 4][b], xor_constant::<AB>(high_xor, h_bit));
            }
        }

        // Boundaries: the first message is the seed, the last digest is y.
        for w in 0..8 {
            let [low, high] = limbs::<AB>(&local.message[w]);
            builder.when_first_row().assert_eq(low, public[2 * w].clone());
            builder.when_first_row().assert_eq(high, public[2 * w + 1].clone());
            let [low, high] = limbs::<AB>(&local.digest[w]);
            builder.when_last_row().assert_eq(low, public[16 + 2 * w].clone());
            builder.when_last_row().assert_eq(high, public[16 + 2 * w + 1].clone());
        }
        // The chain: each row's message is the previous row's digest.
        for w in 0..8 {
            for b in 0..32 {
                builder.when_transition().assert_eq(next.message[w][b], local.digest[w][b]);
            }
        }
    }
}

/// One G half step on words, as the reference computes it.
const fn half_g(mut a: u32, mut b: u32, mut c: u32, mut d: u32, m: u32, second: bool) -> (u32, u32, u32, u32) {
    let (r1, r2) = if second { (8, 7) } else { (16, 12) };
    a = a.wrapping_add(b).wrapping_add(m);
    d = (d ^ a).rotate_right(r1);
    c = c.wrapping_add(d);
    b = (b ^ c).rotate_right(r2);
    (a, b, c, d)
}

fn save<F: PrimeCharacteristicRing>(trace: &mut State<F>, state: &[[u32; 4]; 4]) {
    let limbs = |w: u32| [F::from_u16(w as u16), F::from_u16((w >> 16) as u16)];
    trace.row0 = array::from_fn(|i| limbs(state[0][i]));
    trace.row1 = array::from_fn(|i| u32_to_bits_le(state[1][i]));
    trace.row2 = array::from_fn(|i| limbs(state[2][i]));
    trace.row3 = array::from_fn(|i| u32_to_bits_le(state[3][i]));
}

fn round_trace<F: PrimeCharacteristicRing>(data: &mut Round<F>, s: &mut [[u32; 4]; 4], m: &[u32; 16]) {
    for (second, target) in [(false, 0), (true, 1)] {
        for i in 0..4 {
            (s[0][i], s[1][i], s[2][i], s[3][i]) =
                half_g(s[0][i], s[1][i], s[2][i], s[3][i], m[2 * i + target], second);
        }
        save(if second { &mut data.middle } else { &mut data.prime }, s);
    }
    for (second, target) in [(false, 8), (true, 9)] {
        for i in 0..4 {
            let (b, c, d) = ((i + 1) % 4, (i + 2) % 4, (i + 3) % 4);
            (s[0][i], s[1][b], s[2][c], s[3][d]) =
                half_g(s[0][i], s[1][b], s[2][c], s[3][d], m[target + 2 * i], second);
        }
        save(if second { &mut data.output } else { &mut data.middle_prime }, s);
    }
}

/// One BLAKE2s-256 of a 32-byte message, filling one row; returns the digest words.
fn row_trace<F: PrimeCharacteristicRing>(row: &mut ChainCols<F>, message: [u32; 8]) -> [u32; 8] {
    row.message = message.map(u32_to_bits_le);
    save(&mut row.initial, &V0);
    let words: [u32; 16] = array::from_fn(|i| if i < 8 { message[i] } else { 0 });
    let mut state = V0;
    for (r, data) in row.rounds.iter_mut().enumerate() {
        let m: [u32; 16] = array::from_fn(|k| words[SIGMA[r][k]]);
        round_trace(data, &mut state, &m);
    }
    let digest: [u32; 8] = array::from_fn(|i| H[i] ^ state[i / 4][i % 4] ^ state[2 + i / 4][i % 4]);
    row.row2_bits = state[2].map(u32_to_bits_le);
    row.low_xor = array::from_fn(|i| u32_to_bits_le(state[0][i] ^ state[2][i]));
    row.digest = digest.map(u32_to_bits_le);
    digest
}

/// One BLAKE2s-256 of a 32-byte message, on words: the reference the trace must agree with.
fn compress(message: [u32; 8]) -> [u32; 8] {
    let words: [u32; 16] = array::from_fn(|i| if i < 8 { message[i] } else { 0 });
    let mut s = V0;
    for sigma in SIGMA {
        let m: [u32; 16] = array::from_fn(|k| words[sigma[k]]);
        for (second, target) in [(false, 0), (true, 1)] {
            for i in 0..4 {
                (s[0][i], s[1][i], s[2][i], s[3][i]) =
                    half_g(s[0][i], s[1][i], s[2][i], s[3][i], m[2 * i + target], second);
            }
        }
        for (second, target) in [(false, 8), (true, 9)] {
            for i in 0..4 {
                let (b, c, d) = ((i + 1) % 4, (i + 2) % 4, (i + 3) % 4);
                (s[0][i], s[1][b], s[2][c], s[3][d]) =
                    half_g(s[0][i], s[1][b], s[2][c], s[3][d], m[target + 2 * i], second);
            }
        }
    }
    array::from_fn(|i| H[i] ^ s[i / 4][i % 4] ^ s[2 + i / 4][i % 4])
}

/// The BLAKE2s-256 chain of `n` steps from `seed`.
pub fn chain_words(seed: [u32; 8], n: usize) -> [u32; 8] {
    (0..n).fold(seed, |words, _| compress(words))
}

/// The trace of the chain of `n` steps (a power of two) from `seed`, and y.
pub fn generate_trace<F: PrimeField64>(seed: [u32; 8], n: usize, log_blowup: usize) -> (RowMajorMatrix<F>, [u32; 8]) {
    assert!(n.is_power_of_two(), "the chain length must be a power of two");
    // The messages first: each row hashes the previous digest.
    let mut messages = Vec::with_capacity(n);
    let mut words = seed;
    for _ in 0..n {
        messages.push(words);
        words = compress(words);
    }
    let mut values = F::zero_vec((n * WIDTH) << log_blowup);
    values.truncate(n * WIDTH);
    let mut trace = RowMajorMatrix::new(values, WIDTH);
    let (prefix, rows, suffix) = unsafe { trace.values.align_to_mut::<ChainCols<F>>() };
    assert!(prefix.is_empty() && suffix.is_empty() && rows.len() == n);
    rows.par_iter_mut().zip(messages).for_each(|(row, message)| {
        let digest = row_trace(row, message);
        debug_assert_eq!(digest, compress(message));
    });
    (trace, words)
}
