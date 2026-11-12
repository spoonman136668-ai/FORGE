# Eureka F58 — frozen original historical FIT torque-rule result

**Outcome:** `F58_FIT_ACTION_RULE_NO_GO`. This result records a prospective failure against the strongest learned conventional control. Preserve it permanently; do not tune F57 on it or rerun the consumed FIT as an unseen scientific cohort.

## Exact protocol and source

Protocol-first commit `ec22d962f145f2f55262368b3a5f7381f4806c50`, immutable document blob `a8396cab6180e0aaefbbc799d1f7b8b770d3a372`, before any F58 code/tests/output. F58 implementation commit `c1d0a3cf253fc1310e2c09e18d2c9ac96a266912`; the first focused test exposed a **synthetic unit-test** threshold incorrect under ordinary ridge shrinkage (asserting estimated norm > 0.1 when the fitted unit coefficient was 0.0999959). This test-only expectation was corrected from 0.1 to 0.09 at `f41a7b012ce57f499415ff5c928c8df9c5366477`, without modifying F58 source, frozen metric thresholds, models, FIT data, or future F57 protocol. The first F58 original scoring pass did **not** start before the correction.

Existing own-PR temporary read-only GitHub Actions [run #43202386636](https://github.com/spoonman136668-ai/FORGE/actions/runs/43202386636), focused job `131129282709`: **8/8 unit tests PASS**, actual pinned Farama Gymnasium v1.2.3 commit `365080941ea3a815ac09e57a7d4ee263a142651d` and Acrobot Git blob `28c440af281858c30e95fb6023f19923065d64fe` both verified. Only the six already-consumed original `book` FIT roots, 48 historical episodes, 8,974 transitions, FIT SHA-256 `63d31930006ec2f465e4becd989c1a0b922e15a0842ef991fe424074d436a31a`; 6 disjoint historical root-held-out folds. One exact cold model/prediction replay per fold, 6/6. Python 3.11, NumPy 2.0.2, `OPENBLAS_NUM_THREADS=1`. No F57 transfer or retention seed, new original-scored policy episode, external first-use or owner/authority command.

## Frozen comparative outcome

Root-equal holdout prediction MSE (two normalized real angular-velocity increments, lower is better):

| Model | Historical FIT-root-held-out MSE |
|---|---:|
| Factorized torque rule **candidate** | 0.001866531421154302 |
| Action-specific fully trained ridge **strong conventional** | 0.0018676919940326603 |
| Action-blind fully trained ridge | 0.002004278444615079 |
| Shuffled-torque credit negative | 0.0020121077626618434 |

Prespecified falsifier outputs:
- Candidate / strong action-specific ridge MSE ratio `0.9993786058503937`: **FAIL**, required ≤ `0.98`.
- Candidate beats strong conventional on **2/6 roots**: **FAIL**, required ≥ `5/6`.
- Candidate / action-blind MSE `0.931273509511184`: meets ≤ `0.95` development diagnostic.
- Shuffled action negative / candidate MSE `1.0779929766290857`: meets ≥ `1.05` credit negative.
- Six of six roots had a nonzero learned action-effect coefficient, but this alone is not evidence of superior control.

Therefore retain `F58_FIT_ACTION_RULE_NO_GO` rather than relabeling it a success. This comparison indicates the historical randomized actions carry useful conditional predictive information over action-blind/shuffled controls; the proposed compact factorization did **not** deliver the required advantage over conventional fully trained action-specific ridge. It cannot demonstrate same-state true counterfactuals, a new causal representation, unfamiliar-physics transfer, multi-step policy return, autonomy or RSI.

## Evidence retention and next decision

Actual full F58 report SHA-256 `e34a928e09f5aeea3d492eb38259064bb1895bf0a7a29815091909cbc1ad3276`. The original unmodified report is retained in [Actions artifact 13935323115](https://github.com/spoonman136668-ai/FORGE/actions/runs/43202386636/artifacts/13935323115), artifact ZIP SHA-256 `ce8e7c55492104d7f9bb579df67db1ed0362b9923712b472743cc96200373326`. No evidence was placed in user Library.

F51 `F51_DEV_NO_GO` and F56 `F56_FIT_ONE_STEP_NO_GO` remain unchanged. F57 fully frozen 168 prospective scored episodes plus 168 cold replays remain **NOT EXECUTED** and cannot run without separately authenticated native FORGE FSA issue #83 authority and protected original first-use custody. F58 is complete as a **development falsification**, not SCIENTIFIC_PASS. Do not retune failed thresholds, change original root assignments, or claim that synthetic unit tests proved learning. No new controller/scheduler/runner, paid API, cross-project access, promotion, merge or deployment.
