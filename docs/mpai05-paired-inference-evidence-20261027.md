# MP-AI05 — paired external-model inference evidence

Status: **integration PASS; scientific benefit NOT ESTABLISHED**.

Source: [FORGE Actions run 40465422886](https://github.com/spoonman136668-ai/FORGE/actions/runs/40465422886), workflow `.github/workflows/mpai05-paired-local-inference.yml`, commit `6137e60959ee38160860c79b4177645a5d1af475`.

Read-only Mind-Palace source pinned to `7ad7230a82e3c748aa5336b7288ad2b45d42630c`. Retrieval provenance: PASS. Holdout access: 0. External third-party local tiny GGUF model used; **not Wingless or Yggdrasil**. Inference temperature 0, maximum output 48 tokens, context size 2048.

| Arm | Nonempty inference | Prompt tokens | Completion tokens | Reported seconds | Output SHA-256 |
|---|---|---:|---:|---:|---|
| Baseline | true | 67 | 48 | 0.020 | `6ab973e903ce0680ee8254b17903e50f4bce1e37f8fc79f47c65b044e2c9a3ea` |
| With retrieval | true | 1295 | 48 | 0.148 | `3696ec9134ee94f5f550dcfd263848a514c88e7ab61aff95302ebe35940248ce` |

Interpretation: both calls executed and produced different output hashes. The experiment demonstrates source-backed context injection and real, free local model inference. It **does not** demonstrate accuracy, answer usefulness, retention, generalization, or net benefit. Relative latency and token costs are observational only, not an apples-to-apples efficiency estimate because the prompt lengths differ. Generated answers were not scored; output hashes alone do not indicate quality. The tiny model is not adequate as the primary scientific quality judge.

Next scientific test must use a meaningfully capable external model, fixed blind scoring rubric, several source-grounded questions with withheld expected answers, matched inference settings, and report correct/incorrect/unsupported responses plus token and latency costs. Preserve scientific holdouts and do not transform integration PASS into benefit PASS.
