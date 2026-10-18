#!/usr/bin/env bash
# Oracle: the four-pair line, 4 (n - A + 1) = 3 n / 2 + 4 bad challenges (baseline.py). It validates the
# pipeline, not the task: its reward is about 0.095, below the public floor 2992, so beats_floor is 0.
set -euo pipefail
python3 /opt/proven/baseline.py 10 /workspace/instance.json
echo "placed the floor construction for m = 10"
