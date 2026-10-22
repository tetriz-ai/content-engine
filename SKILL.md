---
name: content-engine
description: Mine approved market signals, cluster evidence-backed themes, audit inventory and competitor gaps, plan refreshes, prepare weekly queues, and draft approved blogs or LinkedIn posts through the bundled Blog and Editorial Draft pipeline. Use for content research, planning, or multi-format drafting in Claude Code or Codex.
---

# Content Engine

This checkout owns the full pipeline: **Editorial Draft ← Blog ← Content Engine**.
Each lower layer works independently and accepts caller-supplied facts, voice and approvals.

## Caller and host contract

Keep the working directory at the caller's repository. Resolve this skill's directory
through the host catalog or real path of its installed symlink; that is `engine_root`.
Run `python3 <engine_root>/scripts/resolve-context.py --working-root <caller-root>`
with an explicit `--config <path>` when supplied. Read the returned paths. Never
search other repositories for a matching config. Engine scripts, rules, presets and
example templates resolve under `engine_root`; config, credentials, signal bank,
theme documents, archives and output resolve under `working_root` unless the caller
supplied an explicit authorized path. Invoke scripts by absolute path, from the
working root, passing the explicit caller config. No state belongs in an imported checkout.

Pass the caller's approved source scope, reviewed product/audience facts, voice guide,
public-use permissions, requested format, output paths and already approved decisions
unchanged. Read only approved sources. Missing facts remain gaps. Neither installation
nor a theme approval authorizes publication, Slack delivery, scheduling or Git writes.
Use the host's actual tools; unavailable tools remain pending. Editorial personas run
in this session unless separate agents really execute. Do not claim independent review.

## Select the canonical workflow

- Run, quickstart, init, scan, cluster, brief, approve, write and report:
  read [.claude/commands/content-engine.md](.claude/commands/content-engine.md).
- Inventory, competitor-gaps and refresh-plan, or richer supplied-source planning:
  read [references/planning.md](references/planning.md). For shared modes, this guide
  supplies editorial/evidence requirements; the command owns scanner and state mechanics.
- Weekly source review and draft queue: read [references/weekly.md](references/weekly.md).
  Stop at the queue; do not begin drafting merely because a theme was previously approved.

Read the selected guide in full, including output templates, examples and anti-patterns.
Forward the exact mode and user arguments; preserve existing mode and config semantics.
Use `--dry-run` for a requested preview: no durable writes, Slack posts or drafting;
only explicitly described scratch previews under the caller's `working/` are allowed.

## Full writing path

Only draft an approved theme/version and its approved formats with sourced signals.
Read [packages/content-engine/rules.md](packages/content-engine/rules.md) first.
For Blog, invoke [skills/blog/SKILL.md](skills/blog/SKILL.md), which owns search strategy,
claim ledger, outline approval, revision, and the Editorial Draft review/polish handoff.
For LinkedIn, invoke [skills/editorial-draft/SKILL.md](skills/editorial-draft/SKILL.md) in
refinement mode with Social Long-Form and the approved brief, format budget and voice.
Run Hemingway, Clarity, Voice, Platform and Detector, followed by scrub and final polish.
For company posts, use company POV and a brand CTA; never invent a personal origin story.
For video, produce the approved video brief, retaining the separate script-generation handoff.

Reuse known style, outline and discovery approvals. Read actual presets and reviewer
files; a prompt containing reviewer names does not establish completed reviews. Save
the polished draft, claim ledger and actual findings/dispositions before marking it
drafted. Record the execution method and publication blockers. Missing resources leave
writing pending; never silently replace the pipeline with a generic single prompt.

An explicitly configured `write.<format>.command` remains a custom writer override.
`write_reference.py` is an opt-in one-prompt/API adapter, not the full editorial pipeline;
the existing CLI and response-file examples continue to work. See Phase 4 for its contract.
