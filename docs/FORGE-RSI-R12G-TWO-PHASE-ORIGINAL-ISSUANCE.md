# F139 RSI R12-G — two-phase lifetime-one original-owner pre-dispatch

Protected parent main `ba2d551788071fba926ffac6d4ed8c26334ddb80`,
tree `2b6a5267cac04402ad3f481ba85e466fa044f528`.

## The observed deadlock, fixed in the candidate contract

R12-B/C require the authenticated GitHub run and job IDs **before**
issuing the original HMAC and original-ledger event. GitHub allocates those
IDs **after** `workflow_dispatch`. Therefore the legacy R12-C issue
function cannot serve as a pre-dispatch admission ticket. Do not fabricate
identifiers or force the existing workflow to admit unsigned FORGE-self work.

R12-G's distinct original event `RSI_SELF_ORIGINAL_PREISSUED` is a
source-only potential future initial issuance. It captures one authenticated
R11 reservation and its immutable candidate binding, exact protected
source/tree and OS, one deterministic job ticket and a domain-separated
HMAC digest **before** run/job IDs exist. The original source event is
SHA-chained and cold audited for historical source, single issuance,
unconsumed original R11 custody, no replay, and no science/promotion.
Its currently inactive writer requires the real original Windows owner
source, original mutex, idle owner, source continuity, operator issue #807
exactly expanded to the three-lane policy, and original signing secret.
The writer creates no workflow job or runner.

After a future separately authorized dispatch, a **read-only** provider
observation can bind newly allocated run/job IDs to the ticket, source,
run-name, repository, owner actor, job/OS and first attempt. In today's
GitHub API the workflow run response does **not** expose dispatch inputs,
so a matching run-name/job is **not** cryptographic proof of HMAC
verification. The latter must be performed by an independent credentialed
authorization job in the existing workflow, with the credential-free job
conditionally dependent on authenticated success and an original-issued
terminal receipt. None of that is enabled by R12-G.

## Isolation / work left

No owner tick, original installed release or policy issue #807 mutated.
No dispatch, signed worker admission, first-use, promotion, paid APIs,
new controller/queue/scheduler/task or scheduled tasks. Existing
Wingless/Yggdrasil and concurrently owned Hybrid PR #1637 remain
untouched; this PR does NOT edit the F139 worker workflow.

R12-C legacy post-dispatch issuance remains inert and is NOT a
pre-dispatch authorization path. A future owner-source transition,
original installed runtime and policy cutover, credentialed authorizer,
credential-free worker binding and exact one-use terminal receipt still
require independent original qualification. Passing synthetic tests
does not prove authentic original-owner issuance or scientific RSI.
