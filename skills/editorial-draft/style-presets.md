# Editorial Draft: Style Guide Preset Library

> When a writer starts a new session, Editorial Draft asks them to either (a) pick a preset, (b) learn their style from sources, or (c) upload a custom guide. Each preset is opinionated — it commits to one style and does it well.

---

## Global Rules (apply to ALL presets — no exceptions)

These override any preset-level setting. Load the caller-supplied shared voice defaults and reviewed team voice for the full list.

**Em-dashes:** Fully banned. Zero in any output. Use commas, periods, colons, semicolons, or parentheses instead.

**Negative parallelisms (FATAL):** Never write "This isn't X. This is Y." / "Not X. Y." / "It's not about X, it's about Y." or any variant. See `ai-pattern-detection.md` for this pattern.

**Banned words:** delve, realm, harness, unlock, tapestry, paradigm, cutting-edge, revolutionize, landscape (abstract), intricate, showcase/showcasing, crucial, pivotal, unparalleled, underscore (verb), leverage, synergy, innovative, game-changer, testament, groundbreaking, align, foster, enhance, holistic, transformative, redefine, seamless, optimize, scalable, robust, breakthrough, empower, streamline, frictionless, elevate, unprecedented, intuitive, accelerate, state-of-the-art, dynamic, future-proof, supercharge — and all others listed in the shared voice defaults.

**Paragraph length (editorial prose):** 3 sentences max. 1-2 preferred.

**AI patterns to eliminate:** puffery, rule-of-three lists in prose, false ranges, meta commentary, trailing participle phrases, metronome rhythm, copulative avoidance. See `ai-pattern-detection.md`.

---

---

## Preset 1: The Conversational Authority

**Best for**: Blog posts, thought leadership, conference talks turned into posts
**Tone**: Smart friend explaining something at dinner — confident but not lecturing
**Think**: Paul Graham, Lenny Rachitsky, Katie Parrott

```yaml
preset_id: conversational-authority
display_name: "The Conversational Authority"
tagline: "Smart, direct, opinionated — like explaining your expertise to a curious friend"
best_for: ["blog", "thought_leadership", "opinion"]

voice:
  personality: >
    Confident but not arrogant. Uses "I" freely — this is a person with a point of view,
    not a faceless institution. Admits uncertainty when genuine but doesn't hedge core claims.
    Treats the reader as an intelligent equal who just doesn't have this specific context yet.
  formality: 6  # out of 10
  humor_style: "observational, dry, self-aware"
  humor_frequency: "1 aside per 400-500 words"
  pov: "first_person"

sentence_patterns:
  avg_length: 16  # words
  max_length: 30
  min_length: 3   # fragments allowed
  variety: "high"
  fragment_frequency: 0.08
  rhetorical_questions: true
  rhetorical_question_max: 2  # per article

paragraph_patterns:
  avg_length: 2  # sentences (1-2 preferred)
  max_length: 3  # hard limit for prose — the shared voice defaults
  one_sentence_paragraphs: true  # For emphasis. Sparingly.
  one_sentence_max_per_1000_words: 2

punctuation:
  em_dash: false  # globally banned — use commas, periods, colons, semicolons, or parentheses
  parentheticals: true
  parenthetical_frequency: "light"
  semicolons: "rare"
  oxford_comma: true
  exclamation_marks: "almost_never"
  ellipsis: "never"

vocabulary:
  level: "accessible_expert"
  jargon_handling: "define_on_first_use"
  contractions: true  # Always. "Do not" reads stiff.
  preferred_words:
    - ["use", "utilize"]
    - ["help", "facilitate"]
    - ["show", "demonstrate"]
    - ["start", "commence"]
    - ["but", "however"]
    - ["get", "obtain"]
    - ["need", "necessitate"]
    - ["try", "attempt"]
    - ["enough", "sufficient"]
    - ["about", "approximately"]
  banned_words:
    - "leverage"
    - "synergy"
    - "paradigm"
    - "deep dive"
    - "unpack"
    - "space"  # as in "the AI space"
    - "landscape"
    - "robust"
    - "granular"
    - "scalable"  # unless literally about infrastructure

structure:
  opening:
    preferred: ["anecdote", "provocative_claim", "counterintuitive_observation"]
    avoid: ["dictionary_definition", "since_the_dawn_of_time", "in_todays_world", "broad_question"]
    hook_requirements: >
      First sentence must make the reader curious or slightly uncomfortable.
      It should NOT summarize the article. It should CREATE a gap the reader wants closed.
    examples:
      good:
        - "I spent three years building the wrong product."
        - "Everyone tells you to ship fast. Nobody tells you when to stop."
        - "Last Tuesday I deleted 40,000 lines of code and felt nothing but relief."
      bad:
        - "In today's fast-paced business environment..."
        - "Have you ever wondered about...?"
        - "According to Wikipedia, innovation is defined as..."

  body:
    section_count: "3-5 for 1500 words"
    subheading_style: "sentence_case, conversational"
    subheading_examples:
      good: ["The part nobody talks about", "Why this keeps breaking", "What I'd do differently"]
      bad: ["Key Considerations", "Analysis of Factors", "Conclusion"]
    transition_style: "natural flow, not signposted"
    transition_avoid: ["Moreover", "Furthermore", "Additionally", "In addition", "Moving on"]
    evidence_style: "personal experience + data when available"
    lists: "inline prose preferred; bullet points only for genuinely parallel items"

  closing:
    preferred: ["callback_to_opening", "forward_looking_provocation", "honest_admission"]
    avoid: ["summary_of_points", "in_conclusion", "to_sum_up"]
    requirements: >
      The ending should feel like arriving somewhere, not like wrapping up.
      Best closings reframe the opening in light of everything that came between.

  word_count_targets:
    short: 800
    standard: 1500
    long: 2500

samples:
  - |
    I didn't set out to build a writing agent. I set out to stop hating Mondays.
    Every week, I had the same problem: a blank doc and 2,000 words between me
    and a deadline. The ideas were there, rattling around in my head during showers,
    on walks, in that three-minute window before sleep. But the moment I sat down
    to type, they'd scatter.
  - |
    Product-market fit? You don't find it.
    You collide with it sideways while looking for something else. All the frameworks
    and canvases and customer interviews: they help. But the moment itself is
    always a surprise. At least it was for us.
```

