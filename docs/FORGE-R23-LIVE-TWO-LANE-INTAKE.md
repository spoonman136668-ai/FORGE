# FORGE R23 — independently observed live two-lane intake (non-authorizing)

This gate checks genuine external Wingless and Yggdrasil GitHub Actions run metadata during a proposed change, rather than accepting only synthetic fixtures or waiting for the hourly observation. Both raw GitHub API snapshots and the classification report are SHA256-addressed and archived together. The observer explicitly reports that **zero FORGE scientific originals were executed and zero scientific results accepted**.

PR-side intake verifies that the read-only observer still works against both live repositories *before* its source change reaches protected main. It does **not** infer scientific success from a green workflow, grant original first-use, dispatch a worker, or replace CKB-plane as scientific owner.

Acceptance requires the R23 source head to pass (1) full Linux/Windows tests/race/vet/build, (2) the newly triggered live observation reading both real repositories and persisting its SHA256 manifest, and (3) independent check of both exact workflows before protected-main merge. Postmerge full Linux/Windows acceptance follows. The hourly read-only schedule remains unchanged.

External FSA is deferred by user directive; it remains out of scope, not qualified. Real once-only dispatch, start/recovery leases, continued original generation, and old-controller succession remain future engineering gates. No paid API or Cloudflare provisioning.
