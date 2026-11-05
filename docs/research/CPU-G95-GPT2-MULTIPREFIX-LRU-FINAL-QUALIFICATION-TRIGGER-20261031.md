# G95 final immutable artifact and capacity adjudication — 2026-10-31

The corrected original-model workflow #41228835448 completed successfully. Source admission and benchmark job both succeeded. Original artifact #13052847529 was recovered and inspected.

Artifact ZIP SHA-256: `85de7577fb9dfb8239d62cef6fcddc3be7248ccc72b966a1da5436aa8dec7871`.
Original result JSON SHA-256: `f633bcc821b5c730c65331b8519b6d5ccb3fd2bb0d85f92f29039e736bf429e2`.
Original environment SHA-256: `e0b96f7968047dd1ebbe81531803f8b37df90f7533af833de9f78c5016781c85`.

Machine-readable receipt: `CPU-G95-GPT2-MULTIPREFIX-LRU-ARTIFACT-RECEIPT-20261031.json`; environment copy: `CPU-G95-GPT2-MULTIPREFIX-LRU-ENVIRONMENT-20261031.txt`. The exact original GitHub Actions artifact remains the source archive and is linked from the receipt.

**Frozen result: engineering PASS, correctness PASS, MULTIPREFIX_LRU_NO_GO.**
- Capacity 1: 0% hit rate, 188 evictions, throughput 0.883×, CPU 1.130×, p95 1.127×, worst paired request 0.852×.
- Capacity 2: 0% hit rate, 184 evictions, throughput 0.885×, CPU 1.129×, p95 1.117×, worst paired request 0.764×.
- Capacity 4: 91.67% hit rate, 176 hits, 16 cold misses, zero evictions, throughput 1.765×, CPU 0.567×, p95 0.993×, RSS 1.091×, resident KV 86,114,304 bytes. But worst paired request speedup was 0.8615×, below the frozen 0.90× guardrail. It therefore does **not** qualify.

All 768 responses and 6,144 generated tokens were verified exact. Cache capacity bounds, cache-copy isolation and resident snapshot checks passed. The complete corrected CPU runtime was 2 intra-op / 1 inter-op threads with affinity [0,1,2].

No threshold is waived. The final receipt-only workflow validates exact source/artifact identities, the three-capacity adjudication, focused tests, FORGE isolation/FSA/F139 custody and Linux/Windows Go final regression. It does not rerun or reinterpret inference. Scientific acceptance remains NOT_GRANTED and promotion remains false.
