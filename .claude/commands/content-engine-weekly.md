---
description: Run the bundled content-engine-weekly workflow with approved sources, voice and output paths.
---

Resolve the engine root from `${CLAUDE_PLUGIN_ROOT}` when loaded as a plugin, otherwise the repository root two levels above this command file's real directory. Keep the
working directory at the caller's repository. Read `references/weekly.md` relative to that root
in full, then execute the exact requested arguments and approval scope. Engine
resources are read-only; durable state belongs to the caller. No automatic publication.
