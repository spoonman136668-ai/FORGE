# FORGE R18 — Native GitHub review intake (non-authorizing)

R18 extends source-only R17 at exact SHA `9aab84c598f3c25c09b6148617bc0d5781fa9ee3` without changing its active, intentionally blocked source-merge workflow.

The bounded Python collector uses the GitHub Actions read-only installation token, REST GET for the native PR and its paginated reviews/files/inline comments, exact-SHA workflow runs and job outcomes, plus GraphQL **read-only** review-thread queries. It rejects cross-host/rewritten pagination links, incomplete responses, missing thread pages, duplicate jobs and changed PR head/base/draft state on a second read.

`cmd/forge-fsa-review` loads the collected snapshot, rejects non-absolute, non-regular, oversized and trailing JSON, then calls the pure R17 `fsamergeattest.Check`. Its output never authorizes a merge. An issue-comment review summary or abbreviated SHA cannot substitute for a native bot APPROVED review whose `commit_id` exactly matches the current source head.

Focused Python tests are transport-injected fixtures, not proof of a real review; the GitHub-hosted workflow performs authentic read-only retrieval. Full Linux/Windows Go regression remains mandatory on this exact head. The live probe can correctly end in a `SOURCE_IDENTITY_NOT_ELIGIBLE`, `FULL_OID_INDEPENDENT_REVIEW_MISSING` or other fail-closed classification without failing the engineering evidence-collection test.

**No operational promotion:** The source merge workflow's hard stop is retained; the collector never merges, modifies an issue, calls a remote repair agent, dispatches research, consumes first-use, touches Cloudflare or changes the optimizer bridge. A separately qualified, authorized last-mile current-head/Codex review/branch-rule admission is necessary before any real automatic merge.

Neither a standalone user-provided JSON snapshot nor synthetic test evidence conveys source authority; trustworthy collection provenance is the verified GitHub job identity and immutable workflow head.
