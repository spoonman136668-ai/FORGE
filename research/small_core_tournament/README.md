# Small-core reasoning tournament

This FORGE research module runs synthetic development screens for seven small-core methods and a dense cross-entropy/AdamW baseline. The only runtime dependency is PyTorch. The work order authorizes the CPU screen in Codex. Colby owns any later first-use decision, promotion, or scientific interpretation.

## Reproduce Round 1 on CPU

From the repository root with Python 3.12 and PyTorch 2.9.1 installed:

```sh
python research/small_core_tournament/tournament.py --round 1 --output /tmp/round1.json
python -m pytest -p no:cacheprovider -q research/small_core_tournament/test_tournament.py
```

The CPU profile uses seed 1729, 192 updates, and 16 examples per update. Every arm consumes the same ordered train structures at the same exact active inference parameter count. All arms get the same update and estimated contraction-FLOP ceilings. Actual contractions differ by method and are reported. The estimate covers attention, linear and spectral contractions, an upper bound for their backward passes and latent sweeps, and all evolutionary search forwards. Elementwise operations, optimizer bookkeeping and explicit relabeling are reflected in wall time. Arm times cover initialization, search and training after a shared runtime warm-up. Evaluation time is recorded separately. The scaffold count is peak trainable parameters.

The two tasks are following a directed graph for a requested number of hops and evaluating a linked program modulo 16. A structure hash assigns the label-independent graph or program to exactly one round and split. The clean label convention includes a deliberate graph shortcut. The substitution test applies a fresh derangement to entity IDs and graph answers. Arithmetic literals and answers keep their numeric values. Each evaluation includes balanced task buckets at 2–4, 8 and 12 steps. Rounds 2 and 3 add concentrated distractors.

Summary accuracy is the fraction of exact answers. The gate uses OOD depth accuracy across the clean 8- and 12-step buckets and pooled substitution drop across ID and OOD. Drop is max(0, clean accuracy minus substituted accuracy). The receipt also preserves the signed gap, paired clean-to-wrong flips, and prediction equivariance. Ties on either gate metric eliminate a contender. Over 2× dense time, the training-time ratio multiplied by the contender's OOD error must be at most the dense OOD error. Surviving arms are ranked by the smaller improvement, in percentage points. Round 1 takes up to four. Round 2 takes up to three after the same direction of gain on all three seeds and at least 2 percentage points mean gain on each metric. An empty field closes the round. An `ADVANCE` verdict means eligibility for owner review.

## Run the standalone script in Google Colab after owner review

Upload just `tournament.py` and the Round 1 receipt to a Colab notebook with a CUDA GPU runtime. Use the preinstalled CUDA-enabled PyTorch. The CPU attempt used PyTorch 2.9.1. The receipt records the actual PyTorch version and device on each run. In a notebook cell:

```python
!python tournament.py --round 2 --previous round1.json.gz --owner-review REVIEW_REFERENCE --output round2.json
```

Replace `REVIEW_REFERENCE` with the reference to the exact FORGE-native owner decision. The script records that reference. Owner authentication and first-use reservations remain with FORGE. The runner checks source hash, prior outcome and the fixed profile before proceeding. Each qualifying finalist and dense are trained from scratch for 768 updates at a matched 5M–25M parameter count on seeds 2718, 3141 and 5772. It reports magnitude pruning and a seeded random-mask control at 50% sparsity, both measured immediately without retraining.

After the Round 2 review:

```python
!python tournament.py --round 3 --previous round2.json --owner-review REVIEW_REFERENCE --output round3.json
```

Round 3 selects the best eligible optimization arm and anti-memorization arm in rank order. It trains the combination, both component arms, and dense on a distinct structure split and measures the combination against each control. It records a closed round if either method family has no eligible finalist. The script emits synthetic development evidence for owner review.
