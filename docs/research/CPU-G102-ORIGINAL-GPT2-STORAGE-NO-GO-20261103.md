# CPU G102 P1 — Original GPT-2 exact-state reconstruction NO_GO (2026-11-03)

**Authentic original-model engineering PASS; storage result `STORAGE_NO_GO_DIAGNOSTIC`.**
The pinned original GPT-2 run reconstructed four independently computed
FP32 KV states **bit-exactly**, but the base-inclusive XOR residual representation
failed its preregistered memory criterion against conventional zlib compression.
This is a genuine negative development result, not an infrastructure failure.

## Source identity and custody

- Frozen original-model experiment source:
  `1f359022f38fe680191422bec3b5ff75cf46f78e`.
- Exact-source focused dual-platform qualification:
  https://github.com/spoonman136668-ai/FORGE/actions/runs/41748018593
  (Linux **PASS**, Windows **PASS**).
- Mandatory exact-head Linux/Windows regression:
  https://github.com/spoonman136668-ai/FORGE/actions/runs/41748028235
  (Linux **PASS**, Windows **PASS**).
- Qualified one-shot original-model run:
  https://github.com/spoonman136668-ai/FORGE/actions/runs/41749647456
  (source admission **PASS**, original-model diagnostic **PASS**).
- Trigger commit `989eb59b148d6cf3d7be65207e4e26dc53e29e89`;
  temporary push trigger disabled at
  `4b7421918b23f88c96c419ab4c80deabce0bfcac`.
  Evaluation checked out the frozen source, never the trigger commit.
- Artifact `cpu-g102-original-gpt2-storage`, ID `13285038083`,
  ZIP SHA-256 `4af2e24665e2f257d20ec8b49e55a1c9c8504420c7f68fb39bf8c20ac73367e9`.
- Receipt `cpu_g102_kv_storage_result.json` SHA-256
  `cf16d75ae0902410b9157664439d2484ad2c9a023d63b5de6f3ef0e49445d5ac`.
- Original GPT-2 weights SHA-256:
  `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`.
- No protected sample was accessed: original G95 prompt family and
  deterministic one-token mutations only; no development/held-out question retrieval.

## Measured storage (decimal MB)

| Strategy | Bytes | MB |
| --- | ---: | ---: |
| Four independent raw KV states | 78,151,680 | 78.152 |
| Four independently zlib-6 compressed KV states | 72,524,820 | 72.525 |
| G102 one full base + four XOR/zlib residuals | 77,847,657 | 77.848 |

The retained base alone costs **19,537,920 bytes**. The four residual
payloads are **14,868,582**, **14,634,728**, **14,566,033**, and
**14,240,394 bytes**. Full reference cost was included exactly as
preregistered, with neither structural pointers nor decompression
buffers treated as free.

Against raw storage the proposed representation saved only **304,023
bytes (0.39%)**. Against independent zlib it increased storage by
**5,322,837 bytes (7.34%)**. Preregistered decision: G102 must use
no more than 90% of the smaller control, which it fails decisively.

All four reconstructed targets were bit-exact and SHA-256 verified.
Original model forward count: five (one base and four variants);
base prefix length: 265 tokens. Single-pass exploratory per-target
decode wall times were ~0.849–0.873 s versus independently compressed
zlib decode ~0.069–0.076 s. XOR encode times were ~1.74–1.88 s per
target; standalone zlib encode ~0.57–0.58 s. These are **not**
throughput or inference performance results; CPU RSS was sampled rather
than full transient memory instrumented.

## Disposition

**Stop this G102 base-inclusive XOR/zlib representation.** It is correct
but not storage-competitive even on favorable same-length and
single-token-variation prefixes. No additional G102 tuning or protected
first-use is justified by this test. The conventional independent
compression control performed better in this tested design.

Any next optimization must be a separate preregistered mechanism,
with explicit independent baselines, complete source/runner provenance,
transient memory and end-to-end CPU/wall accounting. Suggested direction
for a distinct hypothesis: **content-addressed structural sharing** of
exact, already computed KV blocks at stable immutable boundaries, with
copy-on-write append and a collision-resistant identity guard. Treat
existing paged KV approaches as strong conventional controls; genuine
novelty is **UNVERIFIED**. Avoid claiming success from bytes of compressed
intermediate tensors alone.

**Scientific status:** Engineering PASS; exact reconstruction PASS;
storage NO_GO; performance NOT EVALUATED; held-out NOT EXECUTED;
scientific acceptance NOT GRANTED; production promotion PROHIBITED.
