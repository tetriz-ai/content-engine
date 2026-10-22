# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
"""
Platform scans and the CLI, with every HTTP call stubbed: Hacker News
normalisation, Reddit's lookback and date handling, Product Hunt's window,
fit gate and detail fetch, keyword layers, feed-body checks, and the
`failures` record in the output JSON.

Run: python3 -m unittest discover -s tests
"""

import _guard  # noqa: F401  (first: isolates HOME, keys and network)
import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from unittest import mock

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import scanner_core as sc

ATOM_NS = 'xmlns="http://www.w3.org/2005/Atom"'


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _atom(*entries):
    body = "".join(
        "<entry><id>%s</id><title>%s</title><updated>%s</updated>"
        "<content>%s</content><link href='https://www.reddit.com/r/x/%s'/></entry>"
        % (eid, title, updated, text, eid)
        for eid, title, updated, text in entries
    )
    return ('<?xml version="1.0"?><feed %s>%s</feed>' % (ATOM_NS, body)).encode()


class _Resp:
    def __init__(self, body, ctype):
        self._body = body
        self.headers = {"Content-Type": ctype}

    def read(self):
        return self._body


class _CliCase(unittest.TestCase):
    """Runs main() against a config written to a temp dir."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.dir, True))
        for name in ("scan_hn", "scan_reddit", "gql", "http_json"):
            self.addCleanup(setattr, sc, name, getattr(sc, name))
        self.addCleanup(setattr, sc.time, "sleep", time.sleep)
        sc.time.sleep = lambda s: None

    def run_main(self, cfg, *argv, env_text=None):
        cfg_path = os.path.join(self.dir, "c.yaml")
        with open(cfg_path, "w") as f:
            yaml.safe_dump(cfg, f)
        env_path = os.path.join(self.dir, "test.env")
        if env_text is not None:
            with open(env_path, "w") as f:
                f.write(env_text)
        out = os.path.join(self.dir, "out.json")
        args = ["scanner_core.py", "--config", cfg_path, "--env", env_path, "--out", out]
        stderr = io.StringIO()
        with (
            mock.patch.object(sys, "argv", args + list(argv)),
            contextlib.redirect_stderr(stderr),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.exit_code = 0
            try:
                sc.main()
            except SystemExit as e:
                if not os.path.exists(out):
                    raise  # stopped before writing any output
                self.exit_code = e.code
        self.stderr = stderr.getvalue()
        with open(out) as f:
            return json.load(f)


PH_BLOCK = {
    "token_env": "PH_API_TOKEN",
    "window": "lookback",
    "lookback_hours": 48,
    "thin_day_floor": 5,
    "posts_per_page": 20,
    "max_pages": 1,
    "require_fit": True,
    "min_votes": 0,
    "topics": ["developer-tools"],
    "fit_topics": ["developer-tools"],
    "keywords": ["flaky test"],
    "detail_fetch_top": 5,
    "voters_limit": 5,
    "comments_limit": 5,
}


def _ph_post(pid, name, tagline, topics, votes=3):
    return {
        "node": {
            "id": pid,
            "name": name,
            "tagline": tagline,
            "description": "",
            "url": "https://www.producthunt.com/posts/%s?utm_source=x" % pid,
            "website": "https://example.com",
            "votesCount": votes,
            "commentsCount": 1,
            "createdAt": "2026-10-06T08:00:00Z",
            "topics": {
                "edges": [
                    {"node": {"name": t.replace("-", " ").title(), "slug": t}} for t in topics
                ]
            },
            "makers": [
                {
                    "id": "m1",
                    "name": "Jane Doe",
                    "username": "janedoe",
                    "headline": "maker",
                    "url": None,
                    "twitterUsername": None,
                    "websiteUrl": None,
                }
            ],
        }
    }


def _fake_gql(list_pages, detail=None):
    calls = []

    def gql(token, query, variables):
        calls.append((token, variables))
        if "posts(" in query:
            edges = list_pages.pop(0) if list_pages else []
            return {
                "posts": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "edges": edges}
            }
        return {
            "post": detail
            or {
                "id": variables["id"],
                "votes": {
                    "edges": [
                        {
                            "node": {
                                "user": {
                                    "id": "1",
                                    "name": "John Doe",
                                    "username": "johndoe",
                                    "url": None,
                                }
                            }
                        },
                        {
                            "node": {
                                "user": {
                                    "id": "2",
                                    "name": "x",
                                    "username": sc.REDACTED,
                                    "url": None,
                                }
                            }
                        },
                        {
                            "node": {
                                "user": {
                                    "id": "3",
                                    "name": "Jane Doe",
                                    "username": "janedoe",
                                    "url": None,
                                }
                            }
                        },
                    ]
                },
                "comments": {
                    "edges": [
                        {
                            "node": {
                                "body": "Nice launch",
                                "votesCount": 2,
                                "user": {
                                    "id": "1",
                                    "name": "John Doe",
                                    "username": "johndoe",
                                    "url": None,
                                },
                            }
                        },
                    ]
                },
            }
        }

    return gql, calls


class TestProductHuntCli(_CliCase):
    def test_platform_ph_runs_with_the_lookback_window(self):
        gql, calls = _fake_gql(
            [[_ph_post("1", "Example Flaky Radar", "flaky test radar", ["developer-tools"])]]
        )
        sc.gql = gql
        out = self.run_main(
            {"ph": PH_BLOCK}, "--platform", "ph", env_text="PH_API_TOKEN=fake-token\n"
        )
        self.assertEqual([c["id"] for c in out["candidates"]], ["ph:1"])
        self.assertEqual(calls[0][0], "fake-token")
        self.assertIn("rolling 48h lookback", self.stderr)
        self.assertEqual(out["failures"], [])

    def test_ph_day_window_uses_the_board_start(self):
        gql, calls = _fake_gql([[]])
        sc.gql = gql
        block = dict(PH_BLOCK, window="ph_day")
        start = datetime(2026, 10, 7, 7, 0, tzinfo=timezone.utc)
        with mock.patch.object(sc, "ph_day_start", return_value=(start, "PH day 2026-10-07")):
            self.run_main({"ph": block}, "--platform", "ph", env_text="PH_API_TOKEN=t\n")
        self.assertEqual(calls[0][1]["postedAfter"], "2026-10-07T07:00:00Z")
        self.assertIn("thin day: 0 candidates", self.stderr)

    def test_an_unknown_window_is_an_error(self):
        sc.gql = _fake_gql([[]])[0]
        with self.assertRaises(SystemExit) as ctx:
            self.run_main(
                {"ph": dict(PH_BLOCK, window="weekly")},
                "--platform",
                "ph",
                env_text="PH_API_TOKEN=t\n",
            )
        self.assertIn("ph.window", str(ctx.exception))


class TestProductHuntScan(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, sc, "gql", sc.gql)
        self.addCleanup(setattr, sc.time, "sleep", time.sleep)
        sc.time.sleep = lambda s: None

    def test_fit_gate_keeps_keyword_or_fit_topic_matches_only(self):
        sc.gql = _fake_gql(
            [
                [
                    _ph_post("1", "Example Flaky Radar", "a flaky test radar", ["saas"]),
                    _ph_post("2", "Devbox", "dev environments", ["developer-tools"]),
                    _ph_post("3", "Recipes", "cook more", ["food"]),
                ]
            ]
        )[0]
        out = sc.scan_ph({"ph": PH_BLOCK}, "t", "2026-10-05T00:00:00Z")
        by_id = {c["id"]: c for c in out}
        self.assertEqual(sorted(by_id), ["ph:1", "ph:2"])
        self.assertEqual(by_id["ph:1"]["matched_keywords"], ["flaky test"])
        self.assertEqual(by_id["ph:2"]["fit_topics_matched"], ["developer tools"])
        self.assertEqual(by_id["ph:1"]["ph_url"], "https://www.producthunt.com/posts/1")

    def test_fetch_details_skips_makers_and_redacted_users(self):
        gql, _ = _fake_gql([])
        sc.gql = gql
        cand = sc.scan_ph({"ph": PH_BLOCK}, "t", "x") or []
        self.assertEqual(cand, [])
        c = {
            "ph_id": "1",
            "name": "Example Flaky Radar",
            "makers": [{"username": "janedoe"}],
            "top_voters": [],
            "top_commenters": [],
            "discussion": [],
        }
        sc.fetch_details({"ph": PH_BLOCK}, "t", [c])
        self.assertEqual([u["username"] for u in c["top_voters"]], ["johndoe"])
        self.assertEqual(c["pool_redacted"], 1)
        self.assertEqual(c["discussion"][0]["author"], "johndoe")

    def test_a_failed_detail_fetch_is_recorded(self):
        def gql(token, query, variables):
            raise RuntimeError("PH GraphQL error")

        sc.gql = gql
        failures = []
        c = {
            "ph_id": "1",
            "name": "Example Flaky Radar",
            "makers": [],
            "top_voters": [],
            "top_commenters": [],
            "discussion": [],
        }
        with contextlib.redirect_stderr(io.StringIO()):
            sc.fetch_details({"ph": PH_BLOCK}, "t", [c], failures)
        self.assertEqual(failures[0]["platform"], "ph")
        self.assertIn("GraphQL", failures[0]["error"])


class TestAllPlatformsKeepWhatWorked(_CliCase):
    def test_missing_ph_token_under_all_keeps_hn_and_reddit(self):
        sc.scan_hn = lambda cfg, ts, failures=None: [{"id": "hn:1"}]
        sc.scan_reddit = lambda cfg, ts, failures=None: [{"id": "reddit:t3_a"}]
        cfg = {
            "hn": {"tags": ["story"], "min_points": 1},
            "keywords": {"b": ["x"]},
            "subreddits": [{"name": "x"}],
            "ph": PH_BLOCK,
        }
        out = self.run_main(cfg, "--platform", "all")
        self.assertEqual([c["id"] for c in out["candidates"]], ["hn:1", "reddit:t3_a"])
        self.assertEqual(out["failures"][0]["platform"], "ph")
        self.assertIn("Missing Product Hunt API token", out["failures"][0]["error"])

    def test_explicit_ph_without_a_token_is_still_an_error(self):
        with self.assertRaises(SystemExit):
            self.run_main({"ph": PH_BLOCK}, "--platform", "ph")


class TestFailuresAreInTheOutput(_CliCase):
    def test_every_failed_hn_query_is_listed(self):
        def boom(*a, **k):
            raise OSError("network unreachable")

        sc.http_json = boom
        cfg = {
            "hn": {"tags": ["story"], "min_points": 1},
            "keywords": {"b": ["x", "y"]},
            "subreddits": [],
        }
        out = self.run_main(cfg, "--platform", "hn")
        self.assertEqual(out["candidates"], [])
        self.assertEqual(
            [(f["platform"], f["request"]) for f in out["failures"]], [("hn", "x"), ("hn", "y")]
        )
        self.assertIn("network unreachable", out["failures"][0]["error"])
        self.assertEqual(self.exit_code, "Every request failed, so there are no candidates.")

    def test_a_clean_run_has_an_empty_failures_list(self):
        sc.http_json = lambda *a, **k: {"hits": []}
        cfg = {
            "hn": {"tags": ["story"], "min_points": 1},
            "keywords": {"b": ["x"]},
            "subreddits": [],
        }
        self.assertEqual(self.run_main(cfg, "--platform", "hn")["failures"], [])


class TestScanHn(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, sc, "http_json", sc.http_json)
        self.addCleanup(setattr, sc.time, "sleep", time.sleep)
        sc.time.sleep = lambda s: None

    def test_normalises_hits_merges_keywords_and_applies_min_points(self):
        seen = []

        def http_json(url, headers=None, data=None, method=None, timeout=20):
            seen.append(url)
            return {
                "hits": [
                    {
                        "objectID": "7",
                        "title": "Show HN: flaky",
                        "points": 12,
                        "num_comments": 3,
                        "_tags": ["story", "show_hn"],
                        "author": "jdoe",
                        "created_at": "2026-10-06T10:00:00Z",
                        "url": "https://example.com",
                    },
                    {"objectID": "8", "title": "low", "points": 1, "_tags": ["story"]},
                    {"objectID": "9", "title": "at the bar", "points": 3, "_tags": ["story"]},
                ]
            }

        sc.http_json = http_json
        cfg = {
            "hn": {"tags": ["story", "show_hn"], "min_points": 3},
            "keywords": {"precise": ["flaky test"], "broad": ["ci"]},
        }
        out = sc.scan_hn(cfg, 1000)
        self.assertEqual([c["id"] for c in out], ["hn:7", "hn:9"])  # min_points is inclusive
        self.assertEqual(out[0]["type"], "show_hn")
        self.assertEqual(out[0]["matched_keywords"], [["flaky test", "precise"], ["ci", "broad"]])
        self.assertIn("created_at_i>1000", seen[0])
        self.assertIn("typoTolerance=false", seen[0])
        self.assertIn("query=%22flaky+test%22", seen[0])  # an exact phrase


class TestRedditDates(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, sc, "_fetch_rss_raw", sc._fetch_rss_raw)
        self.now = datetime.now(timezone.utc)
        self.since = int((self.now - timedelta(hours=48)).timestamp())
        self.cfg = {
            "keywords": {"precise": ["flaky test"]},
            "subreddits": [{"name": "x"}],
            "reddit_min_gap_seconds": 0,
        }

    def _scan(self, *entries):
        feed = _atom(*entries)
        sc._fetch_rss_raw = lambda sub, kind, sleep=None: feed
        self.failures = []
        with contextlib.redirect_stderr(io.StringIO()) as err:
            out = sc.scan_reddit(self.cfg, self.since, self.failures)
        self.err = err.getvalue()
        return [c["id"] for c in out]

    def test_a_z_timestamp_older_than_the_window_is_dropped(self):
        self.assertEqual(self._scan(("t3_old", "flaky test rant", "2020-01-01T00:00:00Z", "")), [])

    def test_a_recent_z_timestamp_is_kept(self):
        recent = _iso(self.now - timedelta(hours=1))
        self.assertEqual(self._scan(("t3_new", "flaky test rant", recent, "")), ["reddit:t3_new"])

    def test_an_undated_entry_is_dropped_and_counted(self):
        self.assertEqual(self._scan(("t3_nodate", "flaky test rant", "", "")), [])
        self.assertIn("no parseable date", self.err)
        self.assertEqual(
            self.failures,
            [
                {
                    "platform": "reddit",
                    "request": "r/x",
                    "error": "1 entries dropped, no parseable date",
                }
            ],
        )

    def test_iso_to_ts_reads_z_offsets_and_naive_as_utc(self):
        self.assertEqual(sc._iso_to_ts("2026-10-01T00:00:00Z"), 1790812800)
        self.assertEqual(sc._iso_to_ts("2026-10-01T00:00:00+00:00"), 1790812800)
        self.assertEqual(sc._iso_to_ts("2026-10-01T00:00:00"), 1790812800)
        self.assertIsNone(sc._iso_to_ts("yesterday"))
        self.assertIsNone(sc._iso_to_ts(None))


class TestKnownLimits(unittest.TestCase):
    """Known limits of the fetchers, pinned as they behave today."""

    def test_x_lookback_is_clamped_to_seven_days(self):
        seen = {}

        def fake_scan(cfg, token, since_iso, failures=None):
            seen["since"] = since_iso
            return []

        d = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, d, True)
        env = os.path.join(d, "x.env")
        with open(env, "w") as f:
            f.write("TWITTER_BEARER_TOKEN=fake-token\n")
        with (
            mock.patch.object(sc, "scan_twitter", fake_scan),
            contextlib.redirect_stderr(io.StringIO()) as err,
        ):
            sc._run_twitter({"twitter": {"seed_queries": ["q"], "lookback_hours": 500}}, None, env)
        since = datetime.strptime(seen["since"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - since
        self.assertLess(age, timedelta(hours=168))
        self.assertGreaterEqual(
            age, timedelta(hours=168) - sc.TWITTER_LOOKBACK_MARGIN - timedelta(minutes=1)
        )
        self.assertIn("clamped to 168", err.getvalue())

    def test_x_reads_one_page_per_query(self):
        # Design choice: one page per query bounds the cost of a paid API.
        urls = []

        def http_json(url, headers=None, data=None, method=None, timeout=20):
            urls.append(url)
            return {"data": [], "meta": {"next_token": "more"}}

        with (
            mock.patch.object(sc, "http_json", http_json),
            mock.patch.object(sc.time, "sleep", lambda s: None),
        ):
            sc.scan_twitter({"twitter": {"seed_queries": ["a", "b"]}}, "t", "x")
        self.assertEqual(len(urls), 2)
        self.assertFalse(any("next_token" in u or "pagination_token" in u for u in urls))

    def test_reddit_keywords_match_as_plain_substrings(self):
        recent = _iso(datetime.now(timezone.utc) - timedelta(hours=1))
        feed = _atom(
            ("t3_a", "The flakybot is back", recent, ""), ("t3_b", "Nothing relevant", recent, "")
        )
        with (
            mock.patch.object(sc, "_fetch_rss_raw", lambda sub, kind, sleep=None: feed),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            out = sc.scan_reddit(
                {
                    "keywords": {"watch": ["flaky"]},
                    "subreddits": [{"name": "x"}],
                    "reddit_min_gap_seconds": 0,
                },
                0,
            )
        self.assertEqual([c["id"] for c in out], ["reddit:t3_a"])  # "flaky" inside "flakybot"


class TestKeywordLayers(unittest.TestCase):
    def test_an_empty_layer_is_skipped_not_a_crash(self):
        cfg = {"keywords": {"precise": ["a"], "watch": None, "broad": []}}
        self.assertEqual(sc.all_keywords(cfg), [("a", "precise")])

    def test_no_keywords_block_is_an_empty_list(self):
        self.assertEqual(sc.all_keywords({}), [])


class TestRedditFeedBody(unittest.TestCase):
    def setUp(self):
        sc._reddit_last_request = None
        sc._reddit_gap = 0.0
        self.addCleanup(setattr, sc, "_reddit_gap", sc.REDDIT_MIN_GAP_SECONDS)

    def _fetch(self, body, ctype="application/atom+xml; charset=UTF-8"):
        with mock.patch.object(
            sc.urllib.request, "urlopen", side_effect=lambda req, timeout=20: _Resp(body, ctype)
        ):
            return sc._fetch_rss_raw("x", "new", sleep=lambda s: None)

    def test_a_feed_without_an_xml_declaration_is_accepted(self):
        body = ("<feed %s></feed>" % ATOM_NS).encode()
        self.assertEqual(self._fetch(body), body)

    def test_a_utf8_bom_is_stripped(self):
        body = b'\xef\xbb\xbf<?xml version="1.0"?><feed></feed>'
        self.assertEqual(self._fetch(body), body[3:])

    def test_feed_body_accepts_each_feed_start_and_nothing_else(self):
        for body in (b'<?xml version="1.0"?>', b"<rss version='2.0'>", b"<feed>", b"  <rss>"):
            self.assertIsNotNone(sc._feed_body(body), body)
        for body in (b"<html>", b"", b"{}"):
            self.assertIsNone(sc._feed_body(body), body)

    def test_an_html_page_names_the_body_not_the_content_type(self):
        with self.assertRaises(sc._NotRealFeed) as ctx:
            self._fetch(b"<html>consent wall</html>", "text/xml")
        self.assertIn("body that is not an XML feed", str(ctx.exception))

    def test_a_non_xml_content_type_says_so(self):
        with self.assertRaises(sc._NotRealFeed) as ctx:
            self._fetch(b"<html></html>", "text/html")
        self.assertIn("content-type 'text/html'", str(ctx.exception))


class TestTwitterFailures(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, sc, "http_json", sc.http_json)
        self.addCleanup(setattr, sc.time, "sleep", time.sleep)
        sc.time.sleep = lambda s: None

    def test_an_http_error_is_recorded(self):
        def http_json(*a, **k):
            raise urllib.error.HTTPError("https://api.x.example", 400, "Bad Request", {}, None)

        sc.http_json = http_json
        failures = []
        with contextlib.redirect_stderr(io.StringIO()):
            rows = sc.scan_twitter(
                {"twitter": {"seed_queries": ["q"]}}, "t", "2020-01-01T00:00:00Z", failures
            )
        self.assertEqual(rows, [])
        self.assertEqual(failures[0]["platform"], "twitter")
        self.assertIn("400", failures[0]["error"])


class TestGuard(unittest.TestCase):
    def test_the_network_is_blocked(self):
        import socket

        with self.assertRaises(RuntimeError):
            socket.create_connection(("example.com", 80))

    def test_home_is_a_temp_dir(self):
        self.assertEqual(os.environ["HOME"], _guard.HOME)
        self.assertNotIn("PH_API_TOKEN", os.environ)


class TestScannerFailures(unittest.TestCase):
    def setUp(self):
        for name in ("gql", "http_json"):
            self.addCleanup(setattr, sc, name, getattr(sc, name))
        self.addCleanup(setattr, sc.time, "sleep", time.sleep)
        sc.time.sleep = lambda s: None

    def test_one_ph_topic_failing_keeps_the_others(self):
        def gql(token, query, variables):
            if variables["topic"] == "broken":
                raise urllib.error.URLError("connection reset")
            return {
                "posts": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "edges": [
                        _ph_post(
                            "1", "Example Flaky Radar", "flaky test radar", ["developer-tools"]
                        )
                    ],
                }
            }

        sc.gql = gql
        failures = []
        block = dict(PH_BLOCK, topics=["broken", "developer-tools"])
        with contextlib.redirect_stderr(io.StringIO()):
            out = sc.scan_ph({"ph": block}, "t", "2026-10-05T00:00:00Z", failures)
        self.assertEqual([c["id"] for c in out], ["ph:1"])
        self.assertEqual(failures[0]["platform"], "ph")
        self.assertEqual(failures[0]["request"], "topic broken page 1")

    def test_a_rejected_ph_token_still_stops_the_scan(self):
        def gql(token, query, variables):
            sys.exit("PH API rejected the token (401).")

        sc.gql = gql
        with self.assertRaises(SystemExit):
            sc.scan_ph({"ph": PH_BLOCK}, "t", "2026-10-05T00:00:00Z", [])

    def test_iso_to_ts_reads_fractional_seconds_and_compact_offsets(self):
        self.assertEqual(sc._iso_to_ts("2026-10-01T00:00:00.12Z"), 1790812800)
        self.assertEqual(sc._iso_to_ts("2026-10-01T00:00:00+0000"), 1790812800)
        self.assertEqual(sc._iso_to_ts("2026-10-01T05:30:00+0530"), 1790812800)

    def test_x_merges_the_queries_a_tweet_matched(self):
        sc.http_json = lambda *a, **k: {"data": [{"id": "9", "text": "t", "public_metrics": {}}]}
        rows = sc.scan_twitter({"twitter": {"seed_queries": ["q1", "q2"]}}, "t", "x")
        self.assertEqual(
            rows[0]["matched_keywords"], [["q1", "search_query"], ["q2", "search_query"]]
        )

    def test_ph_day_starts_at_midnight_pacific(self):
        now = datetime(2026, 10, 7, 10, 0, tzinfo=timezone.utc)  # 03:00 PDT
        start, note = sc.ph_day_start(now)
        self.assertEqual(start, datetime(2026, 10, 7, 7, 0, tzinfo=timezone.utc))
        self.assertIn("2026-10-07", note)

    def test_ph_min_votes_is_inclusive(self):
        sc.gql = _fake_gql(
            [
                [
                    _ph_post("1", "A", "flaky test", ["developer-tools"], votes=3),
                    _ph_post("2", "B", "flaky test", ["developer-tools"], votes=2),
                ]
            ]
        )[0]
        out = sc.scan_ph({"ph": dict(PH_BLOCK, min_votes=3)}, "t", "x")
        self.assertEqual([c["id"] for c in out], ["ph:1"])

    def test_a_redacted_commenter_is_not_a_top_commenter(self):
        detail = {
            "votes": {"edges": []},
            "comments": {
                "edges": [
                    {
                        "node": {
                            "body": "Hidden",
                            "votesCount": 1,
                            "user": {"id": "2", "name": "x", "username": sc.REDACTED, "url": None},
                        }
                    },
                    {
                        "node": {
                            "body": "Visible",
                            "votesCount": 1,
                            "user": {
                                "id": "1",
                                "name": "John Doe",
                                "username": "johndoe",
                                "url": None,
                            },
                        }
                    },
                ]
            },
        }
        sc.gql = _fake_gql([], detail)[0]
        c = {
            "ph_id": "1",
            "name": "A",
            "makers": [],
            "top_voters": [],
            "top_commenters": [],
            "discussion": [],
        }
        sc.fetch_details({"ph": PH_BLOCK}, "t", [c])
        self.assertEqual([u["username"] for u in c["top_commenters"]], ["johndoe"])
        self.assertEqual([d["author"] for d in c["discussion"]], [None, "johndoe"])
        self.assertEqual(c["pool_redacted"], 1)

    def test_a_429_waits_for_the_larger_header(self):
        self.assertEqual(sc._reddit_429_wait({"x-ratelimit-reset": "5", "Retry-After": "30"}), 31.0)
        self.assertEqual(
            sc._reddit_429_wait({"x-ratelimit-reset": "40", "Retry-After": "12"}), 41.0
        )


EXAMPLE_CONFIG = os.path.join(
    os.path.dirname(__file__), "..", "..", "content-engine", "config.example.yaml"
)


class TestCliOptions(_CliCase):
    def test_twitter_under_scan_is_read(self):
        with open(EXAMPLE_CONFIG) as f:
            text = f.read()
        start = text.index("  # twitter:\n  #   bearer_token_env")
        end = text.index("\n\n", start)
        block = "\n".join(
            ln.replace("  # ", "  ", 1).replace("  #", "  ", 1)
            for ln in text[start:end].splitlines()
        )
        cfg = yaml.safe_load(text[:start] + block + text[end:])
        self.assertIn("twitter", cfg["scan"])
        env = os.path.join(self.dir, "x.env")
        with open(env, "w") as f:
            f.write("TWITTER_BEARER_TOKEN=fake-token\n")
        seen = {}

        def fake(cfg_arg, token, since_iso, failures=None):
            seen["queries"] = cfg_arg["twitter"]["seed_queries"]
            return []

        with mock.patch.object(sc, "scan_twitter", fake), contextlib.redirect_stderr(io.StringIO()):
            sc._run_twitter(cfg, None, env)
        self.assertEqual(seen["queries"], cfg["scan"]["twitter"]["seed_queries"])

    def test_all_skips_hn_and_reddit_without_their_blocks(self):
        sc.scan_hn = lambda *a, **k: self.fail("hn ran without an hn block")
        sc.scan_reddit = lambda *a, **k: self.fail("reddit ran without subreddits")
        out = self.run_main({"keywords": {"b": ["x"]}}, "--platform", "all")
        self.assertEqual(
            out, {"candidates": [], "failures": [], "generated_at": out["generated_at"]}
        )
        self.assertIn("no `hn:` block", self.stderr)
        self.assertIn("no `subreddits:`", self.stderr)

    def test_a_missing_ph_block_under_all_is_skipped_not_a_failure(self):
        sc.scan_hn = lambda cfg, ts, failures=None: []
        cfg = {"hn": {"tags": ["story"], "min_points": 1}, "keywords": {"b": ["x"]}}
        out = self.run_main(cfg, "--platform", "all")
        self.assertEqual(out["failures"], [])
        self.assertIn("[ph] no `ph:` block", self.stderr)

    def test_a_rate_limit_during_details_keeps_the_listed_launches(self):
        list_gql = _fake_gql(
            [
                [
                    _ph_post("1", "A", "flaky test", ["developer-tools"]),
                    _ph_post("2", "B", "flaky test", ["developer-tools"]),
                ]
            ]
        )[0]

        def gql(token, query, variables):
            if "posts(" in query:
                return list_gql(token, query, variables)
            sys.exit("PH API rate limit hit (429).")

        sc.gql = gql
        out = self.run_main({"ph": PH_BLOCK}, "--platform", "ph", env_text="PH_API_TOKEN=t\n")
        self.assertEqual(sorted(c["id"] for c in out["candidates"]), ["ph:1", "ph:2"])
        self.assertEqual(len(out["failures"]), 1)
        self.assertIn("429", out["failures"][0]["error"])

    def test_ph_candidates_are_sorted_by_keyword_matches(self):
        sc.gql = _fake_gql(
            [
                [
                    _ph_post("1", "A", "nothing relevant", ["developer-tools"]),
                    _ph_post("2", "B", "flaky test radar", ["developer-tools"]),
                ]
            ]
        )[0]
        out = self.run_main({"ph": PH_BLOCK}, "--platform", "ph", env_text="PH_API_TOKEN=t\n")
        self.assertEqual([c["id"] for c in out["candidates"]], ["ph:2", "ph:1"])

    def test_details_are_fetched_for_the_top_n_only(self):
        calls = []
        list_gql = _fake_gql(
            [
                [
                    _ph_post("1", "A", "flaky test", ["developer-tools"]),
                    _ph_post("2", "B", "flaky test", ["developer-tools"]),
                ]
            ]
        )[0]

        def gql(token, query, variables):
            if "posts(" not in query:
                calls.append(variables["id"])
            return list_gql(token, query, variables)

        sc.gql = gql
        self.run_main(
            {"ph": dict(PH_BLOCK, detail_fetch_top=1)},
            "--platform",
            "ph",
            env_text="PH_API_TOKEN=t\n",
        )
        self.assertEqual(len(calls), 1)

    def test_a_day_at_the_floor_is_not_thin(self):
        sc.gql = _fake_gql([[_ph_post("1", "A", "flaky test", ["developer-tools"])]])[0]
        start = datetime(2026, 10, 7, 7, 0, tzinfo=timezone.utc)
        with mock.patch.object(sc, "ph_day_start", return_value=(start, "PH day")):
            self.run_main(
                {"ph": dict(PH_BLOCK, window="ph_day", thin_day_floor=1)},
                "--platform",
                "ph",
                env_text="PH_API_TOKEN=t\n",
            )
        self.assertNotIn("thin day", self.stderr)


class TestScanLimits(unittest.TestCase):
    def setUp(self):
        for name in ("gql", "http_json", "_fetch_rss_raw"):
            self.addCleanup(setattr, sc, name, getattr(sc, name))
        self.addCleanup(setattr, sc.time, "sleep", time.sleep)
        sc.time.sleep = lambda s: None

    def test_a_truncated_hn_keyword_is_recorded(self):
        urls = []

        def http_json(url, headers=None, data=None, method=None, timeout=20):
            urls.append(url)
            hits = [
                {"objectID": str(i), "title": "t", "points": 5, "_tags": ["story"]}
                for i in range(50)
            ]
            return {"hits": hits, "nbHits": 120}

        sc.http_json = http_json
        failures = []
        with contextlib.redirect_stderr(io.StringIO()):
            out = sc.scan_hn(
                {"hn": {"tags": ["story"], "min_points": 1}, "keywords": {"b": ["flaky"]}},
                0,
                failures,
            )
        self.assertEqual(len(out), 50)
        self.assertEqual(
            failures, [{"platform": "hn", "request": "flaky", "error": "truncated: 50 of 120 hits"}]
        )
        self.assertIn("hitsPerPage=50", urls[0])  # design choice: one request per keyword

    def test_an_untruncated_hn_keyword_records_nothing(self):
        sc.http_json = lambda *a, **k: {"hits": [], "nbHits": 0}
        failures = []
        sc.scan_hn(
            {"hn": {"tags": ["story"], "min_points": 1}, "keywords": {"b": ["x"]}}, 0, failures
        )
        self.assertEqual(failures, [])

    def test_reddit_feeds_ask_for_a_hundred_entries(self):
        urls = []

        def urlopen(req, timeout=20):
            urls.append(req.full_url)
            return _Resp(_atom(), "application/atom+xml")

        sc._reddit_last_request = None
        with (
            mock.patch.object(sc, "_reddit_gap", 0.0),
            mock.patch.object(sc.urllib.request, "urlopen", urlopen),
        ):
            sc._fetch_rss_raw("x", "new", sleep=lambda s: None)
        self.assertIn("limit=100", urls[0])  # Reddit's feeds serve at most 100

    def test_a_403_is_retried_on_the_other_host(self):
        urls = []
        replies = [
            urllib.error.HTTPError("u", 403, "Blocked", {}, None),
            _Resp(_atom(), "application/atom+xml"),
        ]

        def urlopen(req, timeout=20):
            urls.append(req.full_url)
            r = replies.pop(0)
            if isinstance(r, Exception):
                raise r
            return r

        sc._reddit_last_request = None
        with (
            mock.patch.object(sc, "_reddit_gap", 0.0),
            mock.patch.object(sc.urllib.request, "urlopen", urlopen),
        ):
            body = sc._fetch_rss_raw("x", "new", sleep=lambda s: None)
        self.assertTrue(body.startswith(b"<?xml"))
        self.assertTrue(urls[0].startswith("https://www.reddit.com/"))
        self.assertTrue(urls[1].startswith("https://old.reddit.com/"))

    def test_a_reddit_entry_exactly_at_the_window_start_is_kept(self):
        since = 1790812800
        feed = _atom(("t3_edge", "flaky test at the edge", "2026-10-01T00:00:00Z", ""))
        sc._fetch_rss_raw = lambda sub, kind, sleep=None: feed
        with contextlib.redirect_stderr(io.StringIO()):
            out = sc.scan_reddit(
                {
                    "keywords": {"p": ["flaky test"]},
                    "subreddits": [{"name": "x"}],
                    "reddit_min_gap_seconds": 0,
                },
                since,
            )
        self.assertEqual([c["id"] for c in out], ["reddit:t3_edge"])

    def test_a_failed_ph_page_stops_that_topic(self):
        calls = []

        def gql(token, query, variables):
            calls.append(variables["topic"])
            raise urllib.error.URLError("reset")

        sc.gql = gql
        with contextlib.redirect_stderr(io.StringIO()):
            sc.scan_ph({"ph": dict(PH_BLOCK, max_pages=3)}, "t", "x", [])
        self.assertEqual(calls, ["developer-tools"])

    def test_ph_keywords_match_as_substrings(self):
        # Design choice: Product Hunt keywords are plain substrings.
        sc.gql = _fake_gql([[_ph_post("1", "A", "the flakybot for CI", ["home"])]])[0]
        out = sc.scan_ph({"ph": dict(PH_BLOCK, keywords=["flaky"])}, "t", "x")
        self.assertEqual(out[0]["matched_keywords"], ["flaky"])

    def test_feed_bodies_after_comments_doctype_or_rdf_are_feeds(self):
        for body in (b"<rdf:RDF/>", b"<!-- c --><!DOCTYPE feed><feed/>", b"<!--a-->\n<rss/>"):
            with self.subTest(body=body):
                self.assertIsNotNone(sc._feed_body(body))
        self.assertIsNone(sc._feed_body(b"<!-- unterminated"))


class TestScanEdgeCases(unittest.TestCase):
    def setUp(self):
        for name in ("http_json", "_fetch_rss_raw"):
            self.addCleanup(setattr, sc, name, getattr(sc, name))
        self.addCleanup(setattr, sc.time, "sleep", time.sleep)
        sc.time.sleep = lambda s: None

    def _hn(self, n_hits, nb_hits):
        def http_json(url, headers=None, data=None, method=None, timeout=20):
            hits = [
                {"objectID": str(i), "title": "t", "points": 5, "_tags": ["story"]}
                for i in range(n_hits)
            ]
            reply = {"hits": hits}
            if nb_hits is not None:
                reply["nbHits"] = nb_hits
            return reply

        sc.http_json = http_json
        failures = []
        with contextlib.redirect_stderr(io.StringIO()):
            sc.scan_hn(
                {"hn": {"tags": ["story"], "min_points": 1}, "keywords": {"b": ["x"]}},
                0,
                failures,
            )
        return [f["error"] for f in failures]

    def test_the_hn_truncation_boundary(self):
        self.assertEqual(self._hn(50, 51), ["truncated: 50 of 51 hits"])
        self.assertEqual(self._hn(50, 50), [])

    def test_a_full_page_with_no_total_is_possibly_truncated(self):
        self.assertEqual(self._hn(50, None), ["possibly truncated: 50 hits and no total"])
        self.assertEqual(self._hn(51, None), ["possibly truncated: 51 hits and no total"])
        self.assertEqual(self._hn(49, None), [])

    def test_an_xml_body_that_is_not_atom_is_a_failed_feed(self):
        for body in (
            b'<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml">Log in</html>',
            b'<?xml version="1.0"?><rss version="2.0"><channel/></rss>',
            b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"/>',
        ):
            with self.subTest(body=body):
                sc._fetch_rss_raw = lambda sub, kind, sleep=None, body=body: body
                failures = []
                with contextlib.redirect_stderr(io.StringIO()):
                    out = sc.scan_reddit(
                        {
                            "keywords": {"p": ["x"]},
                            "subreddits": [{"name": "x"}],
                            "reddit_min_gap_seconds": 0,
                        },
                        0,
                        failures,
                    )
                self.assertEqual(out, [])
                self.assertEqual([f["request"] for f in failures], ["r/x new", "r/x hot"])
                self.assertIn("not an Atom feed", failures[0]["error"])


class TestCliEdgeCases(_CliCase):
    def test_twitter_in_both_places_is_an_error_naming_both(self):
        block = {"seed_queries": ["q"]}
        with self.assertRaises(SystemExit) as ctx:
            sc._twitter_block({"twitter": block, "scan": {"twitter": block}})
        self.assertIn("top level", str(ctx.exception))
        self.assertIn("scan:", str(ctx.exception))

    def test_twitter_in_both_places_stops_the_run_before_any_scan(self):
        block = {"seed_queries": ["q"]}
        cfg = {
            "twitter": block,
            "scan": {"twitter": block},
            "hn": {"tags": ["story"], "min_points": 1},
            "keywords": {"b": ["x"]},
            "subreddits": [{"name": "a"}],
        }
        sc.scan_hn, sc.scan_reddit = mock.Mock(return_value=[]), mock.Mock(return_value=[])
        for platform in ("all", "hn", "reddit"):
            with self.subTest(platform=platform):
                with self.assertRaises(SystemExit) as ctx:
                    self.run_main(cfg, "--platform", platform)
                self.assertIn("both at the top level", str(ctx.exception))
                sc.scan_hn.assert_not_called()
                sc.scan_reddit.assert_not_called()

    def test_a_scan_that_is_not_a_mapping_is_a_message(self):
        sc.scan_hn = mock.Mock(return_value=[])
        for scan in ([1], "text"):
            with self.subTest(scan=scan):
                cfg = {"scan": scan, "hn": {"tags": ["story"], "min_points": 1}}
                with self.assertRaises(SystemExit) as ctx:
                    self.run_main(cfg, "--platform", "all")
                self.assertIn("`scan` in --config must be a mapping", str(ctx.exception))
                sc.scan_hn.assert_not_called()

    def test_an_empty_or_non_mapping_config_is_a_message(self):
        for text in ("", "- a\n- b\n", "just text\n"):
            with self.subTest(text=text):
                path = os.path.join(self.dir, "bad.yaml")
                with open(path, "w") as f:
                    f.write(text)
                with self.assertRaises(SystemExit) as ctx:
                    sc._load_yaml(path)
                self.assertIn("not a YAML mapping", str(ctx.exception))

    def test_all_runs_x_from_a_twitter_block_under_scan(self):
        cfg = {"scan": {"twitter": {"seed_queries": ["flaky tests"]}}}
        fake = mock.Mock(return_value=[{"id": "x:1"}])
        with mock.patch.object(sc, "scan_twitter", fake):
            out = self.run_main(cfg, "--platform", "all", env_text="TWITTER_BEARER_TOKEN=t\n")
        self.assertEqual([c["id"] for c in out["candidates"]], ["x:1"])
        self.assertEqual(fake.call_args[0][0]["twitter"]["seed_queries"], ["flaky tests"])

    def test_max_subreddits_scans_the_first_n_only(self):
        seen = {}

        def scan_reddit(cfg, ts, failures=None):
            seen["subs"] = [s["name"] for s in cfg["subreddits"]]
            return []

        sc.scan_reddit = scan_reddit
        cfg = {"keywords": {"b": ["x"]}, "subreddits": [{"name": n} for n in "abc"]}
        self.run_main(cfg, "--platform", "reddit", "--max-subreddits", "2")
        self.assertEqual(seen["subs"], ["a", "b"])
        self.assertIn("scanning 2 of 3 subreddits", self.stderr)
        for n, subs in (("1", ["a"]), ("5", ["a", "b", "c"])):
            with self.subTest(n=n):
                self.run_main(cfg, "--platform", "reddit", "--max-subreddits", n)
                self.assertEqual(seen["subs"], subs)
                self.assertIn("scanning %d of 3 subreddits" % len(subs), self.stderr)
        # 0 would mean "no Reddit", which leaving out `subreddits` already says, so
        # 0 and below are usage errors rather than a silent empty scan.
        cfg_path = os.path.join(self.dir, "c.yaml")
        for n in ("0", "-1"):
            with self.subTest(n=n):
                seen.clear()
                argv = ["scanner_core.py", "--config", cfg_path, "--max-subreddits", n]
                with (
                    mock.patch.object(sys, "argv", argv),
                    contextlib.redirect_stderr(io.StringIO()) as err,
                    self.assertRaises(SystemExit) as ctx,
                ):
                    sc.main()
                self.assertEqual(ctx.exception.code, 2)
                self.assertIn("--max-subreddits must be 1 or more", err.getvalue())
                self.assertEqual(seen, {})


class TestMatchingAndRequests(unittest.TestCase):
    """Matching, failures and request parameters the fetchers promise."""

    def setUp(self):
        self.addCleanup(setattr, sc, "http_json", sc.http_json)
        self.addCleanup(setattr, sc.time, "sleep", time.sleep)
        sc.time.sleep = lambda s: None
        self.recent = _iso(datetime.now(timezone.utc) - timedelta(hours=1))

    def _reddit(self, keywords, *entries, failures=None):
        feed = _atom(*entries)
        with (
            mock.patch.object(sc, "_fetch_rss_raw", lambda sub, kind, sleep=None: feed),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            return sc.scan_reddit(
                {"keywords": keywords, "subreddits": [{"name": "x"}], "reddit_min_gap_seconds": 0},
                0,
                failures,
            )

    def test_reddit_matches_across_line_breaks_and_no_break_spaces(self):
        for title in ("Flaky\ntests again", "flaky\xa0tests again", "flaky   tests again"):
            with self.subTest(title=repr(title)):
                out = self._reddit({"p": ["flaky tests"]}, ("t3_a", title, self.recent, ""))
                self.assertEqual([c["id"] for c in out], ["reddit:t3_a"])
        out = self._reddit({"p": ["flaky\ntests"]}, ("t3_b", "flaky tests", self.recent, ""))
        self.assertEqual(len(out), 1)

    def test_reddit_matching_ignores_case(self):
        out = self._reddit({"p": ["Flaky Test"]}, ("t3_c", "FLAKY TEST rant", self.recent, ""))
        self.assertEqual(out[0]["matched_keywords"], [["Flaky Test", "p"]])

    def test_a_keyword_in_two_layers_is_reported_in_both_as_written(self):
        out = self._reddit(
            {"precise": ["Flaky Test"], "broad": ["flaky test"]},
            ("t3_d", "a flaky test", self.recent, ""),
        )
        self.assertEqual(
            out[0]["matched_keywords"], [["Flaky Test", "precise"], ["flaky test", "broad"]]
        )

    def test_product_hunt_matches_across_line_breaks(self):
        sc.gql = _fake_gql([[_ph_post("9", "Radar", "finds flaky\ntests", ["saas"])]])[0]
        self.addCleanup(setattr, sc, "gql", sc.gql)
        block = dict(PH_BLOCK, keywords=["flaky\xa0tests"], fit_topics=[], require_fit=True)
        with contextlib.redirect_stderr(io.StringIO()):
            out = sc.scan_ph({"ph": block}, "t", "2026-10-05T00:00:00Z")
        self.assertEqual([c["id"] for c in out], ["ph:9"])

    def test_hn_asks_for_exact_phrases(self):
        urls = []
        sc.http_json = lambda url, **k: urls.append(url) or {"hits": [], "nbHits": 0}
        sc.scan_hn({"hn": {"tags": ["story"], "min_points": 1}, "keywords": {"b": ["ci"]}}, 0)
        self.assertIn("advancedSyntax=true", urls[0])
        self.assertIn("typoTolerance=false", urls[0])

    def test_an_hn_hit_with_no_object_id_is_skipped(self):
        sc.http_json = lambda url, **k: {
            "hits": [{"title": "no id", "points": 9}, {"objectID": "", "points": 9}],
            "nbHits": 2,
        }
        out = sc.scan_hn({"hn": {"tags": ["story"], "min_points": 1}, "keywords": {"b": ["ci"]}}, 0)
        self.assertEqual(out, [])

    def _x(self, reply, failures):
        urls = []

        def http_json(url, headers=None, data=None, method=None, timeout=20):
            urls.append(url)
            if isinstance(reply, Exception):
                raise reply
            return reply

        sc.http_json = http_json
        with contextlib.redirect_stderr(io.StringIO()):
            out = sc.scan_twitter(
                {"twitter": {"seed_queries": ["flaky tests"]}},
                "t",
                "2026-10-06T00:00:00Z",
                failures,
            )
        return out, urls

    def test_x_asks_from_the_window_start(self):
        _, urls = self._x({"data": []}, [])
        self.assertIn("start_time=2026-10-06T00%3A00%3A00Z", urls[0])

    def test_x_data_null_and_errors_only_are_recorded_not_a_crash(self):
        failures = []
        out, _ = self._x({"data": None}, failures)
        self.assertEqual((out, failures), ([], []))
        out, _ = self._x(
            {"errors": [{"title": "Invalid Request", "detail": "bad query"}]}, failures
        )
        self.assertEqual(out, [])
        self.assertEqual(failures[0]["error"], "API error: bad query")

    def test_x_with_a_next_page_is_marked_truncated(self):
        failures = []
        out, _ = self._x(
            {"data": [{"id": "1", "text": "t"}], "meta": {"next_token": "abc"}}, failures
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(failures[0]["error"], "truncated: more results than one page")

    def test_x_non_http_error_is_recorded(self):
        failures = []
        self._x(ValueError("not JSON"), failures)
        self.assertEqual(
            failures, [{"platform": "twitter", "request": "flaky tests", "error": "not JSON"}]
        )

    def test_out_dir_writes_a_dated_platform_file(self):
        d = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, d, True)
        config = os.path.join(d, "c.yaml")
        with open(config, "w") as f:
            f.write("hn: {tags: [story], min_points: 1}\nkeywords: {b: [ci]}\nsubreddits: []\n")
        with (
            mock.patch.object(sc, "_run_hn_reddit", lambda cfg, args, failures: {"candidates": []}),
            mock.patch.object(
                sys, "argv", ["sc", "--config", config, "--platform", "hn", "--out-dir", d]
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            sc.main()
        today = datetime.now(timezone.utc).date().isoformat()
        self.assertTrue(os.path.exists(os.path.join(d, "hn-candidates-%s.json" % today)))

    def test_the_ph_token_in_the_env_file_wins_over_the_environment(self):
        d = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, d, True)
        env = os.path.join(d, ".env")
        with open(env, "w") as f:
            f.write("PH_API_TOKEN=from-file\n")
        seen = []

        def scan_ph(cfg, token, since_iso, failures=None):
            seen.append(token)
            return []

        args = mock.Mock(max_subreddits=None)
        with (
            mock.patch.dict(os.environ, {"PH_API_TOKEN": "from-environment"}),
            mock.patch.object(sc, "scan_ph", scan_ph),
            mock.patch.object(sc, "fetch_details", lambda *a, **k: None),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            sc._run_ph({"ph": dict(PH_BLOCK)}, args, env, [])
        self.assertEqual(seen, ["from-file"])


class TestMalformedHnBody(_CliCase):
    """A Hacker News reply with no list of hits is a failed query, and the
    other platforms still run."""

    def _cfg(self):
        return {
            "hn": {"tags": ["story"], "min_points": 1},
            "keywords": {"b": ["flaky test"]},
            "subreddits": [{"name": "x"}],
            "reddit_min_gap_seconds": 0,
        }

    def test_a_malformed_hn_body_under_all_still_yields_reddit_candidates(self):
        recent = _iso(datetime.now(timezone.utc) - timedelta(hours=1))
        feed = _atom(("t3_a", "flaky test rant", recent, ""))
        self.addCleanup(setattr, sc, "_fetch_rss_raw", sc._fetch_rss_raw)
        sc._fetch_rss_raw = lambda sub, kind, sleep=None: feed
        for body in ({"hits": None}, [], {"nbHits": 3}, "not json", {"hits": "abc"}, {"hits": {}}):
            with self.subTest(body=body):
                sc.http_json = lambda *a, _b=body, **k: _b
                out = self.run_main(self._cfg(), "--platform", "all")
                self.assertEqual([c["id"] for c in out["candidates"]], ["reddit:t3_a"])
                self.assertEqual(
                    [(f["platform"], f["request"]) for f in out["failures"]],
                    [("hn", "flaky test")],
                )
                self.assertIn("no list of hits", out["failures"][0]["error"])

    def test_a_hit_that_is_not_a_mapping_is_skipped(self):
        sc.http_json = lambda *a, **k: {
            "hits": ["junk", {"objectID": "5", "title": "t", "points": 9}],
            "nbHits": 2,
        }
        with contextlib.redirect_stderr(io.StringIO()):
            out = sc.scan_hn(self._cfg(), 0)
        self.assertEqual([c["id"] for c in out], ["hn:5"])


class TestHnQueries(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, sc, "http_json", sc.http_json)
        self.addCleanup(setattr, sc.time, "sleep", time.sleep)
        sc.time.sleep = lambda s: None

    def test_a_double_quote_in_a_keyword_does_not_break_the_phrase(self):
        seen = []

        def http_json(url, **k):
            seen.append(url)
            return {"hits": [], "nbHits": 0}

        sc.http_json = http_json
        sc.scan_hn({"hn": {"tags": ["story"], "min_points": 1}, "keywords": {"b": ['say "hi"']}}, 0)
        self.assertIn("query=%22say+hi%22&", seen[0])

    def test_a_keyword_listed_twice_is_matched_once(self):
        sc.http_json = lambda *a, **k: {
            "hits": [{"objectID": "7", "title": "t", "points": 9}],
            "nbHits": 1,
        }
        cfg = {"hn": {"tags": ["story"], "min_points": 1}, "keywords": {"b": ["ci", "ci"]}}
        out = sc.scan_hn(cfg, 0)
        self.assertEqual(out[0]["matched_keywords"], [["ci", "b"]])


class TestRedditFutureDates(TestRedditDates):
    def test_a_future_dated_entry_is_dropped_and_counted(self):
        future = _iso(self.now + timedelta(days=30))
        self.assertEqual(self._scan(("t3_future", "flaky test rant", future, "")), [])
        self.assertIn("1 entries dropped, dated in the future", self.err)
        self.assertEqual(
            [f["error"] for f in self.failures], ["1 entries dropped, dated in the future"]
        )

    def test_an_entry_within_the_clock_slack_is_kept(self):
        soon = _iso(self.now + timedelta(seconds=sc.FUTURE_SLACK_SECONDS - 60))
        self.assertEqual(self._scan(("t3_soon", "flaky test rant", soon, "")), ["reddit:t3_soon"])
        self.assertEqual(sc.FUTURE_SLACK_SECONDS, 300)


class TestPhTopicNames(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, sc, "gql", sc.gql)

    def test_a_hyphenated_topic_name_matches_its_fit_topic(self):
        post = _ph_post("4", "Builder", "build apps", ["no-code"])
        post["node"]["topics"]["edges"][0]["node"]["name"] = "No-Code"
        sc.gql = _fake_gql([[post]])[0]
        block = dict(PH_BLOCK, fit_topics=["No-Code"], keywords=["unrelated"])
        out = sc.scan_ph({"ph": block}, "t", "2026-10-05T00:00:00Z")
        self.assertEqual([c["id"] for c in out], ["ph:4"])
        self.assertEqual(out[0]["fit_topics_matched"], ["no code"])


class TestXRequest(unittest.TestCase):
    def test_x_asks_for_ten_results_per_query_by_default(self):
        urls = []

        def http_json(url, headers=None, data=None, method=None, timeout=20):
            urls.append(url)
            return {"data": []}

        with (
            mock.patch.object(sc, "http_json", http_json),
            mock.patch.object(sc.time, "sleep", lambda s: None),
        ):
            sc.scan_twitter({"twitter": {"seed_queries": ["a"]}}, "t", "x")
            sc.scan_twitter(
                {"twitter": {"seed_queries": ["a"], "max_results_per_query": 50}}, "t", "x"
            )
        self.assertIn("max_results=10&", urls[0])
        self.assertIn("max_results=50&", urls[1])


class TestScannerBoundaries(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, sc, "http_json", sc.http_json)
        self.addCleanup(setattr, sc.time, "sleep", time.sleep)
        sc.time.sleep = lambda s: None

    def test_the_reddit_future_slack_is_exactly_five_minutes(self):
        now = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
        feed = _atom(
            ("t3_out", "flaky test rant", _iso(now + timedelta(seconds=301)), ""),
            ("t3_in", "flaky test rant", _iso(now + timedelta(seconds=299)), ""),
        )
        cfg = {
            "keywords": {"precise": ["flaky test"]},
            "subreddits": [{"name": "x"}],
            "reddit_min_gap_seconds": 0,
        }
        with (
            mock.patch.object(sc, "_fetch_rss_raw", lambda sub, kind, sleep=None: feed),
            mock.patch.object(sc.time, "time", lambda: now.timestamp()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            out = sc.scan_reddit(cfg, int(now.timestamp()) - 3600)
        self.assertEqual([c["id"] for c in out], ["reddit:t3_in"])

    def test_a_fit_topic_with_extra_spaces_still_matches(self):
        self.addCleanup(setattr, sc, "gql", sc.gql)
        post = _ph_post("4", "Builder", "build apps", ["no-code"])
        post["node"]["topics"]["edges"][0]["node"]["name"] = "No-Code"
        sc.gql = _fake_gql([[post]])[0]
        block = dict(PH_BLOCK, fit_topics=["no  code"], keywords=["unrelated"])
        out = sc.scan_ph({"ph": block}, "t", "2026-10-05T00:00:00Z")
        self.assertEqual([c["id"] for c in out], ["ph:4"])

    def test_a_keyword_empty_without_its_quotes_is_skipped_and_recorded(self):
        seen = []

        def http_json(url, **k):
            seen.append(url)
            return {"hits": [], "nbHits": 0}

        sc.http_json = http_json
        failures = []
        cfg = {"hn": {"tags": ["story"], "min_points": 1}, "keywords": {"b": ['"', "  ", "ci"]}}
        with contextlib.redirect_stderr(io.StringIO()) as err:
            sc.scan_hn(cfg, 0, failures)
        self.assertEqual(len(seen), 1)  # only "ci" is searched
        self.assertEqual([f["request"] for f in failures], ['"', "  "])
        self.assertIn("empty without its quotes", err.getvalue())
        recent = _iso(datetime.now(timezone.utc) - timedelta(hours=1))
        feed = _atom(("t3_a", "nothing about it", recent, ""))
        with (
            mock.patch.object(sc, "_fetch_rss_raw", lambda sub, kind, sleep=None: feed),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            out = sc.scan_reddit(
                {
                    "keywords": {"b": ['"']},
                    "subreddits": [{"name": "x"}],
                    "reddit_min_gap_seconds": 0,
                },
                0,
            )
        self.assertEqual(out, [])  # an empty keyword matches no post

    def test_a_keyword_that_is_not_a_string_is_a_message(self):
        for kw in (None, 5):
            with self.subTest(kw=kw):
                with self.assertRaises(SystemExit) as ctx:
                    sc.all_keywords({"keywords": {"b": [kw]}})
                self.assertIn("must be a string", str(ctx.exception))

    def test_a_hit_with_points_that_are_not_a_number_is_skipped_and_noted(self):
        sc.http_json = lambda *a, **k: {
            "hits": [
                {"objectID": "1", "title": "a", "points": "12"},
                {"objectID": "2", "title": "b", "points": 12},
            ],
            "nbHits": 2,
        }
        failures = []
        with contextlib.redirect_stderr(io.StringIO()):
            out = sc.scan_hn(
                {"hn": {"tags": ["story"], "min_points": 1}, "keywords": {"b": ["ci"]}}, 0, failures
            )
        self.assertEqual([c["id"] for c in out], ["hn:2"])
        self.assertEqual(failures[0]["error"], "1 hits skipped, points not a number")


class TestKeywordShapes(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, sc, "gql", sc.gql)
        self.recent = _iso(datetime.now(timezone.utc) - timedelta(hours=1))

    def _reddit(self, keywords, *entries):
        feed = _atom(*entries)
        with (
            mock.patch.object(sc, "_fetch_rss_raw", lambda sub, kind, sleep=None: feed),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            return sc.scan_reddit(
                {"keywords": keywords, "subreddits": [{"name": "x"}], "reddit_min_gap_seconds": 0},
                0,
            )

    def test_a_layer_that_is_not_a_list_is_a_message(self):
        with self.assertRaises(SystemExit) as ctx:
            sc.all_keywords({"keywords": {"b": "flaky"}})
        self.assertIn("`keywords.b` must be a list", str(ctx.exception))
        with self.assertRaises(SystemExit):
            self._reddit({"b": "flaky"}, ("t3_a", "A cat", self.recent, ""))

    def test_keywords_that_are_not_a_mapping_are_a_message(self):
        with self.assertRaises(SystemExit) as ctx:
            sc.all_keywords({"keywords": ["x"]})
        self.assertIn("`keywords` must be a mapping of layer names", str(ctx.exception))

    def _ph(self, keywords):
        sc.gql = _fake_gql([[_ph_post("9", "Cookbook", "recipes for dinner", ["food"])]])[0]
        block = dict(PH_BLOCK, keywords=keywords, require_fit=True)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            out = sc.scan_ph({"ph": block}, "t", "2026-10-05T00:00:00Z")
        return out, err.getvalue()

    def test_an_empty_product_hunt_keyword_is_skipped_not_matched(self):
        for kws in ([""], ["  "], ['"']):
            with self.subTest(kws=kws):
                out, err = self._ph(kws)
                self.assertEqual(out, [])  # no keyword, no fit topic: not kept
                self.assertIn("is empty without its quotes", err)

    def test_a_product_hunt_keyword_that_is_not_a_string_is_a_message(self):
        with self.assertRaises(SystemExit) as ctx:
            self._ph([3])
        self.assertIn("in `ph.keywords` must be a string", str(ctx.exception))

    def test_quoted_keywords_match_on_reddit_and_product_hunt_as_on_hn(self):
        out = self._reddit({"p": ['"Flaky tests"']}, ("t3_a", "flaky tests again", self.recent, ""))
        self.assertEqual(out[0]["matched_keywords"], [['"Flaky tests"', "p"]])
        sc.gql = _fake_gql([[_ph_post("5", "Radar", "finds flaky tests", ["saas"])]])[0]
        block = dict(PH_BLOCK, keywords=['"flaky tests"'], fit_topics=[])
        with contextlib.redirect_stderr(io.StringIO()):
            ph = sc.scan_ph({"ph": block}, "t", "2026-10-05T00:00:00Z")
        self.assertEqual(ph[0]["matched_keywords"], ['"flaky tests"'])


class TestMatchingWhitespaceAndX(TestMatchingAndRequests):
    """Matching, X reply shapes, Reddit counts and the exit code."""

    def test_whitespace_of_every_kind_and_zero_width_characters(self):
        for title in (
            "flaky\ttests",
            "flaky　tests",
            "flaky​tests",
            "fla‍ky tests",
            "﻿flaky tests",
        ):
            with self.subTest(title=repr(title)):
                out = self._reddit({"p": ["flaky tests"]}, ("t3_a", title, self.recent, ""))
                self.assertEqual(len(out), 1)
        for kw in ("flaky  tests", "flaky\ttests", "flaky tests", "fla‌ky tests"):
            with self.subTest(kw=repr(kw)):
                out = self._reddit({"p": [kw]}, ("t3_b", "Flaky tests again", self.recent, ""))
                self.assertEqual(out[0]["matched_keywords"], [[kw, "p"]])

    def test_a_keyword_twice_in_one_layer_is_reported_once(self):
        out = self._reddit({"p": ["ci", "ci"]}, ("t3_c", "ci again", self.recent, ""))
        self.assertEqual(out[0]["matched_keywords"], [["ci", "p"]])

    def test_an_empty_reddit_keyword_and_an_entry_with_no_id_are_recorded(self):
        failures = []
        self._reddit(
            {"p": ['""', "flaky"]},
            ("", "flaky with no id", self.recent, ""),
            failures=failures,
        )
        self.assertIn(
            {"platform": "reddit", "request": '""', "error": "empty keyword, skipped"}, failures
        )
        self.assertIn("1 entries dropped, no id", [f["error"] for f in failures])

    def test_product_hunt_reports_keywords_as_written(self):
        sc.gql = _fake_gql([[_ph_post("9", "Radar", "finds flaky tests", ["saas"])]])[0]
        self.addCleanup(setattr, sc, "gql", sc.gql)
        block = dict(PH_BLOCK, keywords=["Flaky Tests"], fit_topics=[])
        with contextlib.redirect_stderr(io.StringIO()):
            out = sc.scan_ph({"ph": block}, "t", "2026-10-05T00:00:00Z")
        self.assertEqual(out[0]["matched_keywords"], ["Flaky Tests"])

    def test_x_shapes_that_are_not_what_the_api_documents(self):
        for reply, error in (
            (["a list"], "unexpected response: not a JSON object"),
            ("text", "unexpected response: not a JSON object"),
            ({"data": {"id": "1"}}, "unexpected response: data is not a list"),
            ({"errors": {"message": "one error"}}, "API error: one error"),
            ({"errors": [{"message": "m", "detail": "d"}]}, "API error: m"),
            ({"errors": [{"title": "only a title"}]}, "API error: only a title"),
            ({"errors": ["plain"]}, "API error: 'plain'"),
        ):
            with self.subTest(reply=reply):
                failures = []
                self._x(reply, failures)
                self.assertEqual(failures[0]["error"], error)

    def test_x_items_that_are_not_objects_are_skipped(self):
        failures = []
        out, _ = self._x(
            {"data": ["junk", None, {"text": "no id"}, {"id": "7", "text": "t"}]}, failures
        )
        self.assertEqual([c["id"] for c in out], ["twitter:7"])
        self.assertEqual(
            [f["error"] for f in failures], ["3 entries skipped, not an object or no id"]
        )

    def test_main_exits_zero_when_one_request_was_answered(self):
        d = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, d, True)
        config = os.path.join(d, "c.yaml")
        with open(config, "w") as f:
            f.write("hn: {tags: [story], min_points: 1}\nkeywords: {b: [x, y]}\nsubreddits: []\n")
        calls = []

        def http_json(url, **k):
            calls.append(url)
            if len(calls) == 1:
                raise OSError("reset")
            return {"hits": [], "nbHits": 0}

        sc.http_json = http_json
        argv = ["sc", "--config", config, "--platform", "hn", "--out", d + "/o.json"]
        with (
            mock.patch.object(sys, "argv", argv),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            sc.main()  # no SystemExit
        with open(d + "/o.json") as f:
            self.assertEqual(len(json.load(f)["failures"]), 1)


class TestZeroWidthKeywords(TestMatchingAndRequests):
    """A keyword of zero-width characters only is empty."""

    ZW = ["​", '"​"', "‌", "‍", "﻿", " ​‍ ", '"﻿"']

    def test_the_reported_reddit_case_matches_nothing_and_is_recorded(self):
        failures = []
        out = self._reddit(
            {"p": ["​"]},
            ("t3_k1", "Totally unrelated post about cooking", self.recent, ""),
            failures=failures,
        )
        self.assertEqual(out, [])
        self.assertEqual(
            failures,
            [{"platform": "reddit", "request": "​", "error": "empty keyword, skipped"}],
        )

    def test_every_zero_width_only_keyword_is_empty_on_reddit(self):
        for kw in self.ZW:
            with self.subTest(kw=repr(kw)):
                failures = []
                out = self._reddit(
                    {"p": [kw]},
                    ("t3_k", "Totally unrelated post", self.recent, ""),
                    failures=failures,
                )
                self.assertEqual(out, [])
                self.assertEqual([f["request"] for f in failures], [kw])

    def test_hn_sends_no_query_for_it(self):
        for kw in self.ZW:
            with self.subTest(kw=repr(kw)):
                urls, failures = [], []
                sc.http_json = lambda url, urls=urls, **k: (
                    urls.append(url) or {"hits": [], "nbHits": 0}
                )
                with contextlib.redirect_stderr(io.StringIO()):
                    sc.scan_hn(
                        {"hn": {"tags": ["story"], "min_points": 1}, "keywords": {"b": [kw]}},
                        0,
                        failures,
                    )
                self.assertEqual(urls, [])
                self.assertEqual(failures[0]["error"], "empty keyword, skipped")

    def test_product_hunt_keeps_no_launch_for_it(self):
        for kw in self.ZW:
            with self.subTest(kw=repr(kw)):
                sc.gql = _fake_gql([[_ph_post("9", "Cooking", "unrelated", ["food"])]])[0]
                self.addCleanup(setattr, sc, "gql", sc.gql)
                failures = []
                block = dict(PH_BLOCK, keywords=[kw], fit_topics=[], require_fit=True)
                with contextlib.redirect_stderr(io.StringIO()):
                    out = sc.scan_ph({"ph": block}, "t", "2026-10-05T00:00:00Z", failures)
                self.assertEqual(out, [])
                self.assertIn("empty keyword, skipped", [f["error"] for f in failures])

    def test_a_keyword_with_text_and_zero_width_characters_still_works(self):
        out = self._reddit({"p": ["​flaky‍"]}, ("t3_z", "flaky build", self.recent, ""))
        self.assertEqual(len(out), 1)


class TestXExit(_CliCase):
    """A reply with errors and no data answered nothing."""

    CFG = {"twitter": {"seed_queries": ["q"], "lookback_hours": 24}}

    def _run(self, reply):
        sc.http_json = lambda url, **k: reply
        return self.run_main(self.CFG, "--platform", "twitter", env_text="TWITTER_BEARER_TOKEN=t\n")

    def test_errors_and_no_data_exit_non_zero(self):
        for reply in (
            {"errors": [{"message": "bad"}]},
            {"errors": [{"message": "bad"}], "data": []},
        ):
            with self.subTest(reply=reply):
                out = self._run(reply)
                self.assertEqual(out["failures"][0]["error"], "API error: bad")
                self.assertEqual(
                    self.exit_code, "Every request failed, so there are no candidates."
                )

    def test_errors_beside_data_or_an_empty_answer_exit_zero(self):
        for reply in (
            {"errors": [{"message": "partial"}], "data": [{"id": "1", "text": "t"}]},
            {"meta": {"result_count": 0}},
        ):
            with self.subTest(reply=reply):
                self._run(reply)
                self.assertEqual(self.exit_code, 0)


if __name__ == "__main__":
    unittest.main()


class TestSourcePrivacy(unittest.TestCase):
    def test_reddit_identifies_the_scanner(self):
        self.assertIn("scanner-core", sc.RSS_UA)
        self.assertNotIn("Mozilla", sc.RSS_UA)

    def test_shipped_ph_config_does_not_request_people_details(self):
        path = os.path.join(os.path.dirname(__file__), "../../content-engine/ph.example.yaml")
        with open(path) as stream:
            config = yaml.safe_load(stream)
        self.assertEqual(config["ph"]["detail_fetch_top"], 0)
        with mock.patch.object(sc, "gql") as request:
            sc.fetch_details(config, "fake-token", [{"ph_id": "1"}])
        request.assert_not_called()