---

## Preset 2: The Technical Explainer

**Best for**: Technical documentation, engineering blogs, developer tutorials, API guides
**Tone**: Clear, precise, helpful — a senior engineer patiently explaining to a competent colleague
**Think**: Stripe docs, Julia Evans, Dan Abramov

```yaml
preset_id: technical-explainer
display_name: "The Technical Explainer"
tagline: "Clear, precise, zero fluff — teaches through examples, not abstractions"
best_for: ["technical_docs", "engineering_blog", "tutorial", "API_docs"]

voice:
  personality: >
    Patient but efficient. Assumes the reader is smart but may not have this specific
    context. Never condescending. Prefers showing over telling. Uses "you" to directly
    address the reader. Uses "we" for shared actions ("Let's set up the database").
  formality: 5
  humor_style: "understated, rare, technical"
  humor_frequency: "rare"
  pov: "second_person"

sentence_patterns:
  avg_length: 14
  max_length: 25
  variety: "moderate"
  fragment_frequency: 0.03
  rhetorical_questions: false

paragraph_patterns:
  avg_length: 2
  max_length: 4
  one_sentence_paragraphs: true

punctuation:
  em_dash: false  # globally banned — use commas, periods, colons, semicolons, or parentheses
  parentheticals: true
  semicolons: "acceptable"
  oxford_comma: true
  exclamation_marks: "never"
  ellipsis: "never"

vocabulary:
  level: "expert_accessible"
  jargon_handling: "define_inline_first_use"
  contractions: true
  preferred_words:
    - ["run", "execute"]
    - ["set up", "configure"]
    - ["check", "verify"]
    - ["fix", "remediate"]
    - ["use", "utilize"]
  banned_words:
    - "simply"
    - "just"  # As in "just run..."
    - "obviously"
    - "trivial"
    - "easy"
    - "leverage"
    - "utilize"
    - "facilitate"
  code_style:
    inline_code: "for all function names, commands, file paths, variable names"
    code_blocks: "always include language tag, always runnable"
    comments_in_code: "explain WHY, not WHAT"

structure:
  opening:
    preferred: ["problem_statement", "what_you_will_build", "before_and_after"]
    avoid: ["history_lesson", "broad_overview", "motivational_speech"]
    examples:
      good:
        - "Your API is returning 500 errors under load. Here's how to fix it."
        - "By the end of this guide, you'll have a working CI/CD pipeline that deploys on every push to main."
      bad:
        - "In the ever-evolving world of software development..."
        - "Microservices have been gaining popularity..."

  body:
    section_count: "4-8 for technical docs (more sections, shorter each)"
    subheading_style: "task_oriented, imperative"
    subheading_examples:
      good: ["Set up the database", "Handle authentication", "What can go wrong"]
      bad: ["Database Setup Section", "Authentication Overview", "Error Handling"]
    transition_style: "sequential and logical"
    evidence_style: "code examples, before/after comparisons, benchmarks"
    lists: "bullet points encouraged for steps, prerequisites, options"
    callouts:
      - type: "warning"
        usage: "Destructive actions, common mistakes, breaking changes"
      - type: "tip"
        usage: "Shortcuts, performance gains, non-obvious features"
      - type: "note"
        usage: "Important context that doesn't fit the main flow"

  closing:
    preferred: ["what_you_built_summary", "next_steps", "related_resources"]
    avoid: ["motivational_ending", "philosophical_reflection"]

  word_count_targets:
    short: 600
    standard: 1200
    long: 3000
```

