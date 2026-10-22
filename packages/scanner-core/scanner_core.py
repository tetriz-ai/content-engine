#!/usr/bin/env python3
# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
"""
scanner_core.py — fetch candidate posts from Hacker News, Reddit, Product
Hunt and X/Twitter that match a keyword config.

Each platform has one function (scan_hn, scan_reddit, scan_ph plus
fetch_details, scan_twitter) that returns normalized candidate dicts for a
time window. Every result carries the platform's own id, so a caller can
dedupe on it rather than on the URL.

The module keeps no state about posts. Its only module-level state is the
Reddit request pacing: the gap between requests and the time of the last
one. Every call returns the candidates inside the window, up to each
platform's cap (50 Hacker News hits per keyword, 100 entries per Reddit
feed, one page per X query), and deciding what's new is the caller's job.
It only fetches; judging and drafting belong to the caller.

Product Hunt uses the official GraphQL API only, for posts, voters and
commenters.

The only external dependency is PyYAML, and only the CLI needs it.
"""

import argparse
import base64
import html
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

# ------------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------------

# Sent to HN's Algolia API and Product Hunt. Reddit's RSS gets RSS_UA below.
USER_AGENT = "scanner-core:0.1"


def load_env(path):
    """Minimal .env loader (no python-dotenv dependency)."""
    if not os.path.exists(path):
        return {}
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def http_json(url, headers=None, data=None, method=None, timeout=20):
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", USER_AGENT)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# One Algolia request per keyword (a design choice), so a keyword with more
# matches in the window than this returns the newest-ranked ones only, and
# the overflow is recorded in `failures`.
HN_HITS_PER_KEYWORD = 50
# Reddit's public feeds serve at most this many entries (a platform limit).
REDDIT_FEED_LIMIT = 100
# A Reddit entry dated more than this far ahead of now is dropped and
# counted, as the competitor blog scan does: a clock a few minutes off is
# tolerated, a future date is not a fresh post.
FUTURE_SLACK_SECONDS = 300


def keyword_text(kw):
    """The text a keyword matches on: its `"` removed (they would end the HN
    phrase query early) and surrounding whitespace trimmed."""
    return kw.replace('"', "").strip()


# Zero-width characters: a zero-width space separates words; a zero-width
# joiner, non-joiner or byte-order mark is nothing.
ZERO_WIDTH = {0x200B: " ", 0x200C: None, 0x200D: None, 0xFEFF: None}


def match_text(text):
    """`text` lower-cased with every run of whitespace (line breaks, tabs,
    no-break and ideographic spaces, zero-width spaces included) made one
    space, as Reddit and Product Hunt keywords and the posts they are
    matched against are compared."""
    return " ".join(str(text).translate(ZERO_WIDTH).split()).lower()


def _usable_keywords(kws, where, failures=None, platform=None):
    """The keywords of one list (`where` names it in messages). A list that
    is not a list, or a keyword that is not a string, is a config error. A
    keyword empty once quotes, whitespace and zero-width characters go
    (`match_text(keyword_text(kw))`) is skipped with a notice and,
    when `platform` is given and `failures` is a list, recorded there."""
    if kws is None:
        return []
    if not isinstance(kws, list):
        sys.exit("`%s` must be a list of keywords, not %s." % (where, type(kws).__name__))
    out = []
    for kw in kws:
        if not isinstance(kw, str):
            sys.exit("Keyword %r in `%s` must be a string; quote it in the config." % (kw, where))
        if not match_text(keyword_text(kw)):
            print(
                "  [config] keyword %r in `%s` is empty without its quotes; skipped" % (kw, where),
                file=sys.stderr,
            )
            if platform:
                _record_failure(failures, platform, kw, "empty keyword, skipped")
            continue
        out.append(kw)
    return out


def all_keywords(cfg, failures=None, platform=None):
    """Flat list of (keyword, layer) across all configured keyword layers.
    `keywords` must be a mapping of layer names to lists; each list is
    checked by `_usable_keywords`."""
    layers = cfg.get("keywords") or {}
    if not isinstance(layers, dict):
        sys.exit(
            "`keywords` must be a mapping of layer names to keyword lists, not %s."
            % type(layers).__name__
        )
    out = []
    for layer, kws in layers.items():
        for kw in _usable_keywords(kws, "keywords.%s" % layer, failures, platform):
            out.append((kw, layer))
    return out


# Requests made in this process: how many were answered and how many failed.
# main() exits 1 when requests failed and none was answered.
REQUESTS = {"ok": 0, "failed": 0}


def _request_done(ok):
    REQUESTS["ok" if ok else "failed"] += 1


def _record_failure(failures, platform, what, error):
    """Append one failed request to `failures` when the caller passed a list."""
    if failures is not None:
        failures.append({"platform": platform, "request": what, "error": str(error)})


# ------------------------------------------------------------------------
# Hacker News (Algolia public API, no auth)
# ------------------------------------------------------------------------


