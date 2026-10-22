# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
import _guard  # noqa: F401
import base64
import contextlib
import io
import json
import os
import sys
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import scanner_core as sc
from test_scan_paths import _atom


class TestRedditBudget(unittest.TestCase):
    def setUp(self):
        self.clock = 0.0
        self.waits = []
        self.cfg = {
            "keywords": {"b": ["ci"]},
            "subreddits": [{"name": str(n)} for n in range(6)],
            "reddit_min_gap_seconds": 0,
            "reddit_budget_seconds": 30,
        }
        self.feed = _atom(("t3_kept", "CI evidence", "2026-10-20T00:00:00Z", "CI"))
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.object(sc.time, "monotonic", lambda: self.clock))
        self.stack.enter_context(mock.patch.object(sc, "_reddit_last_request", None))
        self.stack.enter_context(contextlib.redirect_stderr(io.StringIO()))

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.clock += seconds

    def run_scan(self, fetch, failures):
        real_fetch = sc._fetch_rss_raw
        with (
            mock.patch.object(sc, "_reddit_fetch_once", fetch),
            mock.patch.object(
                sc, "_fetch_rss_raw", lambda sub, kind: real_fetch(sub, kind, sleep=self.sleep)
            ),
        ):
            return sc.scan_reddit(self.cfg, 0, failures)

    def test_rate_limit_keeps_success_and_reports_every_unfinished_feed(self):
        calls = []

        def fetch(url):
            calls.append(url)
            if len(calls) == 1:
                return self.feed, "application/atom+xml"
            raise urllib.error.HTTPError(url, 429, "limited", {"Retry-After": "90"}, None)

        failures = []
        rows = self.run_scan(fetch, failures)
        self.assertEqual([r["id"] for r in rows], ["reddit:t3_kept"])
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(failures), 11)
        self.assertTrue(all("budget" in f["error"].lower() for f in failures))
        self.assertEqual(self.waits, [])

    def test_affordable_retry_runs_and_does_not_abort_later_feeds(self):
        calls = []

        def fetch(url):
            calls.append(url)
            if len(calls) == 1:
                raise urllib.error.HTTPError(url, 429, "limited", {"Retry-After": "10"}, None)
            return self.feed, "application/atom+xml"

        failures = []
        self.assertEqual(len(self.run_scan(fetch, failures)), 1)
        self.assertEqual(failures, [])
        self.assertEqual(len(calls), 13)
        self.assertEqual(self.waits, [11.0])

    def test_worker_timeout_retains_completed_feeds_and_stops_later_requests(self):
        calls = []

        def run(args, **kwargs):
            calls.append(kwargs)
            if len(calls) == 2:
                raise sc.subprocess.TimeoutExpired(args, kwargs["timeout"])
            return sc.subprocess.CompletedProcess(
                args,
                0,
                json.dumps(
                    {
                        "body": base64.b64encode(self.feed).decode(),
                        "content_type": "application/atom+xml",
                    }
                ),
            )

        failures = []
        with mock.patch.object(sc.subprocess, "run", run):
            rows = sc.scan_reddit(self.cfg, 0, failures)
        self.assertEqual([r["id"] for r in rows], ["reddit:t3_kept"])
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(failures), 11)
        self.assertEqual(calls[-1]["timeout"], 30)

    def test_completed_worker_after_deadline_is_not_accepted(self):
        self.cfg["reddit_budget_seconds"] = 5

        def run(args, **kwargs):
            self.clock += 6
            return sc.subprocess.CompletedProcess(args, 0, "{}")

        failures = []
        with mock.patch.object(sc.subprocess, "run", run):
            self.assertEqual(sc.scan_reddit(self.cfg, 0, failures), [])
        self.assertEqual(len(failures), 12)

    def test_pacing_cannot_sleep_past_the_budget(self):
        self.cfg["reddit_min_gap_seconds"] = 40
        fetch = mock.Mock(return_value=(self.feed, "application/atom+xml"))
        self.assertEqual(len(self.run_scan(fetch, [])), 1)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(self.waits, [])

    def test_invalid_budgets_fail_before_network(self):
        for value in (0, -1, 481, float("nan"), float("inf"), True, "30"):
            with self.subTest(value=value), mock.patch.object(sc.subprocess, "run") as run:
                self.cfg["reddit_budget_seconds"] = value
                with self.assertRaisesRegex(SystemExit, "reddit_budget_seconds"):
                    sc.scan_reddit(self.cfg, 0, [])
                run.assert_not_called()

    def test_a_second_scan_gets_a_fresh_budget(self):
        with mock.patch.object(
            sc, "_reddit_fetch_once", return_value=(self.feed, "application/atom+xml")
        ):
            self.assertEqual(len(sc.scan_reddit(self.cfg, 0, [])), 1)
            self.clock += 100
            self.assertEqual(len(sc.scan_reddit(self.cfg, 0, [])), 1)

    def test_test_guard_blocks_a_forgotten_real_worker(self):
        token = sc._reddit_deadline.set(30)
        try:
            with self.assertRaisesRegex(RuntimeError, "network access is blocked in tests"):
                sc._reddit_fetch_once("https://example.invalid/")
        finally:
            sc._reddit_deadline.reset(token)


class TestRedditWorkerProtocol(unittest.TestCase):
    def invoke(self, opener):
        output = io.StringIO()
        with (
            mock.patch.object(sc.urllib.request, "urlopen", opener),
            mock.patch.object(
                sys,
                "stdin",
                io.StringIO(json.dumps({"url": "https://example.invalid/", "timeout": 1})),
            ),
            contextlib.redirect_stdout(output),
        ):
            sc._reddit_fetch_worker()
        return json.loads(output.getvalue())

    def test_rate_limit_metadata_keeps_only_retry_headers(self):
        error = urllib.error.HTTPError(
            "u",
            429,
            "limited",
            {"Retry-After": "20", "x-ratelimit-reset": "19", "Authorization": "fixture-private"},
            None,
        )
        result = self.invoke(mock.Mock(side_effect=error))
        self.assertEqual(
            result, {"status": 429, "headers": {"Retry-After": "20", "x-ratelimit-reset": "19"}}
        )

    def test_oversized_response_is_closed_and_rejected(self):
        response = mock.Mock()
        response.read.return_value = b"too large"
        with mock.patch.object(sc, "REDDIT_MAX_FEED_BYTES", 2):
            result = self.invoke(mock.Mock(return_value=response))
        self.assertIn("response limit", result["error"])
        response.close.assert_called_once()

    def test_network_errors_do_not_echo_credentials_or_private_paths(self):
        result = self.invoke(mock.Mock(side_effect=urllib.error.URLError("fixture-private")))
        self.assertEqual(result, {"error": "URLError"})
