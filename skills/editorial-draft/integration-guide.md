# Editorial Draft Integration Guide

> How existing commands use Editorial Draft for writing quality refinement.

## The Pattern

Existing commands handle **what to write** (context, structure, templates). Editorial Draft handles **how to write it well** (voice, pacing, clarity, AI-pattern scrub).

```
Command generates content (own template + tone rules)
    ↓
Writer reviews draft
    ↓
Writer says "refine with editorial-draft" or "run review panel"
    ↓
Editorial Draft runs in REFINEMENT MODE:
  - Skips Phase 0 (Style) — preset auto-selected by command
  - Skips Phase 1 (Interview) — context already gathered
  - Skips Phase 2 (Outline) — structure already defined
  - Runs Phase 4 (Review Panel) — selected reviewers only
  - Runs Phase 5 (Polish) — AI-pattern scrub + line edit
    ↓
Writer accepts or iterates
```

## Command → Editorial Draft Mapping

### /changelog → Customer-Facing Polish

| Setting | Value |
|---|---|
| **Auto-preset** | How-To Guide (user-facing, step-by-step, 7th-grade reading level) |
| **Reviewers to run** | Hemingway, Clarity, Voice, Platform, The Detector |
| **Reviewers to skip** | Hitchcock (pacing less relevant for changelogs), Devil's Advocate (not argumentative), Completeness (template enforces structure) |
| **Platform target** | Company Blog (SEO metadata, readability scoring) |
| **Key focus** | Jargon elimination, reading level check, AI-pattern scrub, no hype language |

**Why this combo:** Changelogs fail when they're too technical or too marketing-y. Hemingway catches bloat. Clarity catches jargon. Voice catches hype ("exciting," "powerful"). Platform checks blog formatting.

---

### /narrative → Executive Storytelling Polish

| Setting | Value |
|---|---|
| **Auto-preset** | Conversational Authority (confident storytelling, first-person) |
| **Reviewers to run** | Hitchcock, Voice, Completeness, AI-Pattern Detection, The Detector |
| **Reviewers to skip** | Hemingway (narratives need flow, not just economy), Platform (narratives are presented, not published), Clarity (audience is known — internal execs) |
| **Key focus** | Pacing (does the story build?), voice consistency, story arc completion, AI-pattern scrub |

**Why this combo:** Narratives fail when they drag, when the story arc is incomplete, or when they sound AI-generated. Hitchcock catches pacing issues. Completeness catches broken story threads (intro promise without payoff). Voice catches tonal shifts.

---

### /brief → Decision-Ready One-Pager Polish

| Setting | Value |
|---|---|
| **Auto-preset** | Executive Communicator (BLUF, decisive, zero waste) |
| **Reviewers to run** | Hemingway, Clarity, Devil's Advocate |
| **Reviewers to skip** | Hitchcock (briefs are scanned, not read for pacing), Voice (tone is utilitarian), Platform (internal doc), Completeness (template enforces structure) |
| **Key focus** | Economy (can it be read in 90 seconds?), jargon stripping, argument soundness |

**Why this combo:** Briefs fail when they're too long, too jargon-heavy, or when the ask is weak. Hemingway enforces the 90-second constraint. Clarity catches cross-functional jargon. Devil's Advocate stress-tests the proposal logic — if the brief asks for a decision, the reasoning must hold up.

---

### /battlecard → Sales-Ready Field Tool Polish

| Setting | Value |
|---|---|
| **Auto-preset** | Executive Communicator with override: `voice.formality: 5` (professional but conversational — AEs need natural scripts, not boardroom language) |
| **Reviewers to run** | Devil's Advocate, Clarity, Voice, AI-Pattern Detection, The Detector |
| **Reviewers to skip** | Hemingway (scripts need natural length), Hitchcock (not a narrative), Platform (internal tool), Completeness (template enforces structure) |
| **Key focus** | Argument soundness (will objection responses hold up?), clarity for non-PM readers, natural voice (scripts must sound human), AI-pattern scrub |

