# The Detector Review — Generative Fingerprint (Pangram-style)

## Activation
Run automatically as Reviewer 8 during Phase 4, or invoke with: `rerun detector` / `detector check`.

## Editorial heuristic

Assess structure, specificity, and semantics beyond banned-word checks. Score passages on the rubric below to locate generic prose and guide edits; these are subjective editorial scores.

## ⚠️ This is a slop heuristic, NOT a detection verdict
This reviewer is a **writing-quality tool**, not a real AI-detector. Its score reflects how
*generic and machine-shaped* the prose reads — nothing more. Do not present its output as a
prediction of what Pangram, GPTZero, or any trained classifier will say.

A low score means “reads clean,” not “human-authored” or “will pass a detector.” Do not infer authorship, promise detector evasion, or present an editorial heuristic as a measured classifier result.

## What this reviewer does NOT do
Do not re-flag banned words, em-dashes, or negative parallelisms — those belong to the
**Voice Auditor** (Reviewer 5) and the **AI-Pattern Scrub** (Phase 5). This reviewer catches
what survives *after* those passes are clean: prose with no forbidden words that still reads
generated. If you find yourself quoting a banned word, you're in the wrong reviewer — hand it off.

---

## Instructions

Read the draft paragraph by paragraph. For each paragraph, run the six fingerprint tests
below. Each test that fails pushes the paragraph's score up. A paragraph can be word-clean
and still fail every test here.

### The two core tests for specificity and information

**1. The Interchangeability test** *(specificity)*
Could this exact paragraph appear, almost verbatim, in a competitor's article on the same
topic — written by a different person or a different model? If yes, it carries no fingerprint
of *this* writer, *this* company, or *this* argument. It's the token-probable output any model
would emit for the prompt.
- Tell: no proprietary facts, no named people/products/customers, no first-person specifics,
  no numbers you couldn't have guessed.
- Fix: inject something only this writer could have written — a company-specific fact, a named
  UXR verbatim, a real metric, a concrete anecdote.

**2. The Deletion test** *(information value)*
Delete the sentence. Does the reader lose any information, or just some word-count? Sentences
that only *sound like* content ("This is a critical consideration for modern teams") are the
purest AI fingerprint — high fluency, zero payload.
- Tell: you can cut the sentence and the paragraph still makes every point it made before.
- Fix: delete it. If a real claim was hiding inside, promote that claim and cut the scaffolding.

### The four structural tells

**3. Uniform paragraph architecture.** Three or more consecutive paragraphs built to the same
mold — claim → elaboration → soft example, each ~3 sentences, each ~same length. Human writing
is lumpy: a two-word paragraph next to a seven-line one. Machine writing is a metronome.
- Fix: collapse two paragraphs into one, or blow one open into a list, or drop a one-line jab.

**4. Front-loaded hedging and false balance.** "While there are many approaches, it's important
to consider both sides…"; "on one hand… on the other hand" with no verdict; every claim
immediately cushioned. Models hedge to lower risk; writers with a point of view commit.
- Fix: state the claim, then earn it. Cut the pre-emptive cushion. Take the side the piece is arguing.

**5. Over-scaffolding / explaining the obvious.** Defining terms the audience already owns,
signposting the structure ("First, we'll look at X; then we'll turn to Y"), restating the
section's point at both ends. This is the model padding for coverage, not the writer respecting
the reader's time.
- Fix: trust the reader. Delete the signposts and the on-the-nose recaps.

**6. Frictionless, stakes-free tone.** No idiosyncrasy, no risk, no sentence that a cautious
committee would object to. Everything is smooth, agreeable, and forgettable. Real writing has
edges — a strong verb, an unhedged opinion, a joke that might not land, a specific irritation.
- Fix: find the one place the writer actually cares and let that voice off the leash.

### The predictability probe (do this once for the whole draft)
Cover the second half of five random sentences and predict how they end. If you're right most
of the time, the draft is running on token-probable rails — the single strongest whole-document
signal that survives a clean word list.

---

## Scoring

Score each paragraph 0.00–1.00 using the tests above as evidence, then bucket the document
by its weighted average (weight longer paragraphs more).

| Score | Bucket | Meaning |
|---|---|---|
| 0.00–0.24 | **Human-reading** | Carries a real fingerprint. Ship it. (Still AI-authored if AI wrote it — see caveat.) |
| 0.25–0.49 | **Lightly machine-shaped** | Mostly clean; a few smooth spots. Fix if time allows. |
| 0.50–0.74 | **Moderately machine-shaped** | Reads generated in stretches. Must fix before delivery. |
| 0.75–1.00 | **Heavily machine-shaped** | Interchangeable boilerplate. Rewrite, don't patch. |

The bucket labels describe **how the prose reads**, not who wrote it and not what a detector
will conclude. A "Human-reading" bucket on AI-authored text means the slop is gone, not that
the fingerprint is gone.

**Gate:** the document does not pass Phase 4 above **0.50 (Moderately)**. Any single paragraph
at **0.75+** is a blocking issue regardless of the document average.

## Whitelist rules
If a voice profile exists, a genuinely low-specificity passage the *writer* would also write
(confirmed against their corpus) is not a fingerprint — note `[WHITELISTED — matches writer's corpus]`
and score it as human-reading. The tests target machine-shaped prose, not plain prose.

---

## Output Format

```
Detector Score: 0.XX — [Bucket]
(Slop heuristic, not a detection verdict. Says how generic the prose reads, not what Pangram will say.)

BLOCKING (paragraph ≥ 0.75):
[¶ N — 0.XX Heavily] — failed: Interchangeability, Deletion, Uniform-architecture
"first line of the paragraph…"
Why it reads generated: [one sentence]
Fix: [the specific injection or cut that lowers the score]

MUST FIX (paragraph 0.50–0.74):
[¶ N — 0.XX Moderately] — failed: [tests]
"first line…"
Fix: [specific]

IMPROVE (paragraph 0.25–0.49):
[¶ N — 0.XX Lightly] — failed: [test]
"first line…"
Fix: [specific]

Predictability probe: [X/5 sentence-endings guessed correctly]

Summary:
- Document bucket: [Human-reading | Lightly | Moderately | Heavily machine-shaped]
- Most machine-shaped paragraph: ¶N (0.XX)
- Most human-reading paragraph: ¶N (0.XX)
- Dominant failure mode: [which of the 6 tests fired most]
- Whitelisted passages: X
```