---

## Preset 3: The Newsletter Voice

**Best for**: Email newsletters, weekly roundups, editorial digests
**Tone**: Intimate, opinionated, time-aware — like a smart friend emailing you their take
**Think**: Stratechery, The Hustle, Not Boring, Morning Brew

```yaml
preset_id: newsletter-voice
display_name: "The Newsletter Voice"
tagline: "Intimate, opinionated, timely — the smart friend in your inbox"
best_for: ["newsletter", "editorial", "weekly_roundup", "industry_analysis"]

voice:
  personality: >
    Writes like they're emailing ONE person, not broadcasting. Has opinions and states
    them directly. Acknowledges they might be wrong sometimes. Creates a sense of
    intimacy. Time-aware: references "this week," "yesterday," "last month's issue."
  formality: 5
  humor_style: "sardonic, culturally aware, pop-culture references okay"
  humor_frequency: "moderate"
  pov: "first_person_direct_to_reader"

sentence_patterns:
  avg_length: 15
  max_length: 28
  variety: "high"
  fragment_frequency: 0.10
  rhetorical_questions: true

paragraph_patterns:
  avg_length: 2
  max_length: 3  # hard limit for prose — the shared voice defaults
  one_sentence_paragraphs: true  # Essential for newsletter pacing

punctuation:
  em_dash: false  # globally banned — use commas, periods, colons, semicolons, or parentheses
  parentheticals: true
  semicolons: "rare"
  oxford_comma: true
  exclamation_marks: "sparingly"
  ellipsis: "rare"

vocabulary:
  level: "smart_casual"
  jargon_handling: "assume_some_knowledge_but_gloss_complex_terms"
  contractions: true
  preferred_words:
    - ["big deal", "significant development"]
    - ["wild", "remarkable"]
    - ["the real story", "the key takeaway"]
  banned_words:
    - "dear reader"
    - "in this issue"
    - "stay tuned"
    - "game-changer"
    - "disruptive"

structure:
  opening:
    preferred: ["cold_open_on_news", "personal_observation", "hot_take"]
    avoid: ["welcome_back", "this_week_in", "hope_you_had_a_great_week"]
    examples:
      good:
        - "Apple just did something nobody expected. And I think they're right."
        - "I changed my mind this week. It wasn't comfortable."
      bad:
        - "Welcome to this week's edition of..."
        - "Happy Monday! Hope you had a great weekend."

  body:
    section_count: "2-4 main stories for standard issue"
    subheading_style: "editorial, can be playful"
    transition_style: "conversational pivots"
    evidence_style: "linked sources + personal analysis layered on top"

  closing:
    preferred: ["looking_ahead", "open_question_to_reader", "callback"]
    avoid: ["list_of_links", "see_you_next_week"]
    reader_engagement: "Ask a question or invite replies: 'What am I missing? Hit reply.'"

  word_count_targets:
    short: 500
    standard: 1000
    long: 2000
```

---

## Preset 4: The Executive Communicator

**Best for**: Internal memos, board updates, strategy docs, all-hands emails, investor updates
**Tone**: Clear, decisive, respectful of the reader's time — every sentence earns its place
**Think**: Jeff Bezos shareholder letters, Stripe annual letters

