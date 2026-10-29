# MG16 native-factor isolation — source audit and fail-closed gate

Parent: FORGE MG15 online/frozen PR #1112 at `2ce268131b99587cc9d4e94ed62ab49a7c77d0f7`.
Parent evidence: genuine Wingless Go DK13 source goal on development seed 74307, original opening selected step 144, positive upstream reward at selected step 168, while frozen Go earns zero. Crucial limitation: MG15 frozen arm suppresses **both** live effect updates AND episode memory; it cannot attribute the difference uniquely to either.

This gate freezes a proper two-factor intervention **before executable** in `mg16_learning_factorial_prereg.json`. There are four source treatments per native architecture: both updates enabled, effect-learning only, episode-memory only, neither. Original source inputs, FIT checkpoints, legal original actions, source-derived feedback, caps and precommitted new development seeds are identical across arms, with separate independently implemented conventional four-factor controls and random.

## Verified blocking native source interfaces

- Go source `Wingless/research/native/itd02/dk13/successor.go` at commit `2992a25e3fe05783bfa80ecf70d737bb2a21e281`, blob `b4c0e029f45448117dbf9870b85f6551acf12822`: `Feedback` calls `m.Policy.Feedback(...)` which updates original base effects and `m.Policy.Episode`, **then** updates `m.Attempts` and `m.Visits` jointly; `BeginEpisode` resets source episode information. No original-native independently switchable effect-vs-episode update API.
- Ygg source `Yggdrasil/research/native/itd02/r17/successor_cells.py` at commit `770244b04d011466458b2335d3951daf7653dc8f`, blob `9354a1f0b732100ab943a5caee80b3849e3c1ea0`: `learn_selected` calls `self.parent.learn_selected(adapter,p,q)` (includes its base selected effect and episode updates) **then** writes `attempts` and `visits`. No separate isolated toggle or source-equivalent immutable effect checkpoint interface.

The original MG15 workaround (reloading FIT checkpoint at *each* decision) disables both factors, and therefore **cannot** legitimately serve as an episode-only or effect-only experimental arm. Python wrapping or deleting just one set of counters would create a new non-native actor or invalidate parent ledger/checkpoint invariants. No authentic original-world factorial run should be dispatched under that false label.

## Next implementation criterion

Add narrow opt-in native source APIs for **both architectures** that (1) authenticate each actually selected original public event once, (2) independently advance or hold only the base learned-effect state and only the episode successor/counter state, (3) preserve original read-only source and checkpoint integrity and native source invariants, (4) cold-restore each arm exactly, and (5) qualify focused source tests on Windows and Linux before running three preregistered fresh original DoorKey worlds. The fitted source corpus remains 1,664 original selected events, with unchanged 7×7 image/direction/mission and legal 0–6 actions; no hidden map/route, task oracle, unselected reward, or outside live action.

**Current result:** `MG16_NATIVE_FACTORIAL_SOURCE_OR_EFFECT_ISOLATION_BLOCKED__NO_SCIENCE` at the source API boundary. This is an engineering blocker identification, not a model learning result, and not a completed MG16 original-world trial. We have not run new development seeds or used heldout scientific worlds.

**Safety:** Draft/unmerged, no original Wingless R8 or Ygg R10–R12, accepted model/agent, FORGE/F139 or CKB controller, G29/Atlas, or scientific-first-use changes.
