# F139-D2K-CUSTODY/C — source-only prefix transition witness

The original 23-event D2C/D2J custody is independently pinned before any source-only merge transition. `audit_d2k_custody.py` admits an optional append-only suffix of **at most three** authenticated, sequential `SOURCE_TRANSITION_ADMITTED` entries targeting only the already-merged FORGE protected-main identities (PRs #590, #587, #602).

This extends read-only verification without expanding operator authority. Every suffix event must carry the exact prior hash, the preceding source SHA, four verified historical tasks, zero new dispatches, and `scientific_first_use=false`. The original sealed **23rd** event hash remains authoritative even when the local head advances. Four terminal worker run IDs and all eight external provider-digest-matched ZIPs must remain unchanged.

Successful hosted unit tests and GitHub CI do **not** establish an independently signed external custody head, isolated local runner, or running workstation source. A missing authenticated 23-event head, non-isolated host, mismatched source, synthetic owner-issued task, or failed audit is a **STOP**. No self-hosted workflow is added and no workstation command is executed by this patch.

No new scheduler/controller, science permission, accepted-ref mutation, Cloudflare hosting, CKB-plane linkage, paid inference, issue creation, or research queue modifications.
