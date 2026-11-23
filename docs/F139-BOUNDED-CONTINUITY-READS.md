# Bounded continuity reads — engineering repair, no owner deployment

Protected parent `8b5195121fc7750ec5398275fd86d55b9e2a436c`, tree
`b0c4290856d322a03216c84765e701e014c7daa7`. Original-owner observation
[42639132722](https://github.com/spoonman136668-ai/FORGE/actions/runs/42639132722)
reported repeated `F139_GITHUB_API_RESPONSE_TOO_LARGE`, unchanged ledger event
1462 and installed source `42c70d74dd93ef90d0f4618fefefe2206b81eafe`.

An authenticated read-only GitHub comparison of that installed SHA to this
protected parent returned 265 forward commits, zero behind, the installed SHA
as merge base, 250 returned commits, 200 files and 2,184,735 characters.
Even its character count exceeds the existing transport's 2,100,000-byte cap.
The same fixed-SHA comparison with `?per_page=1&page=2` returned 11,510
characters, one commit, no file patches and identical ancestry metadata.
These are connector response character counts, not measured wire bytes,
runtime throughput, CPU/RAM usage or an original-owner acceptance receipt.

The research-only verifier previously fetched the whole comparison before
checking its 80-commit limit; a transport exception escaped before the existing
release-pin fallback. It now reads patch-free page-2 ancestry first and rejects
out-of-budget histories. Eligible histories still need the complete original
commit/file/patch proof, consistent counts and protected-main recheck. No
ancestry-only response grants research-file or source-transition authority.

The release-pin verifier needs ancestry metadata only and now uses that same
bounded query. Exact policy owner/source, enabled policy, immutable worker ref,
forward ancestry, original clean checkout, database verification/activation and
protected-main recheck retain their existing requirements. Read failures remain
fail closed. No response limit, source allowlist, workflow, branch protection,
retry/write semantics, ledger, policy or scheduled task is changed.

Focused and negative tests cover the 265-commit failure without patch transfer,
full-proof count drift, malformed metadata, unavailable provider, rewrite,
divergence, missing original policy, worker-ref drift, protected-head movement
and forbidden operational file changes. Mandatory final-candidate full
Linux/Windows regression and builds are required before protected merge.

This is source-level engineering only. Installed source 42c70d74 is unchanged;
the existing V40 original-owner preflight has no qualified remote invocation
route, and V40 live application remains disabled. The pending original
publication custody, exact production binary, two-slot/Hybrid migration,
private Hybrid worker access and real signed three-lane receipts remain
independent acceptance gates. No science, GPU work, first-use or model
promotion is performed by this change.
