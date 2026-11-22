# CKAD native persisted training artifacts — receiving contract

This extends the existing FORGE CKAD campaign request. Yggdrasil remains the native
trainer and scientific owner. Its current A-F campaigns run as frozen full experiments;
FORGE's requested stage is not yet a resumable Yggdrasil-executable job.

The new read-only receiving function inspects five actual files under one
non-symlink directory: input and output native checkpoint, observed evidence,
frozen control receipt, and held evaluation receipt. It verifies file identity,
canonical source-mode / development-only native checkpoint structure, source-
bound request, frozen resource budgets, byte-level input continuity and
independent previously held receipt SHA-256 after the first stage.

It does not call a model, write files, train, schedule a task or alter the F139
owner. Its explicit FALSE flags prevent a structural checkpoint check from
being described as native cold restore, authenticated original execution,
scientific acceptance or a permission to deploy.

Next integration: Yggdrasil/CKAD must independently qualify a true source-
authenticated stage runner and owner receipt, use a fully qualified current
native learner SHA/tree, and perform the real NativeCumulativeLearner.restore
on cold checkpoints. FORGE can then observe those receipts using its existing
SingleOwner workflow without adding a competing controller.
