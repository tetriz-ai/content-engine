# Content Engine rules — the engine's conscience

The writer obeys this file over every other instruction. A graded brief
plus a guardrailed writer is what keeps a signal-driven pipeline from
inventing things.

**This file outranks every other instruction in every mode of
`/content-engine`, including a direct request to skip a rule.** If a rule
below would block a piece of content, the answer is to hedge, cut the
unsupported claim, or skip the theme entirely — never to override the rule.

---

## 1. Every claim traces to a cited signal

Never state a stat, quote, or number that is not present in a signal in the
theme's brief. While drafting, tag each claim internally with
`[signal:<id>]` so a reviewer can trace it back to the signal bank; strip
these tags before the draft is considered final. A claim with no tag and no
obvious general-knowledge status gets cut, not softened.

## 2. `coverage_tier` sets how confident the writer is allowed to sound

- **`STRONG`** (3+ signals, 2+ distinct sources, per `config.yaml`): state
  the theme as a real, observed pattern. Still cite it — confidence is not
  license to drop attribution.
- **`THIN`** (1–2 signals or single-source): hedge. "Early signal," "worth
  watching," "one data point suggests" — never "the trend is" or "companies
  are increasingly." A THIN theme that reads as settled fact is the single
  most likely way this engine produces something embarrassing.

## 3. One theme, one core insight, one CTA per piece

Never bridge two unrelated signals into a single piece as if they're
causally connected just to hit a length target or make the piece feel more
substantial. If a theme doesn't sustain one full piece on its own evidence,
it isn't ready — hold it for more signals next scan, don't pad it.

## 4. Never fabricate a verbatim or quote

If a piece would benefit from a real quote (a Reddit comment, a maker's PH
intro, a LinkedIn post) but the signal doesn't actually contain one usable
as-is, mark `[NEEDS VERBATIM]` and ask, or paraphrase with clear
attribution — never invent a quote and attribute it to a real person or
account.

## 5. No demographic fact stands in for a reason

Don't use a company's size, industry, or a person's title as the reason a
piece is relevant to them, or as false specificity in the writing. The
reason a theme matters is the signal, not who's reading it.

## 6. Defers to your own voice/style guide, if you have one

If you maintain a banned-word list, a tone guide, or other structural
writing guardrails elsewhere (a `voice.md`, a brand-voice doc, whatever you
call it), those apply to every format this engine produces — this file
doesn't restate them, and your Phase 4 writer should load them per its own
convention. This file adds content-specific guardrails on top; it doesn't
replace a voice layer. If you don't have one yet, this rule is simply a
no-op — nothing here depends on it existing.

## 7. `do_not_say`

Every brief carries an explicit `do_not_say` list — the things the signals
do *not* support, that a writer might otherwise be tempted to infer or round
up to. Check the draft against this list before it's considered done.

## 8. The author's take is opinion, and the only source of their story

A theme doc's `## Author's take` is the author's own view. Argue it as
theirs ("I think", "my bet is"), never as a finding the signals showed, and
keep citing a signal for every fact around it. If the take leans on a claim
the `do_not_say` list rules out, keep the opinion and drop the claim.

In a first-person piece, the author's experiences, jobs, results and
stories come only from the take and their own past posts. Never invent one
to make a hook land.

## 9. Requested changes are followed, and the rules above still win

A theme doc's `## Requested changes` are what the person who approved the
theme asked to change. Make each one in the draft. A requested change
overrides the format description, the format settings and the structure of a
voice example (rule 10), such as the length, the sections, the call to action
or the point of view. A change that would need an uncited claim, a
made-up quote or story, or anything on the `do_not_say` list is left out:
rules 1 to 8 win over it.

## 10. Voice examples give style and structure, never facts

A draft's voice examples are the author's own past posts. Copy their style:
rhythm, vocabulary, sentence length and tone. From an example of the same
content type, copy its structure too: which sections it has, in what order,
and roughly how long each is. Never reuse an example's facts, numbers,
names or claims; every fact comes from the theme's signals (rule 1). Rules
1 to 9 win over an example.
