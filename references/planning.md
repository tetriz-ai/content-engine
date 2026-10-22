## Procedure

Turn approved external signals into an evidence-graded theme bank and human-approved drafts. Support scan, cluster, brief, write, inventory, competitor-gaps, and refresh-plan. Use the caller-supplied output directory, reviewed product/audience/competitor/GTM/voice context and explicit source scope. Carry the user's exact source scope across all modes.

This guide owns evidence and editorial planning within the standalone Content Engine pipeline. Read the canonical command for scanner and state mechanics. Check actual configured source adapters, local bank/theme files, optional host SEO extensions, optional data providers and the Editorial Draft writing dependency, and availability in this session. Do not vendor another engine, invent script paths, or claim an upstream integration runs merely because its name appears here. If an adapter is missing, use user-approved source material with the same schema and mark the automated fetch unavailable.

### Resolve installed SEO procedures

Read the exact installed SEO skill entrypoints and relevant local resources for the selected mode. Resolve these optional extensions through the host skill catalog. Their absence permits labeled qualitative checks, not claimed formal rubric execution. Provider absence does not justify imagined measurements. Run supplied-data/qualitative modes when appropriate; read the bundled shared references before dependent benchmark checks, and report unavailable provider or automation implementations separately.

| Mode / phase | Installed execution skills |
|---|---|
| Inventory audit | `seo-on-page-seo-auditor`, `seo-internal-linking-optimizer`, `seo-technical-seo-checker` |
| Approved inventory corrections | Metadata: `seo-meta-tags-optimizer`; schema: `seo-schema-markup-generator`; links: `seo-internal-linking-optimizer`; entity definition: `seo-entity-optimizer`; AI-answer structure: `seo-geo-content-optimizer`; stale article: `seo-content-refresher` |
| Competitor gaps | `seo-competitor-analysis`, `seo-content-gap-analysis`, `seo-serp-analysis` |
| Refresh plan | `seo-content-refresher`, `seo-content-quality-auditor`, `seo-geo-content-optimizer` |

### Scope, configuration, and durable state

Confirm approved sources/queries, lookback, bank/theme locations, persona priorities, format settings, prior-theme dedupe window, any measured demand/citation evidence, and approval destination. Do not silently create a scheduler or messaging channel. Read only declared context dependencies and explicitly approved external/local files. A citation inside an approved document does not authorize opening its linked source; if verification needs it, keep the claim pending within the current scope.

Use stable records and retain provenance:

- Signal: source, native ID, stable signal ID, title, URL/path, actual publication/observation and fetch dates, excerpt/paraphrase, relevant metric with unit/window, evidence state, persona relevance, theme assignment.
- Theme: ID/title, member signal IDs, rationale, evidence tier, buyer question, counterpoint, do-not-say, recommended/approved formats, approval evidence, output paths/status, rejected/held reason.
- Run: source counts/status, dates used, exclusions, files changed or proposed, unavailable dependencies, next action.

Configured thresholds take precedence; when missing, propose the explicit editorial defaults below and label them provisional rather than pretending configuration exists. Persistence locations are the approved bank/theme files or configured output files; neither a saved scratch file nor a chat recollection silently becomes canonical.

`--dry-run` previews proposed changes and counts without altering the bank, themes, approval state, source pages, external messages, Git, or schedules. Show the preview in the response; write a preview artifact only when permitted by the configured preview contract. Never report a zero-side-effect preview after mutating durable state.

### Scan: collect and normalize

1. Read the actual configured source list and queries. Run every approved query/source, not a favorable sample. Process available independent sources in parallel; respect quotas and partial failures. Use raw source candidates rather than Buzz's engagement judge when a configured source adapter offers them. A content scan must not mutate Buzz's engagement seen-state.
2. Enforce source freshness. For news/pages, require an actual publication/update date within the configured lookback; unknown age stays excluded/pending rather than assumed fresh. Platform observation dates can be used only when the adapter demonstrably enforces platform recency. Verify RSS/feed parsing before treating it as an available feed; HTTP success returning a catch-all HTML page is not a feed.
3. Normalize while preserving exact platform IDs, timestamps, source links, and quotations. Dedupe on source + native ID. Use normalized URL only when no native ID exists; remove tracking parameters without collapsing distinct objects. For approved pasted material with no link, use a content hash and label its provenance. Reposts and syndications of one study are one underlying evidence lineage, not independent corroboration.
4. Append only genuinely new rows to the approved durable bank on an authorized real run, with theme assignment empty. Show proposed rows when review is required. Preserve old rows and report fetched, invalid/undated/stale, already-known, new, and failed counts per source. A source outage leaves the run partial; it is not zero demand.

