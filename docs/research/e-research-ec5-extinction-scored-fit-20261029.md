# E Research E-C5 — extinction-scored common ecology FIT result (2026-10-29)

**Status:** Isolated local execution engineering PASS. Scientific adaptive/ecological advantage **NOT SUPPORTED**; first-use, validation, independent CI and FORGE scientific acceptance **UNVERIFIED**. Advisory record only.

## Actual execution

Derived E-C5 from E-C4's session-local script and reused 16×16 resource ecology, six FIT seeds 31000–31005, five arms, three training episodes per arm, and common dynamic evaluation schedule. Five arms × six seeds = **30 evaluations**, with deterministic replay PASS. All evaluation runs allowed **up to 300 actual organism decisions**; evaluation scores count **300 decision opportunities** with zero additional harvested resource after extinction or early episode termination.

Fixed one material training parity problem: policy-search now evaluates **three random candidate genome populations over one training episode each**, rather than 18 candidates; all arms receive 3 nominal training episodes. This **does not guarantee equal realized training organism-actions, equal explored parameter counts, or parity of selection information**. Greedy has no meaningful train step. Therefore scientific training parity remains UNVERIFIED.

## FIT outcome (medians across six seeds)

| Arm | Harvest | Harvest / 300 opportunities | Actual decisions | Births | Runs reaching 300 |
|---|---:|---:|---:|---:|---:|
| Evolve dynamic | 2.4975 | 0.008325 | 300 | 0 | 5/6 |
| Evolve static (dynamic evaluation) | 1.5335 | 0.005111667 | 272 | 0 | 3/6 |
| Random-parent dynamic | 0.535 | 0.001783333 | 249.5 | 0 | 2/6 |
| Greedy dynamic | **12.12** | **0.0404** | 300 | **6** | 6/6 |
| Three-candidate policy search | 1.26 | 0.0042 | 258 | 0 | 3/6 |

The score denominator is opportunities, so it does not reward early extinction. Unlike harvest per actual action, this metric captures the cost of unused opportunities after agents cease acting. **This is not evidence that all agents received the same effective training exposures.** Reproduction is allowed within episodes, though median births occur only for greedy.

Engineering: maximum absolute resource+energy ledger discrepancy **1.554548156867952e-11**; intermediate range checks in E-C4 episode source; replay of first row PASS. Source-derived run wall time ~1.9 seconds (not full CPU/RAM accounting). All six seeds are reused FIT, not new validation.

## Findings and scientific disposition

Dynamic evolution exceeds other evolving arms on descriptive development medians but is still approximately 4.85 times below the greedy arm by median opportunity-adjusted harvest. A different policy-search budget changes that comparator's outcome, illustrating selection-budget sensitivity. No held-out transfer, per-seed statistical claim, proof of open-ended capability, evolutionary learning advantage, or genuine adaptive intelligence follows.

**Scientific status NOT SUPPORTED** for this specific weak ecology as an emergent intelligence mechanism. The evidence favors terminating this tuned setting and exploring a qualitatively different coevolution/developmental mechanism. Do not promote candidate to FORGE model development as positive science.

## Provenance

- Session original source: `/mnt/data/e_research/ec5/run_ec5.py`, SHA-256 `73ebdfe86cecc64f83405846a46de66d7095936ce8ae79c08b2b401e5c95b300`.
- Session raw JSON: `/mnt/data/e_research/ec5/results.json`, SHA-256 `807f58a6362b6501db4d8502155c6b39c95ad727814a03ab83e37597f0a7df4e`.
- Neither executable nor original JSON is included in this documentation-only commit. Hashes alone do not authenticate remote source custody. Reproduction from the repository, independent scientific review and FORGE CI remain UNVERIFIED.

## Next

E-C6: perform **closure audit and prospective mechanism choice**, not additional hyperparameter tuning of this setting. Define a new ecological niche-construction/coevolution protocol that actually changes environmental affordances under interaction, against no-niche, static and conventional adaptation baselines. Remain independent of native architectures and FORGE autonomy.

**Plain English:** With extinction counted fairly, evolution still loses to the simple greedy strategy. There is no scientific reason to keep tuning this benchmark.
