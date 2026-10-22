#!/usr/bin/env python3
# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
"""Fetch competitor blog RSS feeds as content-engine signals.

No credentials needed: these are public RSS 2.0, RSS 1.0 (RDF) and Atom feeds. A 200 response with
the wrong content type or body shape (a paywall page, a WAF challenge, a
404 page some sites serve with status 200) counts as a failure for that one
blog and is never fed to the XML parser. The other blogs carry on.

Usage:
    python3 packages/content-engine/competitor-blog-scan.py --config <config.yaml>

The script keeps no state. Every run returns everything in each feed within
lookback_days, and the calling command dedupes against the signal bank by
native_id. Needs PyYAML.
"""

import argparse
import http.client
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.yaml")

UA = "content-engine (+https://github.com/tetriz-ai/content-engine)"
ATOM = "{http://www.w3.org/2005/Atom}"
RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
RSS1 = "{http://purl.org/rss/1.0/}"
DC = "{http://purl.org/dc/elements/1.1/}"

# Everything one feed can raise while being fetched or parsed: HTTP and
# network errors (URLError, timeouts and resets are all OSError), a broken
# HTTP response, a body that is not a feed, and malformed XML.
FEED_ERRORS = (OSError, http.client.HTTPException, ValueError, ET.ParseError)

# A feed's clock may run a little ahead; anything later than this is a bad date.
FUTURE_SLACK_SECONDS = 300


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


def _fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        ctype = resp.headers.get("Content-Type", "")
    if "xml" not in ctype:
        raise ValueError(
            "content-type %r is not an RSS/Atom feed — likely a block page, "
            "redirect target, or dead feed URL" % ctype
        )
    feed = _feed_body(body)
    if feed is None:
        raise ValueError(
            "the body is not an RSS/Atom feed (starts %r) — likely a block "
            "page, redirect target, or dead feed URL" % body.lstrip()[:40]
        )
    return feed


def _to_iso(dt):
    """ISO 8601 in UTC; a date with no offset is taken as UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso(value):
    """A datetime for an ISO 8601 string, or None. A trailing Z, a `+0000`
    offset and fractional seconds of any length are normalised first, so
    Python 3.9's fromisoformat reads them."""
    if not isinstance(value, str):
        return None
    v = value.strip()
    if v.endswith(("Z", "z")):
        v = v[:-1] + "+00:00"
    v = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", v)
    v = re.sub(r"\.(\d+)", lambda m: "." + (m.group(1) + "000000")[:6], v, count=1)
    try:
        return datetime.fromisoformat(v)
    except ValueError:
        return None


def _parse_rss(raw):
    """Items of an RSS 2.0 or RSS 1.0 (RDF) feed, or entries of an Atom feed,
    as dicts with title, url, guid, published_at (ISO 8601 UTC or None) and
    excerpt. Any other root raises ValueError, which fails that one feed."""
    root = ET.fromstring(raw)
    if root.tag == ATOM + "feed":
        return [_atom_entry(e) for e in root.findall(ATOM + "entry")]
    if root.tag == RDF + "RDF":
        return [_rdf_item(it) for it in root.findall(RSS1 + "item")]
    if root.tag != "rss":
        raise ValueError("unrecognised feed format: root element %r" % root.tag)
    out = []
    for it in root.findall(".//item"):  # RSS 2.0
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        guid = (it.findtext("guid") or link).strip()
        pub = it.findtext("pubDate")
        pub_dt = None
        if pub:
            try:
                pub_dt = parsedate_to_datetime(pub)
            except (TypeError, ValueError):
                pub_dt = None
        if pub_dt is None:
            # Some RSS 2.0 feeds date their items with Dublin Core instead.
            pub_dt = _parse_iso(it.findtext(DC + "date") or "")
        desc = (it.findtext("description") or "")[:500]
        out.append(
            {
                "title": title,
                "url": link,
                "guid": guid,
                "published_at": _to_iso(pub_dt) if pub_dt else None,
                "excerpt": desc,
            }
        )
    return out


def _rdf_item(it):
    link = (it.findtext(RSS1 + "link") or "").strip()
    pub_dt = _parse_iso(it.findtext(DC + "date") or "")
    return {
        "title": (it.findtext(RSS1 + "title") or "").strip(),
        "url": link,
        "guid": (it.get(RDF + "about") or link).strip(),
        "published_at": _to_iso(pub_dt) if pub_dt else None,
        "excerpt": (it.findtext(RSS1 + "description") or "")[:500],
    }


def _atom_entry(e):
    link = ""
    for el in e.findall(ATOM + "link"):
        if el.get("rel", "alternate") == "alternate" and el.get("href"):
            link = el.get("href").strip()
            break
    pub_dt = _parse_iso(e.findtext(ATOM + "published") or e.findtext(ATOM + "updated") or "")
    excerpt = e.findtext(ATOM + "summary") or e.findtext(ATOM + "content") or ""
    return {
        "title": (e.findtext(ATOM + "title") or "").strip(),
        "url": link,
        "guid": (e.findtext(ATOM + "id") or link).strip(),
        "published_at": _to_iso(pub_dt) if pub_dt else None,
        "excerpt": excerpt[:500],
    }


def _extract_published_from_page(url, timeout=15):
    """Fallback for feeds with no per-item RSS pubDate (some generated feeds
    only carry a channel-level date). Fetches the
    article page itself and regexes for a structured publish date, trying
    the most reliable source first: JSON-LD 'datePublished', then the
    article:published_time meta tag, then a <time datetime=...> element.
    Returns an ISO date string or None — never raises, a failed fallback
    just means the caller treats the item as undated. Only http(s) links are
    fetched.
    """
    if not url.lower().startswith(("http://", "https://")):
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
    except Exception:
        return None
    for pattern in (
        r'"datePublished"\s*:\s*"([^"]+)"',
        r'article:published_time"\s+content="([^"]+)"',
        r'<time[^>]*\bdatetime="([^"]+)"',
    ):
        m = re.search(pattern, body)
        if m:
            dt = _parse_iso(m.group(1))
            if dt is not None:
                return _to_iso(dt)
    return None


