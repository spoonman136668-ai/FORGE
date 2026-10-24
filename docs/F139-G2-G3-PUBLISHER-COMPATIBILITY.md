# FORGE F139 G2 → G3 publisher compatibility

This change extends the **existing, inactive, single-owner G2 publisher**
with an explicit G3 recipe selector. The default remains the original G1
recipe so older callers and tests retain their behavior. G3 generation is
a distinct local-action evidence threshold (3 genuine observations per arm),
not G1 cross-context outcome pooling.

## Boundaries
- G3 requires retention of the previous G1 mechanism identity in the
  original-owner supplied consumed-mechanism history. Clearing historical
  negatives to manufacture fresh work fails closed.
- G3 and G1 use the same native commit/blob authentication, immutable parent,
  owner draft-PR check, source SHA policy #807, no-replay behavior and dual-OS
  worker eligibility. No new controller, scheduler, queue or API credential.
- The existing publisher remains **inert**. It does not acquire credentials,
  run from ordinary GitHub Actions or attach itself to `run_once`.
- Original-owner SID, mutex/lease, full unchanged SQLite history and write
  custody must be proved independently before a future production invocation.
  The prior read-only G3 dedup observation does not authorize an actual PR write.
- This PR changes no Yggdrasil source and performs no G2 publish/worker dispatch.
- The source-only G3 hypothesis may be a **negative** and is not independently
  scientific-first-use qualified. No acceptance/promotion is permitted.
