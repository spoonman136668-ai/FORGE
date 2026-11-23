# FORGE / Hybrid: cumulative-training continuity (inactive review R1)

**Scope:** exact-source, deterministic, **read-only** evidence intake. FORGE does not own, train, checkpoint, merge, accept, resume, allocate GPUs for, or dispatch the private `spoonman136668-ai/TTT-Hybrid-Lab` learner. This contract does not create another controller. The Hybrid's project-owned training path remains separate from Wingless and Yggdrasil.

## Operational requirement

**Do not silently restart prior learning.** Each new training candidate must descend from a previously verified immutable checkpoint. Persist and restore, together: (1) learned model parameters and buffers; (2) optimizer moments/step state; (3) scheduler state when used; (4) native recurrent state, fast-memory weights, and bounded history; (5) Python, Torch CPU and applicable CUDA/NumPy RNG states; (6) exact sampler/dataloader cursor, cumulative examples and training steps; (7) source, interface, architecture, protocol, dataset/splits, harness and environment fingerprints; and (8) parent checkpoint and content hashes. No 'fresh initialization' fallback counts as continuation.

**Immutable lineage:** root must be an explicit zero-training checkpoint, then every candidate links to the immediate parent, strictly advances training steps and examples, and preserves exact architectural/protocol/environment identity. An incompatible architecture, source or dataset change is a separately authorized migration **with an independently qualified transfer test**, not a normal resume. Never overwrite a retained ancestor or move an accepted pointer during candidate creation. Crash recovery must select a specifically verified immutable tip; ambiguous, lost, orphaned or tampered tips block continuation. Do not replay an uncertain-effect original/seed.

**Qualification before accepting a candidate:** verify project-owner provenance and actual checkpoint blobs independently (FORGE's metadata is insufficient); perform a cold restore and deterministic replay; verify complete optimizer/scheduler/RNG/cursor restoration; preserve prior learned-task performance and counterfactual isolation; test interference, action-consequence learning, unfamiliar transfer, resources and full-process cost against matched trained conventional controls; honor frozen seeds/splits/thresholds and one-time scientific first-use; run exact-SHA full required Windows/WSL regressions and separately authorized scientific acceptance. Failed candidates remain immutable negatives; the previous qualified accepted checkpoint remains intact. No false promise of monotonic capability improvement: **never promote a regression** is the enforceable requirement.

## Implemented in this R1

`hybridcontinuity.Inspect` rejects missing ancestry, duplicate/replayed artifacts, missing state categories, non-advancing steps/cursors, incompatible identities, or dishonest top-level promotions. It returns `REVIEW_ONLY_UNAUTHENTICATED_NO_TRAINING_OR_PROMOTION` and explicitly **does not authenticate the private checkpoint bytes**. It does not connect to the existing inactive integration runtime; no producer/consumer or automatic invocation is enabled. It is an independent, bounded check for a future source-authenticated owner receipt.

The parallel Hybrid-side `native_training_checkpoint.py` proposal provides immutable local candidate publication, exact parent/source fingerprinting, full resumable state capture, cold restore and negative engineering tests. This proposal itself is not a continuously running trainer, an accepted checkpoint, or proof of cumulative scientific improvement.

## Outstanding activation gates

Project-owned source/checkpoint authentication; exact-source cross-platform final regression on both projects; durable multi-host checkpoint storage + crash-consistent owner's accepted pointer; completed training-loop and sampler integration; qualified native GPU/compilation and resource arbitration; explicit original-first-use custody; externally witnessed cold replay/retention and acceptance thresholds; independently authorized project activation. Research already underway must remain uninterrupted while these gates are developed.