```yaml
preset_id: executive-communicator
display_name: "The Executive Communicator"
tagline: "Decisive, structured, zero waste — respects the reader's time above all"
best_for: ["memo", "board_update", "strategy_doc", "investor_update", "allhands_email"]

voice:
  personality: >
    Decisive but not dictatorial. States conclusions first, then supports them.
    Never hides behind passive voice. Acknowledges tradeoffs directly.
  formality: 8
  humor_style: "none"
  humor_frequency: "almost_never"
  pov: "first_person_institutional"  # "We" for the company, "I" for personal recommendations

sentence_patterns:
  avg_length: 15
  max_length: 25
  variety: "moderate"
  fragment_frequency: 0.02
  rhetorical_questions: false

paragraph_patterns:
  avg_length: 2
  max_length: 3  # hard limit for prose — the shared voice defaults
  one_sentence_paragraphs: true  # For key conclusions

punctuation:
  em_dash: false  # globally banned — use commas, periods, colons, semicolons, or parentheses
  parentheticals: "rare"
  semicolons: "acceptable"
  oxford_comma: true
  exclamation_marks: "never"
  ellipsis: "never"

vocabulary:
  level: "business_professional"
  jargon_handling: "use_if_audience_knows_it; define_if_cross_functional"
  contractions: false  # "We do not" rather than "We don't"
  preferred_words:
    - ["recommend", "suggest"]
    - ["because", "due to the fact that"]
    - ["will", "is expected to"]
    - ["decided", "determined"]
  banned_words:
    - "synergy"
    - "circle back"
    - "low-hanging fruit"
    - "move the needle"
    - "boil the ocean"
    - "at the end of the day"
    - "going forward"
    - "leverage"
    - "align"

structure:
  opening:
    preferred: ["bluf", "situation_complication_resolution"]
    avoid: ["background_first", "lengthy_context", "thank_you_for_your_time"]
    examples:
      good:
        - "I recommend we delay the launch by two weeks. The risk of shipping with the current auth bug outweighs the cost of the delay. Here is my reasoning."
        - "Revenue grew 23% QoQ. Churn dropped to 4.1%. We are on track, but two risks need attention."
      bad:
        - "As you know, we have been working on the new product for several months..."

  body:
    section_count: "3-5, each with a clear purpose"
    subheading_style: "declarative statements, not labels"
    subheading_examples:
      good: ["Revenue is growing but margins are compressing", "We should delay the launch"]
      bad: ["Financial Update", "Launch Status"]
    evidence_style: "data first, narrative second"
    callout_patterns:
      recommendation: "RECOMMENDATION: [clear statement]"
      decision_needed: "DECISION NEEDED: [what, by when, who]"
      risk: "RISK: [description] — MITIGATION: [plan]"

  closing:
    preferred: ["clear_next_steps", "decision_request", "timeline"]
    avoid: ["vague_optimism", "let_me_know_if_you_have_questions"]

  word_count_targets:
    short: 400
    standard: 800
    long: 1500
```

---

## Preset 5: The Case Study

**Best for**: Customer success stories, case studies, proof points for sales
**Tone**: Narrative but credible — tells a story with real numbers
**Think**: Stripe Atlas stories, HubSpot case studies

```yaml
preset_id: case-study
display_name: "The Case Study"
tagline: "Story-driven, data-backed — turns customer wins into compelling narratives"
best_for: ["case_study", "customer_story", "success_story"]

voice:
  personality: >
    Journalist covering a success story. Lets the customer be the hero, not the product.
    Uses specific numbers and timelines. Narrative arc: problem — struggle — discovery — result.
  formality: 7
  humor_style: "none"
  pov: "third_person"  # "Acme Corp faced..." not "We helped Acme..."

sentence_patterns:
  avg_length: 16
  max_length: 28
  variety: "moderate"
  fragment_frequency: 0.02
  rhetorical_questions: false

vocabulary:
  level: "business_accessible"
  jargon_handling: "avoid unless industry-specific and audience expects it"
  contractions: true
  required_elements:
    - "Specific numbers: revenue, time saved, % improvement"
    - "Timeline: when did this happen"
    - "Direct quotes from the customer (1-2 per section)"
    - "Before/after comparison"
  banned_phrases:
    - "best-in-class"
    - "world-class"
    - "cutting-edge"
    - "industry-leading"
    - "seamless"
    - "we were thrilled"

structure:
  opening:
    preferred: ["customer_problem_cold_open", "dramatic_result_then_flashback"]
    avoid: ["company_description", "product_description"]
  body:
    section_flow: ["The Challenge", "The Search for a Solution", "The Implementation", "The Results", "What's Next"]
    quote_guidelines: >
      Use 1-2 direct quotes per section. Quotes should reveal emotion or insight,
      not restate facts. "We saved 40%" is a fact — put it in prose.
      "I finally stopped dreading Monday mornings" is a quote worth using.
  closing:
    preferred: ["forward_looking_quote", "next_goal", "invitation_to_reader"]
    result_box: >
      RESULTS AT A GLANCE
      • Metric 1: Before → After
      • Metric 2: Before → After
      • Timeline: X months

  word_count_targets:
    short: 600
    standard: 1000
    long: 1800
```

