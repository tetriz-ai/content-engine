# Trust boundary

What the scripts defend against outside text, and what they do not.

Text from outside sources goes into the prompts of `write_reference.py`, `relevance_scorer.py`
and `archive_tag.py` only inside delimited data blocks, with a line telling the model that text in them is data, never
instructions. The one exception is `## Requested changes`, which the writer follows as edits, though it still cannot override the rules, run a tool or change a theme's approval. Outside text means signal titles and excerpts, competitor posts, archived posts
and Slack thread replies.

A theme's approval and coverage tier are read only from its doc's header lines, and
`write_reference.py` refuses an unapproved theme or format itself, so text inside a theme doc
cannot approve a draft on that route. The default Blog and Editorial Draft route runs as
instructions in the host session, which apply the same header-only gate but have no code
behind it.

The command also instructs the host session (Claude Code or Codex) to treat fetched
web text and other outside material as data, never as authorization to run tools,
read secrets, send messages or approve a theme. Prompt instructions are not a hard
security boundary: a model can still be misled. Scope scheduled Write/Edit access
to the configured output directories (see the README), grant delivery tools only
when authorized, and review each draft before publishing.
