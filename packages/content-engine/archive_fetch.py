#!/usr/bin/env python3
# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
"""
archive_fetch.py — save your own published posts as the writer profile's archive.

Reads `archive_sources` from a writer profile (see writer-profile.example.yaml)
and writes each post, whole, as a Markdown file in its `archive_dir`.
write_reference.py then picks voice examples from that folder, and
relevance_scorer.py reads it as "what this writer covers".

Sources, one entry each:
  - substack: yourname           every post in the publication's archive
                                 (yourname.substack.com, or a custom domain)
  - medium: "@handle"            your Medium feed: the 10 most recent posts
  - medium_export: <zip or folder>    Medium's "Download your information"
  - linkedin_export: <zip or folder>  LinkedIn's "Get a copy of your data"
  - sitemap: https://blog.example.com/sitemap.xml
    path_prefix: /guides/        every page of a site's folder (required)
  - rss: https://blog.example.com/feed  any RSS or Atom feed

A Substack entry reads the publication's archive list, then each post,
`min_gap_seconds` apart (default 1). When the archive list fails it reads
the RSS feed instead, which holds about 20 recent posts. A paid post
arrives as its preview only, and is flagged.

A sitemap entry reads the sitemap (a sitemap index too), keeps the pages
under `path_prefix`, newest first, up to `max_pages` (default 2000), and
saves the text of each page. A page with almost no text, or one that is the
folder page of others, is skipped. Its category is the URL's folder below
`path_prefix` (/guides/ci-reliability/<page> -> ci-reliability).

Every saved post gets a line in archive_dir/.tags.json, the tag index:
its URL, date, category, word count and content type (set later by
archive_tag.py). A file already in archive_dir is never fetched again, so
hand edits survive and an interrupted run resumes; --refresh rewrites them.
No credentials are needed.

Usage:
  python3 packages/content-engine/archive_fetch.py \
      --profile packages/content-engine/writer-profile.yaml
  python3 packages/content-engine/archive_fetch.py --profile ... --dry-run   # list, write nothing

Needs PyYAML.
"""

import argparse
import csv
import gzip
import hashlib
import html
import http.client
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

# The usual bot form, naming this tool and where it lives. Medium resets the
# connection for a User-Agent that doesn't start with "Mozilla/5.0".
UA = "Mozilla/5.0 (compatible; content-engine; +https://github.com/tetriz-ai/content-engine)"
ATOM = "{http://www.w3.org/2005/Atom}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"

# Below this many characters, a post the feed did carry in full is probably
# a teaser all the same: a paid Substack post ships its preview that way.
PREVIEW_CHARS = 500

# A sitemap page with less text than this is a listing or an empty page.
MIN_PAGE_CHARS = 200

# Everything one source can raise while being fetched or parsed.
FEED_ERRORS = (OSError, http.client.HTTPException, ValueError, ET.ParseError, zipfile.BadZipFile)

SOURCE_TYPES = ("medium", "substack", "rss", "sitemap", "medium_export", "linkedin_export")

# The settings each source type takes besides its own key.
SOURCE_OPTIONS = {
    "medium": (),
    "substack": ("min_gap_seconds",),
    "rss": (),
    "sitemap": ("path_prefix", "max_pages", "min_gap_seconds"),
    "medium_export": (),
    "linkedin_export": (),
}

DEFAULT_GAP_SECONDS = 1
DEFAULT_MAX_PAGES = 2000

# Substack's archive list returns at most this many posts a page (it may
# return fewer); paging stops at the first empty page.
SUBSTACK_PAGE = 50

# The Substack audiences whose posts reach the API as a preview only.
PAID_AUDIENCES = ("only_paid", "founding")

# First path segments of medium.com URLs that name no profile or publication.
MEDIUM_RESERVED = ("p", "m", "tag")

# The tag index, one entry per post in archive_dir. A dot file, so the
# writer and the scorer never read it as a post.
INDEX_NAME = ".tags.json"


def parse_source(source):
    """(type, value, options) for one `archive_sources` entry: a mapping with
    exactly one source type and the settings that type takes. Raises
    ValueError for anything else."""
    if not isinstance(source, dict):
        raise ValueError(
            "each archive_sources entry needs exactly one of %s, not %r"
            % (", ".join(SOURCE_TYPES), source)
        )
    kinds = [k for k in source if k in SOURCE_TYPES]
    if len(kinds) != 1:
        unknown = [k for k in source if k not in SOURCE_TYPES]
        if not kinds and len(unknown) == 1:
            raise ValueError(
                "unknown archive source %r; use one of %s" % (unknown[0], ", ".join(SOURCE_TYPES))
            )
        raise ValueError(
            "each archive_sources entry needs exactly one of %s, not %r"
            % (", ".join(SOURCE_TYPES), source)
        )
    kind = kinds[0]
    options = {k: v for k, v in source.items() if k != kind}
    for key in options:
        if key not in SOURCE_OPTIONS[kind]:
            allowed = ", ".join(SOURCE_OPTIONS[kind]) or "no other settings"
            raise ValueError("%s source takes %s, not %r" % (kind, allowed, key))
    value = str(source[kind] or "").strip()
    if not value:
        raise ValueError("archive source %r has no value" % kind)
    if "min_gap_seconds" in options:
        gap = options["min_gap_seconds"]
        if isinstance(gap, bool) or not isinstance(gap, (int, float)) or gap < 0:
            raise ValueError("min_gap_seconds must be a number of 0 or more, not %r" % (gap,))
    if "max_pages" in options:
        pages = options["max_pages"]
        if isinstance(pages, bool) or not isinstance(pages, int) or pages <= 0:
            raise ValueError("max_pages must be a whole number above 0, not %r" % (pages,))
    if kind == "sitemap":
        if urllib.parse.urlparse(value).scheme not in ("http", "https", "file"):
            raise ValueError("sitemap source %r must be an http(s) or file URL" % value)
        prefix = options.get("path_prefix")
        if not isinstance(prefix, str) or not prefix.strip().strip("/"):
            raise ValueError(
                "sitemap source %r needs path_prefix, the folder to save (e.g. /guides/), "
                "so a whole site is never read by accident" % value
            )
        options["path_prefix"] = "/" + prefix.strip().strip("/") + "/"
    elif kind == "substack":
        substack_base(value)  # raises for a value that names no publication
    elif kind in ("medium", "rss"):
        feed_url({kind: value})
    return kind, value, options


