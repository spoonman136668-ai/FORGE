# ACC G61 — corrective source-admission amendment, committed before amended executable and rerun

**Original G61 initial experiment retained as a genuine engineering BLOCKED outcome.** GitHub Actions [run #41033592653](https://github.com/spoonman136668-ai/FORGE/actions/runs/41033592653), exact head `e664bf476be7420209de857799a7ca144314ecf0`, original artifact #12967740651 ZIP SHA256 `e24f731d218367789e1c3ae56c9a8ffb4159d5eb0b2dd9e874cbdcc989824e3d`. Successfully verified original TinyLlama 1.1B checkpoint 2,200,119,864 bytes SHA256 `6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933`, actual CUDA matmul (RTX 5070 Ti sm120, Torch 2.8.0+cu128), but failed before timing at `ATTENTION_BACKEND_NOT_REALIZED:sdpa:sdpa:LlamaAttention`. This is a **class-name assertion failure**, NOT evidence that the SDPA kernel did or did not execute, nor any performance negative. Do not misclassify or discard first attempt. Entire temporary environment removed, no system changes.

## Correction — independent of measured speed or model output

Transformers 4.48.3 on the pinned environment may expose shared `LlamaAttention` even when `model.config._attn_implementation` reports `sdpa`; class names alone do not prove actual PyTorch optimized attention dispatch. Official [Hugging Face 4.52.3 AttentionInterface](https://huggingface.co/docs/transformers/v4.52.3/attention_interface) describes selected backend dispatch through `attn_implementation` and `ALL_ATTENTION_FUNCTIONS`. **Freeze new dependency: `transformers==4.52.3`**, while leaving Torch 2.8.0+cu128, huggingface_hub 0.30.2, safetensors 0.5.3, tokenizers 0.21.1, exact TinyLlama original revision/weights, RTX GPU and all benchmark cases, warmups, five alternating repeats, output checks, and novelty/no-promotion boundary **unchanged**.

Actual backend gate now requires:
1. `model.config._attn_implementation` equals requested `eager` or `sdpa`;
2. PyTorch profiler **actually records `aten::scaled_dot_product_attention`** within one real model prefill on `cuda:0` for SDPA, and records **zero** such ops for eager;
3. Both profiler sessions must be genuine CUDA model forwards, with no model comparison timings included; if profiler unsupported or backend falls back, classify BLOCKED and do not fabricate. Class name reported as descriptive metadata only, no brittle class-name assertion.

**Predeclared study remains unchanged:** batch 1, prompt 128/512/1536, 32 greedy continuations, FP16 model, 2 warmups per backend per context, 5 alternating AB/BA pairs, exact same generated token IDs across backends, CUDA sync prefill/decode and full duration, VRAM accounting. No candidate novelty acceptance; only establish an actually optimized 1.1B SDPA GPU reference.

This amendment is an **engine/toolchain repair** made after source-admission failure and **before any timing data exists**, not a retuning of workload, performance thresholds or observed speedups. Preserve both source commits and receipts; don't pool hardware trials across different software versions. Existing G60 and G59 results unaffected. No FORGE controller/protected main/science first-use or model-training changes.
