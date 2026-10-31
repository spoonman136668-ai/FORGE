# G95 initial execution attempt — configuration blocked, 2026-10-31

The first benchmark workflow attempt (#41226496573), pinned to source commit `cb4fc66ac4f644933a8560ffa2e3bce0ddadb487` and source blob `3b1396f28f13ead4ebc1489a0bbf8a83bf2121f6`, was launched after source admission passed.

A post-admission code/contract audit found that its entry point called `torch.set_num_threads(1)`, while the frozen G95 preregistration requires **intra-op threads = 2** and **inter-op threads = 1**. The benchmark job had progressed to the original-model measurement step. This configuration mismatch invalidates any measurements from that attempt against the frozen preregistration.

Disposition: `BLOCKED_ENV_CONFIGURATION`; it is not a benchmark NO-GO and is not admissible performance evidence. Preserve workflow #41226496573 and any eventual artifact as a historical invalid attempt; do not use its performance results.

Corrective source commit: `84955eb33ab60339af03216bed0e9963a24e9bc8`; corrected source blob: `d6230da03cb4946f90569d2bdd96987e7e4704fb`. The runner now sets and reads back 2 intra-op / 1 inter-op threads and records both values in the result. The focused regression test additionally asserts this contract; the workflow pins the corrected source and test blobs and checks the recorded runtime settings.

The corrected run is queued by the workflow's existing non-cancelling concurrency group behind the original attempt. Do not start a parallel or duplicate benchmark. Thresholds, cache capacities, prompts, model, dataset ranks, interleaved stream and measurement counts remain unchanged.


## Subsequent invalid attempts — source-pin and syntax harness failures

Two subsequent workflow attempts were blocked before original-model measurement and are not admissible performance evidence:

- Run #41227689464 (head `1b4b6957d0245bbe6f889c103caf9b360c9af46b`) failed source admission because the workflow's runtime-stage source blob pin still referenced the earlier source version, while the branch contained the new source. No model run occurred.
- Run #41227702350 (head `0688722c659f80b25592958410e7ac158f5b1fe3`) passed source admission but the benchmark job failed before runtime installation: the runtime job still pinned source blob `3b1396f28f13ead4ebc1489a0bbf8a83bf2121f6` instead of the corrected implementation. No benchmark ran and no artifact was produced.

The latest workflow correction pins source blob `b401c86e4dff2f25eb995a47ba58884838f232eb` in the runtime job, matching the current implementation. New exact head: `c79f560b1ccdb58bf1a01564ce04c7acc47086a2`; new attempt #41228835448 is queued. These are workflow/provenance failures, not cache-performance outcomes or LRU NO-GOs.