def feed_url(source):
    """The feed URL for an `archive_sources` entry of type medium, substack or
    rss. Raises ValueError for anything else."""
    kinds = [k for k in source if k in SOURCE_TYPES] if isinstance(source, dict) else []
    if len(kinds) == 1 and kinds[0] in ("medium", "substack", "rss"):
        kind = kinds[0]
        value = str(source[kind] or "").strip()
        if not value:
            raise ValueError("archive source %r has no value" % kind)
    else:
        kind, value, _ = parse_source(source)
        raise ValueError("%s source has no feed" % kind)

    if kind == "rss":
        if urllib.parse.urlparse(value).scheme not in ("http", "https", "file"):
            raise ValueError("rss source %r must be an http(s) or file URL" % value)
        return value

    if kind == "medium":
        if "://" not in value and re.match(r"(?:[a-z0-9-]+\.)*medium\.com(?:/|$)", value, re.I):
            value = "https://" + value  # medium.com/@jane, without its scheme
        no_profile = ValueError(
            "medium source %r names no Medium profile; use rss: for a custom domain" % value
        )
        if "://" in value:
            parts = urllib.parse.urlparse(value)
            host = parts.netloc.lower()
            if host.endswith(".medium.com") and host != "www.medium.com":  # jane.medium.com
                return "https://%s/feed" % host
            if host not in ("medium.com", "www.medium.com"):
                raise no_profile
            segments = [seg for seg in parts.path.split("/") if seg]
            if segments[:1] == ["feed"]:  # already a feed URL: medium.com/feed/@jane
                segments = segments[1:]
            name = segments[0] if segments else ""
            if name in MEDIUM_RESERVED:  # a post (/p/<id>), the app (/m/...) or a tag page
                raise no_profile
        else:
            name = value.strip("/")
            if "." in name or "/" in name:  # a domain or a path, not a handle
                raise no_profile
        if not name:
            raise no_profile
        return "https://medium.com/feed/%s" % name

    return substack_base(value) + "/feed"


def substack_base(value):
    """`https://<host>` for a substack value: a bare name (with or without
    @), a substack.com/@name profile, or a custom domain with or without its
    scheme. An explicit http:// is kept. Raises ValueError when the value
    names no publication."""
    if "://" not in value and "." not in value and ":" not in value:
        name = value.strip("/").lstrip("@")
        if not name or "/" in name:
            raise ValueError("substack source %r names no publication" % value)
        return "https://%s.substack.com" % name
    parts = urllib.parse.urlparse(value if "://" in value else "https://" + value)
    host = parts.netloc.lower()
    if host in ("substack.com", "www.substack.com"):
        first = parts.path.strip("/").split("/")[0]
        if first == "profile":
            raise ValueError(
                "substack source %r is a profile page; use the publication name" % value
            )
        name = first.lstrip("@")
        if not name:
            raise ValueError("substack source %r names no publication" % value)
        return "https://%s.substack.com" % name
    scheme = "http" if parts.scheme == "http" else "https"
    return "%s://%s" % (scheme, host)


class _TextExtractor(HTMLParser):
    """Plain text with Markdown-ish structure: headings as `#`, list items as
    `- `, a blank line between blocks. Scripts, styles and figure captions
    are dropped."""

    BLOCKS = {"p", "div", "section", "article", "blockquote", "pre", "ul", "ol", "br", "hr"}
    SKIP = {"script", "style", "figcaption", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.current = []
        self.kind = "p"
        self.skipping = 0

    def _flush(self):
        text = " ".join("".join(self.current).replace("\xa0", " ").split())
        if text:
            self.blocks.append((self.kind, text))
        self.current = []
        self.kind = "p"

    def handle_starttag(self, tag, attrs):
        tag = tag.rpartition(":")[2]  # Atom xhtml content arrives as ns0:p
        if tag in self.SKIP:
            self.skipping += 1
        elif re.fullmatch(r"h[1-6]", tag):
            self._flush()
            self.kind = tag
        elif tag == "li":
            self._flush()
            self.kind = "li"
        elif tag in self.BLOCKS:
            self._flush()

    def handle_endtag(self, tag):
        tag = tag.rpartition(":")[2]
        if tag in self.SKIP:
            self.skipping = max(0, self.skipping - 1)
        elif tag == "li" or tag in self.BLOCKS or re.fullmatch(r"h[1-6]", tag):
            self._flush()

    def handle_data(self, data):
        if not self.skipping:
            self.current.append(data)

    def text(self):
        self._flush()
        out: list[str] = []
        prev = None
        for kind, text in self.blocks:
            if kind == "li":
                text = "- " + text
            elif kind.startswith("h"):
                text = "#" * int(kind[1]) + " " + text
            if out:
                out.append("\n" if kind == "li" and prev == "li" else "\n\n")
            out.append(text)
            prev = kind
        return "".join(out)


def html_to_text(html):
    parser = _TextExtractor()
    parser.feed(html or "")
    parser.close()
    return parser.text()


def _feed_body(body):
    """The body without a UTF-8 BOM and leading whitespace, when it starts like
    an RSS or Atom feed; otherwise None."""
    b = body.lstrip()
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:].lstrip()
    return b if b.startswith((b"<?xml", b"<rss", b"<feed")) else None


def _date(value, iso):
    """YYYY-MM-DD from an RSS (RFC 822) or Atom (ISO 8601) date, else None."""
    value = (value or "").strip()
    if not value:
        return None
    if iso:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", value)
        return m.group(1) if m else None
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError, IndexError):
        # A date with no time ("Tue, 29 Sep 2026") is not RFC 822 enough
        # for the parser; the day, month and year still are.
        m = re.search(r"(\d{1,2}) ([A-Za-z]{3})[a-z]* (\d{4})", value)
        if not m:
            return None
        try:
            return datetime.strptime(" ".join(m.groups()), "%d %b %Y").date().isoformat()
        except ValueError:
            return None


