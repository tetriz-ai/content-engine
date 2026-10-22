# Cache outage postmortem

Source: https://blog.example.com/guides/ci-reliability/cache-outage-postmortem (published 2026-05-03)
Category: ci-reliability

## What happened

The dependency cache went stale and every build downloaded everything.

## Three numbers we tracked

- Build minutes
- Cache hit rate
- Queue time
