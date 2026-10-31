# E-D68 — corrected decay-controller audit and limited rerun (2026-10-30)

**Engineering execution PASS, prior E-D67 decay comparison INVALIDATED. Scientific acceptance NOT GRANTED.**

## Root cause confirmed
E-D67's purported decay mode was a no-op: `st=last_seen.get(i,(0,0,0)) if memory_mode else (0,0,0)` treats both the string `last` and string `decay` as truthy and returns the identical stored state. It initialized `last_time` without using it. Thus E-D67's exact equality of last-cache and decay was **a harness bug**, not a result about decaying belief. E-D67's observations about cache versus no-cache remain separately exploratory.

## Corrected mechanism
E-D68 implements `memory_mode='decay'` as discrete first-two cue bins `int(last_seen_bin * 0.94**age)`, maintaining the final direction index, while cache returns the unaltered last-seen cue. Both use matched resource dynamics, original learned Q policy, and no evaluation updates. A second AST harness bug (two initialization assignments; only one inserted) was corrected before the successful run. The expanded 336-episode matrix exceeded this session's execution window and yielded **no reported result**. The completed gate is a reduced exploratory **96-evaluation** matrix: six new seeds 43000–43005, two shifts (clustered/sweeping), two masks (40 and 60 steps starting at step 20), four arms (TD without memory, TD-last, TD-decay, no-update).

## Observed mean harvest/action (higher better)
| Shift / mask | TD no cache | TD last | TD real decay | No updates |
|---|---:|---:|---:|---:|
| clustered / 40 | 0.01062250 | **0.01431727** | 0.01198206 | 0.00544322 |
| clustered / 60 | 0.01034831 | 0.01049091 | **0.01054566** | 0.00544322 |
| sweeping / 40 | 0.01318680 | **0.01822929** | 0.01462539 | 0.00817681 |
| sweeping / 60 | 0.01141545 | **0.01302709** | 0.01206586 | 0.00817681 |

Paired last-cache vs decay across six seeds: clustered 40: 4 wins/0 ties/2 losses; clustered 60: 3/0/3; sweeping 40: 6/0/0; sweeping 60: 5/0/1. **The two memory modes now produce genuinely differing outcomes.** Longer masks generally reduce the benefit; no causal superiority of one controller is independently established.

Deterministic first-seed replay of all 16 cells PASS by source assertions; max energy ledger discrepancy `2.1714186004828662e-11`; execution 12.149s. Exploratory code SHA-256 `9e5dbbeecf1b97ccdf00d428a9df21cd9bb540fc002468fad104ab3b6222745b`, results JSON SHA-256 `a1a37661e0a492c87c986d819127c056cb70a99d9fe8d98b9a89d6be3c1dfa2f`. Raw files are in the session under `/mnt/data/e_research/ed68/`; **not independently committed/custodied in GitHub**.

## Scientific boundaries
The decay intervention is human-coded and uses integer quantization, not a learned Bayesian belief state. The mask60 intervention runs from step 20 to the end of an 80-step episode, so it does not test post-mask recovery. Only six exploratory seeds were run. No native Wingless/Yggdrasil or original external MiniGrid qualification; no independent held-out benchmark, causal intelligence claim, or FSA scientific first-use. FORGE autonomy unchanged.

Next E-D69: track exact observation-bin transitions and action differences between last and decay, then evaluate with matched conventional recurrent controls and sealed evaluation. Avoid labeling E-D67 decay equality a valid experimental negative.