def _element_html(el):
    """An element's content as HTML: its text for escaped HTML (RSS CDATA,
    Atom type="html"), its serialised children for Atom type="xhtml"."""
    if el is None:
        return ""
    if len(el):
        return "".join(ET.tostring(child, encoding="unicode") for child in el)
    return el.text or ""


def parse_feed(raw):
    """Posts in an RSS 2.0 or Atom feed, each a dict with title, url,
    published (YYYY-MM-DD or None), text (the full body when the feed
    carries it, else its summary) and full (whether it did). Raises
    ValueError when `raw` is not a feed."""
    body = _feed_body(raw)
    if body is None:
        raise ValueError(
            "the response is not an RSS/Atom feed (starts %r); check the handle "
            "or URL" % raw.lstrip()[:40]
        )
    root = ET.fromstring(body)
    posts = []
    if root.tag == "rss":
        for item in root.iter("item"):
            full = _element_html(item.find(CONTENT + "encoded"))
            html = full or _element_html(item.find("description"))
            posts.append(
                {
                    "title": (item.findtext("title") or "").strip() or "Untitled",
                    "url": (item.findtext("link") or "").strip(),
                    "published": _date(item.findtext("pubDate"), iso=False),
                    "text": html_to_text(html),
                    "full": bool(full.strip()),
                }
            )
    elif root.tag == ATOM + "feed":
        for entry in root.iter(ATOM + "entry"):
            url = ""
            for link in entry.findall(ATOM + "link"):
                if link.get("rel", "alternate") == "alternate":
                    url = link.get("href", "")
                    break
            full = _element_html(entry.find(ATOM + "content"))
            html = full or _element_html(entry.find(ATOM + "summary"))
            posts.append(
                {
                    "title": (entry.findtext(ATOM + "title") or "").strip() or "Untitled",
                    "url": url.strip(),
                    "published": _date(
                        entry.findtext(ATOM + "published") or entry.findtext(ATOM + "updated"),
                        iso=True,
                    ),
                    "text": html_to_text(html),
                    "full": bool(full.strip()),
                }
            )
    else:
        raise ValueError("unsupported feed root <%s>; expected RSS 2.0 or Atom" % root.tag)
    return posts


class _Node:
    """One element of a parsed HTML page: its tag, attributes and children
    (nodes and text)."""

    __slots__ = ("tag", "attrs", "children")

    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.children: list = []

    def has_class(self, name):
        return name in (self.attrs.get("class") or "").split()

    def find(self, match):
        """The first element below this one, depth first, for which
        `match(node)` is true; None when there is none."""
        for child in self.children:
            if isinstance(child, _Node):
                if match(child):
                    return child
                found = child.find(match)
                if found is not None:
                    return found
        return None

    def text(self):
        parts: list[str] = []
        for child in self.children:
            parts.append(child if isinstance(child, str) else child.text())
        return " ".join("".join(parts).split())


class _TreeBuilder(HTMLParser):
    """A forgiving HTML tree: an end tag closes the nearest open element of
    that name and everything opened inside it; a stray end tag is ignored."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta"}
    VOID |= {"source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("#root", {})
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, {k: v or "" for k, v in attrs})
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(_Node(tag, {k: v or "" for k, v in attrs}))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_html(text):
    builder = _TreeBuilder()
    builder.feed(text or "")
    builder.close()
    return builder.root


# Page furniture, never part of a post's text.
PAGE_FURNITURE = {"nav", "header", "footer", "aside", "script", "style", "form", "noscript"}
PAGE_FURNITURE |= {"svg", "template", "iframe"}


def _inner_html(node, drop=frozenset()):
    """The node's content as plain HTML (no attributes), without the elements
    named in `drop`, for html_to_text."""
    parts = []
    for child in node.children:
        if isinstance(child, str):
            parts.append(html.escape(child, quote=False))
        elif child.tag not in drop:
            parts.append("<%s>%s</%s>" % (child.tag, _inner_html(child, drop), child.tag))
    return "".join(parts)


def _drop_leading_title(text, title):
    """`text` without a first heading block that repeats `title`."""
    first, sep, rest = text.partition("\n\n")
    heading = re.match(r"#{1,6} (.*)$", first)
    if heading and " ".join(heading.group(1).split()).lower() == " ".join(title.split()).lower():
        return rest if sep else ""
    return text


def extract_page(raw, fallback_date=None):
    """(title, published, text) of a web page: the title from its first <h1>,
    else <title>; the date from article:published_time, else the first
    <time datetime>, else `fallback_date`; the text from <article>, else
    <main>, else <body> from its <h1> on, without navigation, headers,
    footers, asides, scripts, styles and forms."""
    root = parse_html(raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw)
    h1 = root.find(lambda n: n.tag == "h1")
    title = h1.text() if h1 is not None else ""
    if not title:
        title_el = root.find(lambda n: n.tag == "title")
        title = title_el.text() if title_el is not None else ""
    meta = root.find(
        lambda n: (
            n.tag == "meta"
            and (n.attrs.get("property") or n.attrs.get("name") or "").lower()
            == "article:published_time"
        )
    )
    published = _date(meta.attrs.get("content"), iso=True) if meta is not None else None
    if not published:
        time_el = root.find(lambda n: n.tag == "time" and bool(n.attrs.get("datetime")))
        if time_el is not None:
            published = _date(time_el.attrs["datetime"], iso=True)
    published = published or fallback_date
    container = None
    for tag in ("article", "main", "body"):
        container = root.find(lambda n, tag=tag: n.tag == tag)
        if container is not None:
            break
    text = html_to_text(_inner_html(container or root, PAGE_FURNITURE))
    if container is None or container.tag == "body":
        # No <article> or <main>: what comes before the page's own <h1> is
        # breadcrumbs and menus, so the text starts at the heading.
        heading = "# " + " ".join(title.split())
        at = text.find(heading + "\n") if title else -1
        if at > 0 and text[at - 1] == "\n":
            text = text[at:]
    return title or "Untitled", published, _drop_leading_title(text, title)


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


class Pacer:
    """Spaces one source's requests at least `gap` seconds apart."""

    def __init__(self, gap):
        self.gap = gap
        self.last = None

    def wait(self):
        if self.last is not None and self.gap > 0:
            delay = self.last + self.gap - time.monotonic()
            if delay > 0:
                time.sleep(delay)
        self.last = time.monotonic()


