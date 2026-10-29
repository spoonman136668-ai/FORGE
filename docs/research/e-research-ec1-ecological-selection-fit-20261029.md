# E Research E-C1 — ecological selection FIT prototype (2026-10-29)

**Status:** Engineering FIT smoke **PASS after corrective rerun**; ecological coevolution, acquired novel capability and unfamiliar-family transfer **UNVERIFIED**. No FORGE-native FSA, scientific first-use, independent acceptance, optimizer promotion, controller/owner/queue or native model changes.

## Experiment actually executed

Isolated Python stdlib 24×24 toroidal grid, renewable spatially heterogeneous resources (bounded [0,1]); 12 agents per population; 6 action-policy coefficients; local and neighboring resource observations only; move/harvest actions. Five selection generations of 80 steps each, then an 80-step FIT evaluation using shifted development resource seeds. Twelve FIT seeds 31000–31011. **72 arm×seed runs** (each includes five training episodes and one evaluation episode).

Arms: evolving policy coefficients + changing resource schedule; evolving + static resource schedule; random parent sampling + changing schedule; fixed policies + changing schedule; greedy reactive policy + changing schedule; evolved policies + reversed/shuffled resource schedule. Mutation/selection is applied **between episodes**. This is **not a population of organisms reproducing continuously within an ecology**: reproduction, genuine coevolution and open-endedness remain to be implemented/qualified.

### Engineering failure and correction

The first run conserved the accounting ledger but **allowed negative-energy agents to continue acting**. That is a simulation validity **FAIL** despite exact accounting. Corrected zero-energy inactivity and clipped the final expenditure to available energy; adjusted the expense ledger and reran the same FIT conditions. Corrected rerun: seeded replay PASS; no negative resource or energy; maximum per-arm accounting residual < 1.89e−10. There are no individual-death reproduction transitions in the prototype.

### Corrected FIT evaluation descriptive medians (12 seeds per arm)

| Arm | Harvested resource | Surviving agents / 12 | Active organism-steps |
|---|---:|---:|---:|
| Evolving + dynamic | 26.09775 | 5.5 | 783.5 |
| Evolving + static | 44.93100 | 7 | 798 |
| Random parent + dynamic | 0.86750 | 0 | 366.5 |
| Fixed population + dynamic | 2.30275 | 0 | 449.5 |
| Greedy reactive + dynamic | **56.08** | **12** | 960 |
| Shuffled schedule + dynamic | 52.16325 | 8 | 846.5 |

**Interpretation:** The simple greedy policy outperforms the evolving-dynamic arm on descriptive medians. Dynamic ecological selection is not proven superior to static selection. Several weak controls go extinct early, so nominal fixed episode budgets are **not equivalent to effective acting steps**. The arms are diagnostic, not yet balanced for opportunity-adjusted performance. The shuffled schedule arm is not independently randomized ecological history, simply deterministic schedule reversal. Evaluation uses altered resource seed/geometry within the same generator—not a qualified unfamiliar challenge family. No confidence intervals or inferential statistical superiority test was performed.

**Scientific decision:** NO novel intelligence claim, NO advantage for dynamic evolution, NO FORGE selection eligibility. Treat as an engineering baseline exposing shortcomings in task definition and selection controls.

## Source identity (original session, not committed in this docs-only PR)

- Standalone source `/mnt/data/e_research/ec1/run_ec1.py`, SHA-256 `bf2105c2d6ee0998b13af63559bc6024a0445388fe8df64c32e1f838483cefbb`
- Raw `/mnt/data/e_research/ec1/results.json`, SHA-256 `6577f95482eb4c5d1d14f83fdd93927e813bf3e476526c40491d77c1be652038`
- Corrected rerun locally ~21.18 wall seconds; no full CPU peak RAM/environment custody receipt.

Neither executable nor raw JSON was added to this advisory GitHub branch. Hashes without actual original bytes are *not independently authenticated custody*, source-birth proof or reproducibility from FORGE alone. No CI or native FSA replay.

## Next gate E-C2

Fix episode-opportunity confounding, implement actual energy-limited death/reproduction and parent-selection budgets; use a matched simple-policy search/evolution baseline and a resource schedule that poses a genuine adaptation challenge. Run only fresh FIT seeds or clearly relabel reused FIT; preserve freezing/first-use constraints before any validation/holdout. Prefer a minimal architecture-independent environment, do not copy Yggdrasil/Wingless implementation or interfere with FORGE autonomy.

**Plain English:** This first simulation works and accounts for resources, but a straightforward greedy agent does better. We're still testing the ecology itself, not discovering intelligent organisms.
