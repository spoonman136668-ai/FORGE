# F139 G35 — Original provider provenance, read-only V2 adapter

G34 PR #947 proved actual hosted artifact upload using synthetic ZIPs;
these are NOT original-owner signed development results. G34 qualified
the real upload transport, not unattended native dispatch.

G35 adds a future V2-only original-owner GitHub API reader:
- GET authentic original run from existing F139 GitHub client (not issue data)
- freeze exact workflow ID, original workflow path, main source and ticket,
  completed attempt 1, authorized event source, original repository ID
- require one distinct native-authorize-v2 success, exactly one V2 worker
  per OS and exactly one matching V2 artifact per OS
- freeze authentic artifact ID, head SHA, repository/run metadata and outer
  GitHub-provided digest; download the actual GitHub outer artifact ZIP,
  require precisely one G33 canonical inner V2 ZIP, and hash both
- cross-check both inner V2 receipts with immutable G14 signed-admission
  validator, preserve negatives and reject job/outcome contradictions
- return original-owner-readable bounded raw ZIP proofs for G32's existing
  ledger and version-bound signed V2 permit reader.

This is SOURCE ONLY. The current live F139 workflow has native-authorize,
native-execute V1: it is intentionally incompatible with G35's future
native-authorize-v2 / native-execute-v2 requirements. No live tickets will
pass unless an independently authorized guarded source migration installs
the distinct V2 authorization path. G35 neither changes original controller
source nor creates tasks/issue numbers. It does not write terminal custody.

Original single owner mutex, latest original SQLite event, signed G31 V2
permit and protected original source must be separately verified by the
caller. The existing provider client is authenticated via the system gh
credentials only when executed on the original authorized owner. A mocked
GitHub API transcript in unit tests does not prove real original custody.

Following gate: implement independently qualified V2-only signed
native-authorize-v2/execute-v2 job with no owner key in candidate code,
then link G35 original-provider check and G32 owner-ledger admission
through an original-owner-safe terminal writer. Preserve G1/G3/#907
historical negatives, no paid API, no science first-use, and one existing
F139 controller.
