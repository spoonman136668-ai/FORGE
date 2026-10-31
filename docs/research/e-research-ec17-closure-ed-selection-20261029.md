# E Research E-C17 — ecological-configuration closure and mechanism selection

**Date:** 2026-10-29. **Gate status:** Historical-source review and design decision PASS; **no new simulation executed**; scientific first-use/acceptance UNVERIFIED. Advisory-only FORGE PR #1194, isolated from FORGE autonomy and native architectures.

## Verified basis and closure

Read E-C16 report on existing draft research branch. Its six development seeds × matched build/sham × 80/160/320 steps (36 trajectories) recorded medians of build-minus-sham harvesting of 0, -0.17880243 and 0. At 320 steps the six individual differences were [0,0,0,-3.6076,+8.9700,-6.3700]; heterogeneity is material. Both structures were assigned a programmed +0.7h nutrient replenishment multiplier after construction; no construction policy evolved during this diagnostic. The reported engineering PASS and original bytes are not independently authenticated in the repository.

Together with E-C1–E-C15, the evidence does **not support** claiming that the present constructed-habitat reward-multiplier ecology yields (a) consistently net-beneficial construction, (b) evolved construction choices superior to greedy conventional control, (c) within-lifetime learning or (d) unfamiliar-family transfer.

**Close only this specific ecology and the tested hypothesis under the FIT configuration: NOT SUPPORTED.** Do not claim a universal null for niche construction, ecology, emergence, or causal learning. Stop further coefficient/horizon tuning on these exposed FIT seeds.

## New prospective mechanism: E-D — causal infrastructure ecology

**Choice:** Investigate **physical environmental infrastructure enabling new actions**, rather than increasing reward directly. Candidate 2D local world has energy-limited organisms, a bounded stock of movable materials, resources behind changing barriers, and a local build/remove action that alters traversability or fluid flow. The resulting opportunity is accessible only after local causal interaction. No free reward for building; costs deducted identically across arms. This is not a built-in "build leads to food" score: harvest occurs only when organisms physically reach and collect resources.

**Hypothesis:** Local policies can discover, select, retain and transfer useful environmental interventions to unfamiliar barrier/resource configurations under matched observation and compute budgets. Evolutionary adaptation and *within-lifetime plasticity* are separately tested, not conflated.

## Prospective controls

- Evolved local action policy with building allowed.
- Same-capacity evolved no-build ablation, with matched selection and training interactions.
- Reactive shortest-path/greedy navigator with and without building, using only identical local visibility.
- Random-build policy matched for build count and materials.
- Fixed-handcrafted build policy as upper control.
- Environmental reset at reproduction, and persistent infrastructure across descendant lifetimes.
- Within-lifetime adaptation disabled or reset control **only if** an actual learner is implemented; do not invent a learning claim.
- Static versus changing barrier layouts, with identical environment sources and resource flow.

**Primary functional outcome (prospective):** net resource gathered per fixed potential decision slot, extinction scored as zero opportunities, on novel barrier/resource layout families. Secondary: first-use intervention success, lineage survivorship, resource-material ledger, descendant benefit attributable to persistent constructions, transfer cost, CPU/RAM/wall and failure rates.

## Preimplementation E-D0 contract

Before code or training:
1. Freeze local observation/action encoding, grid/barrier and resource material accounting, energy costs, construction durability and reset physics.
2. Specify one **solvable** barrier intervention on FIT and one corresponding impossible intervention to detect reward leakage or global oracle.
3. Verify by BFS offline that a path appears from an intervention *without* privileged action information, and that no-build control truly cannot traverse the barrier in that case. BFS is evaluation-only, not a policy input.
4. Require paired counterfactual worlds with identical weather, resource supply and seed, and no accidental leakage of target labels through map generation.
5. Predefine independent FIT/VAL/HOLDOUT source identities, matched training search/decision budgets and conventional controls. Holdout first-use sealed and independently authorized before evaluation, not consumed by design.
6. Fail closed on ambiguous custody/authority. A documentation-only branch cannot qualify original science.

**Plain English:** Our previous ecology paid organisms extra food for building, but even then evolving agents rarely chose to build. The next world will let building change what is physically possible—like opening a route to resources. We will test whether organisms discover that causal opportunity instead of being rewarded just for building.

**Next gate:** E-D0 offline causal-infrastructure world specification and solvability/unit-test design, followed by bounded FIT engineering implementation only if this contract can be satisfied. No new controllers, queues, autonomous scheduling, FORGE owner changes or model integration.