TRACKING_PARAMS = ("ref", "source")


def _netloc(parts):
    """A URL's host and port, lower-cased, without the scheme's default port."""
    host = (parts.hostname or "").lower()
    port = parts.port
    if port is not None and port not in (80, 443):
        host = "%s:%d" % (host, port)
    if parts.username or parts.password:
        host = "%s@%s" % (parts.netloc.rsplit("@", 1)[0], host)
    return host


def _upper_escapes(text):
    return re.sub(r"%[0-9a-fA-F]{2}", lambda m: m.group(0).upper(), text)


def url_key(url):
    """The form two URLs of one post share: http and https folded together,
    the host lower-cased, the default port (80, 443), the fragment, a trailing
    slash and the utm_*, ref and source query parameters dropped, %-escapes
    upper-cased, every other query parameter kept in order."""
    parts = urllib.parse.urlsplit(url.strip())
    scheme = parts.scheme.lower()
    if scheme == "http":
        scheme = "https"
    query = [
        (k, v)
        for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS
    ]
    return urllib.parse.urlunsplit(
        (
            scheme,
            _netloc(parts),
            _upper_escapes(parts.path.rstrip("/")),
            _upper_escapes(urllib.parse.urlencode(query)),
            "",
        )
    )


def category_from_url(url, path_prefix):
    """The deepest folder of `url`'s path below `path_prefix`, lower-cased:
    /guides/ci-reliability/flaky-quarantine under /guides/ is ci-reliability.
    None when the page sits right in the prefix folder, or the URL is outside
    it."""
    if not url or not path_prefix:
        return None
    path = urllib.parse.urlparse(url).path
    if not path.startswith(path_prefix):
        return None
    folders = [seg for seg in path[len(path_prefix) :].split("/") if seg][:-1]
    return urllib.parse.unquote(folders[-1]).lower() if folders else None


FOLDED_SCRIPTS = ("LATIN", "GREEK", "CYRILLIC")


def _slug(title):
    """A file-name slug. Accents on Latin, Greek and Cyrillic letters are
    folded ("Ünïcödé" -> "unicode"); every other script keeps its marks
    (Japanese voicing, Devanagari vowel signs). Letters, digits and marks of
    any script are kept, everything else becomes a hyphen."""
    out, base = [], ""
    for ch in unicodedata.normalize("NFKD", title.lower()):
        if unicodedata.combining(ch):
            if unicodedata.name(base, "").startswith(FOLDED_SCRIPTS):
                continue
        else:
            base = ch
        out.append(ch)
    text = unicodedata.normalize("NFC", "".join(out))
    chars = [ch if ch.isalnum() or unicodedata.category(ch).startswith("M") else "-" for ch in text]
    slug = re.sub(r"-+", "-", "".join(chars)).strip("-")[:60].rstrip("-")
    return slug or "post"


def _unique(base, taken):
    name, n = base + ".md", 2
    while name in taken:
        name, n = "%s-%d.md" % (base, n), n + 1
    taken.add(name)
    return name


def file_name(post, taken):
    """`<date>-<slug>.md`, with -2, -3 … added when this run already used the
    name for another post."""
    return _unique("%s-%s" % (post["published"] or "undated", _slug(post["title"])), taken)


def page_file_name(url, path_prefix, taken):
    """A sitemap page's file name, from its path below `path_prefix`
    (/guides/ci-reliability/flaky-quarantine -> ci-reliability-flaky-quarantine.md), so a page
    already saved is known before it is fetched."""
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path)
    if path.startswith(path_prefix):
        path = path[len(path_prefix) :]
    return _unique(_slug(path.replace("/", " ")), taken)


def render(post):
    source = post["url"] or "(no link in the feed)"
    if post["published"]:
        source += " (published %s)" % post["published"]
    header = "Source: %s\n" % source
    if post.get("category"):
        header += "Category: %s\n" % post["category"]
    return "# %s\n\n%s\n%s\n" % (post["title"], header, post["text"])


SOURCE_LINE_RE = re.compile(r"^Source: (.*?)(?: \(published (\d{4}-\d{2}-\d{2})\))?$")


def read_header(text):
    """(title, url, published, category) from a saved post's header, the
    block render() writes: a `# title` line, a blank line, then `Source:` and
    `Category:` lines up to the next blank line. Each is None when absent, and
    nothing below the header is read. A file added by hand usually has none."""
    title = url = published = category = None
    lines = text.split("\n")
    if not lines[0].startswith("# "):
        return title, url, published, category
    title = lines[0][2:].strip() or None
    for line in lines[2:] if len(lines) > 1 and not lines[1].strip() else []:
        m = SOURCE_LINE_RE.match(line)
        if m and line.startswith("Source: "):
            if url is None and published is None:  # the first Source line is the post's
                url = m.group(1).strip() if m.group(1).strip().startswith("http") else None
                published = m.group(2)
        elif line.startswith("Category: "):
            if category is None:
                category = line[len("Category: ") :].strip().lower() or None
        else:
            break
    return title, url, published, category


# --- the tag index ---------------------------------------------------------


def index_path(archive_dir):
    return os.path.join(archive_dir, INDEX_NAME)


def load_index(archive_dir):
    """The tag index as {file name: entry}; empty when there is none yet.
    Raises ValueError when the file is there but is not a tag index."""
    path = index_path(archive_dir)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError("%s is not a readable tag index: %s" % (path, e)) from e
    posts = data.get("posts") if isinstance(data, dict) else None
    if not isinstance(posts, dict) or not all(isinstance(v, dict) for v in posts.values()):
        raise ValueError('%s is not a tag index (no "posts" mapping)' % path)
    return posts


