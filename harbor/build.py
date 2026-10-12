#!/usr/bin/env python3
"""Generate the Harbor tasks in tasks/ from templates/, the starter kit and the pinned Lean files.

    python3 build.py            # rewrite tasks/, registry.json and manifest.json
    python3 build.py --check    # exit 1 if they are out of date (the test suite runs this)

Every task is generated; none is written by hand. Count tasks (one per domain size) grade a line's
bad challenges from the definition with a dense reward; Lean tasks (one per pinned target) grade a
proof with Comparator. See README.md.
"""
from __future__ import annotations

import filecmp
import json
import math
import re
import shutil
import sys
import tempfile
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent
PROVEN = ROOT.parent
TEMPLATES = ROOT / "templates"
DATASET, VERSION = "proven-mca", "0.1"
BABYBEAR = 2**31 - 2**27 + 1
GOAL_PER_N = 16
# Domain sizes and the verifier's time: certifying grows with n^2 per challenge.
COUNT_TASKS = [dict(m=8, verifier_timeout=1800, kit_minutes="0.5"),
               dict(m=9, verifier_timeout=3600, kit_minutes="2"),
               dict(m=10, verifier_timeout=10800, kit_minutes="8")]


def toml_str(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render(template: Path, out: Path, mapping: dict) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(Template(template.read_text()).substitute(mapping))
    if out.suffix == ".sh":
        out.chmod(0o755)


def copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)
    for path in dst.rglob("*.sh"):
        path.chmod(0o755)


def count_task(cfg: dict, out: Path) -> dict:
    m = cfg["m"]
    n = 1 << m
    k, A = n // 2, 5 * n // 8
    floor = 4 * (n - A + 1)   # four codeword pairs, one bad challenge per point outside each agreement set
    params = dict(m=m, n=n, k=k, A=A, p=BABYBEAR, floor=floor, goal=GOAL_PER_N * n, goal_per_n=GOAL_PER_N,
                  max_listed=24 * n, verifier_timeout=cfg["verifier_timeout"], kit_minutes=cfg["kit_minutes"])
    task = out / f"count-babybear-m{m}"
    src = TEMPLATES / "count"
    render(src / "instruction.md", task / "instruction.md", params)
    render(src / "task.toml", task / "task.toml", params)
    render(src / "solution" / "solve.sh", task / "solution" / "solve.sh", params)
    copy_tree(src / "environment", task / "environment")
    shutil.copy(PROVEN / "kit" / "certify.py", task / "environment" / "certify.py")
    copy_tree(src / "tests", task / "tests")
    (task / "tests" / "task.json").write_text(json.dumps(
        {"p": BABYBEAR, "m": m, "n": n, "k": k, "A": A, "floor": floor, "goal_per_n": GOAL_PER_N,
         "max_listed": 24 * n}, indent=2) + "\n")
    return {"task": task.name, "kind": "count", "target": "T3", "n": n, "k": k, "A": A, "floor": floor,
            "goal_per_n": GOAL_PER_N, "oracle": "four-pair floor construction", "oracle_reward": round(floor / (GOAL_PER_N * n), 4)}


def definition_block(lean: str, name: str) -> str:
    """The docstring and `def` of one pinned declaration, up to the next blank line."""
    m = re.search(rf"(?ms)^(?:/--(?:(?!-/).)*-/\n)?def {re.escape(name)}\b.*?(?=\n\n)", lean)
    if not m:
        raise SystemExit(f"{name} is not defined in MCAChallenge.lean")
    return m.group(0)


