# ACC G69 — preregistration of first-decoder-attention boundary isolation

**Frozen before G69 executable, unit test, workflow, GPU run. Research DRAFT; no promotion.** Genuine RTX GPU ACC bottleneck track only; CPU GPT-2 serving is independent.

## Custody

Original G68 [draft PR #1279](https://github.com/spoonman136668-ai/FORGE/pull/1279) completed source-push run 41087833006 at immutable code SHA c6427c4f5ca479249c632a55c0d8f38ffa65dec9. Original artifact ID 12993485280, archive SHA256 2673378e907a30aa5cb0fd2d1108b099ebbbfa40ef7ced70c6320399070323a6, original G68 JSON SHA256 90903d667c280a0d4dd82f9683d9bfb124679440a9eacbe73211bdf25662ee0c. G68 executable blob 541cc88752649b2bc6ffd63cbe684c4f84cccc25; original final adjudication blob c01294dcc014f683fc9390f1df189d157df3cf9d; G69 branch rooted at final G68 commit 31845303a570d822d130772325aadc815467fb67. G68 12/12 source tests, 18/18 stage traces, and original FP16/FP32 patterns PASS. Original G63 real-corpus exact-token generalization FAIL and G67 FP32-output-head NO_GO_ENGINEERING remain unchanged.

G68 result: FP16 cached-one-token versus cached-48-chunk last-token final-norm hidden L2 0.0900532454252243; FP32 analogous L2 4.493972664931789e-05. First observed bitwise difference was the complete output of decoder layer_00. No root kernel/operator identified. **G69 aims only to locate the difference within layer 0**, not patch model weights or infer novel acceleration.

Frozen originals unchanged: TinyLlama/TinyLlama-1.1B-Chat-v1.0 revision c13e4efb205d7a8e5d13c088aa10a9dabac9b96a, safetensors SHA256 6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933, 2,200,119,864 bytes; WikiText-2 TEST original revision acc295dc7b90714f1bf47f06004fc19a7fe235c4, SHA256 d790b833ef8cf03a90db7bf1271b7520b83c45ce07ba3c1a9699df81e239eca0; original prompt 1536-token SHA256 19a85c78f14d5470d79d51c83a25d69a9b54953eb0024d223e82e34376529c59. Force exactly original 48 shared FP16 tokens, reproduce original full FP16 baseline SHA 50a1ab137948f57c8c4f06e92ca3900770b0abd01b0e0a531df560315f746d88 and candidate SHA d4e72f3fbdf4b267bf167cce321fd61d4066423ab088ae406f8d20bccf49d01e.

## Preregistered instrumentation

Compare the ORIGINAL unmodified FP16 and full FP32 optimized SDPA pretrained Llama models, in that fixed order. On each model, for three repeats execute (1) cached one-token incremental after same 1536-token prefill; (2) cached 48-token chunk after same prefill; (3) a single full no-cache 1584-token forward. Same frozen token IDs, consistent attention masks, no sampling. Exactly 18 original RTX traces. Capture the **last-token output of the final forward only**, never hidden values from prefill or earlier incremental calls. Capture twelve ordered layer-zero sites:

1. layer0_input (pre-forward input)
2. input_layernorm (output)
3. q_proj (output before RoPE)
4. k_proj (output before RoPE)
5. v_proj (output before SDPA)
6. attention_pre_o_proj (input to layer0 attention.o_proj, after SDPA)
7. attention_output (output of layer0 attention.o_proj)
8. post_attention_layernorm (output)
9. mlp_gate (output)
10. mlp_up (output)
11. mlp_down (output)
12. layer0_output (complete decoder layer output)

Each stage must fire exactly once for each last call. Compare per-stage final-token FP32-converted vector equality, L2, relative L2 and max absolute deviation between cached-one-token and cached-chunk, and cached-one-token and full-no-cache, within each dtype and each of three repeats. No hidden vectors, raw prompts, corpus or weights uploaded; numerical metrics only. The **first bitwise differing observed site** is a descriptive operator-boundary clue, not an inferred root-cause. For example, matching q/k/v projections but divergent pre-o-projection is *consistent with* differences in attention/RoPE/masking operations between projections and o_proj; it does not prove an SDPA kernel defect. Confirm model uses actual profiled SDPA operator and GPU CUDA matmul.

Record true argmax, exact tie count and original token margin after full model computation. Require G66/G68 exact original FP16/FP32 argmax/tie patterns across all repetitions: FP16 cached 7866 tied 2, chunk/full 29871 unique; FP32 all 29871 unique. Block if source, runtime, model, prompt, generation hashes, hooks, finiteness, observation count or repeated values drift.

## Results and hard boundaries

Only possible positive classification is COMPLETE_LAYER0_BOUNDARY_DIAGNOSTIC; missing/invalid evidence BLOCKED_OR_SOURCE_DRIFT. There is **NO** speedup acceptance, no scientific quality/transfer claim, no operator/driver causal proof, no partial fix promotion; keep G63 FAIL, G67 NO_GO, G68 diagnostic-only and acceptance NOT_GRANTED. Do not modify CUDA kernel, attention implementation, tie behavior, inference configuration or any model parameters. One existing Windows isolated self-hosted RTX 5070 Ti runner with labels [self-hosted, Windows, forge-codex-isolated], torch==2.8.0+cu128, CUDA 12.8, transformers==4.52.3, huggingface_hub==0.30.2, safetensors==0.5.3, tokenizers==0.21.1; 30-minute cap, disposable under RUNNER_TEMP, always cleanup, 30-day original numerical artifact. No CKB-plane, no new controller, no protected main or owner F139, no Wingless/Yggdrasil or production modification, no paid API. Draft unmerged research PR; verified evidence only.
