# AC-12 — Pinned upstream dependency triage and original DTR public development

**Declared before AC-12 source-execution workflow.** Parent results are AC-11 on [FORGE draft PR #1062](https://github.com/spoonman136668-ai/FORGE/pull/1062). This protocol does not authorize original scientific first-use.

## Frozen source and intent

The authentic original source is `CausalAILab/Causal-Gymnasium` at Git commit `c94e9a4cd3641588b6b8507e71ccee5c27032bdf`, tree `fd8d8a67c1fc7fa62274dc7e12fb1e77945632f0`; the DTR committed bytes SHA-256 is `e31eff82f862355057653d150967bb44a5ed57a6acaad57f7ecf2a551f6c6811`. Source identity and original untouched tree must be verified by the existing AC-10 check before package installation. AC-11 source-owned runs were zero due original module import failure after successful original setup requirements installation. Linux/Windows original package initializers import unrelated environments (MiniGrid, torchvision, OGBench). The *first actual exception module name* was not captured in AC-11 and must not be guessed.

AC-12 reuses AC-11's authenticated ephemeral venv, obtains the real Python traceback classification **without emitting private source state**, then permits precisely **one** upstream-import repair: if and only if the first missing Python module is `minigrid`, download the genuine PyPI wheel `minigrid==2.3.1` (`minigrid-2.3.1-py3-none-any.whl`, SHA-256 `6e841a9f95378abe1fdb053d4dfaead1613ceb2fa1e9548a8525882fbdb4f6f3`). Verify exact wheel bytes before installation, then allow only its genuine normal resolver dependencies (no forged module, fake environment, source edits, or arbitrary additional inferred imports). Minigrid 2.3.1 predates this test and advertises Python 3.11 support.

## Hard stop and bounded real public smoke

Attempt genuine `from causal_gym.envs.dtr import DTRPCH,DTRSCM` before and after the exact dependency addition, record actual first missing `ModuleNotFoundError` name, hash stderr, record install status/freeze. If another missing module or import failure appears, **STOP with a correctly named blocker**, rather than blindly adding packages (especially heavyweight torch/OGBench). No unapproved dependency chain, no frozen scientific source family consumed.

If—and **only if**—the original import succeeds, run at most two source-owned, public-development DTR episodes with seed `759011, 759013`, original `Task(learning_regime=do)`, original `do(lambda *_:0)` and `do(lambda *_:1)` for two stages, require original `ctf_do` permission denial, filter out raw `info` and all hidden `env`, `u`, graph, oracle and counterfactual access. Driver receives only explicit fields `stage, observation, action, next_observation, reward, terminated, truncated, valid_actions` from a separate subprocess. These fixed policies are **connectivity probes, not learned models**. No saved consequence labels beyond two public smoke seeds; FIT `760000..760007`, validation `760100..760103`, DEV `760200..760203`, and all unknown-family/sealed scientific source material remain untouched.

If a smoke subprocess fails midway, **unknown episode/action count** is recorded, not fabricated zero; only a validated complete two-episode result receives exact counts. No model training, benchmarking of native intelligence, F139 work item, controller/queue change, merge, first-use signature or scientific admission. Preserve negative results in the existing draft, and do not interpret package import or matched toy controls as superiority.

## Explicit qualification boundaries

Workflow uses the existing `.github/workflows/forge-ac07-remaining-sourcefree.yml` Linux/Windows matrix, runs AC-12 direct tests with existing focused regression, then executes the original dependency/version/wheel validation and writes `ac12-report.json` and `ac12-freeze.txt`. Both OSes must report original source identity and either a real PUBLIC smoke success **or** a definite dependency/import **BLOCKED** result; an exact-source engineering job may succeed while genuine DTR execution remains blocked. Semantic no-first-use flags are mandatory.

`AC12_ORIGINAL_SCIENTIFIC_ADMISSION=NO_GO`  
`AC12_NATIVE_MODEL_TRAINED=FALSE`  
`AC12_DEPENDENCY_CHOICE=PINNED_MINIGRID_ONLY`  
`AC12_NO_SOURCE_EDITS_OR_STUBS=TRUE`  
`AC12_CONTROLLER_OR_QUEUE_MODIFIED=FALSE`
