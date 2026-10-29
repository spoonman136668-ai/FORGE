# AC-14 — Authentic OGBench repair and real DTR public-development smoke: qualified results

**Gate outcome:** `AC14_AUTHENTIC_CROSS_OS_PUBLIC_SOURCE_SMOKE=PASS`. Original scientific admission remains **NO-GO**, and native Wingless/Yggdrasil training remains **NOT_RUN**.

## Exact authority and source boundaries

- Original upstream `CausalAILab/Causal-Gymnasium` at `c94e9a4cd3641588b6b8507e71ccee5c27032bdf`, tree `fd8d8a67c1fc7fa62274dc7e12fb1e77945632f0`, canonical committed DTR SHA-256 `e31eff82f862355057653d150967bb44a5ed57a6acaad57f7ecf2a551f6c6811`. Source was reverified before and after; no source checkout edits. Prior AC-13 exact source and authenticated PyTorch CPU wheel report was required before AC-14.
- New genuine package: PyPI `ogbench==1.2.1`, official `ogbench-1.2.1-py3-none-any.whl`, SHA-256 `597ac2207935e4edc46de5d5742e940a753f2329e18612e9cfe7f9e857435f83`, **8,940,331 bytes**; metadata verified against official version-specific `https://pypi.org/pypi/ogbench/1.2.1/json`. No source fork or stub; install from exact verified wheel with wheel-only dependencies into the existing isolated AC-11–13 venv.
- Executable qualification commit **`02d3f56466d468021f78f1a33fcefe2fd9830989`** on existing [FORGE draft PR #1062](https://github.com/spoonman136668-ai/FORGE/pull/1062), stacked on #1061. Exact [GitHub Actions run #40790619395](https://github.com/spoonman136668-ai/FORGE/actions/runs/40790619395) completed **SUCCESS** on Linux and Windows; branch push workflow intentionally SKIPPED to avoid a second expensive dependency installation. Existing focused AC-05 through AC-13 tests and AC-08 36-candidate portfolio guard remained part of the cross-OS job.

## Observed real package and source-runtime results

| Exact measured field | GitHub-hosted Linux | GitHub-hosted Windows |
| --- | --- | --- |
| Official wheel bytes and SHA-256 | 8,940,331, PASS | 8,940,331, PASS |
| Original `ogbench` wheel installation exit | 0, PASS | 0, PASS |
| New wheel/dependency installation wall duration | 4.295 s | 10.453 s |
| Unmodified original `DTRPCH,DTRSCM` import | **PASS**, exit 0 | **PASS**, exit 0 |
| Unmodified DTR import wall duration | 2.311 s | 4.532 s |
| Actual original-source smoke | **PASS** | **PASS** |
| Original-source public episodes | 2 | 2 |
| Original-source public actions | 4 | 4 |
| Original `ctf_do` forbidden by source PCH | YES, both seeds | YES, both seeds |
| Actual public smoke records | Identical to Windows | Identical to Linux |
| Frozen environment entry count | 111 | 96 |

**Exact public seed/observation/reward events, the same across both systems:**

- Seed `759011`: initial public observation `1`, stage-0 action `0` yields next observation `1` and nonterminal reward `0`; stage-1 action `1` terminates with reward `0`.
- Seed `759013`: initial public observation `0`, stage-0 action `0` yields next observation `1` and nonterminal reward `0`; stage-1 action `1` terminates with reward `1`.
- Every exported event uses only `stage, observation, action, next_observation, reward, terminated, truncated, valid_actions`. No original `info` dict, `env`, hidden `u`, graph, oracle or counterfactual consequence was passed to a learner. These are two predetermined connectivity policies, **not trained native agents**. No other source-owned episodes were executed in AC-14.
- FIT `760000..760007`, VALID `760100..760103`, DEV `760200..760203`, unfamiliar and sealed scientific first-use families were not consumed. No source-birth signature/witness, model promotion, controller dispatch or scientific admission is demonstrated by public smoke.

## Source-bound artifacts

Exact run #40790619395 uploaded separate ZIP artifacts with full AC-05–14 regressions, original-source checks, the full 36-candidate advisory report, AC-14 JSON, and dependency freezes.

| Platform | Artifact ID | ZIP SHA-256 | AC-14 report JSON SHA-256 |
| --- | --- | --- | --- |
| Linux | `12861197944` | `5ff42deff79f1cac03dda7eeaa87488e2ea8fa4887f91f69f8ab333ec9fb80c0` | `07b309c08cc6845987d051bc61007026b8142e83d9ce7d89376b064c1e8a6405` |
| Windows | `12861816875` | `1f652c92bd7bb6a2cfdfb1cf931a1bbcd003c4d19d6d12cc0c9e63ce32cc4d25` | `3bd1f1d04a70371e7216f4d6fb4297bedb9046b0f7c00fb7b1a5afee482b6dba` |

The two JSON files have different installation/runtime timings and environment-freeze hashes, but **public source-owned action/consequence records match exactly**.

## Science and next native-development boundary

This gate clears upstream dependency and runtime compatibility. It does **not** establish causal-learning performance, long-term retention, unfamiliar-family generalization, native algorithm advantage, or resource efficiency of Wingless/Yggdrasil. No native model consumed the public records during AC-14. It changes no protected main, queue, or source custody.

**AC-15 recommended:** With independently permitted **public development only**, build a narrow typed adapter that reads the already qualified eight-field source-public event tuple in a separate process; demonstrate parity for an existing native Wingless/Yggdrasil learner and properly fitted equal-information controls. First inspect the live native learner/checkpoint identity and deduplicate against ongoing work. Do not reuse protected originals or invent novel source birth; independently authenticate source owner/FSA/complete family ledger before scientific first-use. One original environment's public connectivity success cannot make W1 source custody automatically eligible.

`AC14_OGBENCH_PINNED_AUTHENTIC_WHEEL=PASS_BOTH_OS`  
`AC14_REAL_SOURCE_DTR_IMPORT=PASS_BOTH_OS`  
`AC14_PUBLIC_DEV_EPISODES=2_PER_OS`  
`AC14_PUBLIC_DEV_ACTIONS=4_PER_OS`  
`AC14_CROSS_OS_PUBLIC_EVENT_PARITY=PASS`  
`AC14_NATIVE_MODEL_TRAINING=FALSE`  
`AC14_SCIENTIFIC_FIRST_USE_AUTHORIZED=FALSE`  
`AC14_CONTROLLER_OR_ACCEPTED_RESEARCH_CHANGED=FALSE`
