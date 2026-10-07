"""Statements of the proven.provably.fast open board, and how the judge makes them.

A statement is a JSON object with a fresh seed for every run, so no entry can cache results
across runs. Fields named witness_* go to the prover only; the verifier sees the rest.

blake2s-chain-v0: y = H^n(seed), H = BLAKE2s-256 of the previous 32-byte digest (one
compression per step, no key, 32-byte output). Public: n, seed, y. Anyone can check it natively.

u32-matmul-v0: C = A * B mod 2^32 for random k x k matrices of 32-bit words, little-endian,
row-major. Public: k, a, b, c. Anyone can check it natively.

stwo-verify-v0, a recursion step: the pinned inner verifier (the Stwo chain entry's
`inner-verify`, 107 queries) accepts witness_inner_proof, a zero-knowledge-blinded proof that
someone knows a seed whose n-step chain ends at y. Public: n, y. The seed is never published,
so an entrant must verify the inner proof rather than prove the chain.

    python3 -m proven.statements blake2s-chain-v0 --n 1024 > statement.json
    python3 -m proven.statements blake2s-chain-v0 --n 1024 --seed 00..00 --wrong-y > false.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

BLAKE2S_CHAIN = "blake2s-chain-v0"
STWO_VERIFY = "stwo-verify-v0"
U32_MATMUL = "u32-matmul-v0"
# The Stwo entry binary holds the recursion statement's inner prover and verifier.
CHAIN_BIN = Path(os.environ.get("PROVEN_CHAIN_BIN",
                                Path(__file__).resolve().parents[1] / "entries/stwo-chain/chain"))
# The board: the size every entry is measured at, and caps at twice the Stwo reference entry
# measured on the evaluator host (Linux x86-64, 16 cpus, 2026-10-07): the chain's 616 KB proof
# verified in 0.32 s including process start.
BOARD = {BLAKE2S_CHAIN: {"n": 16384, "floor_bits": 96, "max_proof_bytes": 1_232_000,
                         "max_verify_seconds": 0.64, "reference": "stwo-circuit-chain"}}
# The recursion step: the inner chain length, and caps at twice the reference on the host
# (627 KB, verify 0.31 s).
BOARD[STWO_VERIFY] = {"n": 1024, "floor_bits": 96, "max_proof_bytes": 1_254_000,
                      "max_verify_seconds": 0.62, "reference": "stwo-circuit-recursion"}
# The matrix product: n is k, the matrix size, and caps at twice the reference on the host
# (528 KB, verify 0.37 s).
BOARD[U32_MATMUL] = {"n": 48, "floor_bits": 96, "max_proof_bytes": 1_056_000,
                     "max_verify_seconds": 0.74, "reference": "stwo-circuit-matmul"}


def blake2s_chain(seed: bytes, n: int) -> bytes:
    if len(seed) != 32 or n < 1:
        raise ValueError("a blake2s-chain-v0 seed is 32 bytes and n is at least 1")
    digest = seed
    for _ in range(n):
        digest = hashlib.blake2s(digest).digest()
    return digest


def chain_statement(n: int, seed: bytes | None = None) -> dict:
    seed = secrets.token_bytes(32) if seed is None else seed
    return {"statement": BLAKE2S_CHAIN, "n": n, "seed": seed.hex(),
            "y": blake2s_chain(seed, n).hex()}


def verify_statement(n: int, seed: bytes | None = None) -> dict:
    seed = secrets.token_bytes(32) if seed is None else seed
    inner = subprocess.run([str(CHAIN_BIN), "inner-prove", str(n)], input=seed.hex().encode(),
                           capture_output=True, check=True).stdout
    return {"statement": STWO_VERIFY, "n": n, "y": blake2s_chain(seed, n).hex(),
            "witness_inner_proof": inner.hex()}


def words(data: bytes) -> list[int]:
    return [int.from_bytes(data[i:i + 4], "little") for i in range(0, len(data), 4)]


def matmul_product(k: int, a: bytes, b: bytes) -> bytes:
    a_words, b_words = words(a), words(b)
    out = bytearray()
    for i in range(k):
        row = a_words[i * k:(i + 1) * k]
        for j in range(k):
            total = sum(row[t] * b_words[t * k + j] for t in range(k)) & 0xFFFFFFFF
            out += total.to_bytes(4, "little")
    return bytes(out)


def matmul_statement(k: int, seed: bytes | None = None) -> dict:
    if k < 2 or k > 64 or k % 2:
        raise ValueError("k must be even, from 2 to 64")
    a, b = secrets.token_bytes(4 * k * k), secrets.token_bytes(4 * k * k)
    return {"statement": U32_MATMUL, "k": k, "a": a.hex(), "b": b.hex(),
            "c": matmul_product(k, a, b).hex()}


GENERATORS = {BLAKE2S_CHAIN: chain_statement, STWO_VERIFY: verify_statement,
              U32_MATMUL: matmul_statement}


def public(statement: dict) -> dict:
    """What the verifier sees: every field but the witnesses."""
    return {key: value for key, value in statement.items() if not key.startswith("witness_")}


def check(statement: dict) -> bool | None:
    """Is the statement true? None when the judge cannot tell (a recursion statement without
    its witness: deciding it would mean finding a preimage)."""
    kind = statement.get("statement")
    if kind == BLAKE2S_CHAIN:
        seed, y = bytes.fromhex(statement["seed"]), bytes.fromhex(statement["y"])
        return blake2s_chain(seed, statement["n"]) == y
    if kind == STWO_VERIFY:
        if "witness_inner_proof" not in statement:
            return None
        return inner_verifies(statement)
    if kind == U32_MATMUL:
        a, b = bytes.fromhex(statement["a"]), bytes.fromhex(statement["b"])
        return matmul_product(statement["k"], a, b).hex() == statement["c"]
    raise ValueError(f"unknown statement {kind!r}")


def inner_verifies(statement: dict) -> bool:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path, proof = Path(tmp) / "s.json", Path(tmp) / "inner.bin"
        path.write_text(json.dumps(public(statement)))
        proof.write_bytes(bytes.fromhex(statement["witness_inner_proof"]))
        return subprocess.run([str(CHAIN_BIN), "inner-verify", str(path), str(proof)],
                              capture_output=True).returncode == 0


def false_variants(statement: dict) -> dict[str, dict]:
    """False statements derived from a true one, as the verifier sees them: it must reject each
    of them with the true statement's proof."""
    flip = lambda data, i: (data[:i] + bytes([data[i] ^ 1]) + data[i + 1:]).hex()
    if statement["statement"] == U32_MATMUL:
        a, c = bytes.fromhex(statement["a"]), bytes.fromhex(statement["c"])
        return {"wrong-c-first-bit": {**statement, "c": flip(c, 0)},
                "wrong-c-last-byte": {**statement, "c": flip(c, len(c) - 1)},
                "wrong-a": {**statement, "a": flip(a, 0)},
                "a-and-b-swapped": {**statement, "a": statement["b"], "b": statement["a"]}}
    y = bytes.fromhex(statement["y"])
    if statement["statement"] == STWO_VERIFY:
        view = public(statement)
        return {"wrong-y-first-bit": {**view, "y": flip(y, 0)},
                "wrong-y-last-byte": {**view, "y": flip(y, 31)}}
    seed = bytes.fromhex(statement["seed"])
    return {
        "wrong-y-first-bit": {**statement, "y": flip(y, 0)},
        "wrong-y-last-byte": {**statement, "y": flip(y, 31)},
        "wrong-seed": {**statement, "seed": flip(seed, 0)},
        "seed-and-y-swapped": {**statement, "seed": statement["y"], "y": statement["seed"]},
        "y-of-n-minus-1": {**statement, "y": blake2s_chain(seed, statement["n"] - 1).hex()}
        if statement["n"] > 1 else {**statement, "y": seed.hex()},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("statement", choices=[BLAKE2S_CHAIN])
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--seed", help="32-byte seed in hex (default: fresh random)")
    parser.add_argument("--wrong-y", action="store_true", help="emit a false statement (y flipped)")
    args = parser.parse_args(argv)
    statement = chain_statement(args.n, bytes.fromhex(args.seed) if args.seed else None)
    if args.wrong_y:
        statement = false_variants(statement)["wrong-y-first-bit"]
    json.dump(statement, sys.stdout)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
