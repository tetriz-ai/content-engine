# AI-Pattern Detection

## Activation
Invoke with: `ai check` or runs automatically during Phase 5 Step 1.

Load the caller-supplied shared voice defaults and reviewed team voice before running. The full banned lists live there.

---

## Patterns to Detect

### Category A: Banned word-level flags (Section 3A)

Flag any appearance of: delve, realm, harness, unlock, tapestry, paradigm,
cutting-edge, revolutionize, landscape (abstract), intricate, intricacies,
showcasing, crucial, pivotal, surpass, meticulously, vibrant, unparalleled,
underscore (verb), leverage, synergy, innovative, game-changer, testament,
commendable, meticulous, highlight (verb), emphasize, boast, groundbreaking,
align, foster, showcase, enhance, holistic, garner, accentuate, pioneering,
trailblazing, unleash, versatile, transformative, redefine, seamless, optimize,
scalable, robust, breakthrough, empower, streamline, frictionless, elevate,
adaptive, effortless, data-driven, insightful, proactive, mission-critical,
visionary, disruptive, reimagine, unprecedented, intuitive, leading-edge,
synergize, democratize, accelerate, state-of-the-art, dynamic, immersive,
predictive, transparent, proprietary, integrated, plug-and-play, turnkey,
future-proof, paradigm-shifting, supercharge, enduring, interplay, valuable, captivate

Also flag: "serves as," "stands as," "marks a," "represents a," "boasts a,"
"features a," "offers a" when used instead of "is" or "has."

---

### Category B: Banned phrase-level flags (Sections 3B + 3C + 3D + 3E)

- "In today's [anything]..."
- "It's important to note that..." / "It's worth noting..."
- "In order to" (flag, suggest "to")
- "Straightforward"
- "Let's dive in" / "Let's explore" / "Let's unpack" / "Delve into"
- "At the end of the day"
- "Moving forward"
- "To put this in perspective..."
- "What makes this particularly interesting is..."
- "The implications here are..."
- "In other words..."
- "It goes without saying..."
- "Here's the part nobody's talking about" / "What nobody tells you"
- Any phrase using "nobody" or "most people don't realize"
- "In this article, I will..." (or any meta-announcement of upcoming content)
- "Despite its [positive words], [subject] faces challenges..."
- "Furthermore" / "Additionally" / "Moreover"
- "That said" / "That being said"
- "With that in mind"
- "It is also worth mentioning"
- "On top of that"
- "Let that sink in" / "Read that again" / "Full stop"
- "This changes everything"
- "Here's the thing" / "Here's what's interesting" / "Here's the kicker"
- "The reality is" / "The truth is" / "The fact of the matter is"
- "At its core" / "At the heart of" / "Fundamentally"
- "stands as a testament" / "serves as a reminder"
- "When it comes to"
- "One thing is clear"
- "The question becomes"
- "Only time will tell"

---

### Category C: FATAL — Negative parallelisms (Section 3F)

These are the highest-priority flag. Every instance must be rewritten.

**Direct forms:**
- "This isn't X. This is Y."
- "Not X. Y."
- "Forget X. This is Y."
- "Less X, more Y."
- "Not only X, but also Y."
- "It's not just about X, it's about Y."
- "No X, no Y, just Z."
- "X? No. Y."
- "Stop thinking X. Start thinking Y."
- "It's not about X. It's about Y."
- "X is dead. Y is the future."
- "The question isn't X. The question is Y."
- "You don't need X. You need Y."
- "X is overrated. Y is what matters."

**Sneaky versions (same skeleton, different coat):**
- "While X might seem right, Y is actually..."
- "Sure, X works. But Y is where the real..."
- "X gets all the attention, but Y is what actually..."
- Any concession-plus-pivot where the structure is: acknowledge claim → negate it → assert replacement

**The fix:** Delete everything before the positive claim.
"It's not about the prompt. It's about the context." → "It's about the context."

---

### Category D: Em-dashes

Flag every em-dash (—). Zero allowed anywhere.

Suggest replacement: comma, period, colon, semicolon, or parentheses depending on context.

---

### Category E: Structural AI patterns (Section 4)

**4A. Puffery / significance inflation**
Flag: "A pivotal moment," "marks a significant shift," "setting the stage for," "a key turning point," "a watershed moment."
Fix: Delete the inflation. State the fact.

**4B. Rule of three (prose)**
Flag: Three adjectives in a row, three parallel phrases, three parallel items used as a thesis or conclusion.
Note: This applies to prose only. Structural templates (numbered lists, tables) are fine.

**4C. False ranges**
Flag: "From [ancient/traditional/simple] to [modern/complex/advanced]" constructions.
Check: Can the writer name a meaningful middle ground? If not, it's fake. Delete.

**4D. Elegant variation**
Flag: A person, place, or concept being referred to by multiple different terms across consecutive sentences for no reason other than avoiding repetition.
Fix: Repeat the noun.

**4E. Meta commentary**
Flag: "In this section, we will discuss..." / "This document covers..." / "Below you will find..."
Fix: Say the thing. Delete the announcement.

**4F. Participle phrases for fake depth**
Flag: Trailing "-ing" phrases — "highlighting its importance," "underscoring its significance," "reflecting broader trends," "contributing to the rich tapestry of..."
Fix: Delete the phrase. If the point matters, write it as its own sentence with a specific claim.

**4G. Metronome rhythm**
Flag: Three or more consecutive paragraphs with the same sentence count. Three or more consecutive sentences of similar length.
Fix: Vary deliberately. Insert a fragment. Or a longer sentence that earns its space.

**4H. Copulative avoidance**
Flag: "serves as," "stands as," "represents," "marks a," "holds the distinction of being."
Fix: "is."

**4I. Title case in headers**
Flag: Headers where more than two words are capitalized beyond proper nouns.
Fix: Sentence case only. "This Is A Title Case Header" → "This is a sentence case header."

---

## Whitelist Rules

If a voice profile exists, check the whitelist before flagging. If the writer genuinely uses a flagged phrase in their natural writing (confirmed via source analysis), do NOT flag it. Note: `[WHITELISTED — found in writer's corpus]`

---

## Pattern Combination Rules

- Two or more Category A/B flags in the same sentence → HIGH CONFIDENCE AI
- Any Category C (negative parallelism) → FATAL — rewrite regardless of other score
- Any em-dash → HARD FAIL — replace regardless of other score
- Three or more Category A/B flags in a single paragraph → REWRITE ENTIRE PARAGRAPH

---

## Output Format

```
AI-Pattern Score: X/10 (0 = reads fully human, 10 = obvious AI)

FATAL (must fix before delivery):
[NEGATIVE_PARALLELISM] — "exact quoted text"
→ Fix: "rewritten version"

[EM_DASH] — "sentence containing —"
→ Fix: "sentence with replacement punctuation"

SERIOUS (fix before delivery):
[CATEGORY_A: word] — "exact quoted text"
→ Suggested rewrite: "..."

[CATEGORY_E: 4F_PARTICIPLE] — "exact quoted text"
→ Suggested rewrite: "..."

MINOR (improve if time allows):
[CATEGORY_B: phrase] — "exact quoted text"
→ Suggested rewrite: "..."

Summary: X patterns detected (X FATAL, X SERIOUS, X MINOR).
Highest-density section: [name].
Whitelisted patterns (not flagged): X
```
