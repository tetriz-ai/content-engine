---
status: draft
format: blog
source_theme_doc: examples/theme-example-ci-flakiness.md
generated_at: hand-authored example
note: >
  A hand-written example of the draft format, for the fictional product in
  examples/theme-example-ci-flakiness.md. Real drafts carry a drafted_by
  field naming the model or the Claude Code session that wrote them.
---

# The Quiet Tax of Flaky Tests

A flaky test is easy to stop noticing. It becomes a habit — the kind you
stop seeing because you've built your whole day around it.
Red build, shrug, re-run, green. Nobody files a ticket. Nobody owns the fix.
It just costs time, quietly, every single day.

One recent Show HN post put a number on the quiet part: a small CI plugin
that re-runs a failed test once and, if it passes the second time, tags it
flaky instead of failed. Nothing fancy — no root-cause analysis, no test
rewrite. Just a label. The team that built it reported their false-red rate
dropped by about a third in the first month.

A third isn't a fix. It's a tag. But it's the kind of thing you only build
once you've stopped pretending the problem will go away on its own — and
the same week that post went up, a practitioner on r/ExperiencedDevs was
describing the exact failure mode it's a response to: roughly 15 tests in
their suite fail about one run in twenty, for no reason anyone's tracked
down, and the team's informal policy is now "just re-run it." Nobody trusts
a single red build anymore. Everyone reruns and moves on.

That's two independent accounts of the same pattern in the same week — one
team building a tool for it, another team just living with it. Worth asking
whether it's actually as common as it feels from the inside. One answer:
a survey of 400 engineering teams this year found a median of 6.5
engineering hours lost per week to re-running CI builds over tests that
weren't actually broken. That's a median across a real sample, not a
universal number — but it's the first time this particular tax has shown up
with a number attached instead of just a vibe everyone shares in private.

None of this means flakiness is solved. The HN tool's own author was clear
that tagging cut false-reds by about a third, not to zero — the underlying
non-determinism is still there, just labeled instead of hidden. But "label
it, then decide what to do about it" is a meaningfully different starting
point than "re-run and hope," and it's the starting point more teams seem
to be reaching for right now, not fewer.

If your team's informal policy is also "just re-run it", you're in the
company of the two teams above. The question worth asking
isn't whether your suite has flaky tests. It's whether anyone's actually
measuring how much they cost you yet.
