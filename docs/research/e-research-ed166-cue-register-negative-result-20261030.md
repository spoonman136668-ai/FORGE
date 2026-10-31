# E-D166 — Authentic cue-register ablation: no reward improvement

Draft FORGE PR #1194 source SHA `d194cdb2aa4374e1d7ce7f457b15f6604fa7a317`. GitHub Actions [run 41148732606](https://github.com/spoonman136668-ai/FORGE/actions/runs/41148732606), Linux job `124381442399` PASS; Windows job `124381443184` IN PROGRESS at original observation. `PASS_ENGINEERING_LOOP_ESCAPE_CUE_ABLATION` in authenticated Linux log.

| Exposed seed | Frozen loop escape actions / reward | Cue switch actions / reward | Delta |
|---|---|---|---|
| 84000 | 47 / 0 | 47 / 0 | 0 |
| 84001 | 21 / 0.9776331360946745 | 21 / 0.9776331360946745 | 0 |
| 84002 | 21 / 0 | 54 / 0 | 0; +33 actions |
| 84003 | 38 / 0 | 38 / 0 | 0 |

For seed 84002, original action hashes: baseline `db5ae78cdff640f9556c0010a178b96ddd7048da989a71b848587d2b4a4fff6d`; candidate `a656eab66a3ad43ae7bec2a54ec9a64dd545c686bb8de4ee8447a40e4df8f229`. For seeds 84000,84001,84003, action traces match their respective baselines. Cue register 5,5,6,5 on seeds 84000..84003, **none verified as original starting-room cue**.

**Decision: REJECT cue-switch variant for advancement on current evidence.** Preserve E-D161 loop-escape candidate as the stronger engineering baseline only; do not confuse engineering selection with scientific acceptance or FORGE model promotion. Four exposed seeds, no learned memory or independent holdout transfer. Next work should address reliable observation-only original-cue localization and genuine matched memory-conditioned rewards, not repeat cue-switch variants. No native Wingless/Yggdrasil, controller, or autonomy changes.