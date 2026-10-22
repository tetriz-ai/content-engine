# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
"""
Unit tests for scanner_core.py's helpers, X normalisation and Reddit's
request pacing. Every HTTP call is stubbed; the platform scans themselves
are in test_scan_paths.py. Live calls are checked by hand, so CI never fails
because a website is slow.

Run: python3 -m unittest discover -s tests
"""

import _guard  # noqa: F401  (first: isolates HOME, keys and network)
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import scanner_core as sc


class TestAllKeywords(unittest.TestCase):
    def test_flattens_layers_with_layer_label(self):
        cfg = {"keywords": {"precise": ["a", "b"], "broad": ["c"]}}
        result = sc.all_keywords(cfg)
        self.assertEqual(
            sorted(result),
            sorted([("a", "precise"), ("b", "precise"), ("c", "broad")]),
        )

    def test_empty_keywords(self):
        self.assertEqual(sc.all_keywords({"keywords": {}}), [])


class TestPHHelpers(unittest.TestCase):
    def test_clean_url_strips_query_and_fragment(self):
        self.assertEqual(
            sc._clean_url("https://example.com/post?utm_source=ph&ref=1#comments"),
            "https://example.com/post",
        )

    def test_clean_url_strips_trailing_slash(self):
        self.assertEqual(sc._clean_url("https://example.com/post/"), "https://example.com/post")

    def test_clean_url_none_passthrough(self):
        self.assertIsNone(sc._clean_url(None))

    def test_user_builds_profile_url_from_username_when_no_url(self):
        u = sc._user({"username": "jdoe", "name": "Jane Doe", "url": None})
        self.assertEqual(u["ph_profile"], "https://www.producthunt.com/@jdoe")
        self.assertEqual(u["name"], "Jane Doe")

    def test_user_none_passthrough(self):
        self.assertIsNone(sc._user(None))
        self.assertIsNone(sc._user({}))


class TestLoadEnv(unittest.TestCase):
    def test_parses_simple_env_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# a comment\nFOO=bar\nBAZ=\"quoted\"\n\nQUX='single'\n")
            path = f.name
        try:
            env = sc.load_env(path)
            self.assertEqual(env, {"FOO": "bar", "BAZ": "quoted", "QUX": "single"})
        finally:
            os.unlink(path)

    def test_missing_file_returns_empty_dict(self):
        self.assertEqual(sc.load_env("/definitely/not/a/real/path.env"), {})


class TestLoadYamlErrorHandling(unittest.TestCase):
    def test_missing_config_exits_cleanly_not_a_traceback(self):
        with self.assertRaises(SystemExit) as ctx:
            sc._load_yaml("/definitely/not/a/real/config.yaml")
        self.assertIn("not found", str(ctx.exception))


class TestScanTwitter(unittest.TestCase):
    """scan_twitter's own HTTP call is stubbed out here — this tests the
    normalization logic (does a raw API response become the right signal
    row shape), not live network access. No bearer token needed to run
    this test; a fake one is passed through to confirm the auth header
    gets built correctly."""

    def setUp(self):
        self._real_http_json = sc.http_json

    def tearDown(self):
        sc.http_json = self._real_http_json

    def test_normalizes_a_real_shaped_api_response(self):
        seen_headers = {}

        def fake_http_json(url, headers=None, data=None, method=None, timeout=20):
            seen_headers.update(headers or {})
            return {
                "data": [
                    {
                        "id": "111",
                        "text": "flaky tests again",
                        "created_at": "2026-10-05T10:00:00.000Z",
                        "public_metrics": {
                            "like_count": 5,
                            "retweet_count": 1,
                            "reply_count": 2,
                            "quote_count": 0,
                        },
                    },
                ]
            }

        sc.http_json = fake_http_json
        cfg = {"twitter": {"seed_queries": ["flaky tests"], "max_results_per_query": 10}}
        rows = sc.scan_twitter(cfg, "test-token", "2026-09-28T00:00:00Z")

        self.assertEqual(seen_headers.get("Authorization"), "Bearer test-token")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["id"], "twitter:111")
        self.assertEqual(row["platform"], "twitter")
        self.assertEqual(row["url"], "https://x.com/i/web/status/111")
        self.assertEqual(row["raw_metric"]["likes"], 5)
        self.assertEqual(row["matched_keywords"], [["flaky tests", "search_query"]])

    def test_dedupes_the_same_tweet_id_across_queries(self):
        def fake_http_json(url, headers=None, data=None, method=None, timeout=20):
            return {
                "data": [
                    {
                        "id": "111",
                        "text": "x",
                        "created_at": "2026-10-05T10:00:00.000Z",
                        "public_metrics": {},
                    }
                ]
            }

        sc.http_json = fake_http_json
        cfg = {"twitter": {"seed_queries": ["query one", "query two"]}}
        rows = sc.scan_twitter(cfg, "test-token", "2026-09-28T00:00:00Z")
        self.assertEqual(len(rows), 1)  # same id from both queries, not duplicated

    def test_one_query_failing_does_not_abort_the_others(self):
        calls = {"n": 0}

        def flaky_http_json(url, headers=None, data=None, method=None, timeout=20):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("simulated failure")
            return {
                "data": [
                    {
                        "id": "222",
                        "text": "ok",
                        "created_at": "2026-10-05T10:00:00.000Z",
                        "public_metrics": {},
                    }
                ]
            }

        sc.http_json = flaky_http_json
        cfg = {"twitter": {"seed_queries": ["bad query", "good query"]}}
        rows = sc.scan_twitter(cfg, "test-token", "2026-09-28T00:00:00Z")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "twitter:222")


