# F109 — failure-driven, resource-matched mechanism comparison

## Authentic negative intake and first-use boundary

Preimplementation F109 freeze was committed first at `9c9b1c7d42725070821266f10baf533ee9118652`, before implementing these alternatives or running the new diagnostic. Parent F108 exact source branch head: `8cc29268eee3915308b83c219f8c2031845c9646`. Ancestor drafts F99–F108 remain unmerged.

The runner validates F108's *real current-run* JSON against its SHA-256 receipt, independently recomputes its entire source-bound comparison from F107, and requires preservation of both negative findings: Wingless generated variant 36/48 versus unchanged parent 48/48 with **unmatched two-versus-one observation cost**; Yggdrasil 48/48 versus 48/48 with equal edge/state cost. These results are **never rewritten as positive**.

## New frozen challenge and genuinely different mechanisms

Wingless has 96 new public TRAIN pairs on seeds 66000–66031 and 48 separately frozen diagnostic pairs on 66048–66095. Each example contains four observations, a query depth and a public *source tag offset* metadata value (available to both arms). The paired sign flip affects only the evidence from the relevant offset-adjusted source tag. A 64-parameter conditional source-routing model learns an offset/query/tag attention map using 100 full-batch BCE updates, then at inference chooses a **single** evidence value to inspect. The 18-parameter prior query-depth-attention parent is trained for the **same** 100 updates on the same 96 new examples and also reads exactly one evidence value. The gap, if any, tests the added learnable source-routing architecture, not extra training or additional evidence reads. The offsets are public context, not answer labels, and source-matching ground truth is an independent validation control.

Yggdrasil uses 96 fresh public development pairs on seeds 66100–66131 and 48 separately frozen diagnostic pairs on 66148–66195. Three role-compatible four-hop paths share a target, while the two distractor paths deliberately have conflicting variable-slot links. It compares the original F103 differentiable soft slot-compatibility graph mechanism with a new **hard equality-gated variable-slot architecture** that reuses exactly the original F103 fitted role/scale parameters. Both receive the same 100 original frozen training updates, exactly twelve edges and four hops, and no new labeled fit available only to the alternative. This is a structural inductive bias, **not evidence of a separately trained new representation**. The exact coded graph oracle remains a separate truth control; neither candidate prediction calls it.

## Locked comparison

All new diagnostic seeds and thresholds were fixed in the first F109 commit. On 48 genuinely paired new examples per lane, record all candidate-only and parent-only wins, trained blind controls, negative false-positive rates, family subgroup accuracies, resource costs and all raw per-pair decisions. A positive restricted-public-development screen requires at least six additional correct pairs and at least six net paired wins, worst-family accuracy 0.60 or above, and equal/lower evidence or graph cost. **Negative screens preserve all results and do not constitute failing engineering CI.**

Any missing or nonmatching prior report, changed protected authority, mislabeled oracle controls, source SHA disagreement or unfair training budget fails closed. Training and diagnostic splits cannot overlap and diagnostic outcomes cannot be used to tune a model or freeze.

## What it does not establish

F109 is bounded, source-frozen synthetic development. The mechanisms and generators are authored here, not autonomously invented by a GPT research agent. No authenticated original Wingless/Yggdrasil scientific result, unrestricted real-world generalization or sustained self-improvement is asserted even if a public screen passes.

Reuse existing Ubuntu/Windows GitHub CI. No Codex, paid model APIs, ChatGPT Work tasks, Cloudflare writes, CKB-plane coupling, other repository mutation, additional scheduler, accepted-ref changes, protected first-use, optimizer promotion or native scientific dispatch. Keep the PR draft and preserve parent branch ancestry.
