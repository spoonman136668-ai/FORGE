# F103 — learned Yggdrasil variable binding (public development only)

**Frozen prior to implementation:** commit 2704d9dd27637f85e7d6e42943853badf92eb67b contains the preregistration; parent F102 exact head is 6f9a64ae9cd9b7631f6296268e98120b7f4cafb2, retaining ancestry back through F101, F100 and F99. The candidate is F100's separately reserved Y100-C2, not a relabel of F102's Y100-C1.

## Question

Can a 20-parameter trained recurrent graph composer maintain variable binding across four hops, even when both members of a counterfactual pair have identical edges, query roles and edge-role codes, but one variable argument breaks unification? Does it remain invariant to alpha-renaming and node relabeling?

This is a deliberately restricted synthetic public-development feasibility task, not native Yggdrasil research, independent cognition, accepted science or unseen-domain transfer.

## Frozen cohort and model

The exact development seeds and thresholds are in reference/research-intake/f103-yggdrasil-variable-binding-freeze.json, locked before any F103 model implementation. Three disjoint sixteen-seed blocks, each with three instances per seed, produce 144 paired cases: 96 training and 48 later public diagnostic cases. Each has two competing role-correct four-hop paths, of which one remains binding-inconsistent. The negative breaks exactly one of the otherwise binding-consistent main-path arguments without changing topology or roles.

The candidate propagates differentiable weighted messages keyed by node and variable slot. Learned 4x4 role compatibility and learned matched/mismatched slot gates determine mass at the target; the readout is also trained. Slot identity is a public one-hot representation and a dot-product comparison, not ground-truth target labels or an oracle invocation. Full-batch BCE gradients update 20 parameters for exactly 100 fixed steps at learning rate 0.2. The model is not a generic free-form language model.

An independently trained role-aware variable-blind control gets the same role parameters and optimizer budget. Additional controls disrupt slot consistency, always answer yes, and use the exact coded oracle only as a separate control/ground-truth verifier. Accuracy is paired: a correct pair requires accepting positive and rejecting its one-argument negative.

## Acceptance and limits

Report full control scores, worst query-role group, worst broken-binding position, alpha-renaming and node-relabelling agreements, false-positive rate, and exact frozen SHA. Public screen minima are 0.75 paired accuracy, +0.15 over blind, 0.60 worst group, and 0.95 alpha-renaming agreement. Always retain negative findings if those thresholds fail. No post-assessment tuning.

The F103 workflow uses existing native hosted Ubuntu/Windows CI and required full Linux/Windows regression, plus F103 adversarial tests. Do not create a second scheduler, alter Cloudflare/CKB-plane or production repositories, trigger Codex, add paid inference, enable scientific first-use, or promote policy/accepted refs. Leave this branch as a draft, and reconcile F99/F100/F101/F102 ancestry before any protected merge.
