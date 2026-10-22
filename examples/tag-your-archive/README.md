Tags each post in a small sample archive with its content type, from a saved answer, the way a Claude Code session tags them when no API key is set. Then it lists the archive's categories and types, and shows which posts the writer picks as voice examples for a theme doc that asks for a postmortem in `ci-reliability`. With `max_examples: 3`, it takes both postmortems, then one more post from the same category.

```sh
examples/tag-your-archive/run.sh
```

```text
  tag index: 4 post(s) added, from files with no entry
4 tagged, 0 untagged left -> <tmp>/archive/.tags.json
posts: 4, untagged: 0
categories: ci-reliability (3)
content types: checklist (1), personal story (1), postmortem (2)
voice examples: 2 of type "postmortem", 1 of category "ci-reliability"
```
