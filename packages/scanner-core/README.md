# scanner-core

scanner-core finds recent posts on Hacker News, Reddit, Product Hunt and X that match your keywords, and returns them as JSON. content-engine uses it for its scans, and you can also run it on its own from the command line or import it in Python.

## Contents

- [What it does](#what-it-does) lists the platforms and what each needs.
- [Quick start](#quick-start) runs a Hacker News search with a five-line config.
- [Config](#config) describes the keys each platform reads.
- [Output](#output) describes the JSON it returns.
- [Using it from Python](#using-it-from-python) shows the library functions.
- [Before you rely on it](#before-you-rely-on-it) covers the limits worth knowing.
- [Tests](#tests) covers the offline test suite.

## What it does

| Platform | What it needs | How it searches |
|---|---|---|
| Hacker News | Nothing | Exact-phrase search through the public Algolia API |
| Reddit | Nothing | The public RSS feeds of the subreddits you list, new and hot |
| Product Hunt | A free developer token | The official GraphQL API, for today's board (or a rolling window) with optional voter/commenter details (off in the example config) |
| X | A paid bearer token | The v2 recent-search API, for up to the last 7 days |

It only fetches. It keeps no state between runs, so every run returns what it finds inside the time window, up to each platform's cap, and deciding what's new is up to you. Every result carries the platform's own id, so you can dedupe on that rather than on the URL.

## Quick start

You need Python 3.9 or newer.

```sh
pip install -r requirements.txt
```

Save this as `keywords.yaml`:

```yaml
lookback_hours: 48
hn:
  tags: [story]
  min_points: 20
keywords:
  broad: ["python"]
subreddits: []
```

Then run:

```sh
python3 scanner_core.py --config keywords.yaml --platform hn
```

Progress goes to stderr and the results go to stdout as JSON:

```
Scanning Hacker News (last 48h)...
  [hn] 2 candidates
{
  "candidates": [
    {
      "id": "hn:00000001",
      "platform": "hn",
      "type": "story",
      "title": "…",
      "url": "https://news.ycombinator.com/item?id=00000001",
      "points": 42,
      "num_comments": 7,
      "created_at": "2026-10-06T09:00:00Z",
      "matched_keywords": [["python", "broad"]]
    }
  ],
  "failures": [],
  "generated_at": "2026-10-07T10:02:11+00:00"
}
```

The output above is shortened. Add `--out-dir <folder>` to write a dated file such as `hn-candidates-2026-10-07.json` instead of printing.

## Config

One YAML file per run, passed with `--config`. Each platform reads its own keys and ignores the rest.

| Key | Used by | Meaning |
|---|---|---|
| `lookback_hours` | Hacker News, Reddit | How far back to look. Default 48. |
| `keywords` | Hacker News, Reddit | Named groups of phrases, such as `precise` or `broad`. A match is reported with its group name. |
| `hn` | Hacker News | `tags` (any of `story`, `show_hn`, `ask_hn`) and `min_points`. |
| `subreddits` | Reddit | A list of `{name: <subreddit>}` entries. |
| `reddit_min_gap_seconds` | Reddit | Seconds between Reddit requests. Default 10. |
| `reddit_budget_seconds` | Reddit | Total pacing/retry budget per scan, default 240 seconds; finite number from 1 to 480. Unfinished feeds are recorded in `failures`, completed results retained. |
| `ph` | Product Hunt | Topics, keywords, page limits, the token's variable name, and `window`: `ph_day` (today's board, the default) or `lookback` (the last `lookback_hours`). |
| `twitter` | X | `seed_queries`, `lookback_hours`, `max_results_per_query` and the token's variable name. |

Complete, commented examples:

- [`../content-engine/hn-reddit-scan.example.yaml`](../content-engine/hn-reddit-scan.example.yaml) for Hacker News and Reddit.
- [`../content-engine/ph.example.yaml`](../content-engine/ph.example.yaml) for Product Hunt.
- The commented `twitter:` block in [`../content-engine/config.example.yaml`](../content-engine/config.example.yaml) for X.

Tokens are read from the environment, or from a `.env` file next to the config. Use `--env <path>` to point at a different file. The variables are `PH_API_TOKEN` and `TWITTER_BEARER_TOKEN`.

`--platform` takes `hn`, `reddit`, `ph`, `twitter` or `all`. With `all`, a platform whose config block is missing is skipped without an error, and a platform that fails (a missing token, a rejected token) is skipped and listed in `failures`. Asked for by name, a missing block or token stops the run with an error.

`--max-subreddits <n>` scans only the first n subreddits of the config, for a quick preview.

## Output

Every candidate has an `id` and a `platform`. The `id` is the platform's own id with a prefix, such as `hn:00000001` or `reddit:t3_abc`, so dedupe on it. The other fields differ by platform.

| Platform | Fields |
|---|---|
| Hacker News | `type`, `title`, `url`, `external_url`, `text_excerpt`, `points`, `num_comments`, `author`, `created_at`, and `matched_keywords` as `[phrase, group]` pairs |
| Reddit | `subreddit`, `type`, `title`, `url`, `text_excerpt`, `author`, `created_at`, and `matched_keywords` as `[phrase, group]` pairs. `score` and `num_comments` are always null, because the feeds do not carry them |
| Product Hunt | `ph_id`, `name`, `tagline`, `description_excerpt`, `ph_url`, `website`, `votes_count`, `comments_count`, `created_at`, `topics`, `matched_keywords` as plain phrases, `fit_topics_matched`, `makers`, `top_voters`, `top_commenters`, `discussion`, `pool_redacted` |
| X | `url`, `text_excerpt`, `raw_metric` (likes, retweets, replies, quotes), `published_at`, `fetched_at`, and `matched_keywords` as `[query, "search_query"]` pairs |

Beside `candidates`, the output has `failures`: one entry per request that failed, with its `platform`, the `request` (a keyword, a feed, a query) and the `error`. An empty list means every request answered. A platform with no candidates and no failures found nothing in the window.

## Using it from Python

```python
import time
import scanner_core as sc

cfg = {"hn": {"tags": ["story"], "min_points": 20}, "keywords": {"broad": ["python"]}}
since = int(time.time()) - 48 * 3600
for post in sc.scan_hn(cfg, since):
    print(post["points"], post["title"])
```

| Function | Arguments |
|---|---|
| `scan_hn(cfg, since_ts, failures=None)` | Config and a Unix timestamp |
| `scan_reddit(cfg, since_ts, failures=None)` | Config and a Unix timestamp |
| `scan_ph(cfg, token, since_iso, failures=None)` | Config, token and an ISO 8601 time. A failed topic page is recorded and the next topic runs |
| `fetch_details(cfg, token, candidates, failures=None)` | Config, token and the `scan_ph` results to enrich |
| `scan_twitter(cfg, token, since_iso, failures=None)` | Config, token and an ISO 8601 time |

Pass a list as `failures` to collect each failed request, as the command line does for its output.

Importing the module needs no dependencies. Only the command line needs PyYAML.

## Before you rely on it

- **Reddit is slow without an account.** Reddit allows about one feed request every 10 seconds per IP address. Requests are spaced to match, and after a "rate-limited" reply the scanner waits the time Reddit asks for. Each subreddit costs two requests.
- **X costs money and only looks back 7 days.** A longer `lookback_hours` is cut to 7 days. Each query returns one page of results.
- **Product Hunt and X haven't been run against the live APIs.** Their tests use response shapes written from the API documentation, not recorded traffic. Check them with your own token before depending on them.
- **Hacker News search matches exact phrases.** A typo or a different word form won't match.
- **Hacker News returns 50 hits per keyword.** One request per keyword is a design choice. When more match in the window, the rest are left out and the keyword gets a `truncated: 50 of <n> hits` entry in `failures`.
- **Reddit feeds hold 100 entries.** Each subreddit's new and hot feeds serve at most 100 posts each, a limit of Reddit's feeds.

## Tests

```sh
python3 -m unittest discover -s tests
```

The tests need no network and no tokens: a guard blocks every connection and points `HOME` at a temp folder. Every HTTP call is stubbed. They cover each platform's normalisation, Reddit's dates and request pacing, Product Hunt's window, fit gate and detail fetch, X result handling, keyword layers, `.env` parsing, config errors and the `failures` list. Live calls are left to manual runs like the Quick start, so the suite never fails because a website is slow.

Reddit requests run in short-lived workers so a deadline can stop DNS, connection,
header and body stalls. A worker is terminated and joined on expiry; previously
completed feeds remain in the output. Each feed response is limited to 8 MiB.
`scan_reddit` uses this transport automatically; the internal worker flag is not
a separate user workflow. No external credentials are required or read by it.
