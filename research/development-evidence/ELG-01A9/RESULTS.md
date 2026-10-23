# ELG-01A9 — prospective synthetic compositional program-to-text development

**Classification: DEVELOPMENT-ONLY, non-authorizing scientific evidence; no independent scientific first use.**

This archive is inert, not a FORGE/F139 work order, CKB-plane orchestration instruction, FSA admission or experiment dispatch. It must not be used to promote models, mutate accepted refs or select scientific first-use cohorts.

## Bounded test and frozen inputs

A new synthetic operator-tree language was created instead of reusing the exhausted ELG-01A8 fixture. Input consists of binary event/operator abstract syntax trees; each leaf has subject, action and patient identifiers. Three arbitrary operator names have randomized-seeming surface word/reversal mappings inferred from complete example sentences, without gold *operator phrase segmentation*. All models receive the same 1,104 train programs and full output strings. Development has 192 four-event nested programs unseen at training time; training contains only atomic and two-event structures. Source tokens are seen individually during training. The data producer, learner and evaluator share one developer, so this is **prospective synthetic development only**, not independently born or sealed science.

Source manifest values:
- Train: 1,104, source-list SHA-256 `3f16c2a6ac226fc5a21dc286671a8ab97d86cff3db08f20e95b3d1901c4b56f6`.
- Dev: 192, source-list SHA-256 `c8c22db37859bdbb0601c99611a667a76ff5022ce393d77c8c1b1794e9b70dfb`.
- Generator seed: 20261023.
- **Strong prior:** binary AST and three-slot atomic clause order are given; neither grammar-aware method has to discover the number of children, the input parse, or open-domain syntax.

## Results (full standalone local run)

| Model | Exact /192 unseen nested trees | Training / fit | Median dev inference | Notes |
|---|---:|---:|---:|---|
| Factorized grammar learner | 192 | 0.0068 s | 0.385 ms | Fits lexical mapping and operator realization rules by whole-string matching |
| Exhaustive grammar-aware control | 192 | 0.0010 s | 0.367 ms | Same program hypothesis class, direct elimination; **equally accurate, faster** |
| GRU full-sentence seq2seq, seed 13 | 0 | 11.579 s | 7.447 ms | 45 epochs, 41,599 parameters |
| GRU full-sentence seq2seq, seed 29 | 0 | 12.250 s | 9.394 ms | 45 epochs, 41,599 parameters |

The GRU comparison is **diagnostic only**: its training examples are much shorter than evaluation, and it was not convergence/capacity/compute-matched. Do NOT present this as a general neural-model failure or an architecture victory.

Tests: **8/8 external pytest checks** plus 9/9 internal source/logic checks PASS. One final local full regression completed on the current source. It is not a full FORGE integration regression. No independent original-source, energy, FLOPs, general-language, or system-level acceptance was performed.

## Machine-verifiable local source identities (SHA-256)

- Full original experiment (with GRU) `experiment.py`: `a63db080f71b286bca955c475454e585d8cbeea0daa64fa2e94c41b587d5346c`.
- Original `test_experiment.py`: `bb6b66d519b2b520b99c35b93d831f1f36ce0e813ed8aaf9781ef809b69cc32e`.
- `source_manifest.json`: `ab5975c62e26176dc7259ac384491c27714767ba4332944ec90f6040e9b6433a`.
- `results.json`: `945a90e167b72d654c98ec5953e77eef23aa02ad6647cae152d38a6e93b5761e`.
- `full_regression.log`: `ab1e303c5172f69c44817173bdf56fdfc1fead482f0250d8e93e66037cd8145e`.
- Full local development bundle `ELG-01A9-development.tar.gz`: `d7dbe14341068b35d07c52a0ed8160b97b499475b5a65c2c8df39c141189404b`.
- The **separate** small standalone GitHub reproducer `reproduce_symbolic.py`: `9cad9c585cd44f04f3ce7850161bebfb29c7c7a3e278e69fc079602e6fb389b9`.

**What is actually in GitHub:** The runnable compact symbolic reproduction, this evidence record, and identities above. **The original full GRU code/tests/result bundle currently exists in local conversation artifacts only, not in this GitHub branch**. Do not claim GitHub reproduces GRU results until those exact bytes are deposited and hash verified.

## Disposition

**NO SCIENTIFIC ADVANCEMENT.** Structurally decomposed grammar induction succeeded, but a comparably informed symbolic baseline matched accuracy and was faster. A weak out-of-length GRU is not a sufficient alternative control. Advancement requires a task for which strong grammar-aware controls cannot trivially solve the problem, genuinely trainable composition with fewer supplied priors, prospectively separated independent evaluation, and stronger matched learned and symbolic comparators.

Archive scope only. No paid API, controller, queue, workflow, promotion, accepted ref or protected main modification.
