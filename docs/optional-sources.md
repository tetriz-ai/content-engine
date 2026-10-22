# Optional sources

Hacker News and Reddit need nothing from you, and competitor blogs need only a feed URL in `config.yaml`. The sources on this page each need something extra, and the run turns each one on only when that is there. Every run starts by printing its source plan, one line per source, with on or off and the reason.

Every source writes rows to the signal bank, `context-library/content-signal-bank.jsonl`, one JSON object per line. The fields that matter here are `source`, `native_id` (the dedupe key), `url`, `title`, `excerpt`, `raw_metric`, `published_at`, `fetched_at` and `theme_id`.

## Semrush

**Prerequisites.** A Semrush account and a Semrush MCP server connected to Claude Code, plus a `scan.semrush` block in `config.yaml`. It needs `seed_keywords`, `competitor_domains` and `database`, the regional database such as `us`.

**What it outputs.** For each seed keyword, search volume and trend. For your competitors' domains, the keywords they rank for that you do not.

Each finding becomes a bank row like a news row. Its `native_id` falls back to a normalised URL or the topic, because Semrush results have no stable id, and the numbers go in `raw_metric`.

**When it fails or is missing.** With no MCP server, or an empty `scan.semrush`, the run skips Semrush and says so in its summary. A report that fails is listed as a failed source and the other sources carry on. Tool names vary between MCP servers, so the run checks what yours exposes rather than assuming one.

## AEO report (Semrush)

**Prerequisites.** Everything Semrush needs, `scan.semrush.aeo_check: true`, and a Semrush MCP server that exposes an AI-overview or answer-engine visibility report.

**What it outputs.** Whether your content shows up in AI answers for the same seed keywords. The rows look like the other Semrush rows. They only inform which themes get picked.

**When it fails or is missing.** With `aeo_check` false or unset, the report never runs. When the server has no such report, the run says so and skips it.

## SEO pass (blog drafts)

This one is on the writing side, not a source.

**Prerequisites.** `write.blog.seo_optimize: true` in `config.yaml`, or `--seo` on `write_reference.py`. Blog drafts only.

**What it outputs.** A blog draft whose frontmatter also carries `seo_title`, `meta_description` and `target_keywords`, inferred only from the theme doc. The draft opens with a direct answer and uses scannable subheadings. A requested change on the theme can override that layout.

**When it fails or is missing.** Off by default. With it on, an answer without exactly one `---BODY---` marker writes no draft and exits non-zero, because the metadata and the body cannot be told apart.

## Google Trends

**Prerequisites.** `scan.google_trends.keywords` in `config.yaml`. Google Trends has no public API, so the agent reads it.

**What it outputs.** One row per keyword per run, with `native_id` `trends:<keyword>:<date>`. Its `raw_metric` records how the trend was read and its direction.

`{"method": "screenshot", "direction": "rising"}` means the agent opened the Trends chart in a browser tool and read it. `{"method": "websearch-fallback", "direction": "rising"}` means no browser tool was available and the agent read third-party pages from a web search, a weaker signal.

**When it fails or is missing.** With no keywords, Trends is skipped. A row without `raw_metric.method` is incomplete, and the command tells the agent to fix it before appending. No code writes Trends rows, so this rule lives in the command file only.

## Product Hunt

**Prerequisites.** `PH_API_TOKEN` in `packages/content-engine/.env` (a free developer token) and a `ph.yaml` from `ph.example.yaml`.

**What it outputs.** Launches matching your keywords or fit topics, through the official GraphQL API, with `native_id` `ph:<id>`.

**When it fails or is missing.** Without a token, Product Hunt is off. A rejected token or the rate limit stops Product Hunt only, and each failed request is listed under `failures` in the scan output.

## X

**Prerequisites.** `TWITTER_BEARER_TOKEN` in `.env` and a `scan.twitter` block. X has no free tier, so this costs money.

**What it outputs.** Posts from the recent-search API, up to 7 days back, one page per query, with `native_id` `twitter:<id>`.

**When it fails or is missing.** Without a token, X is off. A failed query, an API error or a page with more results than one page holds is listed under `failures`.

## Source access and terms

Use each source only with authorization and under its applicable terms, rate limits
and reuse rules. Public availability is not permission for every downstream use.
Reddit RSS uses an honest scanner identity; a 403 or other denial is a failed source,
not a reason to impersonate a browser or bypass the restriction. Use an authorized
access method separately if RSS is unavailable. Review [Reddit's terms](https://redditinc.com/policies/user-agreement)
and [Data API terms](https://redditinc.com/policies/data-api-terms) before a live run.

Product Hunt uses the official API with your own token. Review its
[API documentation and terms](https://api.producthunt.com/v2/docs) for your intended
use, including commercial use. The example sets `detail_fetch_top: 0`, so it fetches
launch metadata without voter/commenter profiles or discussion excerpts. Existing
output keys remain empty. Increase that setting only when those details are needed
and you have reviewed the access, privacy and retention requirements. The Content
Engine drafting workflow does not require those personal details.
