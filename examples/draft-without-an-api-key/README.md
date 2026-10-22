Turns a saved answer into a draft file, the way a Claude Code session drafts when no API key is set. The answer is a fixed sample written for the sample theme. The draft lands under `working/examples/`, and the script prints it.

```sh
examples/draft-without-an-api-key/run.sh
```

```text
Draft written -> working/examples/draft-without-an-api-key.md
---
status: draft
format: blog
source_theme_doc: "packages/content-engine/examples/theme-example-ci-flakiness.md"
generated_at: <time>
drafted_by: "agent-session"
---

# Flaky tests cost more than the re-run

One Show HN post this month described a small CI plugin that re-runs a failed test once and
tags it flaky if the second run passes. Its authors say false-red builds fell by about a third
in the first month.

The same week, an engineer on r/ExperiencedDevs described a suite where about 15 tests fail
roughly one run in twenty, and a team that now re-runs every red build.

One named survey of 400 teams puts the median cost at 6.5 engineering hours a week. That is
one survey's median, not a rule for every team.

If your team also re-runs and moves on, start by counting how often it happens.
```