---

## Preset 6: The How-To Guide

**Best for**: Step-by-step guides, tutorials, playbooks, SOPs
**Tone**: Supportive coach — assumes the reader will follow along
**Think**: DigitalOcean tutorials, Tania Rascia, Josh W. Comeau

```yaml
preset_id: how-to-tutorial
display_name: "The How-To Guide"
tagline: "Step-by-step, patient, gets you from stuck to done"
best_for: ["how_to", "tutorial", "playbook", "SOP", "guide"]

voice:
  personality: >
    A patient teacher who remembers what it's like to not know this yet.
    Never talks down. Celebrates small wins. Warns about common mistakes BEFORE
    the reader makes them. Always tells the reader what they should see at each step.
  formality: 4
  humor_style: "light, empathetic"
  humor_frequency: "rare"
  pov: "second_person"

sentence_patterns:
  avg_length: 13
  max_length: 22
  variety: "moderate"

vocabulary:
  level: "beginner_friendly"
  jargon_handling: "define_everything_on_first_use"
  contractions: true
  banned_words:
    - "simply"
    - "just"
    - "easy"
    - "obviously"
    - "trivial"
    - "straightforward"

structure:
  opening:
    required_elements:
      - "What the reader will have at the end"
      - "Time estimate"
      - "Prerequisites list"
      - "Difficulty level (Beginner / Intermediate / Advanced)"
  body:
    step_format: >
      Every step must include:
      1. What to do (action)
      2. How to do it (command, screenshot, or instruction)
      3. What you should see (verification)
    callouts:
      - type: "warning"
        usage: "BEFORE the step that could cause problems"
      - type: "checkpoint"
        usage: "After every 3-4 steps"
      - type: "troubleshooting"
        usage: "Common errors for each step with solutions"
  closing:
    preferred: ["what_you_built_recap", "next_steps", "further_reading"]
    celebration: "Acknowledge the reader's effort: 'You now have a working X. Nice work.'"

  word_count_targets:
    short: 500
    standard: 1500
    long: 4000
```

---

## Preset 7: The Social Long-Form

**Best for**: LinkedIn posts, Threads posts, long-form social content
**Tone**: Punchy, scroll-stopping, personal — optimized for mobile reading
**Think**: Top LinkedIn creators, viral Threads posts

