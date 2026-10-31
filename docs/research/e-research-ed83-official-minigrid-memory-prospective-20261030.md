# E-D83 — External memory benchmark source-pinning and prospective qualification (2026-10-30)

**Authentic upstream source PASS. Runtime test, frozen scientific split and first-use acceptance UNVERIFIED.**

## Verified original source
Official Farama-Foundation/Minigrid repository, immutable commit `7f5853792ea7f04f75614661006d87fcf949f26d`. The `minigrid/envs/memory.py` file is actual Git blob `660b0a1b769948034c87bb421759c2b9a4f24548`. The original `minigrid/__init__.py` registers:
- `MiniGrid-MemoryS11-v0`, size=11, fixed hallway
- `MiniGrid-MemoryS13-v0`, size=13, fixed hallway
- `MiniGrid-MemoryS13Random-v0`, size=13, random_length=True
- `MiniGrid-MemoryS17Random-v0`, size=17, random_length=True

The benchmark requires the agent to remember a sampled initial object while traversing a corridor and select the matching terminal object, with 7 native actions and a partial 7×7×3 visual observation by default. The original module exposes mission `go to the matching object at the end of the hallway` and terminal successes/failures/timeouts. This is a memory-dependent action task, not next-observation MSE.

## PROPOSED — not frozen/authorized or scientifically first-use
If independently approved before any benchmark use, use `MemoryS11` for FIT implementation, `MemoryS13` for validation, `MemoryS13Random` for fresh original-source distribution-shift DEV, and `MemoryS17Random` as separately held-back challenge. Freeze actual seed lists, source commit, environmental wrappers, observation schema, action budget, per-family train/dev/holdout and total compute/energy before any read or test on held-out sequences. A single deterministic seed or environment identifier alone does not freeze an independent split.

Compare no-memory reactive baseline, explicit last-cue cache, matched history-window model, conventional trained recurrent model, and the independently native Wingless/Yggdrasil implementations **only once those interfaces and training procedures are genuinely qualified**. Match observations, action budget, training experience and resources; never grant either native architecture shared state/answers or hidden ground-truth mission shortcuts. Measure success rate and return, first-use provenance, retention after restarts, action/observation access, CPU wall time, memory, and true unfamiliar variants. Use standard controls and independently authenticated original run/witness receipts.

## Hard evidence/authority boundaries
The original MiniGrid Git source **has been retrieved** read-only via connected GitHub. The official Python benchmark has **NOT been installed/executed here**; an existing unrelated DoorKey smoke on PR #1194 is separately runner-blocked (#1245). No source custody of new experiment run, original learned predictor checkpoint, trained native model, controlled full reward benchmark, or scientific holdout witness is established. This record is only preparatory source verification, not an accepted frozen protocol. Do not imply research PR #1194 is ready to merge or apply its executable workflow to main. Do not touch FORGE autonomy or CKB-plane.

## E-D84
Qualify an authorized runner for source-pinned official MiniGrid Memory reset/step and deterministic replay with exact returned stdout/stderr; only after engineering PASS lock training/evaluation protocol and run controls. Keep negative E-D80/81/82 results.
