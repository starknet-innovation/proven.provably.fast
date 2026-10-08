"""The mathematics track's records: validation, target statuses, and the issue-form draft."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from proven import mathematics as m

ROOT = Path(__file__).resolve().parents[1]


def row(rid, kind="idea", target="T1", status="posted", who="alice", reviews=(), **extra):
    return {"id": rid, "target": target, "kind": kind, "title": f"{kind} {rid}", "status": status,
            "who": [{"name": who}], "builds_on": [], "reviews": list(reviews), "date": "2026-10-08", **extra}


class ShippedData(unittest.TestCase):
    def test_targets_and_records_validate(self):
        m.validate(m.load_targets(), m.load_records())

    def test_lean_declarations_exist_in_the_pinned_file(self):
        targets = m.load_targets()
        lean = (ROOT / targets["lean"]["file"]).read_text()
        for target in targets["targets"]:
            for name in target["lean"] + target.get("milestones", []):
                short = name.split(".", 1)[1]
                self.assertRegex(lean, rf"(?m)^def {re.escape(short)}\b", msg=name)

    def test_lean_commit_matches_the_lakefile(self):
        targets = m.load_targets()
        lakefile = (ROOT / "lean" / "lakefile.toml").read_text()
        self.assertIn(f'rev = "{targets["lean"]["commit"]}"', lakefile)

    def test_summary_lists_every_target_open_with_no_records(self):
        summary = m.summary(m.load_targets(), [], now="2026-10-08T00:00:00+00:00")
        self.assertEqual([t["id"] for t in summary["targets"]], ["T1", "T2", "T3"])
        self.assertTrue(all(t["status"] == "open" for t in summary["targets"]))


class Statuses(unittest.TestCase):
    def setUp(self):
        self.targets = m.load_targets()
        self.t1 = self.targets["targets"][0]

    def test_a_posted_proof_that_settles_is_a_claim(self):
        status = m.target_status(self.t1, [row("M-0001", "proof", settles=True)])
        self.assertEqual((status["status"], status["by"]), ("claimed", "M-0001"))
        self.assertEqual(m.target_status(self.t1, [row("M-0001", "proof")])["status"], "open")

    def test_an_accepted_proof_needs_a_holding_review_by_someone_else(self):
        self_reviewed = row("M-0001", "proof", status="accepted", reviews=[{"by": "alice", "verdict": "holds"}])
        with self.assertRaises(m.RecordError):
            m.validate(self.targets, [self_reviewed])
        reviewed = row("M-0001", "proof", status="accepted", settles=True, reviews=[{"by": "bob", "verdict": "holds"}])
        m.validate(self.targets, [reviewed])
        self.assertEqual(m.target_status(self.t1, [reviewed])["status"], "solved")

    def test_an_accepted_partial_result_leaves_the_target_open(self):
        partial = row("M-0001", "proof", status="accepted", reviews=[{"by": "bob", "verdict": "holds"}])
        m.validate(self.targets, [partial])
        self.assertEqual(m.target_status(self.t1, [partial])["status"], "open")
        with self.assertRaises(m.RecordError):
            m.validate(self.targets, [row("M-0002", "idea", settles=True)])

    def test_an_accepted_counterexample_refutes(self):
        counter = row("M-0001", "counterexample", status="accepted", settles=True,
                      reviews=[{"by": "bob", "verdict": "holds"}])
        self.assertEqual(m.target_status(self.t1, [counter])["status"], "refuted")

    def test_lean_checked_needs_a_solve_and_the_pinned_declaration(self):
        proof = row("M-0001", "proof", status="accepted", settles=True, reviews=[{"by": "bob", "verdict": "holds"}])
        lean = row("M-0002", "formalization", status="accepted", who="carol", lean="MCAChallenge.T1",
                   reviews=[{"by": "bob", "verdict": "holds"}])
        milestone = row("M-0003", "formalization", status="accepted", who="carol", lean="MCAChallenge.T1Uniform",
                        reviews=[{"by": "bob", "verdict": "holds"}])
        m.validate(self.targets, [proof, lean, milestone])
        self.assertTrue(m.target_status(self.t1, [proof, lean])["lean_checked"])
        self.assertFalse(m.target_status(self.t1, [proof, milestone])["lean_checked"])
        self.assertFalse(m.target_status(self.t1, [lean])["lean_checked"])
        with self.assertRaises(m.RecordError):
            m.validate(self.targets, [row("M-0003", "formalization", lean="MCAChallenge.Nope")])

    def test_withdrawn_rows_do_not_count(self):
        status = m.target_status(self.t1, [row("M-0001", "proof", status="withdrawn")])
        self.assertEqual(status["status"], "open")


class Validation(unittest.TestCase):
    def setUp(self):
        self.targets = m.load_targets()

    def test_builds_on_must_resolve(self):
        m.validate(self.targets, [row("M-0001", builds_on=["DKT26", "#7"]), row("M-0002", builds_on=["M-0001"])])
        with self.assertRaises(m.RecordError):
            m.validate(self.targets, [row("M-0001", builds_on=["M-0002"])])
        with self.assertRaises(m.RecordError):
            m.validate(self.targets, [row("M-0001", builds_on=["Nobody99"])])

    def test_agents_say_who_runs_them(self):
        agent = row("M-0001")
        agent["who"] = [{"name": "some-agent", "agent": True}]
        with self.assertRaises(m.RecordError):
            m.validate(self.targets, [agent])
        agent["who"][0]["runs"] = "alice"
        m.validate(self.targets, [agent])

    def test_ids_and_kinds(self):
        with self.assertRaises(m.RecordError):
            m.validate(self.targets, [row("M-1")])
        with self.assertRaises(m.RecordError):
            m.validate(self.targets, [row("M-0001", kind="vibe")])
        with self.assertRaises(m.RecordError):
            m.validate(self.targets, [row("M-0001"), row("M-0001")])
        self.assertEqual(m.next_id([row("M-0001"), row("M-0007")]), "M-0008")


class IssueDraft(unittest.TestCase):
    BODY = """### Target

T1 (linear count in the first-order regime)

### Kind

Lemma

### Claim

The solution families of the first-order explainer have degree O(1/eta) in z.

### The work

https://example.org/sketch.pdf

### What was checked, and how

By hand; the degree count is unverified for p < 5.

### Builds on

DKT26 Section 5.4, #3 and #5

### Credits

alice
"""

    def test_a_form_becomes_a_posted_row(self):
        issue = {"number": 9, "title": "T1 lemma: degree of solution families",
                 "body": self.BODY, "url": "https://github.com/x/y/issues/9", "author": {"login": "alice"}}
        draft = m.draft_from_issue(issue, [row("M-0001")], "2026-10-08")
        self.assertEqual((draft["id"], draft["target"], draft["kind"], draft["status"]), ("M-0002", "T1", "lemma", "posted"))
        self.assertEqual(draft["builds_on"], ["#3", "#5"])
        self.assertEqual(draft["title"], "T1 lemma: degree of solution families")
        m.validate(m.load_targets(), [row("M-0001"), draft])

    def test_an_issue_without_the_form_is_refused(self):
        with self.assertRaises(m.RecordError):
            m.draft_from_issue({"title": "a question", "body": "### Something else\n\nhello\n"}, [], "2026-10-08")


if __name__ == "__main__":
    unittest.main()