```yaml
preset_id: social-longform
display_name: "The Social Long-Form"
tagline: "Punchy, scroll-stopping, personal — built for feeds"
best_for: ["linkedin_post", "threads_post", "social_longform"]

voice:
  personality: >
    Direct, personal, pattern-interrupting. Every line has to earn its place
    because the reader is one thumb-scroll from leaving. Uses "I" constantly.
    Never sounds like a press release.
  formality: 3
  humor_style: "self-deprecating, unexpected"
  humor_frequency: "moderate"
  pov: "first_person"

sentence_patterns:
  avg_length: 10  # Very short. Punchy.
  max_length: 20
  variety: "extreme"
  fragment_frequency: 0.20  # High. Fragments are the currency of social.
  rhetorical_questions: true

paragraph_patterns:
  avg_length: 1  # Often one sentence per line
  max_length: 3
  one_sentence_paragraphs: true  # This IS the format
  line_break_frequency: "after_every_1-2_sentences"

punctuation:
  em_dash: false  # globally banned — use commas, periods, colons, semicolons, or parentheses
  semicolons: "never"
  oxford_comma: true
  exclamation_marks: "sparingly"
  ellipsis: "acceptable"  # For dramatic pause
  colon_for_reveal: true  # "The result: [punchline]"

vocabulary:
  level: "everyday"
  jargon_handling: "avoid_entirely_unless_audience_is_expert"
  contractions: true
  power_words:
    - "mistake"
    - "learned"
    - "wrong"
    - "actually"
    - "truth"
    - "nobody talks about"
  banned_patterns:
    - "Excited to announce..."
    - "I'm humbled to..."
    - "Thrilled to share..."
    - "Grateful for..."
    - "Agree?"
    - "Thoughts?"
    - hashtag_stuffing

structure:
  opening:
    preferred: ["hook_line", "counterintuitive_claim", "personal_failure"]
    requirements: >
      First line MUST stop the scroll. It should be surprising, vulnerable,
      or contrarian. Test: would YOU stop scrolling for this line?
    examples:
      good:
        - "I got fired from my dream job. Best thing that ever happened to me."
        - "Stop asking for feedback. Start asking for criticism."
      bad:
        - "5 Tips for Better Productivity"
        - "I'm excited to share some thoughts on leadership"

  body:
    pattern: "Hook → Story → Insight → Reframe → CTA"

  closing:
    preferred: ["reframe_the_hook", "actionable_takeaway", "vulnerable_admission"]
    avoid: ["follow_me_for_more", "like_and_share", "link_in_comments"]
    engagement_prompt: "Ask a genuine question that invites stories, not yes/no"

  word_count_targets:
    linkedin: 200-300
    threads: 100-200
    long_linkedin: 500
```

---

## Preset 8: The Internal Doc

**Best for**: RFCs, design docs, strategy memos, team proposals, decision documents
**Tone**: Rigorous, structured, designed for async reading and decision-making
**Think**: Amazon 6-pagers, Google design docs, well-written RFCs

```yaml
preset_id: internal-comms
display_name: "The Internal Doc"
tagline: "Rigorous, structured, built for async decisions — the Amazon 6-pager approach"
best_for: ["RFC", "design_doc", "strategy_doc", "proposal", "decision_doc"]

voice:
  personality: >
    Rigorous and thorough. Every claim has evidence. Every recommendation
    acknowledges tradeoffs. Structured for skimming — a reader should get
    the gist from headings alone. Written for async readers without you present.
  formality: 7
  humor_style: "none"
  pov: "first_person_plural"

sentence_patterns:
  avg_length: 16
  max_length: 28
  variety: "moderate"
  fragment_frequency: 0.01

vocabulary:
  level: "professional_technical"
  jargon_handling: "use_if_internal_audience_knows_it; acronym_glossary_for_cross_team"
  contractions: false
  required_sections:
    - "TL;DR / Executive Summary (3-5 sentences max)"
    - "Context / Background"
    - "Problem Statement"
    - "Proposed Solution"
    - "Alternatives Considered (at least 2)"
    - "Tradeoffs & Risks"
    - "Implementation Plan / Timeline"
    - "Open Questions"
    - "Decision Needed"

structure:
  opening:
    preferred: ["tldr_first", "problem_statement"]
    required: >
      MUST start with a TL;DR of 3-5 sentences. A senior leader should be able
      to read ONLY the TL;DR and understand what is being proposed and why.

  body:
    evidence_style: "data, benchmarks, customer quotes, competitive analysis"
    alternatives_required: true
    tradeoff_format: >
      For each option:
      OPTION: [description]
      PROS: [list]
      CONS: [list]
      EFFORT: [estimate]
      RISK: [assessment]

  closing:
    required: >
      RECOMMENDATION: [clear statement]
      DECISION NEEDED: [what decision, who decides, by when]
      OPEN QUESTIONS: [unresolved items]
      NEXT STEPS: [if approved, what happens first]

  word_count_targets:
    short: 800
    standard: 2000
    long: 4000
```

---

## Override System

Writers can modify any preset without starting from scratch:

```yaml
# Example: Use conversational-authority but make it more formal
base_preset: conversational-authority
overrides:
  voice.formality: 8
  vocabulary.contractions: false
  sentence_patterns.fragment_frequency: 0.02
  punctuation.exclamation_marks: "never"
```

**Natural language overrides (handled by agent):**
- "Make it less casual" → Increase formality, reduce fragments, remove contractions
- "More punch" → Shorter sentences, more fragments, more one-sentence paragraphs
- "Sound more like a newsletter" → Mixin newsletter-voice pacing and opening patterns
- "Tone down the humor" → Set humor_frequency to "rare"
