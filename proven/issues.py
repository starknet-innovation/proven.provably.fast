"""Contribution issues on the public repository, judged with no maintainer in the loop.

The frontier autopilot (research/discovery/scripts/frontier_autopilot.py) runs this on the
evaluator host every 20 minutes, so nobody logs in to queue an entry (a login stops the running
Stwo job):

1. an open issue titled "proven contribution: ..." whose form names a task, an https repository, a
   full commit and optionally an entry directory is queued for the proven runner, once per commit,
   and the issue says so; a form that does not parse gets a comment saying what is wrong;
2. once the runner has judged it (it runs while the Stwo lane is idle), the issue gets the verdict,
   the gates and the measurements, and the official row is published: the autopilot adds it to
   results/oracle.jsonl, regenerates the board and re-exports the public repository;
3. a passing entry is "claimed" on the board; it can set a frontier only after someone reads its
   verifier (results/reads.jsonl), which the issue says.

Editing the issue to a new commit queues that commit.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

TITLE = re.compile(r"^proven contribution\b", re.IGNORECASE)
TASKS = ("blake2s-chain-v0", "u32-matmul-v0", "stwo-verify-v0")
# The request reaches the root-run runner: plain URLs and paths only, as host/judge-contribution.sh.
REPOSITORY = re.compile(r"^https://[A-Za-z0-9._/-]+$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
ENTRY = re.compile(r"^[A-Za-z0-9._/-]*$")
FIELDS = {"Task": "task", "Repository": "repository", "Full commit": "commit",
          "Entry directory": "entry"}
NO_RESPONSE = "_No response_"


def parse_form(body: str) -> dict[str, str]:
    """The issue form's answers, keyed task / repository / commit / entry."""
    form: dict[str, str] = {}
    for section in re.split(r"^### ", body or "", flags=re.MULTILINE)[1:]:
        label, _, value = section.partition("\n")
        key = FIELDS.get(label.strip())
        value = value.strip()
        if key and value and value != NO_RESPONSE:
            form[key] = value.splitlines()[0].strip()
    return form


def problems(form: dict[str, str]) -> list[str]:
    found = []
    if form.get("task") not in TASKS:
        found.append(f"the task must be one of {', '.join(TASKS)}")
    if not REPOSITORY.fullmatch(form.get("repository", "")):
        found.append("the repository must be a plain https URL")
    if not COMMIT.fullmatch(form.get("commit", "").lower()):
        found.append("the commit must be the full 40-character hash")
    entry = form.get("entry", "")
    if not ENTRY.fullmatch(entry) or ".." in entry.split("/") or entry.startswith("/"):
        found.append("the entry directory must be a plain relative path inside the repository")
    return found


def request(form: dict[str, str]) -> dict[str, str]:
    """The runner's queue request for a checked form."""
    wanted = {"url": form["repository"], "commit": form["commit"].lower()}
    if form.get("entry"):
        wanted["entry"] = form["entry"]
    return wanted


def result_for(rows: list[dict], wanted: dict[str, str]) -> dict | None:
    """The runner's latest official row for this repository, commit and entry."""
    for row in reversed(rows):
        source = row.get("source") or {}
        if (source.get("repository") == wanted["url"] and source.get("commit") == wanted["commit"]
                and (source.get("entry") or None) == (wanted.get("entry") or None)):
            return row
    return None


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def _seconds(value) -> str:
    if isinstance(value, list) and value:
        value = sorted(value)[len(value) // 2]
    return "n/a" if value is None else f"{value:.2f} s"


def verdict(row: dict) -> str:
    """The issue comment for a judged row."""
    lines = [f"**Verdict: {row.get('verdict', 'FAIL')}** (evaluator host, official)."]
    gates = row.get("gates")
    if isinstance(gates, dict):
        lines.append("Gates: " + ", ".join(f"{name} {'passed' if ok else 'failed'}"
                                         for name, ok in gates.items()) + ".")
    if row.get("prove_seconds") is not None:
        lines.append(
            f"Prove {_seconds(row.get('prove_seconds'))}, peak memory "
            f"{(row.get('peak_bytes_max') or 0) / 1e9:.2f} GB, proof "
            f"{round((row.get('proof_bytes_max') or 0) / 1e3)} KB, verify "
            f"{_seconds(row.get('verify_seconds_median'))}, claimed bits {row.get('claimed_bits')}.")
    if row.get("error"):
        lines.append(f"Error: `{str(row['error'])[:600]}`")
    if row.get("build_log_tail"):
        tail = re.sub(r"(pfast1_|github_pat_|gh[pousr]_)[A-Za-z0-9._~-]+", "REDACTED",
                      str(row["build_log_tail"]))[-1500:]
        lines.append(f"Build log tail:\n```\n{tail}\n```")
    if row.get("verdict") == "PASS":
        lines.append("The row is on the board as claimed. It can set the frontier once someone reads "
                     "the entry's verifier (results/reads.jsonl); the maintainers are notified.")
    else:
        lines.append("Fix it and edit this issue to the new commit; it is queued again.")
    return "\n\n".join(lines)
