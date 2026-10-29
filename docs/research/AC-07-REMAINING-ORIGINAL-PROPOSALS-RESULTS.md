# AC-07 — Remaining original hypotheses: bounded source-free development tests

**Disposition: SOURCE-FREE DEVELOPMENT PASS; SCIENTIFIC ADMISSION = FALSE.** No hidden/original source consumption, native Wingless/Yggdrasil execution, model changes, controller/queue use, protected-main modification, or science first-use.

## Source and qualification custody

- Stacked on [AC-06 draft PR #1061](https://github.com/spoonman136668-ai/FORGE/pull/1061), exact parent `aac74498ec2be61af140b0e2602da8a73d6221e2`. AC-01 #1054, AC-02 #1055, AC-03 #1057, AC-04 #1058, AC-05 #1060 remain distinct stacked research drafts, not science/production acceptance.
- Native scientific authority remains FORGE [ITD-02 charter #857](https://github.com/spoonman136668-ai/FORGE/issues/857) and its existing FSA owner/independent-source gates. No CKB-plane research dependency or new controller.
- Candidate code `research/ac07_sourcefree/remaining.py`, source-only tests `test_remaining.py`, narrowly branch/PR-scoped Linux+Windows workflow `.github/workflows/forge-ac07-remaining-sourcefree.yml`.
- Initial source run [#40782695690](https://github.com/spoonman136668-ai/FORGE/actions/runs/40782695690) passed, then we corrected two evidence-accounting labels: compression now explicitly times **one-time encoding**, and the procedural generator's eight-byte seed is an **assumption**, not a proved minimum. Earlier run retained as development history.
- **Exact corrected-code commit:** `d63640071100dcc6e31030f0a69c07b324eeef47`. **Cross-OS passing run:** [#40782813491](https://github.com/spoonman136668-ai/FORGE/actions/runs/40782813491). Both GitHub-hosted OS jobs passed 11 AC-07 focused tests and inherited AC-06/05 source-free checks, ran 9 source-visible families x 3 fixed seeds = 27 records *per OS*, and uploaded complete JSON.
- GitHub workflow artifacts: Linux `12858350605` (ZIP SHA-256 `8a916d525f234f5817c022689d6afed0b3c2a41f4c939cc10a024c607cceda44`); Windows `12858022279` (ZIP SHA-256 `abf3a4b256de36d2f017b2c80543bdedab8a836bbefac38c6bd5f948d59cd236`). JSON SHA-256 Linux `98e507c0ecffc8b1c3dc7da95de7863102b74a9f463e8d40aeea444de34711cd`, Windows `410eff02ebdd80d00177ca9cb0f7d1678860bbe01c8101cbf793ec3ca813caaf`.
- **Independent artifact inspection:** all 27 per-seed, per-family functional result records agree across Linux and Windows after excluding platform-specific wall timings. Runtime, Python tracked bytes and I/O timings are *not* native-model efficiency claims. Source-free experiment output is not qualified independent scientific evidence.

## Honest direct coverage

Original AC-06 restricted families exercised 15 IDs:
`U07 U08 U10 U18 U19 U20 U21 U22 U23 U24 U26 U27 U28 U29 U30`.

AC-07 now covers the **15 complementary IDs**:
`U01 U02 U03 U04 U05 U06 U09 U11 U12 U13 U14 U15 U16 U17 U25`.

Thus all **30/30 original proposals have an initial restricted engineering probe or explicit physical impossibility substitute**, *not* 30 validated proposals or 30 trained architectures. U03/U06 in particular are not physically tested; they are labeled hardware-only claim boundaries with pure digital stand-ins. Six newly suggested AC-D1–D6 hypotheses remain separate (AC-05), with no scientific success declared.

## Results (source-visible, synthetic, not native learning)

| Probe | Direct IDs | Actual result and bounded negative |
| --- | --- | --- |
| Lossless compression + finite procedural seeds | U01 U09 U14 U17 | Repetitive 8192-byte data compressed to **57 bytes**, equal-length random bytes to **8203**. All decoded SHA-256 matched; one-time zlib encode and decode wall timings recorded. A tiny procedural pattern recreated structured synthetic bytes, not independently random 4096-byte arrays. No model weights, token generation or whole-life speedup measured. Direct-reference timing is intentionally **not** a matched physical memory-copy baseline. |
| Compiled constants in Python | U16 | For 100 literal integers, a serialized code object occupied **238 bytes** vs **227** for an eight-integer version; source text 406 bytes. Runtime sum was correct. Python compiler folding means this is **not** a machine instruction-cache, native weight placement or universal lower-bound measurement. |
| Fitted grammar speculation with mandatory target verification | U02 | 400 FIT symbols; 127 heldout transitions; draft correct **28–33**, wrong **94–99** across three seeds; all 127 target positions were verified. No target evaluation reduction, speculative decoding speedup or LLM accuracy proof. |
| Exact cache | U05 | In 110 requests, **67 exact hits**, 43 missed/computed entries, and exact output parity with 110 direct evaluations. Perturbed key differs. Cache records retained and memory cost not amortized; no semantic approximation. |
| Sharded gradient aggregation | U04 | Four 80-element integer gradient arrays reduced exactly; simple gather/return topology counted **1920 communication bytes** on a nominal float32-vector interpretation. No actual network transfer, LoRA training, reliability or Wi-Fi overhead measurement. |
| Ternary arithmetic and operator fusion | U11 U15 | Python integer dot and two-stage vs fused arithmetic maintain exact parity; per-variant rough wall timings retained but sensitive to interpreter overhead. **No** SIMD, C/C++, GPU, neural weight quantization accuracy or native fused kernel. |
| Out-of-core storage | U12 | Read the same 196608-byte synthetic file whole and in **24 × 8192-byte chunks**, byte-for-byte equal; OS page caching not controlled and storage device throughput unmeasured. No disk-streaming performance advantage established. |
| Fixed-size sketch + bounded grammar search | U13 U25 | Four-by-53-slot count sketch **overcounted every distinct key (602–615 across seeds)** but never undercounted this source-visible stream. A 12-program grammar found an in-class fit in five attempts and **failed after all 12** for an out-of-class rule. No unlimited exact memory or universal search. |
| Digital-only physical substitutes | U03 U06 | Software interleave recovered array order; digital dot product matched direct reference. **No software-defined HBM bandwidth or DRAM analog arithmetic was executed or demonstrated.** They are explicitly not tested physical mechanisms. |

## Scientific and performance limits

This is a development screening of restricted analogues, not the proposed full implementations. It neither establishes native intelligence nor shows that the methods improve learning/retention/unfamiliar-family transfer. Some source-visible operations are correct but dominated by trivial controls. Short Python timers, OS cache, no real network/hardware workloads, prestructured synthetic data and unpriced learning/search can invalidate any attempt to claim practical speedups.

All first-use/accepted-science statuses remain **FALSE**. No controller, queue, owner or experimental source changed. Before an actual native experiment, FORGE must independently verify an authentic action–consequence source; freeze FIT/CHECK/restart/novel families and strong fully fitted conventional baselines; charge training/compilation/caching/decompression/memory/disk/network costs; preserve contradictory, abstained and failed trials; qualify exact native source in Windows/Linux; and enforce the existing scientific authorization and final full integration regression. Nothing in this PR authorizes model integration.

## AC-08 recommended gate

**Consolidate and prioritize this exploratory portfolio before creating more candidate PRs.** Reconcile stacked-draft dependencies, cross-check 30+6 hypothesis IDs against exact source cases, compute truthful two-axis classifications (mathematically possible vs resource/learning advantage), select only experimentally competitive mechanisms for separately authorized native pilots, and leave negative/hardware-infeasible results as auditable records. No automatic admission or queue dispatch.

`AC07_RESTRICTED_ENGINEERING_COVERAGE=15_OF_15_COMPLEMENT`  
`AC06_AC07_ORIGINAL_RESTRICTED_OR_SUBSTITUTE_COVERAGE=30_OF_30`  
`AC07_PHYSICAL_PROOFS=NONE`  
`AC07_DEMONSTRATED_NATIVE_INTELLIGENCE_SUPERIORITY=NONE`  
`AC07_WINDOWS_LINUX_SOURCEFREE_TESTS=PASS`  
`AC07_NATIVE_MODEL_OR_PROTECTED_MAIN_CHANGED=FALSE`  
`AC07_SCIENTIFIC_FIRST_USE=FALSE`  
`AC07_CONTROLLER_OR_QUEUE_CHANGED=FALSE`