class TestTwitterDispatch(unittest.TestCase):
    """The CLI-level graceful-skip / explicit-error behavior for a missing
    `twitter:` block — same pattern already verified for `ph:`."""

    def test_run_twitter_errors_cleanly_without_a_twitter_block(self):
        with self.assertRaises(SystemExit) as ctx:
            sc._run_twitter({}, None, "/tmp/doesnt-matter.env")
        self.assertIn("No `twitter` block", str(ctx.exception))

    def test_run_twitter_errors_cleanly_without_a_token(self):
        cfg = {"twitter": {"seed_queries": ["x"]}}
        with self.assertRaises(SystemExit) as ctx:
            sc._run_twitter(cfg, None, "/definitely/not/a/real/.env")
        self.assertIn("Missing X/Twitter bearer token", str(ctx.exception))


class TestRedditRateLimit(unittest.TestCase):
    """Reddit's unauthenticated RSS allows roughly one request per ~10s per
    IP; a scan that ignores that gets 429 on every feed. urlopen is mocked
    here, so this covers the pacing/retry logic, not Reddit itself."""

    FEED = b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'

    def setUp(self):
        sc._reddit_last_request = None
        sc._reddit_gap = sc.REDDIT_MIN_GAP_SECONDS
        self.sleeps = []

    def _ok(self):
        from unittest import mock

        resp = mock.MagicMock()
        resp.read.return_value = self.FEED
        resp.headers = {"Content-Type": "application/atom+xml; charset=UTF-8"}
        return resp

    def _429(self, reset="19"):
        import urllib.error

        return urllib.error.HTTPError(
            "https://www.reddit.com/r/x/new/.rss",
            429,
            "Too Many Requests",
            {"x-ratelimit-reset": reset, "x-ratelimit-remaining": "0.0"},
            None,
        )

    def test_429_waits_for_reddits_reset_then_succeeds(self):
        from unittest import mock

        with mock.patch.object(
            sc.urllib.request, "urlopen", side_effect=[self._429("19"), self._ok()]
        ):
            body = sc._fetch_rss_raw("devops", "new", sleep=self.sleeps.append)
        self.assertEqual(body, self.FEED)
        self.assertIn(20.0, self.sleeps)  # reset 19s + 1s slack, not a 1.5s guess

    def test_429_wait_is_capped(self):
        self.assertEqual(
            sc._reddit_429_wait({"x-ratelimit-reset": "3600"}), sc.REDDIT_MAX_RESET_WAIT_SECONDS
        )

    def test_429_wait_never_below_gap_or_with_no_headers(self):
        self.assertEqual(sc._reddit_429_wait({"x-ratelimit-reset": "0"}), sc.REDDIT_MIN_GAP_SECONDS)
        self.assertEqual(sc._reddit_429_wait({}), sc.REDDIT_MIN_GAP_SECONDS)

    def test_consecutive_requests_are_spaced_by_the_gap(self):
        clock = [100.0]
        sc._reddit_throttle(now=lambda: clock[0], sleep=self.sleeps.append)
        clock[0] += 2.0  # next request 2s later — must wait the remaining 8s
        sc._reddit_throttle(now=lambda: clock[0], sleep=self.sleeps.append)
        self.assertEqual(self.sleeps, [8.0])

    def test_gives_up_after_three_429s_without_sleeping_after_the_last(self):
        from unittest import mock

        with mock.patch.object(
            sc.urllib.request, "urlopen", side_effect=[self._429(), self._429(), self._429()]
        ):
            with self.assertRaises(sc.urllib.error.HTTPError):
                sc._fetch_rss_raw("devops", "new", sleep=self.sleeps.append)
        self.assertEqual(self.sleeps.count(20.0), 2)


if __name__ == "__main__":
    unittest.main()
