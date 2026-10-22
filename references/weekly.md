## Procedure

Run the weekly content review as a bounded sequence of the Content Engine procedures. This command defines the cadence's operating contract; it does not itself create a schedule, fetch from an invented engine, write approved content, or publish. Use the caller-supplied output directory, reviewed context and explicitly approved signal/theme files. Verify the current Content Engine guide and actual configured source adapters before execution.

1. **Establish the run contract.** Confirm the review period/time zone, source/query scope, durable bank/theme locations, prior-run watermark, freshness/dedupe thresholds, persona priorities, output/approval destination, and available scheduler if scheduling is separately requested. A one-line recurring prompt can invoke this command after a real schedule is configured; do not claim one exists from this review alone.
2. **Scan all configured sources.** Apply Content Engine scan rules to every authorized source/query. Collect native IDs and dates, dedupe without mutating another engine's engagement state, and report source-level fetched/new/known/stale/failed counts. One failed source need not abort the week; continue with a clearly partial run. A failed fetch must not advance that source's complete watermark or be described as no signals.
3. **Cluster the unspent bank.** Include eligible unassigned signals from earlier runs, not just new rows. Exclude stale candidates without deleting evidence. Group by the same buyer question and independent origin, leaving weak singletons unspent. Compare against prior themes to avoid repeating a thesis without meaningful new evidence. Demand/citation context can rank a theme when actually measured, but never raises the signal count or evidence tier. Record exact source dates and freshness warnings.
4. **Brief and rank.** For each viable theme, retain tier, source lineage, persona/problem, core insight, counterpoint, do-not-say, recommended format/bar, approved version/formats if any, and next evidence needed. Rank by relevance, credible evidence, timing, strategic priority, and actual measured opportunity when available. Keep “produce next,” “collect evidence,” “strategic discretion,” and “hold/reject” distinct. No theme should win solely because it has the highest discussion count.
5. **Prepare the human review packet.** Show concise theme summaries with top source IDs/dates, suggested formats, measured/unavailable demand/citation fields, freshness warnings, and a specific approval question. Deliver locally unless external posting is already explicitly authorized. Do not invent Slack posting, reaction monitoring, or an approval decision. Queue proposed/approved themes separately so nobody mistakes recommendation for permission to write or publish.
6. **Stop before writing.** This weekly routine ends after scan/cluster/brief and the human decision queue. Even an already approved theme is only queued; deliberate write-mode execution is a separate task unless the user explicitly changes the routine contract. Reject/hold decisions retain reasons and signal assignment state, preventing the same rejected idea from resurfacing without reconsideration.
7. **Report and preserve state.** Save permitted outputs and show proposed durable updates under the reviewed write flow. State what persisted, what was preview-only, which sources remain partial, and what next week will use. If durable shared state changed, propose or follow the authorized repository PR workflow; never push default directly, create/merge a PR, or auto-commit because the source routine once did so. If no Git action is authorized, identify the pending persistence step rather than pretending fresh clones will have local-only state.

`--dry-run` uses the Content Engine preview contract: no source-state mutation, durable bank/theme/approval write, external messages, Git actions, or schedule changes. Render the packet in the response or explicitly permitted preview artifact and label it a preview.

### Review depth with concise output

The routine's output is an editorial queue, not a weekly essay. Keep each theme to title, buyer problem, evidence/tier, why now, format recommendation, what not to claim, and the next decision. Keep failed-source detail in the receipt. Preserve exact evidence and rejected reasons behind the short summary. A sparse week can correctly return no ready themes; do not manufacture content to fill a calendar.

## Output template

```markdown
# Weekly content review: [period] | [timezone]
Run: [complete/partial/preview] | Last complete source watermarks: [...]
Scope: [configured sources/queries and bank/theme version]

## Source health
| Field | Value |
|---|---|
| Source | |
| Fetched/new/known/excluded | |
| Coverage | |
| Latest evidence date | |
| Failure/gap | |

## Ranked themes
| Field | Value |
|---|---|
| Priority | |
| Theme ID/title | |
| Buyer question | |
| Tier/origins | |
| Why now | |
| Formats | |
| Decision | |

### [Theme]
Evidence: [top dated signals; support/counterpoint]
Do not say: [unsupported leap]
Demand/citation: [measured prompt IDs/dates/denominators, or unavailable]
Next evidence or approval: [specific action]

## Draft queue
Approved to draft: [exact theme versions/formats; queued only]
Proposed: [awaiting human decision]
Held/rejected: [reason and reconsideration trigger]

## Handoff
Actual/proposed files: [...]
External posting: [not requested / actual authorized receipt / unavailable]
Shared-state persistence: [actual PR/commit if authorized, or pending]
Next run: [what remains unspent/partial, no implied schedule]
```

## Worked example

Fictional illustration only. Three approved sources are configured. A forum adapter fails, a news feed returns one undated page, and an approved seed file contains two independent dated discussions.

**Status:** Partial. Forum remains unchecked; the undated page is excluded. The two discussions produce one THIN theme.
**Recommendation:** Collect more evidence or approve an exploratory blog brief. LinkedIn is not recommended on these facts.
**Queue:** Proposed, not approved. No writing, publication, or external digest occurred.
**Next run:** Retry the failed source without claiming a complete watermark; preserve the unspent signal IDs.

Weak: “No signals this week; posting a trend summary anyway.” Better: “The run is partial. One thin theme is ready for editorial review, with the missing source named.”

## Quality checks

- The same source/freshness/tier rules apply as in a manual Content Engine run.
- All configured sources are attempted or explicitly unavailable; coverage and watermarks are honest.
- Ranking separates evidence, relevance, and measured opportunity; repeats need meaningful new evidence.
- Recommended, approved, queued, written, and published states stay distinct.
- No write mode runs within the routine; messaging/Git/scheduling require their existing explicit authorization.
- The review packet is concise but references durable receipts and exact theme versions.

## Anti-patterns

Automated publication under a weekly review; fake empty weeks after source failures; advancing incomplete cursors; forcing content-calendar volume; recycling rejected theses; treating citation data as corroborating signals; implicit Slack approval; local-only state called shared; automatic PR merges; invented scheduler or external engine capabilities.
