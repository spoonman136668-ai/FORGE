# E-D81 — paired seed-level diagnosis of E-D80 negative transfer (2026-10-30)

**Executed post-hoc analysis PASS; causal explanation NOT established.**

Original E-D80 results file SHA-256 `cf9fd53408ba52913efe149dd82334ea3d7333d8836c7212a1b5c97241ff06ad`. Reanalyzed the **actual retained per-seed MSE arrays** (three repeats, each with 16 evaluation seeds, under three reused masking schedules) by pairing original-only and two-family curricula for the identical model, repeat, mask and evaluation seed. Difference = two-family MSE minus original-only MSE; positive means diversified training is worse. No additional model optimization or new environment execution.

| Mask | GRU worsening / 48 pairs | GRU mean delta | History MLP worsening / 48 pairs | MLP mean delta |
|---|---:|---:|---:|---:|
| Shifted20 | 30 | +0.00167453 | 42 | +0.00757196 |
| Longer50 | 34 | +0.00364660 | 45 | +0.00905774 |
| Late25 | 30 | +0.00192609 | 46 | +0.00840055 |
| All | **94 / 144** | **+0.00241574** | **133 / 144** | **+0.00834342** |

**Interpretation:** The history MLP's negative effect is widespread across the paired retained evaluation seeds, rather than only a few large outliers. GRU deterioration is more heterogeneous but negative on average. This is compatible with a training-family distribution mismatch, but does not causally isolate domain mismatch, insufficient history, or model capacity. No matched capacity scaling experiment, history sweep or frequency-domain feature analysis was executed. Masks and initialization seeds reuse the same evaluation trajectories; **144 comparisons are dependent, not 144 independent experimental trials**.

Executed analysis source `/mnt/data/ed81/paired_analysis.py`, SHA-256 `d80d115ded9bd57bf008ec9c515dd1ef0b1461b14fc2a1f78fc4d5729a741ee6`; derived numeric JSON `/mnt/data/ed81/paired_analysis.json`, SHA-256 `f96746e89088d5f65281181e58ed40af5c10bae3422782c12faffed18ae9a076`. These are locally created, **not independently authenticated remote scientific artifacts**.

**Next E-D82:** construct a bounded factorial intervention varying history span and model capacity with unchanged training/test source identities, same sequence budget, frozen evaluations, and full compute accounting. Require ordinary independent scientific qualification before FORGE research selection or native Wingless/Yggdrasil integration. Original MiniGrid execution and E-D52 repository custody remain separately blocked. No FORGE autonomy or controller changes.
