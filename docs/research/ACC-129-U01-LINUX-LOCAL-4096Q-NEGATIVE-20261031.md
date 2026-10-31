# ACC-129 — U01 4,096-query Linux local frozen-cohort execution (negative resource screen)

**Evidence class: EXACT-SOURCE LOCAL LINUX ONLY; NO ORIGINAL GITHUB CI / SCIENCE ACCEPTANCE.**

- Original PR: #1238, base `research/acc34-acceleration-36-stage2-go-delta-20261029`, evaluated head `0eac6de14b5ec641a9366896a030ff77ab4f441e` (before committing this document).
- Preregistration: `docs/research/ACC-61-U01-JIT-DECOMPRESSION-PREREG.md`, Git blob `19bfe750f02bdf2a396351dbc6a11c17acb74a75` (unmodified); original AC08 identity blob `5126c860771fb024ccfc14c3f7ee8925edf29787`.
- Exact-source local mirror: all 9 `research/acc61_u01` Go source/test file blobs and `go.mod` independently verified against GitHub using `git hash-object`. **Not a full FORGE repository checkout.**
- Environment: isolated Linux/amd64, Go 1.23.2; newly built `u01worker` SHA256 `972ee017e1dc928822a3aced2f34b3c6ea6795edf2b74a3cc8a3c7dd0466c577`, `u01runner` SHA256 `65ed57d4543870071d8a68a37d3b72142fbb4441d04d5603da24297ae9724a2b`.
- Commands: `go test -count=1 ./research/acc61_u01/...` **PASS**; `go vet ./research/acc61_u01/...` **PASS**; source build both tools **PASS**; `./u01runner -worker-bin "$PWD/u01worker" -queries 4096 -out acc129-full-linux-4096q.json` **exit 0**.
- Raw local receipt SHA256 `508b11ed4129d421b3d4ebd20f07cc00b3997c010d3511c5059b75f454c4de5c` (original 60-child JSON, ~62 KiB); this digest is recorded for custody. The raw receipt remains a **local file** and is *not* uploaded to this PR. Do **not** pretend it is a GitHub artifact.
- Execution: 4 frozen sizes (64/128/256/512) × 5 paired seeds (161101/103/107/109/111) × DENSE/RLE_PREDECODE/RLE_STREAM = **60 actual independent Linux child processes**, each with **4,096 inference input vectors**, 20 distinct source cases. Runner independently computed scalar signed-int64 reference output digests. All source-weight, full input, full output digests matched across all three arms per case; `all_exact_output_hashes_matched=true`.
- Receipt's explicit flags: `full_frozen_60=true`; `parent_generation_cpu_peak_rss_qualified=false`; `predecode_fit_cost_qualified=false`; `independent_science_witness=false`; `scientific_acceptance=NOT_GRANTED`; `decision=RESOURCE_AND_SCIENCE_WITNESS_UNVERIFIED`.

## Local measured per-size medians

Each reported CPU is the process's OS user+system CPU counter; peak RSS is Linux `getrusage(RUSAGE_SELF)` high-water RSS. D/P/S = dense / predecoded RLE / streaming RLE. Each size is the median of five paired seeds. The CPU ratio is median streaming CPU divided by the **smaller** of median D or median P CPU for that size, not a best single sample.

| N | CPU D/P/S, ms | Peak RSS D/P/S, KiB | Representation D/P/S, bytes | Streaming CPU / fastest control | Streaming RSS / DENSE |
|---:|---|---|---|---:|---:|
| 64 | 25.4 / 26.6 / 16.1 | 6368 / 6368 / 6368 | 4096 / 4096 / 1280 | 0.634 | 1.000 |
| 128 | 85.8 / 87.5 / 44.2 | 7264 / 7264 / 7264 | 16384 / 16384 / 5045 | 0.515 | 1.000 |
| 256 | 314.8 / 328.9 / 143.1 | 8188 / 8316 / 8444 | 65536 / 65536 / 20480 | 0.455 | 1.031 |
| 512 | 1135.2 / 1204.8 / 446.0 | 8444 / 8444 / 8444 | 262144 / 262144 / 81920 | 0.393 | 1.000 |

These are **local, single-session, nonindependently qualified timings**. They show conditional source-only compression and CPU speed on this structured workload but **not** lower peak process RSS. Different kernel implementations (streaming uses per-vector prefix sums) and incomplete parent setup/fit accounting prohibit a general equivalent-operator comparison.

## Exact per-case local counters

Each row has 4,096 complete, equal-input query results for all three arms; output SHA fingerprints are truncated here for human review, so **this table is not a full raw-prediction archive**. CPU is user+system time, ms; RSS is peak physical RSS, KiB.

