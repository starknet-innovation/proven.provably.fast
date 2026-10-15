"""The Harbor environments: generated tasks, the count grader against the kit, and the templates."""
from __future__ import annotations

import importlib.util
import json
import random
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARBOR = ROOT / "harbor"
COUNT = HARBOR / "templates" / "count"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


kit = load("kit_certify", ROOT / "kit" / "certify.py")
baseline = load("count_baseline", COUNT / "environment" / "baseline.py")
HAVE_NUMPY = importlib.util.find_spec("numpy") is not None
grade = load("count_grade", COUNT / "tests" / "grade.py") if HAVE_NUMPY else None


def task_for(inst: dict) -> dict:
    n = len(inst["domain"])
    return {"p": inst["p"], "n": n, "k": inst["k"], "A": inst["A"], "floor": 9 * n // 4,
            "goal_per_n": 16, "max_listed": 24 * n}


class Generated(unittest.TestCase):
    def test_tasks_are_up_to_date(self):
        res = subprocess.run([sys.executable, str(HARBOR / "build.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_registry_lists_every_task_directory(self):
        registry = json.loads((HARBOR / "registry.json").read_text())[0]
        listed = sorted(t["name"] for t in registry["tasks"])
        self.assertEqual(listed, sorted(p.name for p in (HARBOR / "tasks").iterdir()))
        for t in registry["tasks"]:
            for name in ("instruction.md", "task.toml", "environment/Dockerfile", "solution/solve.sh", "tests/test.sh"):
                self.assertTrue((HARBOR / t["path"] / name).is_file(), f"{t['name']}: {name}")

    def test_lean_tasks_pin_the_challenge_templates(self):
        index = json.loads((ROOT / "lean" / "challenges" / "index.json").read_text())
        pinned = (ROOT / "lean" / "MCAChallenge.lean").read_text()
        for target, spec in index["targets"].items():
            template = (ROOT / "lean" / "challenges" / spec["template"]).read_text()
            self.assertRegex(pinned, rf"(?m)^def {re.escape(target)}\b")
            self.assertIn(f"MCAChallenge.{target}.{{u}}", template)
            self.assertRegex(template, r"(?m)^theorem solution\.\{u\}")
            for hole in spec["holes"]:
                self.assertRegex(template, rf"(?m)^(?:noncomputable )?def {re.escape(hole)} : .* := sorry$")
            task = next(p for p in (HARBOR / "tasks").iterdir() if p.name.startswith("lean-")
                        and json.loads((p / "tests" / "task.json").read_text())["challenge"] == target)
            self.assertEqual((task / "tests" / "Challenge.lean").read_text(), template)
            self.assertEqual(json.loads((task / "tests" / "task.json").read_text())["comparator"]["definition_names"], spec["holes"])

    def test_lean_controls_share_the_challenge_statement(self):
        controls = HARBOR / "controls"
        challenge = (controls / "Control.lean").read_text()
        statement = challenge[challenge.index("theorem solution"):challenge.index(":= sorry", challenge.index("theorem solution"))]
        for name in ("ok", "choice"):
            self.assertIn(statement, (controls / "solutions" / f"{name}.lean").read_text(), name)
        self.assertNotIn(statement, (controls / "solutions" / "weak.lean").read_text())
        config = json.loads((controls / "config.json").read_text())
        self.assertEqual((config["theorem_names"], config["definition_names"]), (["solution"], ["C"]))

    def test_only_the_lean_verifier_gets_net_admin(self):
        # grade.py's iptables rule needs NET_ADMIN. Harbor reads tests/docker-compose.yaml for the
        # separate verifier alone; an environment/docker-compose.yaml would also reach the agent,
        # whose root could then lift the no-network policy of the namespace it shares.
        for task in sorted((HARBOR / "tasks").iterdir()):
            self.assertFalse((task / "environment" / "docker-compose.yaml").exists(), task.name)
            compose = task / "tests" / "docker-compose.yaml"
            if not task.name.startswith("lean-"):
                self.assertFalse(compose.exists(), task.name)
                continue
            text = compose.read_text()
            self.assertRegex(text, r"(?m)^    cap_add:\n      - NET_ADMIN$", task.name)
            self.assertRegex(text, r"(?m)^      context: \.\./environment$", task.name)
            self.assertRegex(text, r"(?m)^      - \./:/tests:ro$", task.name)
            self.assertEqual(text.count("cap_add"), 1, task.name)

    def test_public_prose_has_no_em_dash(self):
        for path in [*HARBOR.rglob("*.md"), *HARBOR.rglob("*.toml")]:
            self.assertNotIn("—", path.read_text(), path)


class Floor(unittest.TestCase):
    def test_kit_certifies_four_times_n_minus_A_plus_one(self):
        inst = baseline.build(5)
        bad, failures = kit.check(inst)
        self.assertEqual(failures, [])
        self.assertEqual(len(bad), 4 * (32 - 20 + 1))
        self.assertEqual(len(inst["challenges"]), 52)

    def test_kit_refuses_a_witness_above_k(self):
        inst = baseline.build(5)
        inst["challenges"] = [{"z": 1, "witness": list(range(inst["k"] + 1))}]
        bad, failures = kit.check(inst)
        self.assertEqual(bad, set())
        self.assertEqual(len(failures), 1)


@unittest.skipUnless(HAVE_NUMPY, "numpy is not installed; the grader runs in the task image")
class Grader(unittest.TestCase):
    def certify_both(self, inst):
        task = task_for(inst)
        dom, f, g, chal = grade.validate(inst, task)
        fast = grade.certify(dom, f, g, chal, task["k"], task["A"], task["p"])
        slow = kit.check(inst)
        return fast, slow

    def test_agrees_with_the_kit_on_the_floor(self):
        (bad, failures), (kbad, kfail) = self.certify_both(baseline.build(5))
        self.assertEqual(bad, kbad)
        self.assertEqual(len(bad), 52)
        self.assertEqual(failures, [])

    def test_agrees_with_the_kit_on_random_challenges(self):
        rng = random.Random(7)
        inst = baseline.build(5, seed=3)
        n, k, p = 32, inst["k"], inst["p"]
        chal = []
        for ch in inst["challenges"][:6]:          # true challenges, witness in another order
            chal.append({"z": ch["z"], "witness": rng.sample(ch["witness"], k)})
        for ch in inst["challenges"][:4]:          # a witness touching a point outside S
            chal.append({"z": ch["z"], "witness": rng.sample(range(n), k)})
        for _ in range(12):                        # random challenges
            chal.append({"z": rng.randrange(p), "witness": rng.sample(range(n), k)})
        inst["challenges"] = chal
        (bad, failures), (kbad, kfail) = self.certify_both(inst)
        self.assertEqual(bad, kbad)
        self.assertEqual(sorted(z for z, _ in failures), sorted(z for z, _ in kfail))
        self.assertGreaterEqual(len(bad), 6)

    def test_arithmetic_next_to_the_prime(self):
        # Values at p - 1 everywhere: no product may overflow int64 and the two checkers must agree.
        inst = baseline.build(4, seed=5)
        p, n = inst["p"], 16
        inst["f"] = [p - 1] * n
        inst["g"] = [p - 1 - (i % 3) for i in range(n)]
        inst["challenges"] = [{"z": p - 1, "witness": list(range(inst["k"]))},
                              {"z": p - 2, "witness": list(range(1, inst["k"] + 1))}]
        (bad, failures), (kbad, kfail) = self.certify_both(inst)
        self.assertEqual(bad, kbad)
        self.assertEqual(len(failures), len(kfail))

    def test_rejects_a_tampered_instance(self):
        inst = baseline.build(4)
        task = task_for(inst)
        cases = {
            "p": dict(p=inst["p"] + 2), "k": dict(k=inst["k"] - 1), "A": dict(A=inst["A"] - 1),
            "domain": dict(domain=[3 if x == inst["domain"][1] else x for x in inst["domain"]]),
            "short f": dict(f=inst["f"][:-1]),
            "witness size": dict(challenges=[{"z": 1, "witness": list(range(inst["k"] + 1))}]),
            "witness repeat": dict(challenges=[{"z": 1, "witness": [0] * inst["k"]}]),
            "composite witness entry": dict(challenges=[{"z": 1, "witness": [[0]] + list(range(1, inst["k"]))}]),
            "string z": dict(challenges=[{"z": "1", "witness": list(range(inst["k"]))}]),
            "bool z": dict(challenges=[{"z": True, "witness": list(range(inst["k"]))}]),
            "too many": dict(challenges=[{"z": 1, "witness": list(range(inst["k"]))}] * (24 * 16 + 1)),
        }
        for name, change in cases.items():
            with self.assertRaises(grade.Rejected, msg=name):
                grade.validate({**inst, **change}, task)

    def test_main_writes_the_dense_reward(self):
        inst = baseline.build(5)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "tests").mkdir(); (tmp / "artifacts").mkdir()
            (tmp / "tests" / "task.json").write_text(json.dumps(task_for(inst)))
            (tmp / "artifacts" / "instance.json").write_text(json.dumps(inst))
            grade.TESTS, grade.VERIFIER_DIR, grade.INSTANCE = tmp / "tests", tmp / "verifier", tmp / "artifacts" / "instance.json"
            self.assertEqual(grade.main(), 0)
            reward = json.loads((tmp / "verifier" / "reward.json").read_text())
            self.assertEqual(reward["certified_bad"], 52)
            self.assertEqual((reward["over_floor"], reward["beats_floor"], reward["above_goal"]), (52 - 72, 0, 0))
            self.assertEqual(reward["reward"], round(52 / (16 * 32), 6))
            # a second bad challenge per point would beat the floor
            inst["challenges"] += [{"z": (c["z"] + 1) % inst["p"], "witness": c["witness"]} for c in inst["challenges"]]
            (tmp / "artifacts" / "instance.json").write_text(json.dumps(inst))
            grade.main()
            again = json.loads((tmp / "verifier" / "reward.json").read_text())
            self.assertEqual(again["certified_bad"], 52)
            details = json.loads((tmp / "verifier" / "grading.json").read_text())
            self.assertEqual(details["failed"], 52)
            # tampering with the domain scores 0 with a reason
            inst["domain"][0] = 5
            (tmp / "artifacts" / "instance.json").write_text(json.dumps(inst))
            grade.main()
            self.assertEqual(json.loads((tmp / "verifier" / "reward.json").read_text())["reward"], 0.0)
            self.assertIn("rejected", json.loads((tmp / "verifier" / "grading.json").read_text())["reason"])


if __name__ == "__main__":
    unittest.main()
