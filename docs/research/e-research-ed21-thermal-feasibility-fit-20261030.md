# E-D21: Thermal infrastructure feasibility (2026-10-30)

**Engineering FIT PASS. No learner evaluated. Scientific first-use and FORGE acceptance UNVERIFIED.** Documentation-only advisory; no autonomy or native model changes.

Following E-D20's negative results on binary-probe reliability changes, E-D21 switched to a different physical task family: single-variable temperature control with inertia. An insulated shutter changes coupling to the ambient temperature. An unobserved time-varying heat/cold pulse is implemented in the physical transition, with random small disturbances. The public agent observation is rounded current temperature, and legal actions are shutter open/closed. Switching shutter position incurs 0.35 energy units; there is no intrinsic reward for acting. Score is cumulative negative absolute difference from target temperature 20, minus action cost. 80-step episodes.

**Actually executed:** 24 FIT development seeds 87000–87023 x four fixed/reference policies = 96 trajectories. Full deterministic seeded replay PASS. Forced open vs forced closed change the state trajectory PASS. Resource ledger check (energy + switching expenditure = initial 160) and nonnegative energy PASS. These are entirely synthetic programmer-defined dynamics, not externally sourced ecology or an independently qualified real environment.

| Policy | Median net | Median switching-energy cost |
|---|---:|---:|
| Fixed closed | -107.5024 | 0 |
| Temperature-reactive (open above 22) | -139.1258 | 0.7 |
| Random | -211.9342 | 13.65 |
| Fixed open | -240.9291 | 0.35 |

**Interpretation:** Fixed closed outperforms the naive reactive, random and fixed-open controls in this FIT system. This demonstrates that shutter actions have consequential delayed physical effects, **not** that useful control requires learning. The rule open-if-hot is naive: during heat pulses opening the shutter can warm the room faster. This environment may reward inference about ambient conditions from state history, but that hypothesis is UNTESTED. There is no memory-enabled policy, Bayesian model-based controller, action-conditioned dynamics learner, conventional optimal planner, uncertainty calibration or novel distribution evaluation. Do not declare new intelligence or positive memory evidence.

**Original executed local source:** `/mnt/data/e_research/ed21/run_ed21.py`; SHA256 `9061004cf649aed2226bac6c3694dc4d835ed2ee051d5ee0c93aac250eab96b9`.
**Original raw JSON:** `/mnt/data/e_research/ed21/results.json`; SHA256 `12e1036183324f962c4968238d058580979a6a8d937fc7c056fc3c28d95806fe`.
Original bytes are outside this documentation-only branch; SHA alone is not independent first-use evidence. Source custody/independent qualification remain unresolved.

**Next gate E-D22:** freeze this physics; compare learned short-term transition memory and selective episodic memory against equal-information conventional Kalman/filter-like state estimation, online control, fixed closed, and matched reactive control. Predeclare a FIT intervention-sensitivity criterion requiring learned-model ablation to degrade return. Introduce independent heat-pulse timings and do not tune to these used FIT seeds. Before science promotion, commit original runnable code and qualifying source/holdout to an authenticated evidence path and obtain independent verification.

**Plain English:** We built a new kind of problem where actions physically alter future conditions. So far, doing nothing is better than our simple reaction rule. The next test is whether remembering trends can beat doing nothing.