def save_index(archive_dir, index):
    path = index_path(archive_dir)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(
            {"version": 1, "posts": dict(sorted(index.items()))}, f, indent=2, ensure_ascii=False
        )
        f.write("\n")
    os.replace(tmp, path)


def index_entry(
    text, title=None, url=None, published=None, category=None, content_type=None, fetched=False
):
    """One tag-index entry for a saved post's text. Fields not given come
    from the post's header; a fetched post's category comes only from its
    source (`fetched`)."""
    h_title, h_url, h_published, h_category = read_header(text)
    return {
        "title": title or h_title,
        "url": url or h_url,
        "published": published or h_published,
        "category": category if fetched else category or h_category,
        "content_type": content_type,
        "words": len(text.split()),
    }


def post_files(archive_dir):
    """The post files in archive_dir: every .md and .txt file."""
    return sorted(
        n
        for n in os.listdir(archive_dir)
        if n.lower().endswith((".md", ".txt")) and os.path.isfile(os.path.join(archive_dir, n))
    )


def sync_index(archive_dir, index):
    """Adds an entry for each post file the index lacks (a file added by
    hand, or saved before the index existed) and drops each entry whose file
    is gone. Returns (added, dropped)."""
    files = set(post_files(archive_dir))
    added = dropped = 0
    for name in sorted(files - set(index)):
        with open(os.path.join(archive_dir, name), encoding="utf-8", errors="replace") as f:
            index[name] = index_entry(f.read())
        added += 1
    for name in sorted(set(index) - files):
        del index[name]
        dropped += 1
    return added, dropped


# --- sources ---------------------------------------------------------------
#
# Each reader returns (label, items). An item is a dict with either "post"
# (a post already read) or "name" and "load" (a post fetched only when its
# file is not saved yet). A post is a dict with title, url, published
# (YYYY-MM-DD or None), category, text and full, plus "check_preview" when a
# short body may be a paid preview, and "paid" for a post a paywall cut.


def _read_feed(url, pacer=None):
    if pacer is not None:
        pacer.wait()
    posts = parse_feed(fetch(url))
    for post in posts:
        post["category"] = None
        post["check_preview"] = True
    return url, [{"post": post} for post in posts]


def _substack_archive(base, pacer):
    """Every post in a Substack publication's archive list, newest first, as
    the API's own dicts. Pages until a page is empty or brings no new post.
    A failed first page raises; a later one ends the list with a notice."""
    posts: list[dict] = []
    seen: set[str] = set()
    while True:
        url = "%s/api/v1/archive?sort=new&offset=%d&limit=%d" % (base, len(posts), SUBSTACK_PAGE)
        pacer.wait()
        try:
            page = json.loads(fetch(url))
            if not isinstance(page, list):
                raise ValueError("the archive list is not a JSON list")
        except FEED_ERRORS as e:
            if not posts:
                raise
            print(
                "  [archive] %s: the archive list stopped at %d posts: %s" % (base, len(posts), e),
                file=sys.stderr,
            )
            return posts
        new = [p for p in page if isinstance(p, dict) and p.get("slug") and p["slug"] not in seen]
        if not new:
            return posts
        seen.update(p["slug"] for p in new)
        posts.extend(new)


def _substack_post(base, entry, pacer):
    """Loads one Substack post's whole body. A post for paid subscribers
    arrives as its preview and is marked paid."""
    pacer.wait()
    data = json.loads(fetch("%s/api/v1/posts/%s" % (base, urllib.parse.quote(entry["slug"]))))
    if not isinstance(data, dict):
        raise ValueError("the post is not a JSON object")
    audience = str(data.get("audience") or entry.get("audience") or "everyone").lower()
    text = html_to_text(data.get("body_html") or "")
    return {
        "title": (data.get("title") or entry.get("title") or "").strip() or "Untitled",
        "url": data.get("canonical_url") or entry.get("canonical_url") or "",
        "published": _date(data.get("post_date") or entry.get("post_date"), iso=True),
        "category": None,
        "text": text,
        "full": bool(text),
        "paid": audience in PAID_AUDIENCES,
        "check_preview": True,
    }


def read_substack(value, options, taken):
    base = substack_base(value)
    pacer = Pacer(options.get("min_gap_seconds", DEFAULT_GAP_SECONDS))
    try:
        listing = _substack_archive(base, pacer)
    except FEED_ERRORS as e:
        print(
            "  [archive] %s: the archive list failed (%s); reading the RSS feed instead, "
            "which holds only recent posts" % (base, e)
        )
        return _read_feed(base + "/feed", pacer)
    items = []
    for entry in listing:
        if entry.get("type") == "thread":  # a discussion thread, not a post
            continue
        stub = {
            "title": (entry.get("title") or "").strip() or "Untitled",
            "published": _date(entry.get("post_date"), iso=True),
        }
        items.append(
            {
                "name": file_name(stub, taken),
                "title": stub["title"],
                "url": entry.get("canonical_url") or "%s/p/%s" % (base, entry["slug"]),
                "load": lambda entry=entry: _substack_post(base, entry, pacer),
            }
        )
    return "%s (archive)" % base, items


SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def _local(tag):
    return tag.rpartition("}")[2]


def parse_sitemap(raw):
    """("urlset", [(loc, lastmod)]) or ("sitemapindex", [(loc, lastmod)]) from
    a sitemap, gzipped or not. Raises ValueError when it is not a sitemap."""
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    body = raw.lstrip()
    if body.startswith(b"\xef\xbb\xbf"):
        body = body[3:].lstrip()
    if not body.startswith((b"<?xml", b"<urlset", b"<sitemapindex")):
        raise ValueError("the response is not a sitemap (starts %r)" % body[:40])
    root = ET.fromstring(body)
    kind = _local(root.tag)
    if kind not in ("urlset", "sitemapindex"):
        raise ValueError("unsupported sitemap root <%s>" % kind)
    entries = []
    for el in root:
        loc = lastmod = ""
        for child in el:
            if _local(child.tag) == "loc":
                loc = (child.text or "").strip()
            elif _local(child.tag) == "lastmod":
                lastmod = (child.text or "").strip()
        if loc:
            entries.append((loc, _date(lastmod, iso=True)))
    return kind, entries


