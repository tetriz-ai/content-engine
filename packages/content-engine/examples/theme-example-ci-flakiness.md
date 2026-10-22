# Theme: Flaky Tests Are a Quiet, Measurable Tax on CI Throughput

**Status:** approved
**Coverage tier:** STRONG
**Category:** none
**Content type:** explainer
**Relevant to:** practitioners re-running CI builds; engineering managers who own CI reliability as a team metric (see `context.example.md`)
**Formats suggested:** [blog, linkedin, video]
**Formats approved:** [blog, linkedin, video]
**Slack card:** none
**Created:** 2026-10-03

## Rationale

Three independent, corroborating signals surfaced within the same week: a
practitioner-built fix shipped to HN (tag-and-rerun flaky detection), a
raw complaint thread on the exact same pain (r/ExperiencedDevs), and a named
third-party survey quantifying the cost in hours/week. That's a real,
observed pattern — not a single anecdote. It clears STRONG (3 signals from 3
distinct sources: HN, Reddit and a competitor blog), and the named survey and
the third source clear the LinkedIn bar too.

## Signals

| Source | Title | URL | Published | Metric |
|---|---|---|---|---|
| hn | Show HN: We cut our flaky-test rate by tagging non-deterministic failures automatically | https://news.ycombinator.com/item?id=00000001 | 2026-10-01 | 42 pts |
| reddit | Tests failing randomly again — anyone else re-running CI 3x a day just to get a green build? | https://www.reddit.com/r/ExperiencedDevs/comments/0000001/ | 2026-10-02 | — |
| competitor_blog | Flaky Tests Cost More Than You Think: A 2026 Survey of 400 Engineering Teams | https://competitor-one.example.com/blog/flaky-tests-cost-more-than-you-think | 2026-09-28 | — |

## Do not say

- Don't claim "most teams" lose 6.5 hours/week — the survey's own framing is
  a *median* across 400 teams it surveyed, not a universal number; cite it
  as "one named survey found," not as an established industry-wide fact.
- Don't imply the HN tool (tag-and-rerun) is a complete fix — the post
  itself says it reduced false-reds by "about a third," not eliminated
  them. Don't round that up.

## Output

| Format | Status | Path |
|---|---|---|
| blog | not started | — |
| linkedin | not started | — |
| video | not started | — |
