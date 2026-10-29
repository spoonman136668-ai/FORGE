# E Research E2-M5 — short-range history × cue FIT pilot (2026-10-29)

**Classification:** Executed local engineering PASS; associative learning **NOT SUPPORTED** in tested chemical memory family. Advisory only, never FORGE scientific acceptance, first-use permission, optimization selection or autonomy controller change.

## Execution and exact design
Ran executable `e2m5/run_e2m5.py` in isolated session on 2026-10-29. Reused existing original FIT seeds 12000–12005, 64×64 periodic Gray–Scott physics and stimulus at rows/cols 8:12. Switched outcomes to **adjacent (rows 8:12, cols 12:16)** vs **near (rows 8:12, cols 16:20)** output ports (positive E2-M4 cue-communication distance). Two balanced history orderings ABAB/BABA, each with identical cue and outcome counts/doses at t=40,70,100,130, against cue or no-cue sham at t=200. Observed signed difference v(adjacent)−v(near), before probe t=199 and after t=210.

6 FIT seeds × 2 histories × 2 probe conditions × 3 dynamics (local slow field, memory-ablated Gray–Scott, passive diffusion) = **72 trajectories**. Four explicit Euler dt=.25 substeps per nominal time unit. Finite/nonnegative every substep **PASS for all 72**. Terminal state reexecution **PASS**. Elapsed wall-clock 7.216 s (not a complete resource-accounting receipt). No training, new model, optimization, independent validation or holdout.

## Prespecified difference-in-differences readout

For each seed/mode, contrast the history effect of cue vs sham:
```
interaction =
 [response(ABAB,cue) − response(BABA,cue)]
 − [response(ABAB,sham) − response(BABA,sham)]
response = (v_adjacent − v_near) at t=210 minus same at t=199
```

| Mode | Median absolute interaction | Max absolute interaction | Median absolute preprobe history contrast |
|---|---:|---:|---:|
| Local slow chemical field | 1.22550367e−7 | 1.22551119e−7 | 1.22568705e−5 |
| Memory ablated Gray–Scott | 1.22422445e−7 | 1.22423029e−7 | 1.22567004e−5 |
| Passive diffusion | 6.93889390e−18 | 1.73472348e−17 | 0.00358529356 |

**Result:** A small cue-specific history interaction occurs in reactive Gray–Scott dynamics, but is matched almost exactly by the no-memory ablation. Its existence is insufficient evidence for local learned association. The preprobe state also differs between histories. Diffusion shows large history state differences but nearly zero cue-specific interaction for this fixed readout.

**Disposition:** Close this specifically tested short-range chemical-association subline as **NOT SUPPORTED**, without generalizing to all artificial-life/chemical-memory systems. Do not feed into FORGE as positive scientific discovery or native model change.

## Original file identity and limits

- Isolated executable: `/mnt/data/e_research/e2m5/run_e2m5.py` SHA-256 `298d58beee28e5570afcad2d1197df41522e125b8eb50575372ccfa12fb26bbb`
- Isolated raw results: `/mnt/data/e_research/e2m5/results.json` SHA-256 `a4bbbe0fcd77afffe00ac0eca63183a8b59658704ea335410f9632d07357ad5c`
- Both files were created in an isolated session, and are **not committed in this documentation-only report**. Full original source dependencies include E2-P1 and E1-B modules. These digests do not constitute remote original custody or independently replicated qualification.
- Only FIT seeds; no separate sealed holdout or first-use event, no independent scientific reviewer, no explicit-memory capacity-matched comparator executed, no full CPU/RAM budget receipt. The closure decision is narrow, not a universal null.

## Next research recommendation

Move to separately isolated **E-B self-organizing artificial-life structures** instead of tuning the same chemical history loop. Before testing, freeze a minimal environmental/resource model, distinguish passive persistence from damage-specific repair, and include fixed-pattern, preprogrammed repair and random-rule controls. Keep E Research separate from Wingless/Yggdrasil and FORGE autonomous execution.

**Plain English:** The signal is real but is not caused by the extra chemical memory. The simpler chemistry does just as well. This test does not show learning.
