# FORGE autonomy — Native unattended lane supervision

**Ownership:** This workflow belongs to the **FORGE autonomy** engineering track. The separate optimizer/enhancement track owns Dream-RSI, Shinka/Pareto, ThetaEvolve, Promptbreeder, and DGM/GenEnv. This gate cannot train or change optimizer policies.

**What is now automated:** Every six hours, and on demand, a disposable GitHub-hosted runner reads the **actual current** Wingless and Yggdrasil research-only configuration, main and active branch sources, the source-pinned research state, and each state record's associated genuine successful GitHub workflow run. It verifies the original workflow type, commit, execution result, clock order, run attempt and historical source commit, then rereads the active branch to catch races. It uses only existing short-lived GitHub Actions read credentials. There is no local desktop/ChatGPT app dependency.

**Crucial distinction:** A successful research continuation is not automatically successful science. For example, Wingless presently reports `qualified-scientific-result` while Yggdrasil reports `preregistered-blocked`, even though both latest continuation workflows succeeded. This audit reports those statuses faithfully as self-reported research state, **not independently accepted results**. It does not upgrade a blocked preregistration, infer first-use availability, select research mechanisms, or dispatch a prospective experiment.

**Operational isolation:** Each lane is independently quarantined on stale/moving source identity, missing or forged run evidence, wrong authority, unreadable origin, invalid clock or schema drift. The other lane's verified observation survives. The complete pulse fails closed whenever either lane is unverified; a normal over-24-hour delay emits a diagnostic warning **without retrying an experiment**. The result is a bounded content-addressed artifact with program, source SHA, run ID and status, not raw private research content. No status is a worker permit.

**Architecture:** FORGE is native and independent; Mind-Palace is the only optional cross-project **advisory** context route. The supervisor never reads or depends on CKB-plane, never needs a new FSA/controller or signing keys, and does not call Cloudflare or the private backup vault. No Mind-Palace credentials are requested or inferred by this workflow. Wingless and Yggdrasil remain separate scientific programs. No KTRADE coupling.

**Protection:** Read-only GitHub token, never POST/PUT/PATCH/DELETE; protected main and exact source check; hostile fixture tests of source/owner/clock/status drift, mid-read branch changes and one-lane quarantine; the FORGE repository's standard Linux/Windows PR checks before protected-main merge. Scientific first-use, original retry, accepted-result promotion, Worker start, Cloudflare writes, optimizer changes and auto-merge are all **forbidden**.

**Remaining authorization gap:** Real independently authenticated current FORGE scientific-owner/witness decision, genuinely complete two-lane consumed/active/uncertain seed/lease custody, and safe production D1 first-use/recovery/Worker permit. Native health monitoring does not resolve these. Continue safe unattended observational supervision, not another fake science-activation gate.

## F93 — Current research continuation attempt truth

A successfully recorded older repository-local continuation is historical operational
source provenance, **not proof the newest attempt is healthy**. The native
read-only observer now checks each project's bounded, exact-workflow GitHub
Actions attempt history. A newer failed, cancelled, in-progress, rerun, or
identity-drifted launcher quarantines that lane independently rather than
continuing to issue a misleading global green pulse from the previous
successful state. The other lane retains its separately verified diagnostic.

Authentic observed source for this repair: the Wingless scheduled continuation
run [38959678190](https://github.com/spoonman136668-ai/Wingless/actions/runs/38959678190)
and Yggdrasil scheduled continuation run
[38959928826](https://github.com/spoonman136668-ai/Yggdrasil/actions/runs/38959928826)
failed on 2026-10-16 after their last state-pinned successes. Both job logs
reported that the *research repositories' own* Codex-only launchers hit their
usage limit. This FORGE source change does not invoke Codex or modify those
research workflows, subscriptions, credentials, or agent routing. A later
independently verified successful research continuation can restore the lane's
operational status; it does not retroactively convert failed attempts into
scientific successes. The actual two-scheduled-observation FORGE gate and
original-science/first-use ownership remain separate and pending.
