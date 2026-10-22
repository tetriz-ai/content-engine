# content-engine package

This package holds the configuration, writing rules and helper scripts that `/content-engine` uses. To set it up and run it, follow the [Quick start in the root README](../../README.md#quick-start). This page is the reference for tuning it.

## Contents

- [Files](#files) says what each file in this folder is for.
- [Changing what it does](#changing-what-it-does) maps each change to the setting that controls it.
- [Theme docs](#theme-docs) describes the file behind each approval card.
- [Drafts](#drafts) describes the draft format and how to plug in your own writer.
- [Running the scripts directly](#running-the-scripts-directly) shows each script's command line.
- [Tests](#tests) covers the offline test suite.

## Files

| File | What it's for |
|---|---|
| `.env.example` | Template for `.env`, the one file you edit by hand: your Slack ID and optional keys. |
| `config.example.yaml` | Template for `config.yaml`: sources, thresholds and per-format settings. The first run writes your copy. |
| `hn-reddit-scan.example.yaml` | Template for the Hacker News and Reddit keywords and subreddits. |
| `ph.example.yaml` | Template for the Product Hunt topics and keywords. Only used with a Product Hunt token. |
| `context.example.md` | Template for `context.md`, a short description of what's relevant to you. Grouping reads it to judge relevance, and each theme doc notes the part of it the theme speaks to. |
| `writer-profile.example.yaml` | Optional. Your topics and a folder of your past posts, for scored relevance and for matching your writing voice. |
| `rules.md` | The writing rules. Every draft follows them over any other instruction. |
| `write_reference.py` | Opt-in single-prompt reference writer; full Blog/Editorial Draft drafting lives in native skills. |
| `archive_fetch.py` | Optional. Saves your own posts into the writer profile's `archive_dir`, for voice matching: a whole Substack archive, Medium's or LinkedIn's data export, one folder of a site's sitemap, or a feed. |
| `archive_tag.py` | Optional. Tags each saved post once with one of the profile's `content_types`, so drafts get examples of the same kind. |
| `relevance_scorer.py` | Optional. Scores a theme from 0 to 10 against your writer profile. |
| `competitor-blog-scan.py` | Reads the competitor blog RSS feeds listed in `config.yaml`, and exits with a message when none are listed. |
| `report.py` | Counts signals per source and themes per status. |
| `examples/` | A signal bank, a theme doc and a draft for a made-up product. |

The templates use a made-up product, a dashboard for flaky CI tests, so every file shows realistic values. Your own copies replace them on the first run.

## Changing what it does

Edit your own copies (`config.yaml`, `hn-reddit-scan.yaml`, `context.md`), never the `.example` files. Run `/content-engine --dry-run` after a change to preview its effect.

| To change | Edit |
|---|---|
| The keywords and subreddits searched | `hn-reddit-scan.yaml`, under `keywords` and `subreddits` |
| The news and Medium/Substack search queries | `config.yaml`, `scan.news.queries` |
| Which competitor blogs are read | `config.yaml`, `scan.competitor_blogs.feeds`. Check each feed URL loads before adding it. |
| How far back each source looks | `lookback_hours` in `hn-reddit-scan.yaml`, and `lookback_days` under `scan.news` and `scan.competitor_blogs` |
| What counts as relevant | `context.md`, or `cluster.writer_profile` for a scored check (one extra model call per theme) |
| How many posts make a theme | `cluster.min_signals_per_theme` (default 2) |
| What counts as STRONG | `brief.coverage_tier` (default 3 posts from 2 sources) |
| How soon a topic can come back | `brief.dedupe_window_days` (default 21) |
| The bar for LinkedIn and proper-length videos | `brief.format_eligibility.linkedin`: `personal_requires` (default STRONG) for a post under your own name, the margin settings for a company voice and for proper-length videos |
| How LinkedIn posts sound | `write.linkedin.voice_override` (`pov: personal` for your own first person, the default; `pov: company` for the company's "we") and `word_count_target` |
| Matching your own writing voice | `write.voice_profile`, pointing at a writer profile with an `archive_dir` of your past posts; its `archive_sources` lets `archive_fetch.py` fill that folder |
| The kinds of post a draft can be | `content_types` in the writer profile. `archive_tag.py` tags each saved post with one, and each theme gets one |
| How many past posts a draft copies | `max_examples` in the writer profile (default 5): same content type first, then same category, then the closest type |
| How much of each past post is read | Each example is read whole, up to `archive_max_chars` (default 100000) in all. `excerpt_chars` cuts each one when set. The scorer cuts each post at 6,000 characters and reads up to 60,000 in all. |
| Your own opinion in a draft | An `## Author's take` section in the theme doc, or a reply in the Slack card's thread |
| Changes to make in a draft | A `## Requested changes` section in the theme doc, or a ✏️ on the Slack card with replies saying what to change |
| SEO title, meta description and keywords on blog drafts | `write.blog.seo_optimize: true` |
| The model used for drafts | `write.model`, or `write.<format>.model` for one format |
| What drafts may claim | `rules.md` |

Reddit requests are spaced `reddit_min_gap_seconds` apart (default 10, in `hn-reddit-scan.yaml`). Raise it if you still see "rate-limited" lines, for example on a shared office network.

## Theme docs

Each theme becomes `docs/content-themes/theme-<date>-<slug>.md`. These fields at the top drive the approval flow.

| Field | Meaning |
|---|---|
| `Status` | `proposed`, then `approved`, `rejected` or `needs_edit`, then `written` once every approved format has a draft. `write_reference.py` refuses any other status in code, and the other routes are told to. |
| `Coverage tier` | `STRONG` (3+ posts from 2+ sources) or `THIN`. Anything else is drafted, and counted by `report.py`, as `THIN`, with a warning. |
| `Category` | A category from the archive's tag index (the folder of a post's URL, like `ci-reliability`), or `none`. |
| `Content type` | One of the writer profile's `content_types`, or `none`. The writer's voice examples are posts of this type first. |
| `Closest type in archive` | Only when no saved post has the content type: the most similar type that one has. |
| `Formats suggested` | The formats the evidence supports. A 👍 approves exactly these. |
| `Formats approved` | What gets drafted. Edit it by hand to approve without Slack. |
| `Slack card` | Where the approval card was posted, or `none`. |

Below the fields come the rationale, the evidence table, a "Do not say" list and an output table that tracks each draft. [`examples/theme-example-ci-flakiness.md`](examples/theme-example-ci-flakiness.md) is a complete one.

## Drafts

A draft is a Markdown file with frontmatter, saved to `docs/content-themes/drafts/`.

```
---
status: draft
format: blog
source_theme_doc: "docs/content-themes/theme-2026-10-03-flaky-tests.md"
generated_at: 2026-10-07T09:12:44+00:00
drafted_by: "claude-sonnet-5"
---
```

`drafted_by` records the actual host/model or custom adapter. Default Blog/LinkedIn drafts use the bundled skills with real editorial review receipts; `write_reference.py` is an explicit opt-in single-prompt alternative. Blog drafts with the SEO pass on also carry `seo_title`, `meta_description` and `target_keywords`.

The three formats are a blog post, a LinkedIn post, and a video brief. A video brief holds the topic, angle, hook, key facts and target viewer, not a full script.

**Using your own writer.** Set `write.<format>.command` to any program that takes `--theme-doc <path> --format <blog|linkedin|video> --out <path>` and writes a draft in the format above. It must never publish anything. [`examples/plug-in-your-own-writer`](../../examples/plug-in-your-own-writer/) is a complete one.

## Running the scripts directly

The run uses these helpers for the selected phase. `write_reference.py` runs only when explicitly selected. From an imported installation, invoke helpers by absolute engine path with the caller’s working directory and explicit config; resource files stay in the engine and state stays in the caller.

```sh
# Preview the exact drafting prompt for a theme, without calling any model
python3 packages/content-engine/write_reference.py \
  --theme-doc packages/content-engine/examples/theme-example-ci-flakiness.md \
  --format blog --dry-run

# Write a draft (uses ANTHROPIC_API_KEY from .env or the environment)
python3 packages/content-engine/write_reference.py \
  --theme-doc <theme doc> --format blog --out <draft path>

# Signal and theme counts
python3 packages/content-engine/report.py --config packages/content-engine/config.yaml

# Read the competitor blog feeds
python3 packages/content-engine/competitor-blog-scan.py

# Save your past posts, then tag each by type (add --dry-run to either first)
python3 packages/content-engine/archive_fetch.py --profile <writer profile>
python3 packages/content-engine/archive_tag.py --profile <writer profile>

# Score a theme against your writer profile (add --dry-run to see the prompt)
python3 packages/content-engine/relevance_scorer.py \
  --profile packages/content-engine/writer-profile.example.yaml \
  --title "Flaky tests are a quiet tax" --rationale "Three posts on CI re-runs this week"
```

`write_reference.py` also takes `--config <config.yaml>` to apply the `write` settings, `--profile <writer profile>` for voice matching, `--seo` for the blog SEO pass, `--model` to pick a model, `--length short|proper` for video briefs, and `--response-file` to turn a model answer you already have into a draft file. A theme doc is refused unless `## Signals` holds a table row or list item with the post's http(s) URL, and an empty or cut-off answer writes no draft.

## Tests

```sh
cd packages/content-engine
python3 -m unittest discover -s tests
```

The suite needs no network and no keys: a guard blocks every connection, unsets the keys and points `HOME` at a temp folder. It covers the example configs, theme-doc parsing, prompt assembly with every `write` setting, the setting priority order, `.env` key loading, the competitor blog reader, the report counts and the relevance scorer's parsing and exit code. It also covers the archive sources against a fake web and sample exports, the tagging answers, and how voice examples are picked.