def scan_hn(cfg, since_ts, failures=None):
    """Search HN for every keyword. Each failed query is printed and, when
    `failures` is a list, appended to it."""
    hn = cfg["hn"]
    tags = "(" + ",".join(hn["tags"]) + ")"  # OR across story/show_hn/ask_hn
    min_points = hn["min_points"]
    by_id: dict = {}  # objectID -> candidate (accumulates matched keywords)

    for kw, layer in all_keywords(cfg, failures, "hn"):
        # Phrase-quote + disable typo tolerance for EVERY keyword, not just
        # multi-word ones — quoting alone still lets Algolia stem/fuzz a
        # single word (e.g. unquoted "flaky" matching "flakes").
        # A `"` inside the keyword would end the phrase early, so it goes.
        query = '"%s"' % keyword_text(kw)
        params = urllib.parse.urlencode(
            {
                "query": query,
                "tags": tags,
                "advancedSyntax": "true",
                "typoTolerance": "false",
                "hitsPerPage": HN_HITS_PER_KEYWORD,
            }
        )
        url = (
            "https://hn.algolia.com/api/v1/search?"
            + params
            + "&numericFilters=created_at_i>%d" % since_ts
        )
        try:
            data = http_json(url)
        except Exception as e:
            print("  [hn] query '%s' failed: %s" % (kw, e), file=sys.stderr)
            _record_failure(failures, "hn", kw, e)
            _request_done(False)
            continue
        hits = data.get("hits") if isinstance(data, dict) else None
        if not isinstance(hits, list):
            bad = "unexpected response: no list of hits"
            print("  [hn] query '%s' failed: %s" % (kw, bad), file=sys.stderr)
            _record_failure(failures, "hn", kw, bad)
            _request_done(False)
            continue
        _request_done(True)
        nb_hits = data.get("nbHits")
        reason: Optional[str] = None
        if isinstance(nb_hits, int) and nb_hits > len(hits):
            reason = "truncated: %d of %d hits" % (len(hits), nb_hits)
        elif not isinstance(nb_hits, int) and len(hits) >= HN_HITS_PER_KEYWORD:
            reason = "possibly truncated: %d hits and no total" % len(hits)
        if reason:
            print("  [hn] query '%s' %s" % (kw, reason), file=sys.stderr)
            _record_failure(failures, "hn", kw, reason)
        bad_points = 0
        for h in hits:
            if not isinstance(h, dict):
                continue
            oid = h.get("objectID")
            if not oid:
                continue
            htags = h.get("_tags") or []
            if "show_hn" in htags:
                ctype = "show_hn"
            elif "ask_hn" in htags:
                ctype = "ask_hn"
            else:
                ctype = "story"
            points = h.get("points") or 0
            if not isinstance(points, int) or isinstance(points, bool):
                bad_points += 1
                continue
            if points < min_points:
                continue
            if oid not in by_id:
                by_id[oid] = {
                    "id": "hn:%s" % oid,
                    "platform": "hn",
                    "type": ctype,
                    "title": h.get("title") or h.get("story_title") or "",
                    "url": "https://news.ycombinator.com/item?id=%s" % oid,
                    "external_url": h.get("url"),
                    "text_excerpt": (h.get("story_text") or h.get("comment_text") or "")[:600],
                    "points": points,
                    "num_comments": h.get("num_comments") or 0,
                    "author": h.get("author"),
                    "created_at": h.get("created_at"),
                    "matched_keywords": [],
                }
            mk = by_id[oid]["matched_keywords"]
            if [kw, layer] not in mk:
                mk.append([kw, layer])
        if bad_points:
            note = "%d hits skipped, points not a number" % bad_points
            print("  [hn] query '%s': %s" % (kw, note), file=sys.stderr)
            _record_failure(failures, "hn", kw, note)
        time.sleep(0.2)  # be polite to Algolia

    return list(by_id.values())


# ------------------------------------------------------------------------
# Reddit (public RSS, no auth)
# ------------------------------------------------------------------------

ATOM = "{http://www.w3.org/2005/Atom}"
# Identify this client honestly. An access denial is reported as a source failure;
# never switch to a browser identity to bypass it.
RSS_UA = "scanner-core/0.1 (+https://github.com/tetriz-ai/content-engine)"


def _strip_html(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s or "")).strip()


def _iso_to_ts(s):
    """Unix time for an ISO 8601 string; a trailing Z and a missing offset
    both mean UTC. A `+0000` offset and fractional seconds of any length are
    normalised first, so Python 3.9 reads them. None when the string is
    missing or unparseable."""
    if not s:
        return None
    v = s.strip()
    if v.endswith(("Z", "z")):
        v = v[:-1] + "+00:00"
    v = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", v)
    v = re.sub(r"\.(\d+)", lambda m: "." + (m.group(1) + "000000")[:6], v, count=1)
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _feed_body(body):
    """The body without a UTF-8 BOM and leading whitespace, if it starts like
    an XML feed: an XML declaration, <rss, <feed or <rdf:RDF, after any
    leading comments and DOCTYPE. Otherwise None."""
    b = body.lstrip()
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:].lstrip()
    head = b
    while True:
        if head.startswith(b"<!--"):
            end = head.find(b"-->")
            if end < 0:
                return None
            head = head[end + 3 :].lstrip()
        elif head[:9].upper() == b"<!DOCTYPE":
            end = head.find(b">")
            if end < 0:
                return None
            head = head[end + 1 :].lstrip()
        else:
            break
    return b if head.startswith((b"<?xml", b"<rss", b"<feed", b"<rdf:RDF")) else None


class _NotRealFeed(Exception):
    """Raised when Reddit returns 200 but the body isn't an Atom feed."""


# Reddit's unauthenticated RSS budget is far smaller than its old documented
# 10 req/min: measured live (Oct 2026), one IP gets roughly one request per
# ~10s — anything faster comes back 429, and every 429'd retry spends the
# same budget again. So every Reddit request is spaced at least this far
# apart, and a 429 waits out Reddit's own x-ratelimit-reset before retrying.
# Override per config with `reddit_min_gap_seconds`.
REDDIT_MIN_GAP_SECONDS = 10.0
REDDIT_MAX_RESET_WAIT_SECONDS = 90.0  # never trust a reset header beyond this
_reddit_gap = REDDIT_MIN_GAP_SECONDS
_reddit_last_request = None
_reddit_deadline: ContextVar[Optional[float]] = ContextVar("reddit_deadline", default=None)


class _RedditBudgetExceeded(TimeoutError):
    pass


def _reddit_remaining():
    deadline = _reddit_deadline.get()
    if deadline is None:
        return 20.0
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise _RedditBudgetExceeded("Reddit scan time budget exhausted; feed not completed")
    return remaining


def _reddit_sleep(seconds, sleep):
    if _reddit_deadline.get() is not None and seconds >= _reddit_remaining():
        raise _RedditBudgetExceeded("Wait would exceed Reddit scan time budget; feed not completed")
    sleep(seconds)


