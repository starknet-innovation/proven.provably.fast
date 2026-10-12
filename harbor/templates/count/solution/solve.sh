#!/usr/bin/env bash
# Oracle: the known floor, 4 (n - A + 1) = 3 n / 2 + 4 bad challenges (baseline.py). It validates the
# pipeline, not the task: its reward is (3 n / 2 + 4) / (16 n), about 0.095, and beats_floor is 0.
set -euo pipefail
python3 /opt/proven/baseline.py $m /workspace/instance.json
echo "placed the floor construction for m = $m"
