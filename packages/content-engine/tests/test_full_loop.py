# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
"""
A script-level run of the whole loop, offline: canned Hacker News and Reddit
replies go through scanner_core into signal-bank rows; a theme doc built from
those rows, approved, goes through write_reference.py (--dry-run, then
--response-file) into a draft file; report.py counts the bank and the theme.

What this does not cover: turning candidates into bank rows, grouping rows
into themes and grading them are steps the agent performs from the command
file, not code. This test does them with a fixed mapping and a hand-built
theme doc. A `/content-engine --dry-run` (see docs/demo-transcript.md) shows the agent's
part.

Run: python3 -m unittest discover -s tests
"""

import _guard  # noqa: F401  (first: isolates HOME, keys and network)
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(PKG, "..", "scanner-core"))
import scanner_core as sc

WRITER = os.path.join(PKG, "write_reference.py")
REPORT = os.path.join(PKG, "report.py")


def _atom(*entries):
    body = "".join(
        "<entry><id>%s</id><title>%s</title><updated>%s</updated>"
        "<content>%s</content><link href='https://www.reddit.com/r/devops/%s'/></entry>"
        % (eid, title, updated, text, eid)
        for eid, title, updated, text in entries
    )
    return ('<feed xmlns="http://www.w3.org/2005/Atom">%s</feed>' % body).encode()


def to_bank_row(candidate):
    """The bank row the command's Phase 1 asks the agent to write for a
    candidate, in the shape of the bundled example bank."""
    return {
        "id": candidate["id"],
        "source": candidate["platform"],
        "native_id": candidate["id"],
        "url": candidate["url"],
        "title": candidate["title"],
        "excerpt": candidate.get("text_excerpt") or "",
        "raw_metric": {"points": candidate["points"]} if "points" in candidate else {},
        "published_at": candidate.get("created_at"),
        "fetched_at": "2026-10-06",
        "keywords_matched": candidate["matched_keywords"],
        "theme_id": None,
    }


class TestFullLoop(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.addCleanup(setattr, sc, "http_json", sc.http_json)
        self.addCleanup(setattr, sc.time, "sleep", time.sleep)
        sc.time.sleep = lambda s: None

    def scan(self):
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        sc.http_json = lambda url, **k: {
            "hits": [
                {
                    "objectID": "4242",
                    "title": "Show HN: a quarantine for flaky tests",
                    "points": 51,
                    "created_at": recent,
                    "_tags": ["story", "show_hn"],
                }
            ],
            "nbHits": 1,
        }
        feed = _atom(("t3_loop", "Flaky tests block our deploys", recent, "Every day."))
        cfg = {
            "hn": {"tags": ["story"], "min_points": 5},
            "keywords": {"precise": ["flaky tests"]},
            "subreddits": [{"name": "devops"}],
            "reddit_min_gap_seconds": 0,
        }
        since = int((now - timedelta(hours=48)).timestamp())
        failures: list = []
        with (
            mock.patch.object(sc, "_fetch_rss_raw", lambda sub, kind, sleep=None: feed),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            candidates = sc.scan_hn(cfg, since, failures) + sc.scan_reddit(cfg, since, failures)
        self.assertEqual(failures, [])
        return candidates

    def test_scan_to_bank_to_draft_to_report(self):
        rows = [to_bank_row(c) for c in self.scan()]
        self.assertEqual([r["id"] for r in rows], ["hn:4242", "reddit:t3_loop"])
        themes = os.path.join(self.dir, "themes")
        os.makedirs(themes)
        theme_id = "theme-2026-10-06-flaky-quarantine"
        for row in rows:
            row["theme_id"] = theme_id  # what the brief step does when it spends them
        bank = os.path.join(self.dir, "bank.jsonl")
        with open(bank, "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(r) + "\n" for r in rows))
        signals = "".join(
            "| %s | %s | %s | %s | — |\n" % (r["source"], r["title"], r["url"], r["published_at"])
            for r in rows
        )
        doc = os.path.join(themes, theme_id + ".md")
        with open(doc, "w", encoding="utf-8") as f:
            f.write(
                "# Theme: Flaky-test quarantine\n\n**Status:** approved\n**Coverage tier:** THIN\n"
                "**Formats suggested:** [blog]\n**Formats approved:** [blog]\n\n"
                "## Signals\n| Source | Title | URL | Published | Metric |\n|---|---|---|---|---|\n"
                + signals
                + "\n## Do not say\n- Do not claim quarantine fixes the tests.\n"
            )
        dry = subprocess.run(
            [sys.executable, WRITER, "--theme-doc", doc, "--format", "blog", "--dry-run"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn("https://news.ycombinator.com/item?id=4242", dry.stdout)
        answer = os.path.join(self.dir, "answer.md")
        with open(answer, "w") as f:
            f.write("An early signal: one Show HN post describes a flaky-test quarantine.\n")
        draft = os.path.join(themes, "drafts", theme_id + "-blog.md")
        out = subprocess.run(
            [sys.executable, WRITER, "--theme-doc", doc, "--format", "blog"]
            + ["--response-file", answer, "--out", draft],
            capture_output=True,
            text=True,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        with open(draft, encoding="utf-8") as f:
            text = f.read()
        self.assertIn('drafted_by: "agent-session"', text)
        self.assertIn("An early signal", text)
        report = subprocess.run(
            [sys.executable, REPORT, "--bank", bank, "--themes-dir", themes],
            capture_output=True,
            text=True,
        )
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertIn("Total rows: 2 (0 un-spent, 2 spent)", report.stdout)
        self.assertIn("approved     1", report.stdout)
        self.assertIn("THIN         1", report.stdout)


if __name__ == "__main__":
    unittest.main()
