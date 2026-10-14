#!/usr/bin/env bash
# Oracle: the four-pair line, 4 (n - A + 1) = 3 n / 2 + 4 bad challenges (baseline.py). It validates the
# pipeline, not the task: its reward is about 0.095, below the public floor 9 n / 4, so beats_floor is 0.
set -euo pipefail
python3 /opt/proven/baseline.py $m /workspace/instance.json
echo "placed the floor construction for m = $m"
