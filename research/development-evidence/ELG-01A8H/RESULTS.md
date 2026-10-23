# ELG-01A8H — joint role-factor gating and latent text segmentation

**Classification:** DEVELOPMENT-ONLY NEGATIVE. Evidence archive, not a FORGE work order, scientific first-use, accepted system qualification, deployment or model promotion.

## Tested hypothesis
Does learning how to distribute six semantic input roles across two specialized segment decoders, while marginalizing unknown text boundaries and both orders from full-sentence gold text only, improve the unseen fronted-passive combination relative to an ungated latent two-expert model?

No gold segment boundaries, gold role-to-expert assignments, or per-expert sentence targets were supplied. However, **the fixed six input roles, exactly two contiguous segment experts, marginal split loss, and an order head were predesigned structural priors**. Candidate-only entropy/balance regularization was tested by ablation.

## Corpus and protocol
- Reused synthetic controlled-English A8E/A8G corpus: 576 training, 192 development sentences; 96 development sentences combine fronting and passive voice, absent from training.
- Two fixed seeds: 13 and 29; 50 epochs each, batch 64, Adam 0.006, PyTorch CPU single-thread.
- Metric: exact full-sequence match; separately report all 96 omitted training combinations.
- Baseline: exact original A8G ungated latent two-expert model at same seeds and epochs. This is a diagnostic comparison, **not fully compute/capacity-matched architecture benchmarking**.
- Inputs/targets are neither prospectively frozen novel source data nor canonical ELG-01A7. Prior development observations already informed this architectural family.

## Results

| Arm | Seed | Exact /192 | Withheld joint /96 | Training seconds | Median inference, 192 sentences (ms) |
|---|---:|---:|---:|---:|---:|
| Factor-gated + entropy/balance | 13 | 96 | 0 | 14.964 | 7.711 |
| Factor-gated + entropy/balance | 29 | 96 | 0 | 14.400 | 4.973 |
| Factor-gated, no regularizer | 13 | 96 | 0 | 15.427 | 4.771 |
| Factor-gated, no regularizer | 29 | 96 | 0 | 18.620 | 4.022 |
| A8G ungated latent experts | 13 | 96 | 0 | 12.567 | 3.939 |
| A8G ungated latent experts | 29 | 96 | 0 | 11.607 | 3.507 |
| Deterministic zero-training renderer | — | 192 | 96 | 0 | Not formally benchmarked here |

The gating model has 43,954 parameters; ungated model has 43,942. Factor gates remained soft: mean maximum role allocation probability was 0.5515 (seed 13) and 0.5618 (seed 29), not convincing distinct factor induction. The superficially similar role partition across seeds is NOT evidence of recovered causal abstraction.

## Qualification, custody, reproducibility
- 9/9 focused checks PASS: strict corpus disjointness, omitted composition verification, string serialization, gradient path to factor logits, finite marginalized loss, generation shape, zero-regularizer ablation, default gate uncertainty, and a strict corruption-rejecting oracle.
- Full **standalone local** experiment completed for six configurations and one exact candidate checkpoint replay; seed-13 replay checkpoint hash reproduced exactly.
- **No FORGE full integration regression, independently sealed first use, matched strong plan-aware comparator, or acceptance was run.**

Source hashes (SHA-256):
- `experiment.py`: `089ef17cd1ad15b65d1fe41a2a137a89b86b5ba8832c9fcf80a0e2968936efa2`
- `a8e_reference.py`: `1afb03ba102ccc481f029835b725e53e62ee9b0f33dde25510ee780ebcbcaaa0`
- `a8g_reference.py`: `1239a90d11b0559f9e3f35438b78f7f4241f899bced2271ed837b82828cebfb5`
- `results.json`: `792bb89ba9a2b14502e35ad3d14531a64cc2a6eef1c2ad6b1f246bc964df2553`
- `run.log`: `f154f13020271595283bc50d2b12f7f753705628e5e3d2b50442c11dceca5003`
- `source-only.tar.xz` (local): `c87504a86b019980107bf8819bcef20dddd44545654c3b288ea8429a8d8c5136`

Seed-13 factored checkpoint SHA-256: `d20575df71ef5292d3ebe674887df02750ea862062e0e8944dc852c3428f8dfd`. Seed-29 factored: `42c73f5cdd4a70b4bcd77d08d8d26c35b4709636a0b6e8e74509b22c2e6f437e`.

**Availability caveat:** These are content identifiers for the fully executed local files. The local runnable archive is NOT yet included in this Git branch; source hashes without bytes cannot reproduce a result from GitHub alone.

## Disposition

**NEGATIVE / NO PROMOTION.** Learning a global soft allocation of predefined roles did not address unseen composition, and was slower than the ungated latent control. Do not tune on these repeatedly inspected development results and call the same holdout untouched. The next defensible experiment must use prospective new compositions and a plan-aware equal-information control, with a task on which a free deterministic renderer is not already perfect.

This archive document is inert advisory evidence only. It must not be parsed as a FORGE/F139 work order, used as a science-start receipt, or alter controller, FSA, accepted refs, queues, NCI-04/ITD-01 or current research work.