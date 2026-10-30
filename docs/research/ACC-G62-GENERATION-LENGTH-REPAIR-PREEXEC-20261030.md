# ACC G62 — pre-execution corrective amendment for upstream speculative length overrun

**INITIAL RUN PRESERVED AS METHOD/INTERFACE FAILURE, NO LATENCY ACCEPTED.** Original [Actions #41036817072](https://github.com/spoonman136668-ai/FORGE/actions/runs/41036817072), source SHA `7ae4066029b038274a9fa8cdcb224ce91aa25dc1`. Original immutable artifact #12968477841, ZIP SHA256 `5c4676ad09d837d60dfed2ffb90c06289b2a904ee0eeb4aaaa20b754f5db8ec7`, raw `g62_result.json` SHA256 `681d84fa4cbf04650253018534c0f52f8e2eb58bbede29d0c33084ca9fcb783e`. Real CUDA sm120 GPU, actual optimized SDPA dispatch, authenticated original TinyLlama safetensors identity, **8 source tests**, isolated install and cleanup all PASS. The model benchmarking stopped during the first warmup with `RuntimeError: GENERATION_LENGTH_MISMATCH:candidate:65`: upstream Hugging Face `transformers==4.52.3` generated 65 candidate tokens for a `max_new_tokens=64` request when prompt lookup was enabled. This is an **upstream generator length overrun**, not model quality/performance evidence.

## Fixed narrow correction before amended executable / rerun

Keep unchanged: Torch/CUDA/Transformers versions, exact model/revision/weight SHA, SDPA operator proof, all six prompt workloads, 2×2 warmups, 5 alternating pairs per workload, prompt-lookup config (5 candidates, ngram max3), optimized baseline, 1.15× both structured context thresholds, >=1.00 geometric all-case ratio, peak allocated VRAM <=1.10 baseline, and exact output-token parity. **No performance data were recorded before the original method stopped.**

Repaired result policy for the known candidate overrun:
- Baseline standard greedy `model.generate` **must return exactly 64** continuation tokens.
- Candidate speculative `generate` may return **64–69** raw tokens (at most 5 additional, i.e. at most configured proposal length). It must return at least 64; any smaller/greater output is FAIL.
- **Compare exact first 64 continuation token IDs** from both methods, bitwise. Any mismatch FAIL. This does not relax model behavior in the user-visible 64-token contract.
- **Do not stop or back out timer when 64 tokens are generated**: include all wall time spent by the candidate generating/validating any extra tokens; this biases *against* speculative method and cannot artificially inflate speedup.
- Record raw count and extra candidate tokens separately for each warmup and measurement; retain original implementation metadata. No invisible truncation, no post-hoc ratio alteration.
- Retain warning if upstream disables EOS by `eos_token_id=-1`; with a positive real EOS, model might terminate early and break fixed 64-token workload. Exact original generation kwargs remain frozen, no cherry-picked prompts or early stopping.

This is an **engineering source/interface repair before any timing evidence**; does not establish a speedup by itself. First run remains BLOCKED, corrected rerun separately identified and not pooled. Original source data and science boundaries unchanged. Do not modify FORGE owner controller, protected main, accepted science, live trading, paid APIs or CKB-plane. Research PR remains draft and unmerged.