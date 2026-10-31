# E Research E-D10 — exploration control on elbow layouts (2026-10-29)

**Actual local FIT execution:** engineering PASS, **learned causal-planning advantage NOT SUPPORTED**. Research advisory only, no FORGE owner, controller, native model, selection, scientific admission or autonomy change.

## Scope and execution

864 evaluation trajectories: E-D8 source world generator, three shapes (horizontal, elbow, staggered), 18 existing development seeds 56000–56017 × four repeated stochastic trials × four policies. Exact whole-experiment deterministic replay PASS. Offline independent BFS checked that each generated test map is physically solvable, but evaluation policies never receive BFS output.

Policy comparisons with 65 decision slots, 110 initial energy, one or two construction material units, movement cost one energy and construction cost four energy:
- **Graph-labeled local controller** retains visited-relative-position counts and local wall observations and scores locally legal actions by goal-bearing progress, visit penalty and authored build heuristic. **It does not train an action-conditioned transition model, perform general graph search, or learn physical causality.** The name must not be misread as proof of causal planning.
- **Optimistic conventional controller** uses the same local observation, construction action interface and a simpler authored optimistic visitation bonus.
- **Hand-coded builder** uses a greedy shortest Manhattan-distance move/construction heuristic; this control obtains full goal delta internally, whereas the graph/optimistic policies use the reduced E-D8 observation. This is **not perfectly information-parity-matched**.
- Random uniformly chooses legal actions.

| Shape | Graph-labeled local /72 | Conventional optimistic /72 | Hand-coded greedy /72 | Random /72 |
|---|---:|---:|---:|---:|
| Horizontal | 72 | 72 | 72 | 4 |
| Elbow | 72 | 72 | 0 | 1 |
| Staggered | 72 | 72 | 72 | 5 |

**Key result:** A conventional, locally informed optimistic policy solves the elbow cases that defeat the earlier goal-greedy builder. The graph-labeled controller achieves **exactly equal success** on all three development families. There is **no demonstrated advantage from learned causal structure**, no training or acquired mechanism in this gate, and no independently held-out transfer. Task simplification may make the elbow obstacle solvable by one constructive opening and optimistic action scoring. Four trials of the same seed are not independent environment samples. A few policies' observation and action-choice implementations differ enough that equal strict information budgets must be audited before scientific comparison.

Resource ledger: energy spent at each step <=110, construction material remaining + number built = initial material, nonnegative accounting PASS. Source uses original E-D8 legal action and observation mechanics without an oracle planner input. Recorded process runtime around 0.392 seconds, peak RSS 96828 KiB. No full compute accounting, formal policy correctness guarantee or independent FSA qualification.

## Original local evidence (not committed)

`/mnt/data/e_research/ed10/run_ed10.py` SHA-256 `224e33df9ce5af5445245a4de3b43a361c4af5ec73edf4efa32794f28f8f7e5c`

`/mnt/data/e_research/ed10/results.json` SHA-256 `61b8ecbba2c8403165e418b8ec277890f56915139b168f6224fb9910d0248935`

The source depends on E-D8 and its earlier source modules; **only this summary** is being added to the FORGE draft PR. Source code, complete JSON, immutable original first-use and independent qualification remain unverified in GitHub.

## Decision and E-D11

Treat E-D10 as a **conventional control success / proposed learned-causal novelty FAIL**. Next gate should explicitly implement and audit a transition learner trained using only local observation/action/consequence records, and independently establish it can predict previously unseen action consequences under same information and experience budget. Include **learned-model reset**, **scrambled-consequence** and **oracle-free fixed model-based exploration** ablations, plus credit for model complexity/compute and unfamiliar families. Do not claim cumulative learning from handcrafted navigation.

**Plain English:** A simpler exploration strategy solves the corner obstacle already; a so-called graph controller does no better. We need actual learned mechanics and stronger controls before claiming any emergent intelligence.
