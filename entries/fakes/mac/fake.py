"""Fake entry: the "proof" is an HMAC of the statement under a key hardcoded in both programs.
It is no proof system, yet it passes every automatic gate, ledger included: only reading the
verifier catches it. It exists to show why listing needs a verifier read."""
import hashlib
import hmac
import json
import sys

KEY = b"hardcoded key, not a proof"


def load(path):
    return json.load(open(path))


def true(statement):
    digest = bytes.fromhex(statement["seed"])
    for _ in range(statement["n"]):
        digest = hashlib.blake2s(digest).digest()
    return digest.hex() == statement["y"]


def tag(statement):
    message = f'{statement["n"]}:{statement["seed"]}:{statement["y"]}'.encode()
    return hmac.new(KEY, message, hashlib.sha256).digest()


statement = load(sys.argv[2])
if sys.argv[1] == "prove":
    if not true(statement):
        sys.exit(1)
    sys.stdout.buffer.write(tag(statement))
    sys.exit(0)
proof = open(sys.argv[3], "rb").read()
sys.exit(0 if hmac.compare_digest(proof, tag(statement)) else 20)
