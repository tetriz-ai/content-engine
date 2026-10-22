"""A writer that honours content-engine's writer contract and drafts only an outline.

Contract: take --theme-doc and --format (and --out), refuse a theme with no
evidence, write a Markdown draft with `status: draft` frontmatter, and never
publish anything. Point
`write.<format>.command` in config.yaml at a program like this one to use it.
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone

SIGNALS = re.compile(r"##[ \t]+Signals(?:[ \t]*\([^)\n]*\)|[ \t]+\d+)?[ \t]*$", re.I)
HEADING = re.compile(r"#{1,2}[ \t]")  # a level-1 or level-2 heading ends a section
ITEM = re.compile(r"(?:[-*+]|\d+[.)])\s+")
LABEL = r"[a-z0-9-]*[a-z0-9][a-z0-9-]*"
HOST = re.compile(LABEL + r"(?:\." + LABEL + r")+(?::\d+)?", re.I)

# The fence, comment and indented-code rules mirror the bundled write_reference.py.
FENCE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")
CODE = re.compile(r"(?: {4}| {0,3}\t)")


def real_url(line):
    """An http(s) URL with a dotted host and no placeholder, as the bundled writer requires."""
    for url in re.findall(r"https?://[^\s|]+", line, re.I):
        host = url.split("://", 1)[1].split("/", 1)[0].split("?", 1)[0].rstrip("),.")
        if not any(m in url for m in ("<", ">", "...", "…")) and HOST.fullmatch(host):
            return True
    return False


def readable_lines(text):
    """The lines outside fenced code and HTML comments. A fence opens with 3 or more
    backticks or tildes (a backtick opener has no backtick after it) and closes with a
    bare run of the same character at least as long. An unclosed fence or comment runs
    to the end."""
    kept, fence = [], None
    for line in text.split("\n"):
        m = FENCE.match(line)
        if fence is None:
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                fence = m.group(1)
            else:
                kept.append(line)
        elif (
            m
            and m.group(1)[0] == fence[0]
            and len(m.group(1)) >= len(fence)
            and not m.group(2).strip()
        ):
            fence = None
    return re.sub(r"<!--.*?(?:-->|\Z)", "", "\n".join(kept), flags=re.S).split("\n")


def signal_titles(text):
    """One title per signal under `## Signals`: a table row below the header,
    or a list item, that holds a real URL. Indented code (4 or more spaces at
    the section's start or after a blank line) is skipped."""
    titles, in_signals, header_seen, code_may_start = [], False, False, True
    for line in readable_lines(text):
        if HEADING.match(line):
            in_signals, header_seen, code_may_start = bool(SIGNALS.match(line)), False, True
            continue
        if not in_signals:
            continue
        if not line.strip():
            header_seen, code_may_start = False, True  # the next table starts with its header
            continue
        if code_may_start and CODE.match(line):
            continue
        code_may_start = False
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if header_seen and real_url(line):
                titles.append(cells[1] if len(cells) > 2 else cells[0])
            header_seen = True
        else:
            header_seen = False
            if ITEM.match(line.strip()) and real_url(line):
                titles.append(ITEM.sub("", line.strip(), 1))
    return titles


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--theme-doc", required=True)
    ap.add_argument("--format", required=True, choices=["blog", "linkedin", "video"])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.theme_doc, encoding="utf-8") as f:
        text = f.read()
    title_m = re.search(r"^# Theme:\s*(.+)$", text, re.M)
    title = (
        title_m.group(1).strip()
        if title_m
        else os.path.splitext(os.path.basename(args.theme_doc))[0]
    )
    count = sum(1 for line in readable_lines(text) if SIGNALS.match(line))
    if count > 1:
        sys.exit(
            "%s has %d '## Signals' sections; merge them into one, so no evidence "
            "is left out of the outline." % (args.theme_doc, count)
        )
    titles = signal_titles(text)
    if not titles:
        sys.exit("%s has no signal rows, so there is nothing to outline." % args.theme_doc)
    lines = [
        "---",
        "status: draft",
        "format: %s" % args.format,
        "source_theme_doc: %s" % args.theme_doc,
        "generated_at: %s" % datetime.now(timezone.utc).isoformat(),
        "drafted_by: outline-writer",
        "---",
        "",
        "# %s" % title,
        "",
    ]
    lines += ["%d. Open with: %s" % (i, t) for i, t in enumerate(titles, 1)]
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("Outline written -> %s" % args.out)


if __name__ == "__main__":
    main()
