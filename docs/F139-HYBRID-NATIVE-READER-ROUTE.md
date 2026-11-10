# Hybrid native reader route repair

Baseline: deployed V40 source 2c7caad5a4502d4b874a11d57207a35cf033eb08,
tree 406c97f14e846591570854eaf485e2139dbf9adc. Original handoff run
42784117977 PASS; source/activation ledger events1463/1464. Policy807 still
permits Wingless/Yggdrasil only; Hybrid schema admission remains pending.

The native candidate contract and feeder recognize TTT-Hybrid, but the REAL
GitHub.native_repo_get transport rejects its exact repository prefix. The
feeder tests' FakeProvider bypassed that transport boundary. A regression
through the real GitHub object reproduced F139_NATIVE_FEED_ROUTE_INVALID
before any provider call. Add only repos/spoonman136668-ai/TTT-Hybrid-Lab/
to the existing read-only allowlist. No generic owner prefix, new transport,
credential, controller, queue, worker, source transition or policy change.

The regression covers real native GET argument construction for branch,
commit/tree, PR, source and bounded compare reads, and rejects other owners,
lookalike repositories, unrelated projects, absolute URLs, traversal and
mutation arguments before the provider is called. Existing two-lane opt-out,
source-bound admission, signed worker and migration controls remain intact.

ENGINEERING qualification of this repair does not prove live integration.
The Hybrid repository is private. Connected-app permission does not establish
the FORGE worker token's private read/checkout access. That must be tested
using the SAME scoped hosted worker identity before any Hybrid signed issue,
queue admission, owner schema/policy migration or scientific first-use.
The deployed owner remains pinned to its qualified source until a separately
qualified/authorized source handoff; do not merge this fix ahead of that
coordinated handoff merely because CI passed. Preserve active research.

## Authentic worker-reader qualification

One-shot read-only operation run42786545427, job129729072814, used the SAME
FORGE hosted worker identity (github.token, contents:read), no substitute
credential. Target private main6df5aa3f0dd5a99867098166aeed5b0fc70b4ec2,
tree1159dc3e20a9c457e17d74805edee942985efa07, independently observed through
the authorized connected repository reader. The FORGE token returned HTTP404
on its first fixed repository metadata GET. Result BLOCKED_PRIVATE_READER;
repository_visible=false, exact_commit_tree_readable=false. No checkout,
private source download, owner mutation, dispatch, model call or new credential.
Probe operation branch is finite, GET-only and MUST NOT be merged into main.

This is a failed capability qualification despite successful execution of the
diagnostic workflow. Changing the owner schema or policy cannot fix worker
reader scope. Preserve the existing two-lane owner; do not issue a knowingly
unserviceable signed Hybrid task. No permission setting or credential was
changed. The repair PR also had an initial isolation failure caused by an
unnecessary forbidden-project literal in a negative fixture. Remove that
fixture; the unchanged isolation guard and other foreign/unrelated repository
negative controls remain mandatory. Repeat full regression on final source.
