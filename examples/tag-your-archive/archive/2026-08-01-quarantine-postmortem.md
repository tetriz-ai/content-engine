# Quarantine postmortem

Source: https://blog.example.com/guides/ci-reliability/quarantine-postmortem (published 2026-08-01)
Category: ci-reliability

## What happened

A third of our red builds were flaky tests, not real failures.

## Three numbers we tracked

- Re-runs per day
- Time to a green build
- Tests in quarantine

## What we would do again

Quarantine first, fix second.
