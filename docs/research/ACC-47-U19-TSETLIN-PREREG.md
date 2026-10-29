# ACC-47 — Original U19 finite-state/Tsetlin learning: prospective native Go falsification

**Frozen before implementation or measurement.** The source-of-truth original AC-08 register `research/ac07_sourcefree/ac08_portfolio.py` blob `5126c860771fb024ccfc14c3f7ee8925edf29787` names **U19 "finite-state/Tsetlin learning"**, not U08 reservoir, U22 low-rank or U24 cellular learning. Verify exact name and all 36 original candidate identities in both hosted operating systems before executing Go. Parent is ACC-34 draft #1131 at `45b5d8173538a566bf0f63a8e2ade2dedb6e6166`.

## Hypothesis

A true **two-action finite-state Tsetlin automaton**, learned from sequential public feature-label observations, can learn a binary-rule classifier at lower *total native worker CPU and physical peak memory* than matched conventional fitted online frequency, perceptron and naive Bayes classifiers without forfeiting generalization or robustness to unseen feature combinations.

This is a bounded scalar Go engineering experiment, not an LLM or original Wingless/Yggdrasil training test. The proposed method has finite integer reinforcement states and no oracle rule bits, no future labels, no third-party inference library. Training and prediction are charged to all arms.

## Frozen world and labels

Independent source seeds **97101,97103,97107,97109,97111**, 32 fully reset independent episodes per cold worker, seed namespace `0x479c66e21e08a5f3`. Every episode comprises 1024 FIT examples and 1024 heldout examples; each example has 16 public binary features. Four cohorts:
1. SPARSE_OR: label = Boolean OR of features 0,3,7; class balance measured, not artificially adjusted.
2. CONJUNCTION: label = (feature 0 AND feature 1) XOR feature 4; hidden interaction, no free precomputed conjunctive feature for any arm.
3. DRIFT: FIT first half rule SPARSE_OR; second half and heldout rule CONJUNCTION. No test labels used for training.
4. PARITY: label = XOR of all 16 features (hard mismatch control).

Training features use independent pseudorandom bits; heldout inputs use independent generator streams with half the rows constructed to contain deliberately unseen 4-bit combinations when source FIT fails to cover them. Source and FIT oracle digests identical across methods and operating systems; no data leakage between FIT and heldout.

## Authentic finite-state candidate and strong controls

- **FREQ16**: sixteen-feature × class frequency table, online conditional counts with Laplace smoothing and class prior; fitted conventional naive Bayes.
- **PERCEPTRON**: 16 integer weights and bias, bounded online additive updates on mistakes, deterministic left-to-right FIT order, threshold score.
- **LUT4**: trained 16-entry lookup table indexed by the four most frequent observed feature bits, chosen solely from FIT public inputs/labels; conventional compact exact-pattern classifier.
- **TSETLIN16**: 16 genuine two-action Tsetlin automata, one per feature, 16-bit state in [0,65535] centered around 32768; up/down reinforcement after a correctly/incorrectly classified FIT example, strictly local to each automaton's feature state. Final binary inclusion/exclusion action defines a 16-feature signed voting classifier; no direct access to the rule label except the public current FIT consequence. No hidden-label encodings or solution oracle in the candidate. Fixed reinforcement policy preregistered and source-pinned before trial; deterministic tie=0.

All arms process exactly the same public samples, charge source generation, fitting, scoring, oracle verification and output hashing; no stored full FIT stream in candidate state. Actual logical persistent model bytes recorded and compared to conventional controls. Any auxiliary feature generation or scoring charged.

## Resources, thresholds, classification

Five seeds × four cohorts × four arms = **80 independent cold Go processes per OS**, 32 sessions/worker, 2,048 FIT+heldout samples/session, native Go 1.25.5 on Ubuntu and Windows. Parent measures whole-child User+System CPU and wall, children measure genuine OS peak physical RSS (Linux VmHWM; Windows PeakWorkingSetSize). Each worker emits source/FIT/heldout truth/output SHA256, heldout correct/total, session count, CPU/RSS and state bytes; compare all 80 output/input/oracle digests across OS.

A **restricted engineering positive** requires every cohort on both OS: TSETLIN16 median heldout error <= best conventional median error +0.01, median whole-child CPU <= 0.90× fastest eligible conventional median CPU, OS peak RSS <=1.10× same CPU-fastest control's RSS, and TSETLIN16 state bytes <= matching PERCEPTRON logical bytes. No cherry-picked cohorts, no reweighting after results. A qualified benchmark that fails any condition reports `U19_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN`; broken identity, source, benchmarks, parity or zero CPU/RSS blocks with `ACC47_U19_BLOCKED`. Positive label is `U19_RESTRICTED_GO_ENGINEERING_POSITIVE_ONLY` — **not** a model speedup or scientific first use.

## Implementation and preservation

Pre-executable mechanical AST name check, original immutable prereg Git hash and source-bytes pin; Go tests ensuring actual 16-bit state transitions, learning labels never read from heldout, fixed independent seeds, deterministic tie and source parity, adversarial PARITY regime visible, exact resource thresholds, and no candidate storing original rule/table. Original 36-case negative source screening; GitHub Actions Linux and Windows test/vet/build, 80 cold workers/OS, independent cross-platform reconciliation and raw receipt artifacts. Draft/unmerged research only. No original model training, protected main, F139/controller/autonomy queue, CKB-plane, Mind-Palace authority or paid APIs touched.

This experiment does not rule out full multi-clause Tsetlin Machines or hardware-specific implementations if the frozen TSETLIN16 variant fails. Their evaluation would require independently preregistered variants.