def lean_task(name: str, spec: dict, index: dict, out: Path) -> dict:
    lean_dir = PROVEN / "lean"
    pinned = (lean_dir / "MCAChallenge.lean").read_text()
    lakefile = (lean_dir / "lakefile.toml").read_text()
    commit = re.search(r'rev = "([0-9a-f]{40})"', lakefile).group(1)
    toolchain = (lean_dir / "lean-toolchain").read_text().strip()
    template = (lean_dir / "challenges" / spec["template"]).read_text().rstrip()
    holes = spec["holes"]
    slug = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", name).lower()
    params = dict(target=name, slug=slug, level=spec["level"], arklib_commit=commit, arklib_short=commit[:8],
                  toolchain=toolchain.split(":")[-1], definition=definition_block(pinned, name), template=template,
                  holes_toml="[" + ", ".join(toml_str(h) for h in holes) + "]",
                  holes_prose=" and ".join(f"`{h}`" for h in holes))
    task = out / f"lean-{slug}"
    src = TEMPLATES / "lean"
    render(src / "instruction.md", task / "instruction.md", params)
    render(src / "task.toml", task / "task.toml", params)
    render(src / "solution" / "solve.sh", task / "solution" / "solve.sh", params)
    copy_tree(src / "environment", task / "environment")
    for file in ("lakefile.toml", "lake-manifest.json", "lean-toolchain", "MCAChallenge.lean"):
        shutil.copy(lean_dir / file, task / "environment" / file)
    (task / "environment" / "challenges").mkdir(exist_ok=True)
    for path in sorted((lean_dir / "challenges").glob("*.lean")):
        shutil.copy(path, task / "environment" / "challenges" / path.name)
    copy_tree(src / "tests", task / "tests")
    shutil.copy(lean_dir / "challenges" / spec["template"], task / "tests" / "Challenge.lean")
    (task / "tests" / "task.json").write_text(json.dumps(
        {"challenge": name, "comparator": {"theorem_names": [index["theorem"]], "definition_names": holes,
                                            "permitted_axioms": index["permitted_axioms"]},
         "grade_timeout_sec": 6300}, indent=2) + "\n")
    return {"task": task.name, "kind": "lean", "target": name, "level": spec["level"], "holes": holes,
            "arklib_commit": commit, "oracle": "none (negative control, must score 0)"}


def generate(out: Path) -> None:
    index = json.loads((PROVEN / "lean" / "challenges" / "index.json").read_text())
    tasks_dir = out / "tasks"
    tasks_dir.mkdir(parents=True)
    rows = [count_task(cfg, tasks_dir) for cfg in COUNT_TASKS]
    rows += [lean_task(name, spec, index, tasks_dir) for name, spec in index["targets"].items()]
    (out / "registry.json").write_text(json.dumps([{
        "name": DATASET, "version": VERSION,
        "description": "Mathematics tasks of proven.provably.fast: certified counts of bad challenges "
                       "(dense reward) and Lean proofs of the pinned targets (Comparator).",
        "tasks": [{"name": r["task"], "path": f"tasks/{r['task']}"} for r in rows]}], indent=2) + "\n")
    (out / "manifest.json").write_text(json.dumps({"dataset": DATASET, "version": VERSION, "tasks": rows},
                                                  indent=1, ensure_ascii=False) + "\n")


def differs(a: Path, b: Path) -> list[str]:
    cmp = filecmp.dircmp(a, b)
    out = [f"only in {a.name}: {x}" for x in cmp.left_only] + [f"only in {b.name}: {x}" for x in cmp.right_only]
    out += [f"differs: {x}" for x in cmp.diff_files]
    for sub in cmp.common_dirs:
        out += [f"{sub}/{x}" for x in differs(a / sub, b / sub)]
    return out


def main(argv: list[str]) -> int:
    if argv == ["--check"]:
        with tempfile.TemporaryDirectory() as tmp:
            generate(Path(tmp))
            problems = []
            for name in ("tasks", "registry.json", "manifest.json"):
                if not (ROOT / name).exists():
                    problems.append(f"missing {name}")
                elif name == "tasks":
                    problems += differs(Path(tmp) / "tasks", ROOT / "tasks")
                elif (Path(tmp) / name).read_text() != (ROOT / name).read_text():
                    problems.append(f"differs: {name}")
            if problems:
                print("harbor/ is out of date; run python3 harbor/build.py:\n  " + "\n  ".join(problems))
                return 1
            print("harbor/ is up to date")
            return 0
    if argv:
        raise SystemExit(__doc__)
    with tempfile.TemporaryDirectory() as tmp:
        generate(Path(tmp))
        if (ROOT / "tasks").exists():
            shutil.rmtree(ROOT / "tasks")
        shutil.copytree(Path(tmp) / "tasks", ROOT / "tasks")
        for name in ("registry.json", "manifest.json"):
            shutil.copy(Path(tmp) / name, ROOT / name)
    print(f"generated {len(list((ROOT / 'tasks').iterdir()))} tasks")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