| N | Seed | CPU D/P/S (ms) | RSS D/P/S (KiB) | Input SHA prefix | Output SHA prefix |
|---:|---:|---|---|---|---|
| 64 | 161101 | 24.3/26.2/16.1 | 5728/6368/6368 | ef11ce65bd9d | c1eb5e635c17 |
| 64 | 161103 | 25.4/28.6/16.8 | 6368/6368/6700 | bdbaae7af9a0 | 704b683198ba |
| 64 | 161107 | 27.2/30.9/16.9 | 6368/6368/6368 | 2765a47d3728 | 49265a8ed028 |
| 64 | 161109 | 25.4/25.7/15.5 | 6368/6368/6368 | fcb9e60df0c4 | bd2da12ec413 |
| 64 | 161111 | 26.1/26.6/15.0 | 6368/6368/6444 | 165f8540fd65 | b6ced842ffc6 |
| 128 | 161101 | 85.8/87.6/39.1 | 6700/6624/6624 | f40a746b3aeb | 06d1609798bc |
| 128 | 161103 | 87.8/83.4/39.0 | 6880/6880/6956 | 67ffebd00c39 | 22425b7e03b1 |
| 128 | 161107 | 83.4/91.2/44.7 | 7264/7264/7264 | fb54f82823fa | 2c2e969f6587 |
| 128 | 161109 | 88.8/87.5/44.2 | 7264/7264/7264 | 6f4fdd584898 | b4c82a353be2 |
| 128 | 161111 | 82.4/86.4/45.8 | 7264/7264/7264 | 89e02f82c21d | 3f4774913c0e |
| 256 | 161101 | 315.4/345.3/141.4 | 7884/7884/7884 | 393757c6ba96 | bcfab0b162af |
| 256 | 161103 | 291.0/328.9/144.2 | 7884/7884/7884 | e5ef92b82efc | 88431020f61d |
| 256 | 161107 | 314.8/345.7/143.1 | 8188/8316/8444 | fac093175b42 | 3a316e0d7016 |
| 256 | 161109 | 311.4/328.2/153.7 | 8444/8444/8444 | 14820e7f9417 | 9408d02805c7 |
| 256 | 161111 | 323.4/318.6/139.4 | 8444/8444/8444 | f2502592edaa | 487a43850fdd |
| 512 | 161101 | 1212.6/1229.9/450.3 | 8444/8444/8444 | 4133d56f6e18 | 5a215df07d9d |
| 512 | 161103 | 1135.2/1184.9/451.9 | 8444/8444/8444 | 801930e2ad40 | 6aa7f4e6399f |
| 512 | 161107 | 1181.1/1282.1/446.0 | 8444/8444/8444 | d01fd92672de | e069535b1fe6 |
| 512 | 161109 | 1126.5/1147.6/427.5 | 8444/8444/8444 | d580b14089a3 | 5c699d58900c |
| 512 | 161111 | 1093.4/1204.8/439.1 | 8476/8476/8476 | 076d8accf1e4 | 3e5823a61cb7 |

## Frozen decision boundary

Preregistered U01 all-conjunctive acceptance requires 100% exact output equality, >=50% reduction of measured live non-code weight representation, OS peak RSS <=0.80× DENSE, and median full-process CPU <=1.10× fastest conventional, **on all four sizes and both operating systems**, with complete accounting.

- Exact output parity: **PASS (local Linux)**.
- Reduced *live weight representation bytes*: **PASS (local Linux), about 69%**; this is not whole-process memory.
- CPU per child: **conditional local improvement**; whole-life predecode, input preparation and parent CPU not qualified.
- Peak resident memory <=0.80×: **FAIL (local Linux)** at **all four sizes**. That alone prevents meeting this frozen conjunctive criterion without changing the workload, sources, or thresholds.
- Windows execution, full FORGE regression, independent witness, complete parent CPU/RSS, complete fit/input cost and actual pretrained-model relevance: **UNVERIFIED**.

**Disposition:** `EXACT_SOURCE_LOCAL_LINUX_60x4096_PASS / FROZEN_RSS_GATE_FAIL_LOCAL / ORIGINAL_WINDOWS_AND_FINAL_REGRESSION_UNVERIFIED / SCIENTIFIC_ACCEPTANCE_NOT_GRANTED`. Do not spend further runs as if the local finding were a qualified cross-platform science result. Do not retune the frozen protocol or claim a general LLM speed/memory benefit. Preserve this bounded negative screening result while original owner/runner qualification remains separately gated. No protected-main, FORGE controller, scientific promotion or native Wingless/Yggdrasil change.