def same_origin(url, sitemap):
    """True when `url` has the sitemap's own scheme and host. A file:// URL
    passes only from a file:// sitemap, so a sitemap read over the network
    can never point the script at a local file."""
    a, b = urllib.parse.urlparse(url), urllib.parse.urlparse(sitemap)
    if a.scheme != b.scheme or a.scheme not in ("http", "https", "file"):
        return False
    return a.scheme == "file" or _netloc(a) == _netloc(b)


def _sitemap_urls(url, pacer, depth=0, seen=None, origin=None):
    """[(loc, lastmod)] of every page in a sitemap, following a sitemap index
    two levels down. A nested sitemap on another scheme or host is skipped
    with a notice; one that fails is reported and skipped. An index none of
    whose sitemaps could be read raises ValueError."""
    seen = set() if seen is None else seen
    origin = origin or url
    seen.add(url)
    pacer.wait()
    kind, entries = parse_sitemap(fetch(url))
    if kind == "urlset":
        return entries
    pages = []
    tried = read = 0
    for loc, _ in entries:
        if loc in seen:
            continue
        if depth >= 2:
            print("  [skip] nested sitemap %s: more than two levels down" % loc)
            continue
        tried += 1
        if not same_origin(loc, origin):
            print("  [skip] nested sitemap %s: not on %s" % (loc, origin))
            continue
        try:
            pages.extend(_sitemap_urls(loc, pacer, depth + 1, seen, origin))
            read += 1
        except FEED_ERRORS as e:
            print("  [archive] sitemap %s failed: %s" % (loc, e), file=sys.stderr)
    if tried and not read:
        raise ValueError("none of the %d sitemap(s) in the index %s could be read" % (tried, url))
    return pages


def _sitemap_page(loc, lastmod, prefix, pacer):
    pacer.wait()
    title, published, text = extract_page(fetch(loc), fallback_date=lastmod)
    if len(text) < MIN_PAGE_CHARS:
        print("  [skip] %s has %d characters of text, likely a listing page" % (loc, len(text)))
        return None
    return {
        "title": title,
        "url": loc,
        "published": published,
        "category": category_from_url(loc, prefix),
        "text": text,
        "full": True,
    }


def read_sitemap(value, options, taken):
    prefix = options["path_prefix"]
    max_pages = options.get("max_pages", DEFAULT_MAX_PAGES)
    pacer = Pacer(options.get("min_gap_seconds", DEFAULT_GAP_SECONDS))
    pages: dict[str, str | None] = {}
    foreign = 0
    for loc, lastmod in _sitemap_urls(value, pacer):
        if same_origin(loc, value):
            pages.setdefault(loc, lastmod)
        else:
            foreign += 1
    if foreign and not pages:
        raise ValueError(
            "every page it lists (%d) is on another scheme or host than the sitemap" % foreign
        )
    if foreign:
        print("  [skip] %d page(s) not on the sitemap's own scheme and host" % foreign)
    paths = {loc: urllib.parse.urlparse(loc).path.rstrip("/") for loc in pages}
    inside = [
        loc for loc in pages if (paths[loc] + "/").startswith(prefix) and paths[loc] + "/" != prefix
    ]
    # A page whose path is the folder of other listed pages is that folder's
    # listing (/guides/ci-reliability next to /guides/ci-reliability/<page>).
    folders = {path.rsplit("/", 1)[0] for path in (paths[loc] for loc in inside)}
    listings = [loc for loc in inside if paths[loc] in folders]
    if listings:
        print("  [skip] %d folder page(s) that list other pages" % len(listings))
    keep = [loc for loc in inside if paths[loc] not in folders]
    keep.sort(key=lambda loc: (pages[loc] or "", loc), reverse=True)
    keep.sort(key=lambda loc: pages[loc] is None)  # stable: undated pages last
    print("  %s: %d pages under %s" % (value, len(keep), prefix))
    if len(keep) > max_pages:
        print("  [info] keeping the %d newest; raise max_pages for more" % max_pages)
        keep = keep[:max_pages]
    items = [
        {
            "name": page_file_name(loc, prefix, taken),
            "url": loc,
            "load": lambda loc=loc: _sitemap_page(loc, pages[loc], prefix, pacer),
        }
        for loc in keep
    ]
    return value, items