### Cluster: group relevant, unspent signals

Read all unassigned bank rows, not only this run's rows. Exclude rows older than the briefing freshness cap even if they were fresh when collected; retain them in the bank and report excluded count. Group by shared buyer question, entity/topic, or observed pain. Explain why each member supports the same core insight. Do not glue unrelated facts into a “trend” to fill a quota.

Use the configured minimum; if unset, propose at least 2 relevant independent signals for a candidate cluster. A user-supplied topic can still become a THIN brief without invented bank members. Singletons or noisy/weak groupings stay unassigned. Any existing theme assignment, including a proposed, approved or rejected theme, means spent; do not resurface the same signals as a new theme without an explicit reconsideration decision.

Optional measured demand/citation evidence may rank viable themes. Record exact prompt/query IDs, intent, persona, source date, collection scope, and freshness warnings. Keyword overlap is insufficient when intent differs. This ranking evidence does not count toward the signal minimum or evidence tier. Missing/stale evidence is unavailable/stale, not a guessed demand score. Keep generic discovery and branded/entity correction separate.

### Brief: grade and prepare the human decision

Check prior themes within the configured dedupe window for substantively repeated theses; skip or explicitly describe new evidence and changed angle. Assign evidence tier from independence and quality, not just raw count. Provisional default: STRONG requires at least 3 relevant signals across at least 2 independently originating sources; otherwise THIN. Counts alone do not prove prevalence or causal change.

For each theme record one insight, buyer problem, why now, member signals/dates, supportive and contradictory evidence, intended page role, exact do-not-say claims, and the next evidence needed. User-provided topics follow the same template/tier review without inventing bank rows or marking unrelated signals spent.

Choose formats with explicit reasons:

| Format | Provisional evidence bar | Framing |
|---|---|---|
| blog | STRONG or THIN with useful support | THIN is an early signal or question, with limits. |
| video short | STRONG or THIN | About 60–90 seconds; one hook and 1–2 supported facts. |
| LinkedIn | STRONG plus margin/attributable proof | Brand-attributed assertions need extra support. |
| video proper | Same assertive bar as LinkedIn, plus material for 3–4 distinct beats | Roughly 3–5 minutes; no stretching one anecdote. |

For the extra support default, require at least 5 relevant signals, or at least 3 independent source origins, or a directly attributable named primary study/report/announcement supporting the thesis. Anonymous forum chatter at a bare count threshold is insufficient for a broad brand claim. Show which condition is met. Human format preference may change the recommendation; it never makes an unsupported statement accurate.

When actual demand/citation measurements exist, record the exact buyer prompt, prompt IDs, representative query, measured/proxy demand class, geography/window, mention/citation rates with denominators, inaccurate excerpts, and source paths/dates. A zero citation observation means a gap in that measured run, not proof of global invisibility. Use a disclosed priority matrix: strong evidence + observed gap → produce next; thin + gap → collect evidence; strong + low gap → strategic discretion; thin + low gap → hold. Without measurements, mark this unavailable and rank by reader relevance/evidence instead. Recommend the primary page role from the buyer intent: problem/category discovery -> definition or pillar; comparison -> comparison; solution evaluation -> methodology or verified product proof; branded misunderstanding -> canonical entity page. Entity correction requires the actual inaccurate excerpt and canonical product wording; insufficient excerpt means raw evidence review required.

Save the reviewed theme proposal before an approval message. Associate approval with theme ID/version and individual formats. Rejection keeps prior assignments spent unless explicitly reopened. If posting to a configured digest destination is authorized, send only the reviewed summary and record message identity; otherwise deliver the approval packet locally. No implicit Slack posting, reaction monitoring, commits, PRs, or merges. Update bank assignments/theme log only under the established reviewed write flow and report actual changes.

### Write: approved theme and formats only

Read the approved theme version, evidence ledger, do-not-say, brand voice, and format approvals. Requested “all” means each individually approved format, not blanket approval. Approval to draft is not publication approval.

