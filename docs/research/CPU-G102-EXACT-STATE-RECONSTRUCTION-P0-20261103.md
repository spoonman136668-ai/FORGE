# CPU G102 — Exact cross-prefix residual-state reconstruction (P0)

**STATUS: preregistered MODEL-FREE engineering feasibility; not novel discovery,
not original-model science, not acceptance, and not deployed.**

The G101 full-prefill exact-capture hypothesis is **RETIRED** by its own
frozen stopping rule. Its final original-GPT2 run #41743988650 established
that both SDPA and eager produced 0/10 bit-identical prefix/suffix pairs.
G102 is a new line and does **not** extract KV from a full-prompt prefill.

## New mechanism and controls

Hypothesis: instead of copying or retaining independently computed full
KV states for related prefixes, an immutable *already correct* base KV can
anchor exact XOR residual reconstructions of other independently computed
prefix KV states. Each target can then be reconstructed bit-exactly with
no model forward. This is an experimental combination of established
delta encoding and compression; novelty is **unverified**.

P0 encodes raw bit-pattern bytes of equal-length tensors. The base SHA-256
and target SHA-256 bind both identities. Bounded zlib decompression, explicit
base retention, fail-closed corruption handling, no float approximation
and memory limits are mandatory. The decoder cannot silently substitute
another base, recalculate a prefix or promote approximate values.

Frozen storage controls:
- Uncompressed independent target bytes.
- Independently zlib-compressed targets at identical zlib level.
- Proposed base + compressed cross-prefix XOR residuals.

A state-reconstruction win can only be claimed if **base-inclusive**
residual bytes are strictly below *both* controls and the recovered
target matches bit-for-bit. The codec by itself does not measure
tensor layout, inference speed, decode CPU, RSS, transient peaks,
cache ownership or contention.

## Next gated experiment

1. Run model-free negative controls and qualification on both OSes.
2. Freeze a separate *development-only* original GPT-2 sample and
   per-layer KV extraction. Use same-shape cross-prefix families and
   compare against unrelated/independent bases. Respect development
   rank custody, source SHA, paired resource accounting and original
   model identity. No protected cohort.
3. Obtain bit-exact reconstruction, realistic resident/transient memory,
   all-in decode wall and CPU measurements. A codec that saves storage
   but costs more end-to-end inference is **NO_GO**.
4. Only after an exact-head mandatory Linux/Windows regression may an
   original-model diagnostic execute via a qualified existing workflow.
   Preserve no-cache, exact-prefix KV reuse and independent compression
   as strong controls. No protected first-use or production acceptance.

This P0 is a **falsifiable reconnaissance** experiment, not a claim
that G102 is fundamentally new, faster, or better than mature cache
deduplication. Retire if there is no significant storage advantage
after paying for the base and reconstruction.
