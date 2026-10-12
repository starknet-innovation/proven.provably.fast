#!/usr/bin/env bash
# Oracle: the known floor, 3 n / 8 + 1 bad challenges (baseline.py). It validates the pipeline,
# not the task: its reward is (3 n / 8 + 1) / (16 n), about 0.023, and beats_floor is 0.
set -euo pipefail
python3 /opt/proven/baseline.py 10 /workspace/instance.json
echo "placed the floor construction for m = 10"