def _export_files(path, want):
    """(relative name, bytes) for each file in a zip or folder whose relative
    name (with / separators) `want` accepts, in name order. A leading ~ is
    the home folder."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        raise ValueError("%s not found" % path)
    if os.path.isdir(path):
        found = []
        for dirpath, _, names in os.walk(path):
            for name in names:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, path).replace(os.sep, "/")
                if want(rel):
                    found.append((rel, full))
        for rel, full in sorted(found):
            with open(full, "rb") as f:
                yield rel, f.read()
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            for info in sorted(zf.infolist(), key=lambda i: i.filename):
                if not info.is_dir() and want(info.filename):
                    yield info.filename, zf.read(info)
    else:
        raise ValueError("%s is neither a zip file nor a folder" % path)


def parse_medium_post(raw):
    """A post from one HTML file of Medium's export, or (reason, None) when it
    is not a published story: "draft" (no publish date), "response" (no
    title in its body, as Medium marks a story's) or "unrecognised"."""
    root = parse_html(raw.decode("utf-8", "replace"))
    body = root.find(
        lambda n: (
            n.tag == "section" and (n.attrs.get("data-field") == "body" or n.has_class("e-content"))
        )
    )
    if body is None:
        return "unrecognised", None
    published_el = root.find(lambda n: n.tag == "time" and n.has_class("dt-published"))
    published = _date(published_el.attrs.get("datetime"), iso=True) if published_el else None
    if not published:
        return "draft", None
    if body.find(lambda n: n.has_class("graf--title")) is None:
        return "response", None
    name_el = root.find(lambda n: n.has_class("p-name"))
    title = name_el.text() if name_el is not None else ""
    if not title:
        title_el = root.find(lambda n: n.tag == "title")
        title = title_el.text() if title_el is not None else ""
    canonical = root.find(lambda n: n.tag == "a" and n.has_class("p-canonical"))
    text = _drop_leading_title(html_to_text(_inner_html(body, PAGE_FURNITURE)), title)
    return "story", {
        "title": title or "Untitled",
        "url": canonical.attrs.get("href", "") if canonical is not None else "",
        "published": published,
        "category": None,
        "text": text,
        "full": True,
    }


def read_medium_export(value, options, taken):
    counts = {"draft": 0, "response": 0, "unrecognised": 0}
    items = []
    seen_any = False
    for rel, raw in _export_files(
        value, lambda rel: bool(re.search(r"(?:^|/)posts/[^/]+\.html?$", rel, re.I))
    ):
        seen_any = True
        if os.path.basename(rel).lower().startswith("draft"):  # draft_<title>-<id>.html
            counts["draft"] += 1
            continue
        kind, post = parse_medium_post(raw)
        if post is None:
            counts[kind] += 1
            if kind == "unrecognised":
                print("  [skip] %s: not a Medium post this script recognises" % rel)
            continue
        items.append({"post": post})
    if not seen_any:
        raise ValueError("no posts/*.html in %s; is it Medium's export?" % value)
    labels = {
        "draft": "draft(s)",
        "response": "response(s)",
        "unrecognised": "unrecognised file(s)",
    }
    skipped = ", ".join("%d %s" % (n, labels[k]) for k, n in counts.items() if n)
    if skipped:
        print("  %s: skipped %s" % (value, skipped))
    return value, items


LINKEDIN_TITLE_WORDS = 8


def parse_linkedin_shares(raw):
    """Posts from LinkedIn's Shares.csv (columns Date, ShareLink,
    ShareCommentary). Rows with no commentary are left out. Raises
    ValueError when the file has no ShareCommentary column."""
    try:
        rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig", "replace"))))
    except csv.Error as e:
        raise ValueError("not a CSV file this script can read: %s" % e) from e
    header = None
    for i, row in enumerate(rows[:5]):
        cells = [c.strip().lower() for c in row]
        if "sharecommentary" in cells:
            header = i, cells
            break
    if header is None:
        raise ValueError("no ShareCommentary column")
    start, cells = header
    col = {
        name: cells.index(name)
        for name in ("date", "sharelink", "sharecommentary")
        if name in cells
    }
    posts, empty = [], 0
    for row in rows[start + 1 :]:

        def cell(name, row=row):
            i = col.get(name)
            return row[i].strip() if i is not None and i < len(row) else ""

        text = cell("sharecommentary")
        if not text:
            empty += 1
            continue
        date = cell("date")
        published = date[:10] if re.match(r"\d{4}-\d{2}-\d{2}", date) else _date(date, iso=False)
        words = text.split()
        title = " ".join(words[:LINKEDIN_TITLE_WORDS])
        posts.append(
            {
                "title": title + (" …" if len(words) > LINKEDIN_TITLE_WORDS else ""),
                "url": cell("sharelink"),
                "published": published,
                "category": None,
                "text": text,
                "full": True,
                "slug_title": title,
            }
        )
    return posts, empty


def read_linkedin_export(value, options, taken):
    items: list[dict] = []
    empty = recognised = 0
    for rel, raw in _export_files(value, lambda rel: os.path.basename(rel).lower() == "shares.csv"):
        try:
            posts, n_empty = parse_linkedin_shares(raw)
        except ValueError as e:
            print("  [skip] %s: %s" % (rel, e))
            continue
        recognised += 1
        empty += n_empty
        items.extend({"post": post} for post in posts)
    if not recognised:
        raise ValueError("no Shares.csv with a ShareCommentary column in %s" % value)
    if empty:
        print("  %s: skipped %d rows with no text" % (value, empty))
    return value, items


def read_medium(value, options, taken):
    return _read_feed(feed_url({"medium": value}))


def read_rss(value, options, taken):
    return _read_feed(feed_url({"rss": value}))


READERS = {
    "medium": read_medium,
    "substack": read_substack,
    "rss": read_rss,
    "sitemap": read_sitemap,
    "medium_export": read_medium_export,
    "linkedin_export": read_linkedin_export,
}


def load_profile(path):
    """(archive_dir, [(type, value, options)]) from a writer profile; exits
    with a message on any config error, before anything is fetched."""
    try:
        import yaml
    except ImportError:
        sys.exit(
            "Missing dependency: PyYAML. Install it with:\n"
            "  pip install -r packages/scanner-core/requirements.txt"
        )
    if not os.path.exists(path):
        sys.exit("Writer profile not found: %s" % path)
    with open(path) as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        sys.exit("Writer profile %s is empty or not a YAML mapping." % path)
    archive_dir = raw.get("archive_dir")
    if not archive_dir or not isinstance(archive_dir, str):
        sys.exit("Set `archive_dir` in %s: the folder the posts are saved to." % path)
    sources = raw.get("archive_sources")
    if not sources or not isinstance(sources, list):
        sys.exit(
            "Set `archive_sources` in %s: a list of `substack:`, `medium:`, `medium_export:`, "
            "`linkedin_export:`, `sitemap:` or `rss:` entries (see "
            "writer-profile.example.yaml)." % path
        )
    parsed = []
    for source in sources:
        try:
            parsed.append(parse_source(source))
        except ValueError as e:
            sys.exit("archive_sources in %s: %s" % (path, e))
    return archive_dir, parsed


def _warn_thin(name, post, archive_dir):
    if post.get("paid"):
        print(
            "  [warn] %s is for paid subscribers, so only its preview was saved. Paste the "
            "full post into %s for a better voice example." % (name, archive_dir)
        )
    elif not post["full"]:
        print(
            "  [warn] %s: the feed carries only a summary of this post. Paste "
            "the full post into %s for a better voice example." % (name, archive_dir)
        )
    elif post.get("check_preview") and len(post["text"]) < PREVIEW_CHARS:
        print(
            "  [warn] %s has %d characters of text; it may be a preview only "
            "(a paid post). Paste the full post into %s if it is."
            % (name, len(post["text"]), archive_dir)
        )


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--profile", required=True, help="writer profile with archive_sources")
    ap.add_argument(
        "--dry-run", action="store_true", help="list what would be saved, write nothing"
    )
    ap.add_argument(
        "--refresh",
        action="store_true",
        help="rewrite files already in archive_dir from the source (hand edits are lost)",
    )
    args = ap.parse_args()

    archive_dir, sources = load_profile(args.profile)
    index: dict[str, dict] = {}
    if os.path.isdir(archive_dir):
        try:
            index = load_index(archive_dir)
        except ValueError as e:
            sys.exit(
                "%s\n  -> fix it, or delete it to build a new one (content types are lost)." % e
            )
    if os.path.isdir(archive_dir):
        sync_index(archive_dir, index)  # files saved before the index get their header URL
    # "Already saved" is decided by a post's URL; a file whose index entry has
    # no URL (added by hand) is matched by its name.
    by_url: dict[str, str] = {}
    by_title: dict[
        tuple, str
    ] = {}  # (date, title) of a saved post with no URL, from a feed without links
    for n, entry in index.items():
        for u in (entry.get("url"), entry.get("listed_url")):
            if u:
                by_url[url_key(u)] = n
        if not entry.get("url") and entry.get("title"):
            by_title[(entry.get("published"), entry["title"])] = n
    taken: set[str] = set()
    new = kept = failed = 0
    for kind, value, options in sources:
        try:
            label, items = READERS[kind](value, options, taken)
        except FEED_ERRORS as e:
            failed += 1
            print("  [archive] %s failed: %s" % (value, e), file=sys.stderr)
            continue
        source_new = source_kept = skipped = page_failed = 0
        for item in items:
            post = item.get("post")
            if post is not None:
                stub = dict(post, title=post.get("slug_title") or post["title"])
                name = file_name(stub, taken)
            else:
                name = item["name"]
            url = (post["url"] if post is not None else item.get("url")) or None
            if url:
                saved_as = by_url.get(url_key(url))
            else:
                saved_as = by_title.get((post["published"], post["title"])) if post else None
            if saved_as and os.path.exists(os.path.join(archive_dir, saved_as)):
                if not args.refresh:
                    source_kept += 1
                    continue
                name = saved_as
            elif os.path.exists(os.path.join(archive_dir, name)):
                entry = index.get(name) or {}
                owner, owner_title = entry.get("url"), entry.get("title")
                # Another post may hold this name (a long title cut to the
                # same 60 characters, on the same date): this one then gets a
                # name of its own, from a short hash of its URL, or of its
                # title when neither post has a URL.
                # When exactly one of the two has a URL, the titles decide: a
                # different title is a different post (a link-less "Hello!"
                # beside a linked "Hello?"); the same title is the same post,
                # a link added or lost later.
                other = None
                title = post["title"] if post is not None else item.get("title")
                if owner and url and url_key(owner) != url_key(url):
                    other = url
                elif not owner or not url:
                    if owner_title and title and owner_title != title:
                        other = url or title
                if other is not None:
                    name = "%s-%s.md" % (
                        name[:-3],
                        hashlib.sha1(other.encode("utf-8")).hexdigest()[:8],
                    )
                    taken.add(name)
                if os.path.exists(os.path.join(archive_dir, name)) and not args.refresh:
                    source_kept += 1
                    continue
            path = os.path.join(archive_dir, name)
            if post is None:
                if args.dry_run:
                    source_new += 1
                    print("  would fetch %s -> %s" % (item["url"], name))
                    continue
                try:
                    post = item["load"]()
                except FEED_ERRORS as e:
                    page_failed += 1
                    print("  [archive] %s failed: %s" % (item["url"], e), file=sys.stderr)
                    continue
                if post is None:
                    skipped += 1
                    continue
            source_new += 1
            _warn_thin(name, post, archive_dir)
            if args.dry_run:
                print("  would write %s (%d characters)" % (name, len(post["text"])))
                continue
            os.makedirs(archive_dir, exist_ok=True)
            text = render(post)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            old = index.get(name) or {}
            index[name] = index_entry(
                text,
                title=post["title"],
                url=post["url"] or None,
                published=post["published"],
                category=post.get("category"),
                content_type=old.get("content_type"),
                fetched=True,
            )
            listed = item.get("url")
            if listed and post["url"] and url_key(listed) != url_key(post["url"]):
                # Substack lists one URL and serves the post under another:
                # both are this file's, so neither causes a second copy.
                index[name]["listed_url"] = listed
            for u in (post["url"], listed):
                if u:
                    by_url[url_key(u)] = name
            if not post["url"]:
                by_title[(post["published"], post["title"])] = name
        extra = "".join(
            ", %d %s" % (n, what)
            for n, what in ((skipped, "skipped"), (page_failed, "failed"))
            if n
        )
        print(
            "  %s: %d posts, %d new, %d already saved%s"
            % (label, len(items), source_new, source_kept, extra)
        )
        new += source_new
        kept += source_kept
        if page_failed and not (source_new or source_kept or skipped):
            failed += 1  # every page this source listed failed

    if not args.dry_run and os.path.isdir(archive_dir):
        sync_index(archive_dir, index)
        save_index(archive_dir, index)
        untagged = sum(1 for e in index.values() if not e.get("content_type"))
        if untagged:
            print(
                "  tag index: %d posts, %d without a content type; run archive_tag.py "
                "--profile %s" % (len(index), untagged, args.profile)
            )
    print(
        "%s%d new, %d already saved, %d source(s) failed -> %s"
        % ("[dry run] " if args.dry_run else "", new, kept, failed, archive_dir)
    )
    if failed and failed == len(sources):
        sys.exit("Every archive source failed, so nothing was saved.")


if __name__ == "__main__":
    main()
