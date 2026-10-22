Counts the bundled sample signal bank by source, with how many signals each source got into a theme, and counts the sample theme docs by status and grade. Run it on your own bank to see which sources are worth keeping: one that never reaches a theme is scanning noise.

```sh
examples/count-signals-and-themes/run.sh
```

```text
=== Signal bank ===
Total rows: 3 (3 un-spent, 0 spent)

By source — spent / total (the real tuning signal: a source
that's always near 0% is scanning noise, not evidence):
  competitor_blog       0 /    1     0%
  hn                    0 /    1     0%
  reddit                0 /    1     0%

=== Themes ===
Total: 1

By status:
  approved     1

By coverage tier:
  STRONG       1
```
