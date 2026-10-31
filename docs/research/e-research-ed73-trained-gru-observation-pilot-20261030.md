# E-D73 — Trained GRU observation-transition pilot (2026-10-30)

**Actual local execution PASS; masked-transition prediction benefit observed when trained with matched masking. Full-episode policy/reward advantage and scientific first-use UNVERIFIED.**

## Design
Genuine trained PyTorch GRU recurrent transition (2,138 trainable parameters; 24 hidden units) fitted on 20 synthetic ecology observation streams (seeds 45000–45019), 80 steps per stream, using 35 Adam epochs and MSE next-observation prediction. Eight independent exploratory evaluation streams (seeds 46000–46007) were never used for training. Environment observation streams come from random-walk positions in the original E-C2-style 16×16 resource generation; this is a synthetic observation-model test, not a policy optimization or native Wingless/Yggdrasil experiment. Evaluation masks observations at times 20–59 and compares masked-window prediction MSE against last-visible observation and hand-coded 0.94 exponential-decay cache. No episode rewards under the GRU controller are measured.

First run trained only with fully visible observations. A second, same-architecture run trained with both visible and 40-step masked copies of the same training sequences. Both have 35 epochs; masked training has **twice as many training examples and greater computational exposure**, so it is not a compute-matched comparison with unmasked GRU. Masks applied only to training streams in second condition, not evaluation ground truth.

| Condition | Mean masked-window next-observation MSE |
| --- | ---: |
| GRU trained only on visible streams | 0.064363407 |
| Last-observed state (no training) | 0.032421875 |
| Hand-coded 0.94 decay (no training) | 0.111457749 |
| GRU trained with visible + masked streams | **0.016024437** |

On 8 evaluation seeds the mask-trained GRU beat last-observation cache in **6/8** streams, with ~50.6% lower aggregate MSE. This is a **positive exploratory observation-prediction outcome**, not an advantage over trained conventional recurrent alternatives or a memory/generalization acceptance. Its training objective explicitly targets prediction under the same mask regime; the small heldout sample may overstate robustness. No reward-closed-loop evaluation, no recurrent-vs-tabular compute-matched training, and no unfamiliar task-family transfer.

## Provenance
Files generated locally in `/mnt/data/ed73`:
- `run_ed73.py` SHA-256 `6c1cf5b8206e2070be102f9961ad3d55c9b5d1288d5764a3350e7d6db1dbfd20`
- `run_ed73_masktrained.py` SHA-256 `66041b231c52b943ca3fb43314c04e3e7ba7d484558b32ad02be1efa6512476a`
- `results.json` SHA-256 `41d7320e94decfa0fa4524c47e8843818cf155f76c5b5dff90f5639506d9d7d1`
- `masktrained_results.json` SHA-256 `49b14f5c256bd6eb159bc49392b2a02febdf5ab56be98eb41ed7d788c50eb0f9`

Local hashes are identifiers, **not independently custodied raw result bytes**. No FSA scientific first-use or model acceptance claimed. No FORGE autonomy changes.

## Next gate E-D74
Control training compute and exposure, compare masked GRU against parameter/compute-matched feedforward and conventional recurrent alternatives, evaluate entirely new mask schedules and distinct task-family dynamics. Then run full-episode reward-closed-loop policy experiments only with independent custody and qualified interface. Do not advance FORGE model selection based on exploratory next-observation MSE.