def scan(cfg, lookback_days):
    """Read every configured feed. One feed failing (network, HTTP, a body
    that is not a feed, bad XML, no feed_url) is recorded as failed for that
    feed only; the others carry on. An item dated more than
    FUTURE_SLACK_SECONDS ahead of now is dropped and counted."""
    blogs = (cfg.get("scan") or {}).get("competitor_blogs") or {}
    now = datetime.now(timezone.utc).timestamp()
    since = now - lookback_days * 86400
    results: dict = {"generated_at": datetime.now(timezone.utc).isoformat(), "sources": {}}
    for name, blog in (blogs.get("feeds") or {}).items():
        if blog is not None and not isinstance(blog, dict):
            results["sources"][name] = {
                "status": "failed",
                "error": "feed must be a mapping with feed_url, not %s" % type(blog).__name__,
                "feed_url": None,
            }
            continue
        url = (blog or {}).get("feed_url")
        if not url:
            results["sources"][name] = {
                "status": "failed",
                "error": "no feed_url",
                "feed_url": None,
            }
            continue
        try:
            raw = _fetch(url)
            entries = _parse_rss(raw)
            fresh = []
            dropped_undated = 0
            dropped_future = 0
            for e in entries:
                published_at = e["published_at"]
                if not published_at:
                    # An undated item is never assumed fresh, the same rule
                    # as every other source. Try to recover a real date from
                    # the article page's own structured data, and drop the
                    # item if there isn't one.
                    published_at = _extract_published_from_page(e["url"])
                if not published_at:
                    dropped_undated += 1
                    continue
                dt = _parse_iso(published_at)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt.timestamp() > now + FUTURE_SLACK_SECONDS:
                    dropped_future += 1
                    continue
                if dt.timestamp() < since:
                    continue
                fresh.append(
                    {
                        "native_id": "blog:%s:%s" % (name, e["guid"] or e["url"]),
                        "source": "competitor_blog",
                        "competitor": name,
                        "url": e["url"],
                        "title": e["title"],
                        "excerpt": e["excerpt"],
                        "raw_metric": {},
                        "keywords_matched": [],
                        "published_at": published_at,
                        "fetched_at": datetime.now(timezone.utc).date().isoformat(),
                    }
                )
            results["sources"][name] = {
                "status": "ok",
                "fetched": len(entries),
                "fresh_within_window": len(fresh),
                "dropped_undated": dropped_undated,
                "dropped_future": dropped_future,
                "entries": fresh,
            }
        except FEED_ERRORS as e:
            results["sources"][name] = {"status": "failed", "error": str(e), "feed_url": url}
    return results


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--config",
        default=CONFIG_PATH,
        help="config with scan.competitor_blogs (default: config.yaml next to this script)",
    )
    args = ap.parse_args()

    try:
        import yaml
    except ImportError:
        sys.exit(
            "Missing dependency: PyYAML. Install it with:\n"
            "  pip install -r packages/scanner-core/requirements.txt"
        )
    if not os.path.exists(args.config):
        sys.exit("Config file not found: %s" % args.config)
    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        sys.exit("Config file %s is empty or not a YAML mapping." % args.config)
    scan_cfg = cfg.get("scan") or {}
    if not isinstance(scan_cfg, dict):
        sys.exit("`scan` in %s must be a mapping, not %r." % (args.config, scan_cfg))
    blogs = scan_cfg.get("competitor_blogs") or {}
    feeds = blogs.get("feeds") if isinstance(blogs, dict) else None
    if not feeds or not isinstance(feeds, dict):
        sys.exit(
            "scan.competitor_blogs.feeds in %s is empty or not a mapping of blog names "
            "to feed_url, so there is nothing to scan." % args.config
        )

    lookback_days = blogs.get("lookback_days", 14)
    if isinstance(lookback_days, bool) or not isinstance(lookback_days, int) or lookback_days <= 0:
        sys.exit(
            "scan.competitor_blogs.lookback_days in %s must be a whole number of days above 0, "
            "not %r." % (args.config, lookback_days)
        )
    results = scan(cfg, lookback_days)

    out_dir = os.path.join(os.getcwd(), "working/content-engine/signals")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(
        out_dir,
        "competitor-blog-candidates-%s.json" % datetime.now(timezone.utc).date().isoformat(),
    )
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    total_fresh = sum(
        s.get("fresh_within_window", 0) for s in results["sources"].values() if s["status"] == "ok"
    )
    print("Scanning competitor blog RSS feeds (last %dd)..." % lookback_days, file=sys.stderr)
    for name, s in results["sources"].items():
        if s["status"] == "ok":
            print(
                "  [blog] %s: %d fresh / %d total (%d dropped with no recoverable date, "
                "%d dated in the future)"
                % (
                    name,
                    s["fresh_within_window"],
                    s["fetched"],
                    s.get("dropped_undated", 0),
                    s.get("dropped_future", 0),
                ),
                file=sys.stderr,
            )
        else:
            print("  [blog] %s failed: %s" % (name, s["error"]), file=sys.stderr)
    print("\n%d fresh entries -> %s" % (total_fresh, out_path))
    if all(s["status"] != "ok" for s in results["sources"].values()):
        sys.exit("Every competitor blog feed failed, so there are no entries.")


if __name__ == "__main__":
    main()
