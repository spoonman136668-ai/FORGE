# E Research E-D0 — static causal-infrastructure verification (2026-10-29)

**Scope:** Isolated FIT-only *engineering* feasibility check. Engineering static reachability **PASS**. Intelligence, learning, ecological evolution, scientific first-use and FORGE acceptance **UNVERIFIED**. Documentation-only draft; no autonomous controller or native model changes.

## Verified execution

Executed Python standard-library breadth-first reachability on a fixed 9×9 non-wrapping grid. Start (1,4), destination (7,4). A full wall at x=4 separates them. A single authorized intervention may remove the barrier at gate (4,4). No direct reward on building.

Results:
- With full barrier: destination **UNREACHABLE**, expected.
- After removal of the barrier tile (4,4): **REACHABLE**, expected.
- After intervention at incorrect position (3,4): **UNREACHABLE**, expected.
- Material ledger: initially agent material 2, placed 0; after construction agent material 1, placed 1; conservation **PASS**.
- Energy after intervention 4 from 5, immediate reward 0: charged cost **PASS**.

These are deterministic unit smoke tests, not a complete dynamic world. No organism, policy learner, weather, resource dynamics, or ecological population was simulated. The barrier and correct intervention are **hardcoded in the test**, and BFS is an evaluator-only oracle, not a learner input. A dynamic environment may still have different bugs. Full comparable training budget, held-out worlds, costs, source-birth and independent scientific qualification remain unverified.

## Original local artifact identity
- `/mnt/data/e_research/ed0/verify_ed0.py` SHA-256 `caf41820ec82720d5a9df885ce2efdc32c7c444ed1b78ce18ca998b80a4d4ad1`.
- `/mnt/data/e_research/ed0/results.json` SHA-256 `ed22a4c3f8dcdcf48bbfb4106166b97b42797e86a52a791f141a8158d243b030`.

Files were created and executed in the isolated container. They are **not stored by this docs-only GitHub commit**; digests alone do not establish independently authenticated original custody. Reproduction from FORGE repository alone remains UNVERIFIED.

## Next gate E-D1

Implement a minimal dynamic map, one local perception/action interface, material/energy/resource accounting, and fixed-policy baselines. Require tests for invalid constructions, no leakage of correct gate tile, closed/open world paired causality, and independent FIT seeds. Include a planner as an **evaluation-only upper bound** and reactive/rand fixed policies receiving exactly the same observations as candidate. Never infer learning from solved handcrafted reachability alone.

**Plain English:** We verified that a wall blocks access, and a paid physical intervention opens it. This gives future agents a real causal problem, but none has solved or learned the problem yet.
