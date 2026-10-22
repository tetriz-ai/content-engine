Lists the Product Hunt launches that match your keywords or topics, with their voters and commenters, by calling scanner-core's `scan_ph` and `fetch_details` from Python. A stub in place of `urlopen` plays the GraphQL API from canned replies and fails one topic with HTTP 502, so no token is needed and no request leaves the machine. The output shows an off-topic launch left out, the maker left out of the voters, and the failed topic listed while the other topic's launches still come back.

```sh
examples/list-matching-product-hunt-launches/run.sh
```

```text
ph:11  Example Launch A 120 votes  flaky test
         voter      @janedoe
         commenter  @johndoe: We lose an hour a day to re-runs.
ph:12  Example Launch B  45 votes  topic: developer tools
         voter      @johndoe
failed: ph topic testing page 1: HTTP Error 502: Bad Gateway
```