def _reddit_budget(cfg):
    budget = cfg.get("reddit_budget_seconds", 240)
    if (
        isinstance(budget, bool)
        or not isinstance(budget, (int, float))
        or not math.isfinite(budget)
        or not 1 <= budget <= 480
    ):
        sys.exit("reddit_budget_seconds must be a finite number from 1 to 480 seconds")
    return budget


def _reddit_throttle(now=None, sleep=time.sleep):
    """Block until at least _reddit_gap seconds since the last Reddit request."""
    global _reddit_last_request
    now = now or time.monotonic
    _reddit_remaining()
    if _reddit_last_request is not None:
        wait = _reddit_gap - (now() - _reddit_last_request)
        if wait > 0:
            _reddit_sleep(wait, sleep)
    _reddit_last_request = now()


def _reddit_429_wait(headers):
    """Seconds to wait after a 429, from Reddit's own headers.

    x-ratelimit-reset (seconds until the window resets) or Retry-After,
    whichever is larger, plus 1s of slack — never less than the normal gap,
    never more than REDDIT_MAX_RESET_WAIT_SECONDS."""
    waits = []
    for name in ("x-ratelimit-reset", "Retry-After"):
        try:
            waits.append(float(headers.get(name)))
        except (TypeError, ValueError):
            pass
    wait = max(waits) + 1 if waits else _reddit_gap
    return min(max(wait, _reddit_gap), REDDIT_MAX_RESET_WAIT_SECONDS)


REDDIT_MAX_FEED_BYTES = 8 * 1024 * 1024


def _reddit_fetch_worker():
    """Private subprocess protocol; only the parent handles retries and the scan budget."""
    request = json.load(sys.stdin)
    result: dict
    try:
        response = urllib.request.urlopen(
            urllib.request.Request(request["url"], headers={"User-Agent": RSS_UA}),
            timeout=request["timeout"],
        )
        try:
            body = response.read(REDDIT_MAX_FEED_BYTES + 1)
            if len(body) > REDDIT_MAX_FEED_BYTES:
                result = {"error": "feed exceeds the 8 MiB response limit"}
            else:
                result = {
                    "body": base64.b64encode(body).decode("ascii"),
                    "content_type": response.headers.get("Content-Type", ""),
                }
        finally:
            response.close()
    except urllib.error.HTTPError as error:
        result = {
            "status": error.code,
            "headers": {
                key: error.headers[key]
                for key in ("Retry-After", "x-ratelimit-reset")
                if error.headers and error.headers.get(key) is not None
            },
        }
        if error.fp is not None:
            error.close()
    except Exception as error:
        result = {"error": type(error).__name__}
    print(json.dumps(result))


def _reddit_fetch_once(url):
    if _reddit_deadline.get() is None:
        # Direct low-level callers retain the ordinary urllib transport.
        response = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": RSS_UA}), timeout=20
        )
        return response.read(), response.headers.get("Content-Type", "")
    remaining = _reddit_remaining()
    try:
        # subprocess.run kills AND waits for the child on timeout, including DNS,
        # connect, redirects and header parsing. No transport outlives the budget.
        run = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--reddit-fetch-worker"],
            input=json.dumps({"url": url, "timeout": min(20.0, remaining)}),
            text=True,
            capture_output=True,
            timeout=remaining,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise _RedditBudgetExceeded(
            "Reddit scan time budget exhausted; fetch worker stopped"
        ) from error
    _reddit_remaining()
    if run.returncode:
        raise RuntimeError("Reddit fetch worker failed (exit %d)" % run.returncode)
    result = json.loads(run.stdout)
    if "status" in result:
        raise urllib.error.HTTPError(
            url, result["status"], "Reddit request failed", result["headers"], None
        )
    if "error" in result:
        raise RuntimeError("Reddit fetch failed: %s" % result["error"])
    return base64.b64decode(result["body"], validate=True), result["content_type"]


def _fetch_rss_raw(sub, kind, sleep=time.sleep):
    """Fetch one feed with retry + host fallback for Reddit's intermittent
    403s, its 429 rate limit, AND its interstitial HTML (200 OK,
    login/consent wall)."""
    hosts = ["https://www.reddit.com", "https://old.reddit.com"]
    last: Optional[Exception] = None
    for attempt in range(3):
        host = hosts[attempt % len(hosts)]
        url = "%s/r/%s/%s/.rss?limit=%d" % (host, sub, kind, REDDIT_FEED_LIMIT)
        _reddit_throttle(sleep=sleep)
        try:
            body, ctype = _reddit_fetch_once(url)
            feed = _feed_body(body)
            if "xml" not in ctype:
                last = _NotRealFeed(
                    "%s answered with content-type %r, not an XML feed" % (host, ctype)
                )
                continue
            if feed is None:
                last = _NotRealFeed(
                    "%s answered with a body that is not an XML feed "
                    "(starts %r)" % (host, body.lstrip()[:40])
                )
                continue
            return feed
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429:
                wait = _reddit_429_wait(e.headers or {})
                if attempt < 2:
                    print(
                        "  [reddit] r/%s %s rate-limited, waiting %ds before retry"
                        % (sub, kind, wait),
                        file=sys.stderr,
                    )
                    _reddit_sleep(wait, sleep)
                continue
            if e.code == 403:
                continue
            raise
    assert last is not None  # every attempt either returns or sets it
    raise last


