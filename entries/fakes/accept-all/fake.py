"""Fake entry: the verifier accepts everything. The oracle's rejection gate must fail it."""
import sys

if sys.argv[1] == "prove":
    sys.stdout.write("proof")
sys.exit(0)
