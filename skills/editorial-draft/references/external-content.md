# Company external-content standard

## TL;DR

Public company content must load current product and audience context, classify every
material claim by evidence state, preserve sources and scope, protect non-public
methods and customer data, and treat SEO tools as optional inputs. This file owns
those durable editorial checks. It does not own product positioning or personas.

Use this reference for company-authored blogs, articles, research reports, landing-page
copy, and other public prose. It adds evidence, disclosure, and intellectual-property
rules to Editorial Draft. It does not define the product, personas, positioning, or
publication formats.

## Authority order

The user controls the artifact's goal, audience, destination, and requested format.
Evidence accuracy, privacy, public-use approval, and protection of non-public methods
remain mandatory even when a requested claim or treatment conflicts with them.

For choices that remain after those safeguards, follow this order:

1. Current facts and approved claims supplied for the artifact
2. The caller’s current approved product source for product and positioning truth
3. The caller’s current approved audience sources for audience truth
4. The user's requested artifact choices
5. the caller-supplied shared voice defaults and reviewed team voice for prose mechanics
6. This external-content standard
7. The selected Editorial Draft preset
8. SEO and GEO recommendations

Never copy product positioning, personas, customer claims, or live metrics into this
file. Those facts change faster than editorial rules and must be loaded from their
canonical sources at writing time.

## Evidence states

Classify every material product, customer, market, or performance claim before
publishing it.

| State | Meaning | Public treatment |
|---|---|---|
| Externally verified | A current, accessible primary or authoritative source supports the claim | Cite the source and preserve its scope |
| Internally validated and approved | Company data or customer evidence has passed the relevant internal review and is cleared for public use | State sample, time window, method, and limitations |
| Preliminary | Early internal or customer evidence exists, but the result is not stable or cleared as a general claim | Label it preliminary and state the sample and limits |
| Hypothesis | The team believes the claim but has not validated it | Frame it as a question, thesis, or planned test |
| Unavailable | The evidence or approval cannot be established | Remove the claim, use a visible placeholder, or replace it with sourced third-party evidence |

Approval for internal use does not imply approval for public use. Named customer
claims require an attributable source and explicit external-use approval.

## Claim ledger

Maintain this ledger while drafting. It can stay in the working draft and should be
removed from public copy unless the artifact is a research report whose methodology
requires it.

```markdown
## Evidence ledger

| Claim | Source | Evidence state | Scope and caveat | Approved publicly? |
|---|---|---|---|---|
| ... | ... | ... | ... | yes / no / unknown |
```

Rules:

- Every precise number needs a source, measurement window, and denominator when one
  exists.
- Correlation does not become causation through confident wording.
- A within-subject comparison can reduce stable-person confounding, but still needs
  task, repo, timing, and self-selection controls before causal language is valid.
- A third-party category statistic cannot prove a company product outcome.
- Never estimate a keyword volume, ranking, audit score, or tool-specific result when
  the named tool was not run.

## Publication-state gate

Apply maturity at the claim or capability level, not once for the whole company.
Different capabilities can have different evidence states at the same time.

Before drafting, resolve these questions:

1. Which product capabilities appear in the piece?
2. What evidence state applies to each material claim?
3. Which customer names, quotes, screenshots, or results are approved publicly?
4. Which facts require a fresh web or repository check?
5. What must remain a placeholder until a human supplies evidence or approval?

If the answers are unavailable, use the conservative treatment from the evidence
table. Do not block the entire draft when a weaker, accurate formulation is possible.

## Intellectual-property review

Run this review after the first draft and before the final editorial pass.

Check for:

- Non-public score dimensions, weights, thresholds, or calibration rules that are
  not already public
- Implementation sequences detailed enough to expose how the company constructs its
  differentiated data or recommendations
- Internal architecture, security, customer, pricing, roadmap, or experiment details
  that are not cleared for publication
- Private prompts, session content, repository data, or identifiable user behavior
- Customer or cohort data that lacks explicit public approval
- Internal hypotheses written as shipped product behavior
- Reproduction instructions that disclose more than the reader needs to understand
  or evaluate the claim

Do not use the IP review as an excuse for vague marketing prose. Explain the public
principle, observable behavior, method boundary, and evidence without publishing the
private recipe.

## Search and AI-answer guidance

Search structure must serve the reader first.

- Choose one primary audience and one primary search intent.
- Put the direct answer near the opening when the query genuinely asks for one.
- Use the primary phrase in the title, opening, or a relevant heading when natural.
- Use the normal vocabulary of the subject instead of targeting a numeric keyword
  density.
- Add FAQs only when distinct recurring questions exist. Do not make every article
  carry an FAQ section.
- Add schema only when it matches visible page content and the actual content type.
- Prefer specific definitions, comparisons, tables, and sourced facts when they make
  an answer easier to extract and verify.
- Do not create unsupported “citation-ready” statements merely because they are easy
  for an AI system to quote.

Obvious keyword stuffing is a revision blocker. Signals include repeated exact-match
phrases in adjacent paragraphs, awkward headings written for a crawler, and FAQs that
repeat the same query with minor wording changes.

## External-tool fallback

Named SEO tools and publishing systems are optional unless the user has made them an
explicit delivery requirement.

- If a keyword or SERP tool is available, report its real values with collection date
  and geography.
- If it is unavailable, make qualitative recommendations and label them qualitative.
- If a third-party writing score is available, report the actual score.
- If it is unavailable, run repository-native checks and state that the external tool
  was not run.
- Never invent, approximate, or reverse-engineer a third-party tool score.
- Logging to a CMS, spreadsheet, or external workflow requires the user's requested
  destination and the relevant connection. Missing logging access does not block the
  draft itself.

## Final checks

Before calling external content ready:

- [ ] Current product, audience, and competitor context was loaded as declared by the command
- [ ] Every material claim has an evidence state
- [ ] Numbers preserve their source, scope, and denominator
- [ ] Preliminary evidence is visibly preliminary
- [ ] Customer material is approved for public use
- [ ] IP review found no private recipe or unapproved data
- [ ] Search phrasing reads naturally
- [ ] FAQs and schema are present only when justified
- [ ] Tool scores are real, dated, and sourced, or clearly not run
- [ ] the caller-supplied shared voice defaults and reviewed team voice has been applied