def reddit_rss_entries(sub, kind):
    """Fetch and parse one subreddit Atom feed (kind = 'new' or 'hot').
    Raises _NotRealFeed when the document is XML but not an Atom feed."""
    feed = ET.fromstring(_fetch_rss_raw(sub, kind))
    if feed.tag != ATOM + "feed":
        raise _NotRealFeed("the body is %s, not an Atom feed" % feed.tag)
    out = []
    for e in feed.findall(ATOM + "entry"):

        def txt(tag, e=e):
            el = e.find(ATOM + tag)
            return el.text if el is not None else None

        link_el = e.find(ATOM + "link")
        author_el = e.find(ATOM + "author")
        author = None
        if author_el is not None:
            n = author_el.find(ATOM + "name")
            author = n.text if n is not None else None
        created = txt("published") or txt("updated")
        out.append(
            {
                "id": txt("id"),  # reddit fullname, e.g. t3_abc
                "title": (txt("title") or "").strip(),
                "link": link_el.get("href") if link_el is not None else None,
                "text": _strip_html(txt("content")),
                "author": author,
                "created_at": created,
                "created_ts": _iso_to_ts(created),
            }
        )
    return out


def scan_reddit(cfg, since_ts, failures=None):
    """Scan with a per-call deadline; retain completed feeds and record every unfinished one."""
    budget = _reddit_budget(cfg)
    token = _reddit_deadline.set(time.monotonic() + budget)
    try:
        return _scan_reddit(cfg, since_ts, failures)
    finally:
        _reddit_deadline.reset(token)


def _scan_reddit(cfg, since_ts, failures=None):
    """Read new and hot for every subreddit and keep keyword matches inside
    the window. An entry with no parseable date, or dated in the future, is
    dropped and counted, never assumed fresh. Each failed feed is printed
    and, when `failures` is a list, appended to it."""
    global _reddit_gap
    _reddit_gap = float(cfg.get("reddit_min_gap_seconds", REDDIT_MIN_GAP_SECONDS))
    # Matched without their quotes, as the HN query uses them, and reported
    # as written with their layer: a keyword in two layers is reported twice.
    pairs = [
        (kw, layer, match_text(keyword_text(kw)))
        for kw, layer in all_keywords(cfg, failures, "reddit")
    ]
    by_id = {}
    n_feeds = 2 * len(cfg["subreddits"])
    print(
        "  [reddit] %d feeds, spaced %ds apart for Reddit's rate limit (~%ds)"
        % (n_feeds, _reddit_gap, n_feeds * _reddit_gap),
        file=sys.stderr,
    )
    exhausted = False
    for sub in cfg["subreddits"]:
        entries = []
        for kind in ("new", "hot"):
            if exhausted:
                note = "Reddit scan time budget exhausted; feed not attempted"
                print("  [reddit] r/%s %s: %s" % (sub["name"], kind, note), file=sys.stderr)
                _record_failure(failures, "reddit", "r/%s %s" % (sub["name"], kind), note)
                continue
            try:
                _reddit_remaining()
                entries += reddit_rss_entries(sub["name"], kind)
                _request_done(True)
            except Exception as e:
                if isinstance(e, _RedditBudgetExceeded):
                    exhausted = True
                print("  [reddit] r/%s %s rss failed: %s" % (sub["name"], kind, e), file=sys.stderr)
                _record_failure(failures, "reddit", "r/%s %s" % (sub["name"], kind), e)
                _request_done(False)
        undated, future = set(), set()  # ids, so new and hot count a post once
        no_id = set()  # (title, link), so new and hot count an entry once
        latest = time.time() + FUTURE_SLACK_SECONDS
        for en in entries:
            fid = en["id"]
            if not fid:
                no_id.add((en["title"], en["link"]))
                continue
            if fid in by_id:
                continue
            if en["created_ts"] is None:
                undated.add(fid)
                continue
            if en["created_ts"] > latest:
                future.add(fid)
                continue
            if en["created_ts"] < since_ts:
                continue
            hay = match_text(en["title"] + " " + en["text"])
            matched = []
            for kw, layer, needle in pairs:
                if needle in hay and [kw, layer] not in matched:
                    matched.append([kw, layer])
            if not matched:
                continue
            by_id[fid] = {
                "id": "reddit:%s" % fid,
                "platform": "reddit",
                "subreddit": sub["name"],
                "type": "post",
                "title": en["title"],
                "url": en["link"],
                "external_url": None,
                "text_excerpt": en["text"][:600],
                "score": None,  # not exposed via RSS
                "num_comments": None,  # not exposed via RSS
                "author": en["author"],
                "created_at": en["created_at"],
                "matched_keywords": matched,
            }
        for count, why in (
            (len(undated), "no parseable date"),
            (len(future), "dated in the future"),
            (len(no_id), "no id"),
        ):
            if count:
                note = "%d entries dropped, %s" % (count, why)
                print("  [reddit] r/%s: %s" % (sub["name"], note), file=sys.stderr)
                _record_failure(failures, "reddit", "r/%s" % sub["name"], note)
    return list(by_id.values())


# ------------------------------------------------------------------------
# Product Hunt (GraphQL API v2, needs a developer token — no scraping)
# ------------------------------------------------------------------------

PH_API = "https://api.producthunt.com/v2/api/graphql"
REDACTED = "[REDACTED]"
PH_TZ = "America/Los_Angeles"

LIST_QUERY = """
query($topic: String!, $postedAfter: DateTime!, $first: Int!, $after: String) {
  posts(order: NEWEST, topic: $topic, postedAfter: $postedAfter, first: $first, after: $after) {
    pageInfo { hasNextPage endCursor }
    edges { node {
      id name tagline description url website votesCount commentsCount createdAt
      topics(first: 6) { edges { node { name slug } } }
      makers { id name username headline url twitterUsername websiteUrl }
    } }
  }
}
"""

DETAIL_QUERY = """
query($id: ID!, $voters: Int!, $comments: Int!) {
  post(id: $id) {
    id
    votes(first: $voters) { edges { node { user { id name username url } } } }
    comments(first: $comments) { edges { node { body votesCount user { id name username url } } } }
  }
}
"""


