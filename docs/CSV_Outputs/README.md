# Raw metric exports (evidence)

Raw data exported from the live deployment before teardown — the numbers behind
the README's results table, kept for provenance.

| File | Source | What it holds |
| ---- | ------ | ------------- |
| `Request_latency_(ms)-...-07_05_00-UTC.csv` | CloudWatch dashboard | p50/p95/p99 latency per 5-min bucket, ~2h45m |
| `Requests_&_errors-...-07_05_00-UTC.csv` | CloudWatch dashboard | request count + 5xx errors per 5-min bucket |
| `...-lf-events-export-...csv` | Langfuse | one `/v1/query` trace, per-node tokens/latency/cost |
| `log-events-viewer-result.csv` | CloudWatch Logs | container structured access logs + EMF metric lines |

**Headline (computed from these files):** 1,013 requests · **0 errors** over
~2h45m · p50 ~825 ms · p95 ~1,193 ms · avg cost **$0.000358/query** (gpt-4o-mini).
The shorter `..._04_45_00-UTC.csv` variants are the earlier ~25-min snapshots.
