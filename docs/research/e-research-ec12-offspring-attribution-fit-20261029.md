# E Research E-C12 — offspring-specific habitat inheritance FIT (2026-10-29)

**Engineering PASS; offspring benefit NOT SUPPORTED; evolved construction UNVERIFIED.** Isolated session execution, 216 trajectories. No scientific first-use, FORGE CI, FSA acceptance, native-model change or autonomy modification.

## Scope and execution
Reused E-C11 deterministic fixed-site ecology without changing underlying physics: six FIT seeds (41000–41005), three sites, three viable supply/metabolism configurations, four arms (persistent construction; habitat reset at birth; construction-cost sham; no-cost sham), 300 steps each = 216 trajectories. Recorded *parent vs offspring* post-birth resource harvest separately, plus offspring-alive steps. Both parents and offspring receive the same fixed greedy first-come harvesting rule; **parent acts first** in each timestep. No selection, genetics, learned construction decisions, movement or independent holdout.

All 216 trajectories passed conservation/invariant assertions (maximum ledger discrepancy 1.149080830487037e-13) and first-case deterministic replay. Exact paired first-birth times match before habitat-reset intervention. Resource supply remains externally renewed. This is a FIT attribution measurement, not unfamiliar transfer or independently qualified science.

## Median persistent-minus-reset postbirth harvest across 18 FIT seed/site pairs per configuration

| supply / metabolism | birth-capable pairs | parent postbirth difference | offspring postbirth difference | offspring positives among birth-capable |
|---|---:|---:|---:|---:|
| 0.018 / 0.025 | 8/18 | 0 | 0 | 0/8 |
| 0.008 / 0.012 | 13/18 | +0.1806299148 | 0 | 0/13 |
| 0.018 / 0.012 | 18/18 | +0.6638378517 | 0 | 0/18 |

Offspring-alive-step difference median 0 for every birth-capable subset. Apparent aggregate harvesting gains from E-C11 are **entirely parent-attributed within this fixed parent-first harvesting implementation**. This is not a scientifically general statement about niche-construction inheritance; the parent may consume an incremental resource before offspring have access, and the model has only two agents at one site.

## Provenance
Local executable `/mnt/data/e_research/ec12/run_ec12.py` SHA-256 `1dd16e54deb6d6bfea3cd20cbac5f3a10c1b3aeebb4a790524743291fd749d32`.
Local raw results `/mnt/data/e_research/ec12/results.json` SHA-256 `b98e433cdab8cde901233d333bdd3d6edff1d2923e0ccccd4c97439a11d11ed9`.
The original script and JSON remain session-local and are not committed here. This document is an advisory index; independent repository-only replay and original-evidence authentication remain UNVERIFIED.

## Scientific decision / next gate

**Do not claim offspring benefit or adaptive niche construction.** E-C13 should test a prospective offspring-access control (alternate action order, separate spatial feeding opportunity with same source budget, and equal parent/offspring observation and energy costs). If the offspring result depends only on a designed feeding order, classify it as an ecology artifact and close the single-site inheritance subline. A genuine evolutionary construction policy and unfamiliar transfer require a separate experiment and approved source/first-use custody.

**Plain English:** Construction helped the parent harvest more, but not its child in this test. The parent always gets first access to food, so that fixed schedule is an important confound.
