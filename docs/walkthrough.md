# Walkthrough: one theme, end to end

This follows one theme through a run, using the example files that ship with the repo. The product is made up: a dashboard for flaky CI tests. Every excerpt below is copied from those files.

## 1. Signals land in the bank

A scan saves each new post as one line of `context-library/content-signal-bank.jsonl`. The bundled bank, [`packages/content-engine/examples/content-signal-bank.example.jsonl`](../packages/content-engine/examples/content-signal-bank.example.jsonl), holds three. Here is the first, trimmed:

```json
{"id": "hn:00000001", "source": "hn", "native_id": "hn:00000001", "url": "https://news.ycombinator.com/item?id=00000001", "title": "Show HN: We cut our flaky-test rate by tagging non-deterministic failures automatically", "raw_metric": {"points": 42}, "published_at": "2026-10-01T14:00:00Z", "theme_id": null}
```

The other two are a Reddit thread in r/ExperiencedDevs and a competitor's survey of 400 teams. `theme_id` is `null`, so all three are unspent and the next grouping step may use them.

## 2. The agent groups them into a theme

Grouping and grading are done by the host session, following the command file, not by code. These three posts share one pain, re-running flaky builds, so they become one theme. With 3 posts from 3 sources the theme is STRONG under the example config's `brief.coverage_tier`.

The brief step writes the theme doc. The bundled one is [`packages/content-engine/examples/theme-example-ci-flakiness.md`](../packages/content-engine/examples/theme-example-ci-flakiness.md). Its header, trimmed:

```markdown
# Theme: Flaky Tests Are a Quiet, Measurable Tax on CI Throughput

**Status:** approved
**Coverage tier:** STRONG
**Formats suggested:** [blog, linkedin, video]
**Formats approved:** [blog, linkedin, video]
```

Below the header come the rationale, the signals table with each post's URL, and a "Do not say" list. One of its entries reads: "Don't imply the HN tool (tag-and-rerun) is a complete fix — the post itself says it reduced false-reds by 'about a third,' not eliminated them."

In a real run the doc starts as `**Status:** proposed`. The example shows it after approval.

## 3. A card goes to Slack, and you react

With Slack connected, the brief step posts one card per theme to the destination in `.env`, in this format:

```text
📋 THEME · coverage: STRONG · formats suggested: blog, linkedin, video
"Flaky Tests Are a Quiet, Measurable Tax on CI Throughput"
Why now: <one-line rationale>
Signals (3): <top 2-3 titles with source tags>

👍 approve · ✏️ approve with changes (reply with what to change) · 👎 reject · 💬 needs edit
```

On the next run, the approval step reads the reactions.

👍 sets `**Status:** approved` and copies the suggested formats into `**Formats approved:**`. ✏️ does the same once you have replied with the changes, and puts each reply under `## Requested changes`.

A thread reply on a 👍 becomes `## Author's take`. Without Slack, you edit `**Status:**` and `**Formats approved:**` yourself.

## 4. The approved formats are drafted

The next run drafts each approved format that has no draft yet: the blog post through Blog and Editorial Draft in the host session, unless `write.<format>.command` picks the reference or a custom writer.

Every route is told to refuse a doc that is not approved, a format not in `Formats approved`, and a LinkedIn post or proper-length video below STRONG. Only `write_reference.py` checks this in code. The default Blog and Editorial Draft route follows it as instructions.

A draft opens with frontmatter, and the tool never publishes it. The hand-written example, [`packages/content-engine/examples/draft-example-ci-flakiness-blog.md`](../packages/content-engine/examples/draft-example-ci-flakiness-blog.md), begins:

```markdown
# The Quiet Tax of Flaky Tests

A flaky test is easy to stop noticing. It becomes a habit — the kind you
stop seeing because you've built your whole day around it.
```

Each claim in it traces back to one of the three signals. Before you publish, check each claim against the theme doc's signals yourself.

To run the drafting step on this theme without an API key, see [`examples/draft-without-an-api-key`](../examples/draft-without-an-api-key/).
