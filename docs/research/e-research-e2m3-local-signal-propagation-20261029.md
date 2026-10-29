# E Research E2-M3 — FIT causal signal-propagation feasibility (2026-10-29)

**Engineering:** PASS for 24 isolated trajectories, finite/nonnegative intermediate states and replay.  
**Science:** No associative learning was tested or established; distal cue communication under the original short readout **NOT SUPPORTED**. Advisory only; no FORGE autonomy, FSA, controller, weights, or scientific acceptance changes.

## Actual execution

An isolated 64×64 periodic Gray–Scott simulation, using source-derived E2-M2 local third-field coupling against memory-ablated control. Six existing FIT seeds (first six from E2-P1), local/ablated variants, cue injection versus identical no-cue sham = **6×2×2 = 24 trajectories**. Initial state and random streams matched for cue vs sham; single dose v[CUE] += .04 and u[CUE] reduced by up to .04. dt=.25, four Euler substeps/nominal step, no evolving-state clipping, followed for 400 nominal units. Measured mean-v causal difference (cue minus sham) in fixed near, middle and distant (original OUT) regions at t=1,10,40,100,200,400.

All trajectories numerical-valid (checked after **every** substep); rerun terminal-state hash for first seed/local cue PASS. Local wall-clock ~5.97 seconds, no independent CI.

### Maximum absolute cue-versus-sham effect across six FIT seeds, local-field variant

| t | Near | Middle | Distant original OUT |
|---:|---:|---:|---:|
| 1 | 3.00898e-7 | 0 | 0 |
| 40 | 4.49368e-5 | 1.77729e-11 | 0 |
| 100 | 1.98268e-7 | 1.11272e-10 | 0 |
| 200 | 1.10928e-11 | 2.50795e-12 | 8.09465e-16 |
| 400 | 5.76485e-11 | 5.07719e-10 | 6.14265e-11 |

Matched memory-ablated variant at t=40: near 4.493673e-5, middle 1.777290e-11, far 0; at t=400 far 5.266125e-11. This establishes no useful local-memory advantage for propagation in this pilot.

**Interpretation:** The cue affects nearby chemical dynamics clearly. At the original distant output the causal effect is zero at t=40 to printed numerical precision and ~1e-15 at t=200 (floating-point scale). At t=400 a small signal appears, but its amplitude and signal-to-background implications are not qualified. A negligible distant cue effect explains the preceding cue-sham interaction null for this readout; it does not exclude all alternative local routes or architectures. Differences of ~1e-15 are not meaningful proof of communication. No associative learning, transfer or self-maintenance claim.

## Evidence identity

- Local executable source: `/mnt/data/e_research/e2m3/run_e2m3.py` (SHA-256 `bd5d5098be5b1b3429943fb14385a294d4af60095db051b2a6f630e91f94b501`)
- Local raw JSON: `/mnt/data/e_research/e2m3/results.json` (SHA-256 `fe8a3ab3f368a8ddd6a31b8c40ab96be08d103b9a7bad6a817f4dcd6f8cd0147`)
- Dependent source module: `e2p1/run_e2p1.py` from the original session directory. **Original bytes remain local and are not included in this documentation-only commit.**
- No independent immutable FORGE native FSA custody, CI replay, HOLDOUT, scientific first-use or CPU/RAM full accounting. Reproduction solely from the repo remains UNVERIFIED.

## Decision and next gate

Do not interpret the previous E2-M2 nonresponse as a valid test of long-range associative learning when the cue scarcely reaches the readout. **E2-M4:** prospectively define local-only short-range cue/output ports, demonstrate cue propagation at the selected distance with precision and signal-to-noise controls, and only then test paired history cue-sham interactions against passive chemistry, engineered memory and reactive controls. If short-range variants remain negative, stop this chemistry family and prioritize independent open-ended developmental/ecological hypotheses. No FORGE runtime changes.

**Plain English:** The stimulus does not reach the old distant output strongly enough to test learning there. This is a physics/setup limitation, not an intelligence discovery.