- **Blog:** Delegate to `blog`, including its Editorial Draft writing engine and research/claim/outline/editorial/SEO-GEO checks. Supply the theme's evidence, buyer question, prompt IDs, page role, and scope. Apply any remaining decision gates without redundant confirmation of already approved choices.
- **LinkedIn:** Read `<engine_root>/skills/editorial-draft/SKILL.md` and invoke the actual installed Editorial Draft skill in refinement mode with **Social Long-Form**, LinkedIn platform, the approved theme, evidence, requested format word budget, and reviewed company/person voice. Skip repeated style setup, discovery interview, and outline. No separate Editorial Draft configuration is needed. If absent, report the missing dependency and leave writing pending unless the user explicitly requests a labeled manual bypass. Use the actual Hemingway, Clarity, Voice, Platform, and Detector reviewers, then the canonical AI-pattern scrub and final polish. For company copy, override personal-story defaults with company point of view and a brand CTA. A personal preset does not authorize inventing a founder story or first-person experience. Produce one clear insight, supported examples, and one relevant CTA. Apply economy, clarity, voice, platform fit, and AI-pattern checks. THIN evidence cannot become a settled broad claim.
- **Video short/proper:** Produce an evidence-cited video brief: topic, persona, angle, hook, supporting facts, visual opportunities, limitations, and CTA. Unless an actual configured script-generation stage is available and authorized, this is not a completed script or refiner-ready production asset. Say so in the file and output. Proper video must clear the stronger format bar; do not silently downgrade it to short.

Every quantitative claim/quote traces to a signal or approved product proof. Never fabricate verbatims; use accurate attributed paraphrase or `[NEEDS VERBATIM]`. Maintain one theme, insight, and CTA. Title/industry/size alone does not establish relevance. Apply do-not-say before polish and recheck after. Record actual draft paths and review status on the approved theme; leave publication pending.

### Inventory: source-preserving content audit

Read and delegate the relevant audit passes to `seo-on-page-seo-auditor`, `seo-internal-linking-optimizer` and `seo-technical-seo-checker`. Confirm the repository/corpus scope. Scan approved content-bearing Markdown/MDX/HTML, excluding dependencies, builds, vendors, archives, and generated files unless explicitly included. Record path, canonical URL (inference labeled), page type, topic, title/H1/description, word count, meaningful update date, resolved internal links, dated claims, definitions/FAQ/schema/proof/CTA, and measured analytics/ranking/conversion/backlinks only when actual data exists.

Prioritize measured problems first. Without measurement use explicit observed structural findings or proxy-only hypotheses, each tied to a plausible reader/crawl/citation/conversion consequence. Word count, shallow URL depth, or age alone does not prove low quality or business importance. Return findings, source/date, confidence, proposed change, execution capability, risk, and approval needed.

Without `--apply`, stop at the report. With it, review exact pages/findings and show diffs before writing. Route each approved finding to its exact narrow skill in the table above. Apply only the reviewed correction; report a missing installed skill before using an explicitly labeled scoped manual correction. Preserve frontmatter, page components, links, and unrelated claims. Run relevant repository validation; report every changed file. No automatic commit/PR/publish.

### Competitor-gaps: search coverage, not product positioning

Delegate search competition to `seo-competitor-analysis`, missing coverage to `seo-content-gap-analysis`, and result composition to `seo-serp-analysis`. Confirm the competitor domain, query/topic, geography/window, and source scope. Compare measured visibility when available; current live page intent/format; relevant topic coverage and missing subtopics; definitions, methods, proof/tools/templates; actual observed AI mentions/citations; and gaps we can answer with current evidence. Separate measured data, live observation, and inference. No guessed traffic, rank, difficulty, or citation share. Recommend a response tied to a buyer question and evidence capability, not copying a competitor's page. Product/sales/roadmap implications route to the competitor workflow rather than being smuggled into an SEO finding.

### Refresh-plan: preserve what works, stop at the plan

Read `seo-content-refresher`, `seo-content-quality-auditor` and `seo-geo-content-optimizer`; delegate their diagnosis/checks in planning mode, with writes suppressed. Read only the supplied approved article/corpus and applicable evidence. Diagnose intent/title fit, stale facts/product language, unsupported or unapproved claims, measured performance change if available, current result-format changes if inspected, link/schema/definition/structure issues, and useful material worth preserving. Deliver preserve/update/remove/add/verify/do-not-say with evidence/confidence per proposed change. Preserve approved quotes, links, ranked sections, and unique examples; do not assume old equals bad. This mode does not rewrite. Hand an approved revision plan to `seo-content-refresher`, then `blog` in existing-article mode for its final writing/evidence/voice checks, within the reviewed scope.

## Output template

