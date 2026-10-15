# FORGE R24 — Existing GitHub atomic source-merge safety acceptance

**Objective:** Close engineering safety gaps in *prospective* automatic source promotion without enabling any source merge, extending credentials, changing a user setting, creating a new controller, or invoking Codex.

R24 adds a read-only diagnostic preflight reusing the installed R21 auditor. The preflight pins the full 40-character source head and base SHA, audits the complete eligible FSA diff and exact-head independently successful public and FSA-source jobs, verifies native reviews and current GitHub mergeability, re-reads PR head/base and actual GitHub branch rules at multiple points, and denies on any conflict or drift. It reports a hypothetical readiness *observation only*: `MergeAuthorized=false` and `ScientificAuthority=false` in every outcome.

The real qualified acceptance subject is FSA regression PR #246, source head `82a6cb225e0783adebae66a5607c123080cf2355` and base `6eb6ccda00d3754e872ea791d4ccc025734274f8`; both original GitHub-hosted qualification workflows have passed.

GitHub Actions token ruleset detail lacks `bypass_actors`. The expected authentic result is `POLICY_VISIBILITY_BLOCKED:RULESET_BYPASS_VISIBILITY_MISSING`: source tests are accepted, source merge is correctly denied. This is **not** a signed complete independent ruleset witness, and any local positive fixture is *not* a real policy attestation.

**Atomic merge contract if ever explicitly enabled in a separately approved gate:** the final trusted authority must recheck fresh current PR head/base, native reviews, full server-enforced branch policy and exact required checks; send the exact immutable expected head SHA to GitHub's merge endpoint with merge method `merge`; and accept only GitHub's actual success and accepted main ref. Reject drift, duplicate/unknown files, untrusted workflows, missing bypass visibility, unresolved threads, changes requested, missing independent science custody, or stale base. No fallback to a force, bypass, client-asserted pass or manual comment approval.

The current scheduled workflow remains `contents:read` with no merge call. The separate required **scheduled execution** acceptance is only fulfilled when GitHub records an authentic `schedule` run of that exact default-branch installed workflow **after R21 promotion** (the last observed run predates installation). A hosted R24 PR test is *not* the scheduled event.

Leave Wingless and Yggdrasil science running independently; no Cloudflare/FSA controller work, KTRADE changes, or model spending.
