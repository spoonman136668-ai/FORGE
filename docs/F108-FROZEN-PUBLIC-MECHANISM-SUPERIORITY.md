# F108 — falsifiable generated-mechanism superiority gate (public development)

## Preimplementation freeze

The complete F108 public-development seed allocations, comparison metrics, resource-parity requirement and scientific-denial flags were committed **before F108 code or diagnostic runs** at `2d907b396a436e90a2cd870f8821609a670d8143`.

F108 descends from the exact F107 branch head `51e6dcd98692c68b3cd318f8956082209022e20b`. Preserve F99–F107 draft ancestry. The F107 ASTs are **not reselected** using F108 outcomes: Wingless `query_attention / top_two_contrast / hard_margin`, Yggdrasil `slot_keyed / max / learned_sigmoid`.

## Scientific question

F107 automatically generated 33 structural variants. Its winners scored 48/48 on public diagnostics, but so did the unchanged parent. F108 therefore asks the harder falsifiable question: **can a previously selected alternative outperform its original parent on newly seeded, substantially harder development cases, with equal resource cost, while preserving the old learning budget?**

48 new Wingless paired cases from seeds 65300–65347 have the same four depth tags and queried sign-label semantics, but drastically reduced queried signal strength (0.05, 0.1, 0.2 rather than ±1) and larger, conflicting distractors (0.5, 1, 2). F104's original one-read query selector and F107's prior two-read contrast receive the same examples, their previously trained parameters and a controlled continuous-value readout. The selected program costs **two observations**, parent costs **one**; this **fails equal-resource proof by design**, and any accuracy gain must be labeled *not resource matched* (F108 will not falsely promote it).

48 new Yggdrasil pairs from seeds 65400–65447 challenge the unchanged learned variable-slot graph with connected distractors and variable reuse. Compare the generated maximum-message merge with the parent's additive merge at the same 18-unit encoded edge/state cost, using the identical learned weights and full paired controls.

The diagnostic data were frozen before any outcome. The evaluation contains **no new model fitting** and **no F108 trial-driven selection**: models receive their original F103/F104 100-step public training only. The coded oracle is a separate truth-control, never in an inference program. A correct pair requires both yes-positive and no-negative predictions.

## Locked result criteria

An improvement claim on a *public-development screen only* requires all: at least +6/48 absolute correct pairs over unchanged parent, at least six more candidate-only wins than parent-only wins on the exact same cases, worst family ≥0.60, and no higher computational cost. All 48 per-pair outcomes, blind baseline, cost and negative false-positive rates are archived. If any criterion fails, record `NO_DEMONSTRATED_GAIN_RETAIN_NEGATIVE` without changing a threshold, adjusting the program or re-running a different held-out seed block.

The current run's genuine F107 JSON and SHA256 receipt must match the same GitHub source SHA and the two preregistered selected AST fingerprints; report/authority tampering quarantines. An unfavorable mechanism score is a legitimate scientific-development outcome and **does not fail GitHub CI**.

## Limits

This is a publicly specified synthetic stress test under frozen-source custody, not a sealed independent experiment, accepted Wingless/Yggdrasil science, GPT/AGI progress proof or autonomous scientific promotion. Even if the gain threshold were met, protected scientific first-use, independent acceptance and real cutover remain prohibited.

Existing Linux/Windows hosted integration only; no Codex, paid inference, Work, CKB-plane, Cloudflare, scheduler/controller addition, native scientific dispatch, accepted-ref writes or code changes in Wingless/Yggdrasil. Keep F108 in draft pending cross-platform qualification and literal exact-head ancestry checks.
