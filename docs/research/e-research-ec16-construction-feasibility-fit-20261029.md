# E Research E-C16 — FIT construction affordance feasibility (2026-10-29)

**Engineering PASS; evolutionary construction advantage NOT SUPPORTED; scientific qualification UNVERIFIED.** Not a FORGE-run experiment or authorized first-use. No model, controller, queue, owner, promotion or autonomy modifications.

## Executed experiment

Executed local Python script `e_research/ec16/run_ec16.py` using exactly source-derived E-C7 20×20 resource ecology and fixed greedy harvesting policy. One first-agent construction action at t=10 was paired with a *same-energy, same-material, same-lost-action* sham that omits only the habitat increase. Construction costs .08 energy, .12 material, habitat increment .22, decay .998 and replenishment multiplier (1+0.7h). Six existing FIT seeds 41000–41005, two conditions, three horizons (80,160,320) = **36 trajectories**. These are reused development worlds, not independent test cases. No organism learns or evolves in this diagnostic.

**Numerical:** exact seeded replay PASS; every-step existing nonnegative energy/resources and habitat/material checks PASS; max conservation residual **5.333617991709616e−10** (below existing 1e−7 tolerance). Wall duration ~1.33 seconds; process peak RSS ~96,392 KiB. No independent CI or scientific qualification.

| Horizon | Median (build minus same-cost sham) total harvest | Birth-count median difference | Median survivor difference |
|---|---:|---:|---:|
| 80 | 0 | 0 | 0 |
| 160 | −0.17880243097 | 0 | 0 |
| 320 | 0 | 0 | 0 |

**Per-seed build minus sham harvest (320 steps):** [0, 0, 0, −3.6076, +8.9700, −6.3700] (rounded). Thus a zero median masks strong heterogeneity; construction was sometimes useful but did not reliably improve the matched outcome. These six reused FIT observations cannot justify a statistical population claim or general null. A beneficial `h` multiplier is engineered, not an acquired ability. The paired conditions can diverge downstream in realized actions and ecology, which are explicitly outcomes, not matched post-intervention trajectories.

## Original-byte hashes / custody limits

- E-C7 physics dependency `e_research/ec7/run_ec7.py` SHA-256: `04c81eaaa599030824f789a485359c1ea1d7c0335928481e7084ba4157be8375`.
- E-C16 executable `e_research/ec16/run_ec16.py` SHA-256: `1ac494315ff7784ecb4719cffb7896285a56699ef5aec9c0c7fc102a538619f7`.
- E-C16 JSON raw `e_research/ec16/results.json` SHA-256: `5f35b96436ecdabda4177ae11ca1354ad8519957874f70b3c91e88ad84f9ad65`.

These originals are **session-local** and are not part of this documentation-only commit. Reported digests alone do not authenticate original evidence or make a FORGE branch independently reproducible. No sealed HOLDOUT, first-use witness, independent reviewer or native FORGE science acceptance.

## Gate decision

For the current FIT configuration, construction does not establish a repeatable gain over an otherwise identical paid sham. Do **not** spend more selection compute trying to tune this exact ecology into a claimed intelligence success. The next useful gate is **E-C17 closure and mechanism portfolio decision**: preserve this result as a negative/heterogeneous finding, evaluate whether a distinct *causal environmental modification* world should replace this reward-linked habitat equation, and only then predefine genuinely unfamiliar transfer and strong baselines. No production changes.

**Plain English:** Building sometimes helps and sometimes hurts, despite paying the same cost either way. There is no reliable net benefit for evolution to discover in these current development tests.
