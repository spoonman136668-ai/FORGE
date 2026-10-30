# E-D78 — Equal-exposure training-diversity transfer ablation (2026-10-30)

**Engineering execution PASS. Exploratory synthetic transfer improvement observed, not independent scientific qualification.**

## Protocol
Re-used E-D76's exact GRU (2,138 parameters) and 12-step history MLP (2,108 parameters), and original E-C2 synthetic source trace generator. Alternate synthetic oscillator/telegraph process from E-D77 was used only in the diversified training arm and evaluation, with **nonoverlapping seed ranges**: diversified training 48000–48009; alternate-family evaluation 47000–47015. Original training used 20 E-C2 sequences 45000–45019. Diverse training used 10 E-C2 sequences 45000–45009 and 10 alternate synthetic sequences 48000–48009. **Both** conditions received 20 unique source streams duplicated into 40 training examples (visible and 40-step masked), 35 full-batch Adam steps, learning rate .01, identical architecture/initialization per repeat, 3 independent initializations 780–782, and the same 3 previously used E-D77 mask schedules. Evaluation 16 alternate-family seeds per schedule. Thus sample count and number of updates matched, but FLOPs, training distributions, total information content, and performance measurement independence were not fully matched. This experiment intentionally includes *examples from the test process family* during diversified training: it tests domain coverage, **NOT untouched unfamiliar-family transfer**.

| Evaluation mask | GRU original MSE | GRU diverse MSE | History MLP original MSE | History MLP diverse MSE |
|---|---:|---:|---:|---:|
| shifted20 | .0950877580 | **.0798971291** | .0736680614 | **.0679777416** |
| longer50 | .0949248445 | **.0836071577** | .0879831770 | **.0765900965** |
| late25 | .1000169675 | **.0850860967** | .0837762978 | **.0740671442** |

GRU error averaged over schedules 0.0966765 original vs 0.0828638 diverse (~14.3% reduction); history MLP averaged 0.0818092 original vs 0.0728784 diverse (~10.9% reduction). Even after diversity, history MLP remains lower error in every schedule. Results use only 3 model initializations; user may interpret them as exploratory, not confidence-certified.

## Provenance and limits
Direct execution in local container. Source `/mnt/data/ed78_run.py` SHA-256 `f92e41eb2f2c3703c030ff1159ed2d2206598b1de489b1d23b38be9fa9e3edec`. Raw results `/mnt/data/ed78_results.json` SHA-256 `a2e636fd12837783bdf92bef7f571db828a8607f3f4f3c29cc303ee1f8c3d0ca`. Execution script reads original E-D76 source definitions and E-D77 synthetic-process function; source files are available locally, but exact executed bytes have not been remotely independently authenticated in FORGE. There is no source-pinned external benchmark, sealed family holdout, native Wingless/Yggdrasil learner, real policy reward, closed-loop transfer, independent FSA witness or FORGE acceptance authority.

**Scientific result:** Domain-diverse examples improve prediction on that same alternate synthetic domain; don't call this independent unseen-family generalization. No claim that GRU is superior or compute-efficient. Preserve as advisory only in draft PR #1194; avoid interference with FORGE autonomy and maintain independent official MiniGrid runner blocker #1245.

**Next E-D79:** Train with diversity limited to truly distinct source families and test on a third entirely excluded family, preserving exact example/update resources and stronger history controls. Report both gains and failures; original independent benchmark custody remains necessary.
