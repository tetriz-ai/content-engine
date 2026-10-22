#!/usr/bin/env python3
# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
"""
report.py — a lightweight observability summary for content-engine.

Reads the signal bank and the theme docs directory and prints signal
counts by source (spent and un-spent, and the share that reached a theme)
and theme counts by status and by coverage tier. It never writes.

Usage:
  python3 report.py --config path/to/config.yaml
  python3 report.py --bank path/to/bank.jsonl --themes-dir path/to/themes
"""

import argparse
import glob
import json
import os
import sys
from collections import Counter

from write_reference import read_coverage_tier, read_field, theme_header


def load_bank(path):
    """Rows of the JSONL signal bank. A missing file is an empty list. A line
    that is not UTF-8, not JSON, or not a JSON object is warned about on
    stderr and skipped."""
    rows: list = []
    if not os.path.exists(path):
        return rows
    if os.path.isdir(path):
        sys.exit("The signal bank path is a directory, not a JSONL file: %s" % path)
    with open(path, "rb") as f:
        for lineno, raw in enumerate(f, 1):
            try:
                line = raw.decode("utf-8").strip()
            except UnicodeDecodeError:
                print("  [warn] %s:%d skipped, not UTF-8" % (path, lineno), file=sys.stderr)
                continue
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                print(
                    "  [warn] %s:%d skipped, not valid JSON (%s)" % (path, lineno, e),
                    file=sys.stderr,
                )
                continue
            if not isinstance(row, dict):
                print(
                    "  [warn] %s:%d skipped, not a JSON object" % (path, lineno),
                    file=sys.stderr,
                )
                continue
            rows.append(row)
    return rows


def load_themes(themes_dir):
    """Status and coverage tier of each `theme-*.md`. The tier is read as the
    writer reads it; anything but STRONG or THIN counts as THIN, with a warning."""
    themes: list = []
    if not os.path.isdir(themes_dir):
        return themes
    for path in sorted(glob.glob(os.path.join(themes_dir, "theme-*.md"))):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        # Status and the tier come from the header, as the writer reads them.
        header = theme_header(text)
        status = read_field(header, "Status")
        tier = read_coverage_tier(header)
        if tier is None:
            print(
                "  [warn] %s has no '**Coverage tier:**' line reading STRONG or THIN; "
                "counted as THIN" % path,
                file=sys.stderr,
            )
        themes.append(
            {
                "path": path,
                "status": status or "unknown",
                "coverage_tier": tier or "THIN",
            }
        )
    return themes


def render(rows, themes, out=None):
    """Print the counts to `out` (default: sys.stdout at call time)."""
    if out is None:
        out = sys.stdout
    by_source = Counter(r.get("source", "unknown") for r in rows)
    spent_by_source = Counter(r.get("source", "unknown") for r in rows if r.get("theme_id"))
    unspent = sum(1 for r in rows if not r.get("theme_id"))

    print("=== Signal bank ===", file=out)
    print(
        "Total rows: %d (%d un-spent, %d spent)" % (len(rows), unspent, len(rows) - unspent),
        file=out,
    )
    print(file=out)
    if by_source:
        print("By source — spent / total (the real tuning signal: a source", file=out)
        print("that's always near 0% is scanning noise, not evidence):", file=out)
        for source in sorted(by_source):
            total = by_source[source]
            spent = spent_by_source.get(source, 0)
            rate = "%3.0f%%" % (100.0 * spent / total) if total else " n/a"
            print("  %-18s %4d / %4d   %s" % (source, spent, total, rate), file=out)
    else:
        print("(bank is empty — run --mode scan first)", file=out)

    print(file=out)
    print("=== Themes ===", file=out)
    print("Total: %d" % len(themes), file=out)
    if themes:
        status_counts = Counter(t["status"] for t in themes)
        tier_counts = Counter(t["coverage_tier"] for t in themes)
        print(file=out)
        print("By status:", file=out)
        for status in sorted(status_counts):
            print("  %-12s %d" % (status, status_counts[status]), file=out)
        print(file=out)
        print("By coverage tier:", file=out)
        for tier in sorted(tier_counts):
            print("  %-12s %d" % (tier, tier_counts[tier]), file=out)
    else:
        print("(no theme docs yet — run --mode cluster then --mode brief)", file=out)

    if not rows and not themes:
        print(file=out)
        print("Nothing to report yet. Try --mode quickstart on the bundled", file=out)
        print("example config first to see real output shape.", file=out)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--config",
        default=None,
        help="read scan.bank_path / brief.themes_dir from here "
        "(overridden by --bank/--themes-dir if also given)",
    )
    ap.add_argument("--bank", default=None)
    ap.add_argument("--themes-dir", default=None)
    args = ap.parse_args()

    bank_path = args.bank
    themes_dir = args.themes_dir

    if args.config and (bank_path is None or themes_dir is None):
        try:
            import yaml
        except ImportError:
            sys.exit(
                "Missing dependency: PyYAML. Install it with:\n"
                "  pip install -r ../scanner-core/requirements.txt"
            )
        if not os.path.exists(args.config):
            sys.exit("Config file not found: %s" % args.config)
        with open(args.config) as f:
            cfg = yaml.safe_load(f)
        if not isinstance(cfg, dict):
            sys.exit("Config file %s is empty or not a YAML mapping." % args.config)
        scan_cfg = cfg.get("scan") or {}
        if not isinstance(scan_cfg, dict):
            sys.exit("`scan` in %s must be a mapping, not %r." % (args.config, scan_cfg))
        brief_cfg = cfg.get("brief") or {}
        if not isinstance(brief_cfg, dict):
            sys.exit("`brief` in %s must be a mapping, not %r." % (args.config, brief_cfg))
        if bank_path is None:
            bank_path = scan_cfg.get("bank_path")
        if themes_dir is None:
            themes_dir = brief_cfg.get("themes_dir")

    bank_path = bank_path or "context-library/content-signal-bank.jsonl"
    themes_dir = themes_dir or "docs/content-themes"

    if not os.path.exists(bank_path):
        print(
            "[warn] no signal bank at %s — check scan.bank_path or --bank, "
            "or run --mode scan first" % bank_path
        )
    if not os.path.isdir(themes_dir):
        print(
            "[warn] no themes directory at %s — check brief.themes_dir or "
            "--themes-dir, or run --mode brief first" % themes_dir
        )
    rows = load_bank(bank_path)
    themes = load_themes(themes_dir)
    render(rows, themes)


if __name__ == "__main__":
    main()
