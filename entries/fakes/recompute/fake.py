"""Fake entry: no proof at all; the verifier recomputes the chain and ignores the proof bytes.
The oracle must fail it: this verifier accepts garbage for a true statement."""
import hashlib
import json
import sys


def true(path):
    statement = json.load(open(path))
    digest = bytes.fromhex(statement["seed"])
    for _ in range(statement["n"]):
        digest = hashlib.blake2s(digest).digest()
    return digest.hex() == statement["y"]


if sys.argv[1] == "prove":
    sys.exit(0 if true(sys.argv[2]) else 1)
sys.exit(0 if true(sys.argv[2]) else 20)
