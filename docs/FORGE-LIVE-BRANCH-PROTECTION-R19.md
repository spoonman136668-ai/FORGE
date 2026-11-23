# FORGE R19 — live GitHub main-protection readback (non-authorizing)

Base: `6106675d55c6faec09948587e769c3fbd8e1f105`, R18 fully source and real-original-qualified on both Linux and Windows.

## Verified administrative blocker

As observed on 2026-10-13, GitHub REST reported `main.protected=false` and a top-level empty repository ruleset list `[]`. This means passing source CI, standalone real-original archive intake and signed read-only custody tests **does not establish protected source admission or a safe autonomous cutover**. GitHub app access available to engineering supports readback, not repository-administration or independent enforcement testing. No claim that this task has protected main is justified.

## Bounded R19 implementation

- A standalone, non-authorizing `branchpolicy.Inspect` requires a caller independently pinned exact main SHA and fixed repository identity, validates the GitHub branch plus ruleset API readbacks, rejects nested duplicate/case-alias JSON metadata and excessive depth, and reports content digests and the exact protection state.
- Both an actually unprotected branch and a branch **claiming** protection return `branch_protection_qualified=false`, `cutover_authorized=false`, `original_scientific_execution_authorized=false`. A settings screenshot, an active ruleset label or `protected=true` **cannot** substitute for independent admin attestations, branch-rule applicability and verified bypass/failed-PR rejection tests.
- A bounded read-only GitHub-hosted CI observation collects real `branches/main` and `rulesets` JSON using a contents-read-only token, pins the observed source to the current GitHub workflow main SHA, then exports original API bytes plus a nonauthorizing observation as 90-day artifacts. This is **not** a branch protection setting change.
- Source tests reject branch/commit drift, duplicate protected flags, nested SHA tampering, duplicate rule identities, unrelated tag-only rules, unqualified enforcement claims, malformed/trailing or oversized JSON.

## Actual external acceptance gate (still OPEN #175)

A repository administrator must enforce an applicable main branch protection or ruleset (required fresh PR approvals/status checks, no uncontrolled pushes, no force pushes/deletions, appropriate bypass actor controls). After configuration, independently read back **rule details and applicability** and perform safe failure/bypass rejection checks. Require exact verified GitHub rule IDs and enforced action evidence, not a green diagnostic workflow. Only then can this administrative gate be marked qualified.

Physical 3-domain FSA custody (#20), immutable first-use and CKB S14 owner revocation (#83), real worker side-effect fencing and unattended two-lane research remain separate cutover blockers. No original execution, workflow-dispatch authority, KTRADE mutation or Wingless/Yggdrasil pause occurs.
