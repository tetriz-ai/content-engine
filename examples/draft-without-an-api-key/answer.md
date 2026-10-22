# Flaky tests cost more than the re-run

One Show HN post this month described a small CI plugin that re-runs a failed test once and
tags it flaky if the second run passes. Its authors say false-red builds fell by about a third
in the first month.

The same week, an engineer on r/ExperiencedDevs described a suite where about 15 tests fail
roughly one run in twenty, and a team that now re-runs every red build.

One named survey of 400 teams puts the median cost at 6.5 engineering hours a week. That is
one survey's median, not a rule for every team.

If your team also re-runs and moves on, start by counting how often it happens.