```markdown
# Content Engine: [mode] | [date]
Scope/configuration: [approved sources/corpus, lookback, thresholds]
Capabilities: [actually run / unavailable / manual fallback]
Run status: [complete/partial/preview]

## Signal bank / scan report
| Field | Value |
|---|---|
| Signal ID | |
| Source + native ID | |
| Title/link | |
| Published/observed | |
| Evidence | |
| Theme | |
Counts by source: [fetched/new/known/stale/invalid/failed]

## Candidate theme / brief
ID / title / version: [...]
Status: [proposed/approved/rejected/held/written]
Tier / independent sources: [STRONG/THIN, lineage rationale]
Persona / buyer question / why now: [...]
Core insight / counterpoint: [...]
Signals: [IDs, titles, links, dates, actual metrics]
Do not say: [unsupported leaps]
Demand/citation: [actual prompt IDs, rates/denominators/dates or unavailable]
Page role / priority: [reason]
Formats recommended: [each bar met/not met]
Formats approved: [exact version and approval evidence, or none]
Draft status: [path, checks, pending publication]

## Inventory / competitor gap [when selected]
| Field | Value |
|---|---|
| Page/query | |
| Intent | |
| Finding/gap | |
| Evidence/date | |
| Confidence | |
| Proposed action | |
| Risk | |
Diffs: [preview only until applicable review/apply]

## Refresh plan [when selected]
Preserve / update / remove / add / verify / do-not-say: [specific changes and evidence]

## Handoff
[Actual files/changes, exclusions, unavailable evidence, human decisions, next action.]
```

## Mode-specific draft shapes

Keep the operating receipt internal and the public draft separate. A complete theme brief includes the title/version, tier and provenance, buyer problem, why now, rationale, dated signal table, demand/citation eligibility and denominators when measured, primary page role, exact do-not-say claims, individual format approvals and per-format output paths/status. Empty demand fields say unavailable; the record does not gain fictional measurement for completeness.

For LinkedIn, deliver the actual post plus an internal claim/source ledger and selected voice/review findings. For a video brief, use the following shape so it cannot be mistaken for a finished script:

```markdown
# Video brief: [theme] | short or proper
Status: BRIEF ONLY; script-generation/production pending
Theme/version and approved format: ...
Audience / buyer problem / angle: ...
Estimated length: [60–90 seconds short / 3–5 minutes proper, directional]
Hook: [one supported opening idea, not an invented statistic]
## Supporting facts / narrative beats
| Field | Value |
|---|---|
| Beat | |
| Claim or practitioner question | |
| Signal/source/date | |
| Scope/caveat | |
| Visual possibility | |
[Short: 1–2 supported facts. Proper: 3–4 distinct beats clearing stronger bar.]
## Do not say
[Unsupported prevalence, product outcome, quote or causal leap]
## Close and next step
[One appropriate CTA; no automatic publication]
Missing evidence / script handoff: ...
```

## Worked example

Fictional illustration only. The approved corpus contains 2 independent public discussions about import conflicts and 3 reposts of one of those discussions.

**Scan:** 5 objects, 2 independent evidence origins. Reposts are retained/deduped as configured but cannot inflate the tier.
**Cluster:** “Reviewing conflicting records before import” matches one buyer question. No measured search demand or citation observation exists.
**Brief:** THIN; propose an exploratory blog or short video. Do not say “most operations teams struggle” or “our product cuts import time.” Recommend collecting a primary study or additional independent observations before assertive LinkedIn copy.
**Write:** Wait for approval of that theme/version and format. The video output is a brief, not a production-ready script.

Weak: “Five signals prove a huge market trend.” Better: “Two independent discussions describe this problem; we need more evidence to estimate prevalence.”

## Quality checks

- Approved read scope survives every mode; links are not treated as automatic source authorization.
- Native IDs, dates, provenance, independent evidence lineages, and partial failures are retained.
- Tier, relevance, demand, citation opportunity, and format approval are separate fields.
- No stale/spent/duplicate signal becomes fresh corroboration by being reclustered.
- The do-not-say list constrains every draft, and all formats have actual approval evidence.
- Inventory edits are exact reviewed diffs; competitor findings distinguish observation from measurement; refresh-plan stops before rewriting.
- Missing upstream implementation/tools and pending publication are explicit; no implicit messaging, scheduling, or Git actions.

## Anti-patterns

Forum volume treated as market demand; syndication counted as corroboration; undated news assumed fresh; shared Buzz seen-state mutated; forced unrelated theme bridges; fake keyword/citation metrics; retrospective approvals invented; brand copy using an invented personal story; video brief called a ready script; mass page edits under an audit command; automatically posting digests or merging state; building a duplicate external engine.

Optional SEO extension sources and licenses: [third-party notices](../THIRD-PARTY-NOTICES.md).
