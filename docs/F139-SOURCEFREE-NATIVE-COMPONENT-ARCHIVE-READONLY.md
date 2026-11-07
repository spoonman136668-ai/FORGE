# Source-free native component checkpoint ZIP verification

**Read-only FORGE advisory evidence; never a new owner, controller, queue,
model runner, experiment dispatcher, production adapter or promotion gate.**
This checker is independent of FORGE's existing
\`nativeevidence/model_lineage.py\` verifier for
\`research.portable-checkpoint.v1\`. **Do not convert a component fixture
into a canonical accepted model or infer scientific improvement from checksums.**

## Tested inputs (development only)

- Wingless [draft #465](https://github.com/spoonman136668-ai/Wingless/pull/465),
  source commit \`de84563daaffdfa85ea47a5b05050590b91f69de\`:
  exact prefix, uninterrupted and resumed Go fixture snapshots from CI
  [run #42235047953](https://github.com/spoonman136668-ai/Wingless/actions/runs/42235047953).
  It is a **two-event generated-source engineering fixture**, NOT the accepted
  state-former cognition architecture.
- Yggdrasil [draft #835](https://github.com/spoonman136668-ai/Yggdrasil/pull/835),
  source commit \`324ea724e83ec0889eb7a24438cdbaabbb01692e\`:
  true native eight-cell component checkpoint bytes, three committed
  episode journals, hashes and parent/child lineage from the existing
  Linux/Windows source-free development
  [run #42234713022](https://github.com/spoonman136668-ai/Yggdrasil/actions/runs/42234713022).
  This is **not** the accepted 16/7/9 cognition-consumer model.

Run offline on downloaded immutable GitHub Actions artifacts in an isolated,
unprivileged checkout. No source owner, model or network is invoked:

\`\`\`text
python -B -m nativeevidence.component_checkpoint_artifact --project Wingless \
  --source-sha de84563daaffdfa85ea47a5b05050590b91f69de --archive local-wingless.zip
python -B -m nativeevidence.component_checkpoint_artifact --project Yggdrasil \
  --source-sha 324ea724e83ec0889eb7a24438cdbaabbb01692e --archive local-yggdrasil.zip
\`\`\`

The external SHA is **required**. It must be authenticated independently
against original GitHub PR head and artifact run; its presence in the ZIP
does not independently authenticate ownership, origin or scientific first-use.
This parser checks exact ZIP inventory, limits, path safety, duplicate names,
checkpoint checksums, Yggdrasil native envelope integrity, source-free
role, hash-chained journal order, parentage, and false promotion flags.
It **never extracts, imports, unpickles or executes** any archive member.

The Linux/Windows Yggdrasil outputs have different checkpoint bytes. Neither
they nor Wingless have shown matched-control superiority, retention over
future generations, genuine unfamiliar transfer, accepted scientific first-use,
resource efficiency, or activation of a persistent accepted learning model.
A successful read-only report **cannot** reward FORGE optimizers or mutate
accepted refs. Any serious experiment must separately qualify original
source-owner authority, held-out/fresh-start controls, and science protocol.

The existing \`.github/workflows/native-task-feedback.yml\` tests this checker
on Linux and Windows, with adversarial synthetic ZIP/JSON/journal fixtures.
No workflow downloads artifacts across repos or accesses credentials.