def gql(token, query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(PH_API, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Authorization", "Bearer %s" % token)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            sys.exit(
                "PH API rejected the token (401). Check your PH_API_TOKEN — "
                "regenerate it at https://www.producthunt.com/v2/oauth/applications"
            )
        if e.code == 429:
            sys.exit(
                "PH API rate limit hit (429). The API uses a complexity "
                "budget per 15 min — wait and re-run, or lower "
                "ph.topics / ph.max_pages / ph.detail_fetch_top in config."
            )
        raise
    if data.get("errors"):
        raise RuntimeError("PH GraphQL error: %s" % json.dumps(data["errors"])[:500])
    return data["data"]


def ph_day_start(now=None):
    """Start of the CURRENT Product Hunt day, as a UTC datetime.

    PH's leaderboard resets at 12:01 AM Pacific, so "everything on today's
    board" is a fresher window than a rolling N-hour lookback. Returns
    (utc_datetime, note) or (None, reason) when the tz database is
    unavailable — the caller then falls back to a rolling lookback window.
    """
    try:
        tz = ZoneInfo(PH_TZ)
    except Exception as exc:
        return None, "no tz database for %s (%s)" % (PH_TZ, exc)
    now = (now or datetime.now(timezone.utc)).astimezone(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(timezone.utc), "PH day starting %s PT" % start.strftime("%Y-%m-%d")


def _clean_url(url):
    """Strip query/fragment from PH URLs (the API appends utm params)."""
    return url.split("?")[0].split("#")[0].rstrip("/") if url else url


def _user(u):
    if not u:
        return None
    username = u.get("username")
    return {
        "name": u.get("name"),
        "username": username,
        "ph_profile": _clean_url(u.get("url"))
        or ("https://www.producthunt.com/@%s" % username if username else None),
    }


def scan_ph(cfg, token, since_iso, failures=None):
    """List launches across configured topics since `since_iso`. No
    scraping — GraphQL only. A failed page is printed and, when `failures`
    is a list, appended to it; that topic stops there and the next topic
    runs. A rejected token or the rate limit still stops the scan."""
    ph = cfg["ph"]
    # Checked before anything is fetched, so a config error costs no request.
    kws = _usable_keywords(ph.get("keywords"), "ph.keywords", failures, "ph")  # reported as written
    by_id = {}
    for topic in ph["topics"]:
        after = None
        for page in range(1, ph["max_pages"] + 1):
            try:
                data = gql(
                    token,
                    LIST_QUERY,
                    {
                        "topic": topic,
                        "postedAfter": since_iso,
                        "first": ph["posts_per_page"],
                        "after": after,
                    },
                )
            except SystemExit:
                raise
            except Exception as e:
                print("  [ph] topic %s page %d failed: %s" % (topic, page, e), file=sys.stderr)
                _record_failure(failures, "ph", "topic %s page %d" % (topic, page), e)
                _request_done(False)
                break
            _request_done(True)
            posts = data["posts"]
            for edge in posts["edges"]:
                n = edge["node"]
                pid = n["id"]
                topics = [t["node"]["name"] for t in n["topics"]["edges"]]
                if pid not in by_id:
                    makers = []
                    for m in n.get("makers") or []:
                        mu = _user(m)
                        mu["headline"] = m.get("headline")
                        mu["twitter"] = m.get("twitterUsername")
                        mu["website"] = m.get("websiteUrl")
                        makers.append(mu)
                    by_id[pid] = {
                        "id": "ph:%s" % pid,
                        "ph_id": pid,
                        "platform": "ph",
                        "name": n["name"],
                        "tagline": n.get("tagline") or "",
                        "description_excerpt": (n.get("description") or "")[:600],
                        "ph_url": _clean_url(n["url"]),
                        "website": n.get("website"),
                        "votes_count": n.get("votesCount") or 0,
                        "comments_count": n.get("commentsCount") or 0,
                        "created_at": n.get("createdAt"),
                        "topics": topics,
                        "matched_keywords": [],
                        "makers": makers,
                        "top_voters": [],
                        "top_commenters": [],
                        "discussion": [],
                    }
            if not posts["pageInfo"]["hasNextPage"]:
                break
            after = posts["pageInfo"]["endCursor"]
            time.sleep(0.5)  # be polite to the complexity budget
        time.sleep(0.5)

    def norm_topic(t):
        # "No-Code", "no-code" and "no code" are one topic, in the config
        # and in Product Hunt's topic names alike.
        return " ".join(str(t).lower().replace("-", " ").split())

    fit_topics = {norm_topic(t) for t in (ph.get("fit_topics") or [])}
    require_fit = ph.get("require_fit", False)
    out = []
    for c in by_id.values():
        if c["votes_count"] < ph.get("min_votes", 0):
            continue
        hay = match_text(
            " ".join([c["name"], c["tagline"], c["description_excerpt"], " ".join(c["topics"])])
        )
        c["matched_keywords"] = [k for k in kws if match_text(keyword_text(k)) in hay]
        topics_lower = {norm_topic(t) for t in c["topics"]}
        c["fit_topics_matched"] = sorted(topics_lower & fit_topics)
        if require_fit and not (c["matched_keywords"] or c["fit_topics_matched"]):
            continue
        out.append(c)
    return out


def fetch_details(cfg, token, candidates, failures=None):
    """Voters + commenters for the top candidates only (rate-limit budget).
    Official GraphQL API only. Each failed detail fetch is printed and, when
    `failures` is a list, appended to it. A rejected token or the rate limit
    stops detail fetching; the candidates keep what they have."""
    ph = cfg["ph"]
    for c in candidates[: ph["detail_fetch_top"]]:
        try:
            data = gql(
                token,
                DETAIL_QUERY,
                {
                    "id": c["ph_id"],
                    "voters": ph["voters_limit"],
                    "comments": ph["comments_limit"],
                },
            )
        except SystemExit as e:
            print("  [ph] detail fetching stopped: %s" % e, file=sys.stderr)
            _record_failure(failures, "ph", "details from %s on" % c["name"], e)
            _request_done(False)
            break
        except Exception as e:
            print("  [ph] detail fetch failed for %s: %s" % (c["name"], e), file=sys.stderr)
            _record_failure(failures, "ph", "details for %s" % c["name"], e)
            _request_done(False)
            continue
        _request_done(True)
        post = data.get("post") or {}
        maker_usernames = {m["username"] for m in c["makers"] if m.get("username")}
        redacted = 0
        seen_users = set()
        for edge in (post.get("votes") or {}).get("edges", []):
            u = _user(edge["node"].get("user"))
            if u and u["username"] == REDACTED:
                redacted += 1
                continue
            if not u or u["username"] in maker_usernames or u["username"] in seen_users:
                continue
            seen_users.add(u["username"])
            c["top_voters"].append(u)
        seen_users = set()
        for edge in (post.get("comments") or {}).get("edges", []):
            node = edge["node"]
            u = _user(node.get("user"))
            body = (node.get("body") or "").strip()
            if body:
                c["discussion"].append(
                    {
                        "body": body[:1200],
                        "votes": node.get("votesCount") or 0,
                        "author": None if (not u or u["username"] == REDACTED) else u["username"],
                    }
                )
            if u and u["username"] == REDACTED:
                redacted += 1
                continue
            if not u or u["username"] in maker_usernames or u["username"] in seen_users:
                continue
            seen_users.add(u["username"])
            u["comment_excerpt"] = body[:200]
            c["top_commenters"].append(u)
        c["pool_redacted"] = redacted
        time.sleep(0.5)


# ------------------------------------------------------------------------
# Twitter/X (API v2, needs a paid bearer token — no free tier since Feb
# 2026). Optional, off unless a caller's config has a `twitter:` block.
# ------------------------------------------------------------------------

TWITTER_API = "https://api.twitter.com/2/tweets/search/recent"
# The request's start_time stays this far inside the 7-day limit, so the time
# a request takes to send cannot push it past the limit.
TWITTER_LOOKBACK_MARGIN = timedelta(minutes=5)
TWITTER_MAX_LOOKBACK_HOURS = 168  # 7 days — "recent search" (standard tier)
# cannot go further back than this; only
# the paid full-archive search product
# can, and this module doesn't implement
# that endpoint (different auth scope,
# different cost tier).


def _x_error_text(err):
    """One X API error as text: its message, else its detail, else its title,
    else the error itself."""
    if isinstance(err, dict):
        for key in ("message", "detail", "title"):
            if err.get(key):
                return str(err[key])
    return repr(err)


def scan_twitter(cfg, token, since_iso, failures=None):
    """Search recent tweets (API v2 `tweets/search/recent`) for each
    configured query. One page per query (up to 100 results), no
    pagination: a query with more results in the window returns only the
    first page.

    Standard-tier `recent search` only covers the last 7 days; further back
    needs the paid full-archive search product, a different endpoint this
    module doesn't call. The API rejects an older `since_iso` with an HTTP
    error, which is handled like any failed query: printed, recorded in
    `failures` when it is a list, and the next query runs.
    """
    tw = cfg["twitter"]
    by_id: dict = {}
    for query in tw["seed_queries"]:
        params = urllib.parse.urlencode(
            {
                "query": query,
                "max_results": tw.get("max_results_per_query", 10),
                "tweet.fields": "created_at,public_metrics,author_id,lang",
                "start_time": since_iso,
            }
        )
        url = TWITTER_API + "?" + params
        try:
            data = http_json(url, headers={"Authorization": "Bearer %s" % token})
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(
                    "  [twitter] rate limited on query '%s' — X's pay-per-use "
                    "tier still has a requests-per-15-min cap separate from "
                    "the monthly read cap" % query,
                    file=sys.stderr,
                )
            elif e.code == 401:
                print(
                    "  [twitter] query '%s' failed: 401 — check the bearer "
                    "token is valid and has read access" % query,
                    file=sys.stderr,
                )
            else:
                print("  [twitter] query '%s' failed: %s" % (query, e), file=sys.stderr)
            _record_failure(failures, "twitter", query, e)
            _request_done(False)
            continue
        except Exception as e:
            print("  [twitter] query '%s' failed: %s" % (query, e), file=sys.stderr)
            _record_failure(failures, "twitter", query, e)
            _request_done(False)
            continue
        if not isinstance(data, dict):
            bad = "unexpected response: not a JSON object"
            print("  [twitter] query '%s' failed: %s" % (query, bad), file=sys.stderr)
            _record_failure(failures, "twitter", query, bad)
            _request_done(False)
            continue
        errors = data.get("errors") or []
        for err in errors if isinstance(errors, list) else [errors]:
            detail = _x_error_text(err)
            print("  [twitter] query '%s' error: %s" % (query, detail), file=sys.stderr)
            _record_failure(failures, "twitter", query, "API error: %s" % detail)
        tweets = data.get("data")
        if tweets is not None and not isinstance(tweets, list):
            bad = "unexpected response: data is not a list"
            print("  [twitter] query '%s' failed: %s" % (query, bad), file=sys.stderr)
            _record_failure(failures, "twitter", query, bad)
            _request_done(False)
            continue
        # A reply with errors and no data answered nothing.
        _request_done(not (errors and not tweets))
        meta = data.get("meta")
        if isinstance(meta, dict) and meta.get("next_token"):
            note = "truncated: more results than one page"
            print("  [twitter] query '%s' %s" % (query, note), file=sys.stderr)
            _record_failure(failures, "twitter", query, note)
        unusable = 0
        for t in tweets or []:
            tid = t.get("id") if isinstance(t, dict) else None
            if not tid:
                unusable += 1
                continue
            if tid in by_id:
                mk = by_id[tid]["matched_keywords"]
                if [query, "search_query"] not in mk:
                    mk.append([query, "search_query"])
                continue
            metrics = t.get("public_metrics") or {}
            by_id[tid] = {
                "id": "twitter:%s" % tid,
                "platform": "twitter",
                "url": "https://x.com/i/web/status/%s" % tid,
                "text_excerpt": (t.get("text") or "")[:600],
                "raw_metric": {
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "replies": metrics.get("reply_count", 0),
                    "quotes": metrics.get("quote_count", 0),
                },
                "published_at": t.get("created_at"),
                "fetched_at": datetime.now(timezone.utc).date().isoformat(),
                "matched_keywords": [[query, "search_query"]],
            }
        if unusable:
            note = "%d entries skipped, not an object or no id" % unusable
            print("  [twitter] query '%s': %s" % (query, note), file=sys.stderr)
            _record_failure(failures, "twitter", query, note)
        time.sleep(0.5)  # be polite within the pay-per-use rate window
    return list(by_id.values())


# ------------------------------------------------------------------------
# CLI — a thin wrapper that keeps no state.
# ------------------------------------------------------------------------


def _load_yaml(path):
    try:
        import yaml
    except ImportError:
        sys.exit("Missing dependency: PyYAML. Install it with:\n  pip install -r requirements.txt")
    if not os.path.exists(path):
        sys.exit(
            "Config file not found: %s\n"
            "  -> check the path, and that you're running this from the repo root "
            "(paths in config.yaml are repo-root-relative)." % path
        )
    with open(path) as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        sys.exit("Config file %s is empty or not a YAML mapping." % path)
    return cfg


def _twitter_block(cfg):
    """The `twitter:` block, at the top level or under `scan:` (the shape
    content-engine's config.yaml uses). Both at once is an error, since
    either could be the one meant, and so is a `scan:` that is not a mapping."""
    scan = cfg.get("scan") or {}
    if not isinstance(scan, dict):
        sys.exit("`scan` in --config must be a mapping, not %r." % (scan,))
    top, nested = cfg.get("twitter"), scan.get("twitter")
    if top and nested:
        sys.exit(
            "`twitter` is set both at the top level and under `scan:` in --config; "
            "keep one of them."
        )
    return top or nested


def _run_hn_reddit(cfg, args, failures):
    lookback_hours = cfg.get("lookback_hours", 48)
    since_ts = int((datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).timestamp())
    results = {"generated_at": datetime.now(timezone.utc).isoformat(), "candidates": []}
    if args.platform == "hn" and not cfg.get("hn"):
        sys.exit("No `hn` block in the given --config — nothing to do.")
    if args.platform == "reddit" and not cfg.get("subreddits"):
        sys.exit("No `subreddits` in the given --config — nothing to do.")
    if args.platform == "all" and not cfg.get("hn"):
        print("  [hn] no `hn:` block in --config — skipping for this run", file=sys.stderr)
    elif args.platform in ("hn", "all"):
        print("Scanning Hacker News (last %dh)..." % lookback_hours, file=sys.stderr)
        hn_candidates = scan_hn(cfg, since_ts, failures)
        print("  [hn] %d candidates" % len(hn_candidates), file=sys.stderr)
        results["candidates"] += hn_candidates
    if args.platform == "all" and not cfg.get("subreddits"):
        print("  [reddit] no `subreddits:` in --config — skipping for this run", file=sys.stderr)
    elif args.platform in ("reddit", "all"):
        print("Scanning Reddit (last %dh)..." % lookback_hours, file=sys.stderr)
        reddit_candidates = scan_reddit(cfg, since_ts, failures)
        print("  [reddit] %d candidates" % len(reddit_candidates), file=sys.stderr)
        results["candidates"] += reddit_candidates
    return results


def _run_ph(cfg, args, env_path, failures):
    ph = cfg.get("ph")
    if not ph:
        sys.exit("No `ph` block in the given --config — nothing to do.")
    env = load_env(env_path)
    token_var = ph.get("token_env", "PH_API_TOKEN")
    token = env.get(token_var) or os.environ.get(token_var)
    if not token:
        sys.exit(
            "Missing Product Hunt API token.\n"
            "  -> set %s in your environment or an .env file at %s\n"
            "  -> get a developer token at "
            "https://www.producthunt.com/v2/oauth/applications" % (token_var, env_path)
        )
    window = ph.get("window", "ph_day")
    if window not in ("ph_day", "lookback"):
        sys.exit("ph.window must be `ph_day` or `lookback`, not %r." % (window,))
    since_dt, note = (None, None)
    if window == "ph_day":
        since_dt, note = ph_day_start()
        if since_dt is None:
            print(
                "  [ph] PH-day window unavailable (%s), using the rolling lookback" % note,
                file=sys.stderr,
            )
            window = "lookback"
    if since_dt is None:
        since_dt = datetime.now(timezone.utc) - timedelta(hours=ph.get("lookback_hours", 48))
        note = "rolling %dh lookback" % ph.get("lookback_hours", 48)
    since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    print(
        "Scanning Product Hunt (%s, since %s, %d topics)..." % (note, since_iso, len(ph["topics"])),
        file=sys.stderr,
    )
    candidates = scan_ph(cfg, token, since_iso, failures)
    print("  [ph] %d candidates before detail fetch" % len(candidates), file=sys.stderr)
    candidates.sort(
        key=lambda c: (
            len(c["matched_keywords"]),
            len(c.get("fit_topics_matched") or []),
            c["comments_count"],
        ),
        reverse=True,
    )
    fetch_details(cfg, token, candidates, failures)
    floor = ph.get("thin_day_floor", 5)
    if window == "ph_day" and len(candidates) < floor:
        print(
            "  [ph] thin day: %d candidates on today's board (floor %d). The board may "
            "not have filled yet; set ph.window to `lookback` to widen to %dh."
            % (len(candidates), floor, ph.get("lookback_hours", 48)),
            file=sys.stderr,
        )
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "candidates": candidates}


def _run_twitter(cfg, args, env_path, failures=None):
    tw = _twitter_block(cfg)
    if not tw:
        sys.exit("No `twitter` block in the given --config — nothing to do.")
    env = load_env(env_path)
    token_var = tw.get("bearer_token_env", "TWITTER_BEARER_TOKEN")
    token = env.get(token_var) or os.environ.get(token_var)
    if not token:
        sys.exit(
            "Missing X/Twitter bearer token.\n"
            "  -> set %s in your environment or an .env file at %s\n"
            "  -> X has no free tier since Feb 2026 — this needs a paid "
            "developer account at https://developer.x.com/" % (token_var, env_path)
        )
    lookback_hours = min(tw.get("lookback_hours", 48), TWITTER_MAX_LOOKBACK_HOURS)
    if tw.get("lookback_hours", 48) > TWITTER_MAX_LOOKBACK_HOURS:
        print(
            "  [twitter] lookback_hours clamped to %d (7 days) — recent "
            "search can't go further back on this tier" % TWITTER_MAX_LOOKBACK_HOURS,
            file=sys.stderr,
        )
    window = min(
        timedelta(hours=lookback_hours),
        timedelta(hours=TWITTER_MAX_LOOKBACK_HOURS) - TWITTER_LOOKBACK_MARGIN,
    )
    since_iso = (datetime.now(timezone.utc) - window).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(
        "Scanning X/Twitter (last %dh, %d queries)..." % (lookback_hours, len(tw["seed_queries"])),
        file=sys.stderr,
    )
    candidates = scan_twitter({"twitter": tw}, token, since_iso, failures)
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "candidates": candidates}


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--config",
        required=True,
        help="path to a YAML config — hn/subreddits/keywords for "
        "--platform hn|reddit, a ph: block for --platform ph",
    )
    ap.add_argument("--platform", choices=["hn", "reddit", "ph", "twitter", "all"], default="all")
    ap.add_argument(
        "--env",
        default=None,
        help="path to an .env file for PH_API_TOKEN / "
        "TWITTER_BEARER_TOKEN (default: a .env next to --config)",
    )
    ap.add_argument("--out", default=None, help="exact output JSON path (overrides --out-dir)")
    ap.add_argument(
        "--out-dir",
        default=None,
        help="write a dated '<platform>-candidates-<date>.json' "
        "file here instead of stdout (same naming convention "
        "as competitor-blog-scan.py)",
    )
    ap.add_argument(
        "--max-subreddits",
        type=int,
        default=None,
        metavar="N",
        help="scan only the first N subreddits of the config (a quick preview)",
    )
    args = ap.parse_args()
    REQUESTS.update(ok=0, failed=0)
    if args.max_subreddits is not None and args.max_subreddits < 1:
        ap.error("--max-subreddits must be 1 or more")

    cfg = _load_yaml(args.config)
    if args.platform in ("reddit", "all") and cfg.get("subreddits"):
        _reddit_budget(cfg)
    _twitter_block(cfg)  # a config error here stops the run before any scan
    if args.max_subreddits is not None and cfg.get("subreddits"):
        subs = cfg["subreddits"]
        cfg["subreddits"] = subs[: args.max_subreddits]
        print(
            "  [reddit] scanning %d of %d subreddits (--max-subreddits)"
            % (len(cfg["subreddits"]), len(subs)),
            file=sys.stderr,
        )
    env_path = args.env or os.path.join(os.path.dirname(os.path.abspath(args.config)), ".env")

    output: dict = {"candidates": [], "failures": []}
    failures = output["failures"]
    if args.platform in ("hn", "reddit", "all"):
        r = _run_hn_reddit(cfg, args, failures)
        output["candidates"] += r["candidates"]
    if args.platform == "ph":
        # Explicitly requested — a missing `ph:` block or token is a real error.
        r = _run_ph(cfg, args, env_path, failures)
        output["candidates"] += r["candidates"]
    elif args.platform == "twitter":
        # Explicitly requested — a missing `twitter:` block or token is a real error.
        r = _run_twitter(cfg, args, env_path, failures)
        output["candidates"] += r["candidates"]
    elif args.platform == "all":
        # Opportunistic — a config built for hn/reddit only (no `ph:` or
        # `twitter:` block) is a normal, expected shape here, not a
        # failure. content-engine's hn-reddit-scan.yaml is exactly this
        # shape. A platform that fails here is recorded and skipped, so
        # the platforms that worked still reach the output.
        for name, block, run in (
            ("ph", cfg.get("ph"), _run_ph),
            ("twitter", _twitter_block(cfg), _run_twitter),
        ):
            if not block:
                print(
                    "  [%s] no `%s:` block in --config — skipping for this run" % (name, name),
                    file=sys.stderr,
                )
                continue
            try:
                r = run(cfg, args, env_path, failures)
            except SystemExit as e:
                print("  [%s] skipped: %s" % (name, e), file=sys.stderr)
                _record_failure(failures, name, "whole platform", e)
                _request_done(False)
                continue
            except Exception as e:
                print("  [%s] failed: %s" % (name, e), file=sys.stderr)
                _record_failure(failures, name, "whole platform", e)
                _request_done(False)
                continue
            output["candidates"] += r["candidates"]

    output["generated_at"] = datetime.now(timezone.utc).isoformat()
    payload = json.dumps(output, indent=2)

    out_path = args.out
    if out_path is None and args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)
        out_path = os.path.join(
            args.out_dir,
            "%s-candidates-%s.json"
            % (args.platform, datetime.now(timezone.utc).date().isoformat()),
        )

    if out_path:
        with open(out_path, "w") as f:
            f.write(payload)
        print(
            "\n%d candidates, %d failed requests -> %s"
            % (len(output["candidates"]), len(failures), out_path)
        )
    else:
        print(payload)
    if REQUESTS["failed"] and not REQUESTS["ok"] and not output["candidates"]:
        sys.exit("Every request failed, so there are no candidates.")


if __name__ == "__main__":
    if sys.argv[1:] == ["--reddit-fetch-worker"]:
        _reddit_fetch_worker()
    else:
        main()
