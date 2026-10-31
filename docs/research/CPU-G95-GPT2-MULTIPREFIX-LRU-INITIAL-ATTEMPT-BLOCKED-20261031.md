# G95 initial execution attempt — configuration blocked, 2026-10-31

The first benchmark workflow attempt (#41226496573), pinned to source commit `cb4fc66ac4f644933a8560ffa2e3bce0ddadb487` and source blob `3b1396f28f13ead4ebc1489a0bbf8a83bf2121f6`, was launched after source admission passed.

A post-admission code/contract audit found that its entry point called `torch.set_num_threads(1)`, while the frozen G95 preregistration requires **intra-op threads = 2** and **inter-op threads = 1**. The benchmark job had progressed to the original-model measurement step. This configuration mismatch invalidates any measurements from that attempt against the frozen preregistration.

Disposition: `BLOCKED_ENV_CONFIGURATION`; it is not a benchmark NO-GO and is not admissible performance evidence. Preserve workflow #41226496573 and any eventual artifact as a historical invalid attempt; do not use its performance results.

Corrective source commit: `84955eb33ab60339af03216bed0e9963a24e9bc8`; corrected source blob: `d6230da03cb4946f90569d2bdd96987e7e4704fb`. The runner now sets and reads back 2 intra-op / 1 inter-op threads and records both values in the result. The focused regression test additionally asserts this contract; the workflow pins the corrected source and test blobs and checks the recorded runtime settings.

The corrected run is queued by the workflow's existing non-cancelling concurrency group behind the original attempt. Do not start a parallel or duplicate benchmark. Thresholds, cache capacities, prompts, model, dataset ranks, interleaved stream and measurement counts remain unchanged.
