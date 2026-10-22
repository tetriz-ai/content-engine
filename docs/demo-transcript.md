# Demo transcript: a dry run on the bundled examples

This is a real run of `claude -p "/content-engine --dry-run"` from a fresh clone, on 13 October 2026, with no `config.yaml` and a placeholder Slack member ID (`U00000000`) in `.env`. It is trimmed for length: tool output is cut where marked `…`, and the temporary clone's path is shown as `<clone>`. The run made no change outside `working/` and sent nothing to Slack.

This run's command did not print a source plan or draft through Blog and Editorial Draft, so neither appears below.

A dry run skips the setup interview, so none of its questions appear below.

## What the session did

```text
Glob     packages/{content-engine/*,scanner-core/scanner_core.py}       (preflight: the repo is here)
Grep     ^CONTENT_ENGINE_SLACK_CHANNEL=…  in .env, output_mode count  -> 1   (set; the value is never shown)
Grep     ^(ANTHROPIC_API_KEY|PH_API_TOKEN|TWITTER_BEARER_TOKEN)=…     -> 0   (none set)
Bash     python3 -c "import yaml"                                      (PyYAML is there)
Read     <clone>/packages/content-engine/config.example.yaml           (no config.yaml: the examples)
Bash     python3 packages/scanner-core/scanner_core.py --config packages/content-engine/hn-reddit-scan.example.yaml --platform all --out-dir working/signals/hn-reddit-raw --max-subreddits 2
           [reddit] scanning 2 of 5 subreddits (--max-subreddits)
           Scanning Hacker News (last 48h)...
             [hn] 0 candidates
           Scanning Reddit (last 48h)...
             [reddit] 4 feeds, spaced 10s apart for Reddit's rate limit (~40s)
             [reddit] r/ExperiencedDevs hot rate-limited, waiting 49s before retry
             …
             [reddit] 0 candidates
             [ph] no `ph:` block in --config — skipping for this run
Read     <clone>/working/signals/hn-reddit-raw/all-candidates-2026-10-13.json
           {"candidates": [], "failures": [], …}
Write    <clone>/working/preview-scan-2026-10-13.json
Write    <clone>/working/preview-brief-2026-10-13.md
Bash     python3 packages/content-engine/report.py --config packages/content-engine/config.example.yaml
           === Signal bank ===
           Total rows: 0 (0 un-spent, 0 spent)
           …
Bash     git status --porcelain --ignored
           !! packages/content-engine/.env
           !! working/
```

## The summary it ended with

```text
This was a dry run on the bundled examples. It found no signals, so there are no themes, drafts or cards to preview. Nothing changed outside `working/`.

Setup
- `config.yaml` doesn't exist, so the run used `config.example.yaml` and scanned only Hacker News and Reddit, from the first 2 of its 5 subreddits. No config file was written.
- Slack is configured in `.env`, but a dry run never posts to it.
- Product Hunt, X, Semrush and Google Trends are all off. With no `ANTHROPIC_API_KEY`, this session would write any drafts itself.

Steps
1. Approvals: there were none to process, because `docs/content-themes/` doesn't exist yet and so no cards have been posted.
2. Drafts: none, since no theme is approved, and there were no `voice examples:` lines to report.
3. New themes: the scan returned 0 posts from Hacker News and 0 from Reddit, covering the last 48 hours.
   - Reddit rate-limited 3 feeds. Each one succeeded on retry, so no requests failed.
   - With no posts, the cluster and brief steps had nothing to group, so there were no themes, theme docs or Slack card previews.
   - Competitor blogs were skipped because the example config lists no feeds. That doesn't count as a failure.
4. `report.py`: the signal bank has 0 rows (0 unused, 0 used) and there are 0 themes.

Files written
- `working/signals/hn-reddit-raw/all-candidates-2026-10-13.json`: the raw scan output, with 0 posts and no failures.
- `working/preview-scan-2026-10-13.json`: the rows a real run would add to the bank (none).
- `working/preview-brief-2026-10-13.md`: says no themes were found.
```

Zero posts is a common result on the example keywords, which describe a made-up product. To see a finished draft file without configuring anything, run [`examples/draft-without-an-api-key`](../examples/draft-without-an-api-key/).
