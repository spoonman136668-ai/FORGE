# FORGE R6 — keep science moving while reconciling CKB S14

This is a **non-disruptive, read-only** operational integration. FORGE does not touch CKB-plane's installed controller, original work queues, native researchers, GitHub Actions in Wingless or Yggdrasil, KTRADE, or accepted source references.

## New hosted integration

`.github/workflows/forge-ckb-s14-readonly-history.yml` runs every six hours, on explicit manual dispatch, and after relevant changes merge into FORGE main. It uses a **GitHub-hosted Ubuntu runner** rather than a CKB or Wingless/Yggdrasil self-hosted runner. Its GitHub token has only read access.

The workflow first qualifies existing `ckbhistory`, `ckbreconcile`, `ckbcustody`, and their CLI source. It runs the existing bounded `forge-ckb-s14-history` client, which makes only authenticated GET calls to the **original** CKB S14 workflow and one-use issuer artifact listing; no new first-use original is issued.

A successful observation verifies that the output:
- Has the original CKB repo and workflow identity, strictly checked run/artifact counts, and a content-addressed evidence fingerprint.
- Always has `first_use_replay_authorized=false` and `scientific_execution_activated=false`, even if GitHub lists zero previous runs.
- Is archived for audit. A missing archive, invalid response, inaccessible CKB Action history or unexpected status fails closed.

**Critically:** GitHub Actions history is not the private S09–S14 permanent CKB consumed ledger. This workflow **does not** silently treat GitHub run absence as permission to run S14 again or operate the real research controller. The separate existing `forge-ckb-s14-reconcile` already requires out-of-band authenticated private S09–S14 SHA pins and the CKB state directory. It cannot pass on an ephemeral GitHub-hosted runner merely because this public snapshot is green.

## What remains before authority transfer

Obtain and independently authenticate the private CKB original-first-use state and exact third-source wake identity, reconcile consumed S14 without replay, verify original worker receipts and source-birth provenance, and then qualify FORGE real scientific worker admission with independently isolated Wingless/Yggdrasil lanes. The existing native research continues under its current authority throughout. No migration occurs by this PR.

A permanent hosted observer is **evidence collection**, not distributed scientific authority or an automated scientific worker. If CKB GitHub history becomes unavailable, the observer may fail independently without stopping research.
