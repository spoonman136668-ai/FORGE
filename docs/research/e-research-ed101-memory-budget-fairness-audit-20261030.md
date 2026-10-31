# E-D101 — prospective MiniGrid Memory protocol integrity and resource-fairness audit (2026-10-30)

**Original E-D100 protocol read back from authenticated GitHub:** PR #1194, head `fe2828cda4d3f003e3ddf5a5b9955b767cc39a39`, file `research/e_research/ed100_prospective_memory_protocol.py`, Git blob `bbbc7d21c33778c72a1183f29f903e3ba93bb458`.

**Static source review PASS; approval readiness FAIL; executable official environment run UNVERIFIED.** No training or held-out evaluation performed in this gate.

## Supported checks
- Four groups are defined: FIT MemoryS11 with 100 seeds 10000–10099; VAL MemoryS13 with 30 seeds 20000–20029; DEV MemoryS13Random with 30 seeds 30000–30029; reserved HOLDOUT MemoryS17Random with 60 seeds 40000–40059.
- Python sets by disjoint numeric ranges prove unique seed IDs *within the current manifest*, and the `verify` function checks mutual disjointness at runtime if executed; seed non-overlap is **not** independent-scientific split approval.
- Upstream source commit `7f5853792ea7f04f75614661006d87fcf949f26d` and memory.py blob `660b0a1b769948034c87bb421759c2b9a4f24548` are declared.
- The manifest identifies four proposed conventional controls, explicitly `PROSPECTIVE_NOT_AUTHORIZED_OR_FROZEN`, and `holdout_access=PROHIBITED_UNTIL_INDEPENDENT_APPROVAL`.

## Three blocking fairness deficiencies
1. **Information/exposure matching UNVERIFIED.** `max_training_episodes_per_model=100` is a **ceiling**, not enforced accounting of episodes actually taken, total interactions, training updates or observation opportunities. Reactive, last-cue, history-window and recurrent controls cannot be compared fairly by nominal episode count alone.
2. **Computational resource matching UNVERIFIED.** No fixed measurement procedure or common accounting for training and inference CPU time, peak RSS per process, parameters, update count, optimizer FLOPs, memory access, or deterministic toolchain/environment. A wider model may spend a very different computational budget under the same 100-episode ceiling.
3. **Action/evaluation fairness UNVERIFIED.** `max_evaluation_steps_per_episode=1500` is not proof of equal action budgets or actual per-environment limits. Need measure terminated/truncated, effective `env.spec.max_episode_steps`, rewards, action count, observation shape, agent state resets, and episode timeouts. Blind spot: an algorithm that accesses hidden cue/goal or future observations can invalidate the comparison.

## Gate policy
Until a reviewed and authorized freeze fixes the exact splits, action/observation interface and per-baseline budgets, **do not touch held-out seeds or execute a scientific first-use benchmark**. Original source-pinned engineering smoke remains open under Issue #1245; it is separate from protocol-fairness audit. Negative E-D80/E-D81/E-D82 evidence stays negative. No native Wingless/Yggdrasil training, FORGE owner/autonomy changes or production promotion.

**Next safe engineering gate E-D102:** add a purely offline fail-closed manifest schema checker (without importing MiniGrid, materializing holdout observations, or launching a runner) that refuses qualification when fairness fields, original-source custody, independent authorization and sealed split registry are absent; keep the upstream scientific protocol prospective until approved.