Calls scanner-core's `scan_hn` and `scan_reddit` from Python with a `failures` list, the way you would use the fetchers in your own script. A stub in place of `urlopen` answers from canned data, fails one Reddit feed, and refuses any other URL, so no request leaves the machine. The output shows a post below `min_points` and an off-topic post left out, and the failed feed listed.

```sh
examples/find-posts-from-python/run.sh
```

```text
hn:101           Show HN: A flaky test detector for CI  [flaky test]
reddit:t3_aaa    Our CI pipeline reliability is getting worse  [ci pipeline reliability]
failed: reddit r/devops hot: HTTP Error 500: Internal Server Error
```
