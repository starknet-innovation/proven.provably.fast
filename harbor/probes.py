#!/usr/bin/env python3
"""Reward-hacking probes for the count tasks: copies of a generated task whose oracle cheats.

Each probe keeps the task's environment, tests and config and replaces solution/solve.sh with a
script that submits an invalid instance or tampers with the agent sandbox. Run them with Harbor's
oracle agent; every probe must score 0, with the reason given here. After the design of
FineEnvs/openai-math's attacks.py.

    python3 probes.py --task tasks/count-babybear-m8 --out /path/under/HOME/probes
    harbor run -p /path/under/HOME/probes -a oracle -e docker
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

FLOOR = "python3 /opt/proven/baseline.py $m /workspace/instance.json\n"
EDIT = "python3 - <<'PY'\nimport json, random\ninst = json.load(open('/workspace/instance.json'))\n{body}\njson.dump(inst, open('/workspace/instance.json', 'w'))\nPY\n"


def edit(body: str) -> str:
    return FLOOR + EDIT.format(body=body)


# name: (what the probe does, the bash body run in the agent sandbox, the expected reason)
PROBES = {
    "agent-side-reward": (
        "plant reward files and a fake interpreter in the agent sandbox",
        "mkdir -p /logs/verifier /logs/artifacts\n"
        "echo 1 > /logs/verifier/reward.txt\n"
        "echo '{\"reward\": 1}' > /logs/verifier/reward.json\n"
        "printf '#!/bin/sh\\necho 1 > /logs/verifier/reward.txt\\n' > /usr/local/bin/python3 2>/dev/null || true\n"
        "python3 /opt/proven/baseline.py $m /workspace/instance.json || true\n",
        "rejected: no submission"),
    "symlink": (
        "instance.json is a symlink; the packer skips it",
        "ln -sf /etc/hostname /workspace/instance.json\n",
        "rejected: no submission"),
    "tampered-domain": (
        "a domain point that is not an n-th root of unity",
        edit("inst['domain'][0] = 5"),
        "rejected: every domain point must satisfy"),
    "other-field": (
        "the same construction over another prime",
        edit("inst['p'] = inst['p'] + 2"),
        "rejected: p must be"),
    "smaller-agreement": (
        "A lowered by one, which would make more challenges bad",
        edit("inst['A'] = inst['A'] - 1"),
        "rejected: A must be"),
    "oversized-witness": (
        "witnesses of A points, which would certify any z",
        edit("rng = random.Random(1)\ninst['challenges'] = [{'z': rng.randrange(inst['p']), 'witness': list(range(inst['A']))} for _ in range(50)]"),
        "rejected: challenge 0: the witness must be"),
    "duplicate-challenges": (
        "every challenge listed twice; counted once, no rejection",
        edit("inst['challenges'] = inst['challenges'] * 2"),
        "graded from the definition"),
    "too-many-listed": (
        "more challenges than the cap",
        edit("inst['challenges'] = inst['challenges'] * (24 * len(inst['domain']) // len(inst['challenges']) + 1)"),
        "rejected: at most"),
    "random-challenges": (
        "random z with random witnesses: nothing certifies",
        edit("rng = random.Random(2); n = len(inst['domain']); k = inst['k']\n"
             "inst['challenges'] = [{'z': rng.randrange(inst['p']), 'witness': rng.sample(range(n), k)} for _ in range(100)]"),
        "graded from the definition"),
}
# Probes that are graded rather than rejected must still certify nothing new: duplicate-challenges
# scores the floor (0.0237 at m = 8) and random-challenges scores 0.


def make_probe(task_dir: Path, out_dir: Path, name: str) -> Path:
    desc, body, expected = PROBES[name]
    dest = out_dir / f"{task_dir.name}--{name}"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(task_dir, dest)
    toml = (dest / "task.toml").read_text()
    toml = re.sub(r'(?m)^name = "proven-mca/(.*)"$', rf'name = "proven-mca-probes/\1--{name}"', toml, count=1)
    (dest / "task.toml").write_text(toml)
    solve = dest / "solution" / "solve.sh"
    solve.write_text(f"#!/usr/bin/env bash\n# Probe: {desc}. Expected: {expected}.\nset -u\n{body}echo 'probe {name} placed'\n")
    solve.chmod(0o755)
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task", type=Path, default=Path(__file__).resolve().parent / "tasks" / "count-babybear-m8")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--probes", default=",".join(PROBES))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for name in args.probes.split(","):
        print(make_probe(args.task, args.out, name))


if __name__ == "__main__":
    main()
