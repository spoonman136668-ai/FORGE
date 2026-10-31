# NR-M1D — delayed-reward memory retention diagnostic (exploratory negative)

**Status:** SYNTHETIC DEVELOPMENT SCREEN ONLY. No accepted scientific result, authentic source-world first use, protected held-out evaluation, native Wingless/Yggdrasil integration, or FORGE research selection/promotion. No active controller, queue, schedule, or runtime changes.

## Provenance and preparation

- Experiment protocol SHA-256 `968c861f0aa9aa04679a9016f30073f30e2c465591bfa4459dc1be1e2bb8eb4e`, written before candidate implementation.
- Recurrent comparator addendum SHA-256 `cb4c1659292cd2f210d5c85036eee05c346ed84426855a24da8fc3b5d548f9a0`, frozen after the initial retention screen but before that comparator's code/run. It is expressly **exploratory**, not prospective original science.
- Prototype source SHA-256: `experiment.py = 120a30203d4b3e15c87d937347a033aaf2e5c1ce4e3b1dbe05e11856823746e7`.
- Recurrent source SHA-256: `gru_control.py = 20619bd6142198f66270da3da8da0d0b68d0b4660bdda7d409e76ef58d5890a6`.
- Unabridged machine-readable local result SHA-256: `results.json = c23c257973282e595a375e72da7ae5d9d4f804b12c2777f43fda49a62d23f7eb`; `gru_results.json = 2d45fe2ff85a103e52c8e918c85e0d490cb7027b1fbf13eb926dc059a016c074`.
- Local diagnostic: Linux x86-64, Python 3, PyTorch 2.10.0+cpu. Source hashes are local and must be verified against published code if reused. No independent external replication. SHA-256 hashes are content identities, **not proof of scientific qualification**.

## Design

- Seeds: 17, 31, 47, 61. Per seed 2,500 training episodes, 400 evaluation episodes per split, each split and seed run on common deterministic synthetic generator.
- Two-slot online retention. Ten feature identifiers (0–9); the stream exposes feature ID and bit but not future query. A binary action occurs after distracting observations; the training signal is terminal action reward only.
- Candidate: differentiable feature-ID logits, sequential Plackett-Luce two-of-three stochastic retain/evict, terminal-reward REINFORCE with a running reward baseline; no direct feature-importance target or per-step supervision. Training has no future query.
- Learned same-slot positional comparator: two position parameters, identical action-reward interface, episode budget, and two-slot retention. Other controls: FIFO, reservoir, rule-informed symbolic ceiling (not a fair trained model).
- Recurrent follow-up: GRU, 8 float32 hidden scalars = 256 bits, 745 parameters, 2,500 episodes, **single epoch** and terminal reward reconstructed into binary chosen-action feedback. Its state budget greatly exceeds 10 bits in two symbolic slots. It is undertrained/weak and does **not** count as a strong fully qualified matched recurrent comparator.

## Results (mean accuracy across four seeds)

| Test | Feature retention RL | Position retention RL | FIFO | Reservoir | Symbolic rule-informed ceiling | Exploratory GRU |
|---|---:|---:|---:|---:|---:|---:|
| Familiar | 100.0% | 100.0% | 48.6% | 57.4% | 100.0% | 50.8% |
| Distractor/position shift | 100.0% | 48.6% | 48.6% | 57.4% | 100.0% | 50.1% |
| Relevant-feature ID remap 0/1 -> 2/3 | 51.9% | 100.0% | 49.9% | 59.1% | 100.0% | 50.6% |
| XOR of original two bits | 100.0% | 100.0% | 48.4% | 51.7% | 100.0% | 50.2% |

**Critical negative:** feature-specific retention collapses to approximately chance on a relevance-role reassignment while the simpler positional control succeeds. Conversely, position-specific retention fails on a position shift that the feature policy survives. The complementary brittleness falsifies either approach as a generally sufficient memory-policy mechanism.

**Boundary:** The XOR output was *supplied* as a fixed readout (not learned relational composition). The role change is a synthetic ID remap (not novel causal laws). Training inferred reward only under a binary deterministic task, which is much easier than real-world sparse rewards. The rule-informed ceiling knows task grammar; it is not equally informed training. No cold-restart or real-world causal transfer test, no Bayesian trained baseline, no appropriately trained capacity-matched GRU, no complete physical resource/cross-platform final regression, no original-source authentication or independent scientific first use.

## Decision

**NO-GO** for promoting feature-ID retention alone. Preserve as an interpretable negative diagnostic only. Next NR-M1E should test context-conditioned, action-outcome-aware retention that generalizes to unseen roles, in an independently eligible environment with matched trained model-based/recurrent controls and cold retention. Prioritize the actual Wingless/Yggdrasil decision/action interface before additional synthetic tuning.

Do **not** attach this memo to FORGE's accepted evidence registry or use these synthetic numbers to assert native learning superiority. This branch is research-only draft; protected main and autonomous FORGE work remain untouched.