**Why this combo:** Battlecards fail when objection responses are weak, when scripts sound robotic, or when they oversimplify competitive positions. Devil's Advocate attacks the "Where We Win" claims. Clarity ensures an AE who isn't a PM can use this without confusion. Voice ensures scripts sound natural when spoken aloud.

---

### /content-engine --format linkedin → Brand Thought-Leadership Polish

| Setting | Value |
|---|---|
| **Auto-preset** | Social Long-Form, **with a mandatory brand-voice override** — the base preset is written in first-person personal voice ("uses 'I' constantly," personal-failure hooks) and must not be used unmodified for company-brand content: `pov: company` (not `first_person`), no personal-origin-story hook, CTA points at the company rather than "follow me for more" |
| **Reviewers to run** | Hemingway, Clarity, Voice, Platform, The Detector |
| **Reviewers to skip** | Hitchcock (a 200–500 word post carries less pacing/arc structure than a blog), Devil's Advocate (the piece states an observed signal, not a contested argument), Completeness (the content-engine's own theme-doc template enforces structure) |
| **Platform target** | LinkedIn (post-length formatting, no forced CTA link) |
| **Key focus** | Brand-voice compliance (catch any first-person slip from the base preset), AI-pattern scrub, `coverage_tier`-appropriate hedging (from the caller's approved evidence-strength rules — a `THIN` theme must read as "early signal," never as settled fact) |

**Why this combo, and why the override matters:** this is the one Editorial Draft
integration whose *input* is graded evidence from an external pipeline, not a
PM's own drafted context — the `coverage_tier`/`do_not_say` fields from
`docs/content-themes/theme-<date>-<slug>.md` are load-bearing here in a way no
other integration needs, so Devil's Advocate is skipped (there's no argument
to attack, only a claim strength to calibrate) in favor of trusting
`rules.md`'s hedging rule earlier in the pipeline. Routed to Editorial Draft
rather than the `humanizer` subagent specifically because this is
thought-leadership needing structural/argument-caliber review, not
reply-caliber polish — `humanizer`'s own scope line ("LinkedIn posts and
replies... under ~400 words") otherwise overlaps this preset's 200–300 word
target, and this is the explicit tie-break: multi-paragraph brand
thought-leadership goes here, a short reply/reaction stays with `humanizer`.

---

## How to Invoke

**After any command generates output, the writer can say:**

```
refine with editorial-draft
```

This triggers refinement mode with the pre-configured reviewers for that command type.

**Or selectively run individual reviewers:**

```
rerun hemingway        # Just economy check
rerun devils-advocate  # Just argument strength
ai check               # Just AI-pattern detection (banned words, em-dashes, parallelisms)
detector check         # Just The Detector (generative-fingerprint scoring)
```

> **AI-Pattern Detection vs The Detector — run both, they catch different things.**
> AI-Pattern Detection is a *blacklist*: it catches known lexical tells (banned words,
> em-dashes, negative parallelisms). The Detector is an *editorial heuristic*: it catches prose that trips zero banned words but still reads generated —
> interchangeable boilerplate, hollow sentences, uniform paragraph architecture, frictionless
> tone. A draft can pass `ai check` clean and still fail `detector check`. That residual
> slop is exactly what The Detector exists to catch.
>
> **The Detector is a slop heuristic, not a detection verdict.** It grades how generic the
> prose reads; it does not predict what a trained detector (Pangram, GPTZero) will say. A
> clean `detector check` reports an editorial judgment, not measured authorship or a
> promise that the text will pass detection. See `reviews/detector.md`.

**Or run the full panel regardless of command type:**

```
run full review panel
```

## Future: Other Commands That Could Benefit

| Command | Potential Editorial Draft Use | Priority |
|---|---|---|
| `/gtm` (messaging architecture section) | Voice + Clarity on persona-specific value props | Medium |
| `/deck-review` (slide copy suggestions) | Hemingway + Voice on recommended rewrites | Low |
| `/competitor` (analysis prose) | Devil's Advocate + Clarity | Low |
| `spec` (user-facing copy sections) | Voice + AI-Pattern Detection on any customer-visible text | Medium |
