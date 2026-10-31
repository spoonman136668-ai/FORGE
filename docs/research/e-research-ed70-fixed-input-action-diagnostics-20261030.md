# E-D70 — Fixed-tape counterfactual memory decision comparison (2026-10-30)

**Engineering execution: PASS. Scientific performance superiority: UNVERIFIED.**

## Method
Re-used the original E-D69 local instrumented code with no environment/model changes. From the last-observation controller, recorded 6 baseline masking traces across seeds 43000–43002 and clustered/sweeping resource variants; froze each seed's Q-table after three training episodes. At every recorded baseline masked decision, performed three **counterfactual action queries against the same observed baseline cue**, without re-running the environment for the other choices: (1) cached cue, (2) hand-coded cue decay at 0.94^age, and (3) hand-coded recurrent exponential persistence at 0.97^age. All query the same frozen Q-table and action tie-breaking. This is **matched-input action diagnostics**, not reward comparison. The persistence mechanism is NOT a trained recurrent model. The age is approximated as t-19; it does NOT necessarily equal the actual last-visible age of every newly born agent, so this is not an exact replay of the E-D68 controller internals. Results are purely diagnostic.

## Counts
Six observed baseline tapes, 1,850 masked observations:
- Cached versus 0.94-decay choices differed in **1,722 / 1,850** decisions (93.1%).
- Cached versus 0.97-persistence choices differed in **1,634 / 1,850** decisions (88.3%).
- Decay versus persistence choices differed in **121 / 1,850** decisions (6.5%).

Thus, with *fixed observed cues*, cue transforms affect selected actions; this removes trajectory divergence from this particular **decision-level** comparison. No corresponding counterfactual rewards, memory transfer, or generalization were measured. In particular the 0.97 persistence rule is only a hand-designed alternative, **not a trained recurrent agent**, and this result must not be presented as a recurrent-controller qualification.

Local executable: `/mnt/data/e_research/ed70/run_ed70.py`; outputs `/mnt/data/e_research/ed70/results.json`. Local-only source and outputs are not independently authenticated by FORGE repository custody.

## Status
**Action-difference diagnostic PASS; comparative performance and scientific intelligence claims UNVERIFIED**. Follow-on experiment: log complete pre-mask raw observation tapes and true per-agent last-visible time, train a conventional recurrent baseline at matched resources, then evaluate full rewards on a frozen independently held-out original benchmark. Do not promote exploratory synthetic evidence or affect FORGE autonomy or other researchers. DoorKey official source execution remains separately blocked in #1245.
