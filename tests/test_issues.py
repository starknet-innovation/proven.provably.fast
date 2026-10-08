from __future__ import annotations

import unittest

from proven import issues

FORM = """### Task

u32-matmul-v0

### Repository

https://github.com/someone/fast-matmul

### Full commit

ABCDEF0123456789abcdef0123456789abcdef01

### Entry directory

entries/matmul

### What changed

A smaller trace.

### Credits

someone (implementer)

### Before sending

- [X] The judge passes on my machine
"""


class IssueIntakeTests(unittest.TestCase):
    def test_the_form_becomes_a_runner_request(self) -> None:
        form = issues.parse_form(FORM)
        self.assertEqual(issues.problems(form), [])
        self.assertEqual(issues.request(form), {
            "url": "https://github.com/someone/fast-matmul",
            "commit": "abcdef0123456789abcdef0123456789abcdef01", "entry": "entries/matmul"})
        self.assertTrue(issues.TITLE.match("proven contribution: u32-matmul-v0"))

    def test_an_empty_entry_directory_means_the_repository_root(self) -> None:
        form = issues.parse_form(FORM.replace("entries/matmul", "_No response_"))
        self.assertNotIn("entry", issues.request(form))

    def test_a_form_that_could_reach_a_root_shell_or_leave_the_repository_is_refused(self) -> None:
        for old, new in (("https://github.com/someone/fast-matmul", "https://x/$(id)"),
                         ("https://github.com/someone/fast-matmul", "git@github.com:a/b"),
                         ("ABCDEF0123456789abcdef0123456789abcdef01", "abcdef01"),
                         ("entries/matmul", "../../etc"),
                         ("entries/matmul", "/etc"),
                         ("u32-matmul-v0", "sorting-v0")):
            self.assertTrue(issues.problems(issues.parse_form(FORM.replace(old, new))), new)

    def test_the_verdict_names_the_gates_and_what_happens_next(self) -> None:
        wanted = issues.request(issues.parse_form(FORM))
        rows = [{"source": {"repository": wanted["url"], "commit": "0" * 40, "entry": "entries/matmul"},
                 "verdict": "PASS"},
                {"source": {"repository": wanted["url"], "commit": wanted["commit"], "entry": "entries/matmul"},
                 "verdict": "FAIL", "gates": {"completeness": True, "rejection": False},
                 "error": "a forged proof was accepted",
                 "build_log_tail": "token pfast1_secret.value here"}]
        row = issues.result_for(rows, wanted)
        self.assertEqual(row["verdict"], "FAIL")
        text = issues.verdict(row)
        self.assertIn("**Verdict: FAIL**", text)
        self.assertIn("rejection failed", text)
        self.assertIn("edit this issue to the new commit", text)
        self.assertNotIn("pfast1_secret", text)
        passing = issues.verdict({"verdict": "PASS", "prove_seconds": [3.1, 2.9, 3.0],
                                  "peak_bytes_max": 3.5e9, "proof_bytes_max": 530000,
                                  "verify_seconds_median": 0.37, "claimed_bits": 96.45})
        self.assertIn("Prove 3.00 s, peak memory 3.50 GB, proof 530 KB", passing)
        self.assertIn("reads the entry's verifier", passing)


if __name__ == "__main__":
    unittest.main()
