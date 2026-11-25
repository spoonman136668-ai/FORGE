# FORGE — an autonomous scientific research and AI development platform

**A research laboratory in software, built to discover, test, preserve and improve ideas for artificial intelligence.**

FORGE is not a chatbot, a single AI model, or a replacement for a scientist. It is the machinery around AI research: a system that can organize experiments, try different approaches, compare their results, keep a record of what happened, and use that evidence to decide what is worth investigating next. The long-term goal is to make that cycle increasingly autonomous without allowing the system to decide for itself that an unproven result is a scientific breakthrough.

**Current status (source reviewed November 25, 2026):** The public repository contains runnable development tooling, a native workstation controller implementation, experimental training and architecture-search tools, and scientific custody/qualification components. The older Go planning and replay components remain advisory. The latest source includes the multi-generation Blueprint Lab and local HTML dashboard (F139 Gate 22). This is not a claim that every component is installed, connected to a live model, independently scientifically qualified, or authorized to operate on protected data. See [what is actually demonstrated](#what-is-actually-demonstrated).

## Contents

- [Why FORGE exists](#why-forge-exists)
- [What FORGE actually does](#what-forge-actually-does)
- [How the pieces fit together](#how-the-pieces-fit-together)
- [The research lanes](#the-research-lanes)
- [How FORGE decides what to try](#how-forge-decides-what-to-try)
- [The Blueprint Lab](#the-blueprint-lab)
- [Learning from results and improving FORGE itself](#learning-from-results-and-improving-forge-itself)
- [Evidence, scientific integrity and safety](#evidence-scientific-integrity-and-safety)
- [What is actually demonstrated](#what-is-actually-demonstrated)
- [Getting started with the public source](#getting-started-with-the-public-source)
- [Source map and further reading](#source-map-and-further-reading)

## Why FORGE exists

Developing a fundamentally different kind of AI requires more than inventing a clever mathematical rule. A researcher has to test whether that rule actually improves learning, whether it works on unfamiliar problems, whether earlier knowledge survives new training, whether it costs too much, and whether a simpler competing method can do just as well. The answer may be negative. That negative result is valuable if it prevents the next researcher from spending a week repeating the same mistake.

Ordinary development tools can compile software and tell you whether a test passed. They do not, by themselves, decide which hypothesis is worth testing, remember the lineage of a trained model, enforce a fair scientific comparison, or distinguish genuine learning from a convenient benchmark result.

FORGE is intended to close that gap. It is a structured research platform that brings experiment planning, execution, evidence management, evolutionary search, and improvement of the research process itself into one coherent architecture.

Imagine a laboratory with an experiment notebook, a work coordinator, a collection of instruments, a library of previous attempts, and a skeptical reviewer. FORGE implements parts of each of those roles in software. The instruments can change; the requirement to account for the evidence does not.

The broader research direction is toward AI systems that can learn from experience, retain and build on knowledge, understand the consequences of actions, reason in new situations, and adapt without having to be rebuilt from scratch every time. In particular, Wingless and Yggdrasil pursue independent non-transformer, non-next-token cognitive foundations. FORGE is the platform for investigating such approaches, not proof that those capabilities have already been achieved.

## What FORGE actually does

In practical terms, FORGE has several distinct jobs.

| Job | What that means in everyday language |
| --- | --- |
| Plan research | Decide which existing research proposal is worth considering next, within the permitted budget and evidence rules. |
| Freeze an experiment | Record the exact code, inputs, seeds, conditions, comparison method and success criteria before the relevant evaluation. |
| Run development work | Execute supported, bounded tests or training jobs and collect results rather than relying on someone saying they ran a test. |
| Compare alternatives | Examine accuracy, failure, runtime, memory or other selected measurements; keep useful trade-offs instead of declaring the first apparent winner best. |
| Keep research history | Preserve failures, results, source identity and saved training state so later work can build on the right evidence. |
| Recover safely | Reconcile interrupted or uncertain work instead of automatically running it a second time. |
| Improve research methods | Use permitted historical feedback, search and bounded experiments to propose better ways of choosing and conducting research. |
| Protect acceptance | Keep development results separate from independent scientific acceptance and changes to protected code or deployed models. |

A typical intended research cycle looks like this:

1. Identify a question, such as whether a new learning rule can adapt to changed conditions without forgetting an earlier task.
2. Select an eligible method, record the starting model state and define an experiment with a fair comparison.
3. Run the bounded work, capture the results and retain the failures as well as any promising outcomes.
4. Compare the candidate against the baseline and check the cost of obtaining the result.
5. Preserve the checkpoint and receipts if eligible; reject or quarantine invalid or inconclusive evidence.
6. Use the result to choose a follow-up experiment, design a different candidate, or stop investigating a failed direction.
7. Separately qualify any proposed change to an accepted model or production research policy.

Some of these steps are implemented as runnable development tools today; the full protected scientific cycle requires additional original-source, owner, witness and evaluation evidence. The point is to reduce repetitive manual work while keeping the scientific decision defensible.

## How the pieces fit together

FORGE has multiple layers with intentionally different responsibilities. A layer that can suggest an action does not automatically have permission to execute it.

```text
  Research questions / approved development work
                     |
         Planning and candidate selection
          (proposals, not permission)
                     |
       +-------------+----------------+
       |                              |
  F139 owner controller         Bounded development lab
  approved tickets/receipts     experiments and sweeps
       |                              |
  Authorized worker             Isolated training trials
       |                              |
  Controller SQLite journal     Evidence ledger + checkpoint vault
       +-------------+----------------+
                     |
         Review, comparison, diagnosis
                     |
         Next candidate / draft change
                     |
      Separate scientific acceptance and
       authorized source/model promotion
```

This is a conceptual map of responsibilities, not a claim that every arrow is an activated integration.

### F139: the workstation controller

The [F139 controller](f139/local_controller.py) is the part designed to keep approved work moving without a person repeatedly launching each individual task. Its design places one owner controller on a Windows workstation. It uses a local SQLite database (a small persistent database on disk) to keep track of the queue, source identity, budgets, active intent and evidence history.

GitHub Actions workers can carry out supported source-bound tasks and return receipts. They are workers, not the independent owners of the research schedule. The controller uses a fixed workflow and authenticated GitHub access; source and ticket checks prevent arbitrary issue text from becoming a command. The initial design supports bounded development work rather than unrestricted scientific first-use.

A particularly important feature is **write before dispatch**. Before starting work, the controller records its intention durably. If a network request times out or a computer crashes after a possible start, FORGE must establish what actually happened. An uncertain start remains in a protected state rather than being blindly submitted again. That prevents wasting compute and, more importantly, accidentally repeating a once-only scientific evaluation.

The workstation being off pauses this design; installation and source transitions require their own authorization and evidence. Changing repository main is not the same thing as updating the running owner. See the [controller design](docs/F139-UNIFIED-FORGE-CONTROLLER.md) and [Windows operations guide](f139/README-WINDOWS.md).

### Development experiment engine

The [experiment runner](f139/nci04_experiment_runner.py) accepts structured experiment descriptions and approved runner profiles for Python scripts, Python tests and Go tests. It prepares temporary workspaces, applies time limits, collects metrics and records source-bound receipts. The [hardware-aware runner](f139/nci04_hardware_trainer.py) detects CPU resources and optionally PyTorch/CUDA availability, constructs budgets and passes device/thread hints to experiments.

In everyday terms, this is the bench where a research idea is actually tried. A machine with a GPU does not automatically mean a particular experiment uses the GPU; that depends on the implementation and its verified execution. Budgets and process timeouts are not a replacement for OS-level resource and security isolation.

The [research driver](f139/nci04_research_driver.py) joins scheduling, bounded experiment execution, evidence recording and checkpoint storage into a single local research tick. Its built-in benchmark mappings currently target LLM-Experimental, GLM-WorldModel and AGI-Kernel. The scheduler supports six named tracks, but the existence of a name or a local benchmark does not establish an integrated production learner for that track.

### Evidence and saved model states

The [research evidence store](f139/nci04_evidence_store.py) records results in an append-only JSONL file. Each record is linked to the previous record by a SHA-256 digest (a digital fingerprint), allowing the reader to detect inconsistencies such as changed or reordered records. This is separate from the owner controller's database.

The [checkpoint vault](f139/nci04_checkpoint_vault.py) stores eligible experiment state by its exact byte digest, checks it on reload, deduplicates identical state and enforces a disk quota (512 MiB by default). A checkpoint can be the learned weights or other state produced by a trial. This allows a later investigation to start from an exact saved state instead of guessing which model was trained.

The vault does not automatically make the stored state the accepted model. Keeping a result, being able to reload it, and proving that a learner retains or transfers useful knowledge are three different things.

### FORGE Scientific Authority (FSA)

FSA is the FORGE-native scientific authority design and associated custody, authentication and admission controls. Its purpose is to distinguish an interesting development candidate from a properly authorized scientific original, a once-only evaluation, or an accepted change.

The repository contains source implementations and qualification components for parts of this authority, including a [Cloudflare D1 storage primitive](fsad1/README.md). That storage component is not the F139 controller and its documentation explicitly marks it as not deployed. A successful local signature or structural check does not independently establish owner identity, witness custody or authorization. A complete live FSA service and protected scientific execution must be established by separate evidence.

## The research lanes

FORGE deliberately separates research tracks so a result from one type of system does not silently overwrite another. These are research purposes, not a list of fully trained models shipped with the public repository.

| Track | What the research is about |
| --- | --- |
| Wingless | Predictive causal state: explore how a system can learn useful relationships and consequences from observations and actions, without relying on a conventional next-token language model as its foundation. |
| Yggdrasil | Local and distributed learning: explore whether interacting learning components can develop specialization, retain knowledge and collectively adapt without destroying previously learned capabilities. |
| TTT-Hybrid | A distinct hybrid track for investigating test-time adaptation and combinations of learning/memory mechanisms, under its own model and evidence boundaries. |
| LLM-Experimental | A separate development track for experimenting with conventional language-model-related methods and comparative learning techniques. |
| GLM-WorldModel | A development track for predictive models of changing environments or system state. |
| AGI-Kernel | An exploratory track for general-purpose learning and reasoning primitives, including continual-learning mechanisms. The label is a research aim, not an assertion of artificial general intelligence. |

The original F139 controller and the experimental scheduler have different supported lane sets; the latter's six names are defined in [the multi-lane scheduler](f139/nci04_multi_lane_scheduler.py). Do not infer live six-lane native model training from that registry. The native learner projects retain their own architectural identities, checkpoints and acceptance rules.

FORGE is not committed to one mathematical mechanism for all intelligence. It is intended to make different methods testable under comparable scientific standards while keeping each model's foundations intact.

## How FORGE decides what to try

Running everything is usually a poor research strategy. There are too many possible changes and only so much compute. FORGE includes several complementary methods for making exploration more productive:

- **Frozen portfolio planning:** the Go [planner](planner/plan.go) ranks proposed candidates using stated impact, novelty, robustness and cost values. It checks the frozen input identity, rejects invalid inputs, and emits advisory decisions. Its score is a prioritization rule, not empirical proof of scientific benefit.
- **Dream-RSI:** research-policy optimization using appropriately authenticated historical outcomes and separate training/validation conditions. Its intended role is improving how the platform recommends future research, not giving itself permission to execute or accept science.
- **Shinka-inspired Pareto and evolutionary portfolios:** retain different promising families and compare competing objectives instead of collapsing all research quality into a single number.
- **ThetaEvolve:** propose bounded parameter changes based on eligible training inputs. A parameter proposal must be tested before operational adoption.
- **Promptbreeder and GenEnv:** propose alternative research/prompt or environment designs; those ideas require their own evaluation and must not redefine the protected test after seeing its answer.
- **Evidence-conditioned allocation:** the local development scheduler can respect lane budgets, back off repeatedly failing tracks and prioritize less explored eligible work or recent evidence.

The five existing optimizer libraries are connected to a [read-only shadow runner](docs/F139-EXISTING-OPTIMIZER-SHADOW-RUNNER.md). Shadow means the methods can compute recommendations on independently supplied, pinned evidence without changing the active policy or starting new experiments. The required original evidence and independent audit inputs are not supplied by the public source alone. Prospective evidence of a better research-selection policy remains a separate requirement.

## The Blueprint Lab

The [Blueprint Lab](f139/nci04_blueprint_lab.py), introduced in F139 Gate 21, is an experimental workbench for trying different model structures or learning rules. A blueprint describes an idea in a form the runner can understand, rather than requiring every new experiment to become a separate platform.

There are two execution modes:

- **Composable built-in:** change parameters such as learning rate, state size, decay, clipping, regularization and one of the supported state-update rules. The starter experiments include linear dynamics, slow/fast adaptation, Hebbian-style updates and an elastic consolidation rule.
- **Custom script:** run a researcher-supplied Python entry point from a temporary copy of a workspace, providing the blueprint and seed/output conventions. It can accommodate experiments beyond the starter formulas.

The built-in examples are small controlled development experiments, not full training of Wingless, Yggdrasil or another production model. They measure prediction error under changing conditions and error on an earlier task after adaptation, along with state size and elapsed time.

Custom scripts must be trusted. A temporary working directory, environment-prefix filtering and a subprocess timeout do **not** make arbitrary Python safe to execute on a credentialed machine. The current custom-script code also takes metrics supplied by that script; the resulting receipt is not independent verification that the metrics are scientifically valid. Use an appropriately isolated, explicitly authorized environment for any new executable experiment.

### Trying multiple generations of ideas

The [multi-generation lab CLI](f139/nci04_lab_cli.py) introduced in Gate 22 can run a wave of candidates, keep the non-dominated candidates, breed another wave from a configured search space and repeat within a finite generation limit (1–10). It records verified and negative trials and emits a leaderboard. The starter pack uses total mean squared error (lower is better) and serialized state size (smaller is better) as its two objectives.

Why use more than one measure? Suppose three hypothetical learners produce the following results on the same development task:

| Candidate | Prediction error (lower is better) | State size (smaller is better) |
| --- | ---: | ---: |
| A | 0.10 | 100 bytes |
| B | 0.08 | 180 bytes |
| C | 0.12 | 200 bytes |

A is smaller than B, but B has lower error. Both are worth keeping for consideration. C is worse than A and B on both measures, so it adds no advantage for these objectives. This is a **Pareto frontier**, meaning the set of alternatives that no other measured candidate beats on every chosen dimension. The numbers above are illustrative, not FORGE benchmark results.

FORGE's [Pareto comparator](f139/nci04_pareto_comparator.py) implements this type of comparison. It can guide exploration, but a leaderboard is only as sound as its measurements, budgets, controls and data splits. Repeated development sweeps cannot be treated as fresh protected evaluations.

### Reading the results

The Gate 22 [HTML report exporter](f139/nci04_report_export.py) reads the experiment ledger and checkpoint vault, checks ledger integrity and generates a self-contained local HTML report. It shows aggregate counts, method-family summaries, recent trials (up to 100), recent checkpoints (up to 50), and negative outcomes. It is intended for a researcher who wants to see what happened without manually reading raw JSON files.

It reads the evidence store; it does not start an experiment or change the controller. The export writes the requested HTML file.

## Learning from results and improving FORGE itself

There are two different kinds of improvement in this project.

**Improving the models under investigation:** a new learning rule, model component or training method might reduce error, preserve old knowledge or improve decisions on unfamiliar tasks. FORGE can help organize and measure that experiment and save the resulting state. Actual improvement belongs to the model and must be shown against fair controls.

**Improving the research platform:** FORGE can investigate whether its own approach to selecting or evaluating research candidates could be improved. The [FORGE-on-FORGE loop](f139/nci04_self_improvement_loop.py) evaluates a finite list of supplied patches to allowlisted modules in temporary workspaces. It checks safety boundaries, runs regression tests, evaluates a downstream comparison and ranks strictly improving candidates. It retains rejected candidates instead of quietly discarding them.

An eligible result can become an auditable [draft pull-request proposal](f139/nci04_self_pr_proposer.py), subject to the separate authorized submission and review process. The code explicitly prohibits self-merging through this proposer and protects the controller/kernel/workflow boundary. The research driver can construct a draft payload; this is not itself proof that a GitHub PR was posted.

This is bounded, testable self-improvement machinery. It is not proof of open-ended recursive self-improvement, autonomous invention of arbitrary algorithms, or general intelligence. A useful next goal is to demonstrate that the revised research method selects better experiments on fresh, independently qualified tasks, not merely that it passes a test it was tuned against.

## Evidence, scientific integrity and safety

FORGE is built around a distinction that matters in AI research: **a result can be real without being good, and a good-looking result can be invalid.**

| Status or concept | Meaning |
| --- | --- |
| Development / engineering PASS | A specified implementation or development check worked under the tested conditions. |
| VERIFIED development receipt | The particular runner's checks completed and a receipt was retained. This does not certify a scientific discovery. |
| NEGATIVE / REJECTED | A trial failed, an improvement did not meet its criterion, or the evidence was ineligible. Preserve the reason; a crash is not equivalent to a valid negative scientific measurement. |
| Scientific acceptance | A frozen hypothesis meets its prespecified criterion against appropriate controls with authentic, independently qualified evidence and required reproduction. |
| Deployment | The approved source and state have actually been installed and verified on the intended system. A Git merge or a green CI run does not establish this. |

The safeguards span several parts of the code:

- **Exact identities:** pin code, configuration and evidence to commits and digests so a changed source cannot silently masquerade as the original experiment.
- **Matched comparisons:** compare models with equivalent information, opportunities and resource budgets; use meaningful baselines, ablations and negatives.
- **Frozen protected evaluation:** do not change criteria or reuse consumed first-use trials after learning their outcomes.
- **Recovery rather than blind replay:** distinguish infrastructure failures, uncertain starts, ordinary engineering failures and valid scientific negatives.
- **Retain failures:** a result that disproves a hypothesis is useful research evidence.
- **Independent qualification:** passing a local test or verifying a hash is not an independent witness, authentic external source or scientific approval.
- **Separate promotion:** neither the experiment runner nor the lab automatically replaces an accepted checkpoint or promotes a scientific policy.
- **No implicit paid services:** the built-in development lab and research tick are designed for zero paid model calls. This is not a promise about arbitrary user-supplied scripts or the cost of every possible infrastructure choice.

Hash chains are tamper-evident when checked against trustworthy evidence; they are not a substitute for independent custody or protection against coordinated replacement of an entire unanchored history.

### Architectural isolation

**FORGE must not connect to or depend on CKB-plane.** FORGE owns its own research architecture, authority controls and qualified execution routes. It must not borrow another project's controller, queue, credentials, first-use ledger or private runner to make a gate pass.

Mind-Palace is the sole permitted cross-project **context** bridge: bounded, commit-pinned, read-only advisory retrieval. It can inform research; it cannot approve experiments, sign witnesses or grant execution authority. Historical CKB-derived schemas and reference code remain historical provenance, not a live integration.

See [AGENTS.md](AGENTS.md), [ADR 0002 — standing isolation boundary](docs/ADR-0002-MIND-PALACE-ONLY-NO-CKB-DEPENDENCY.md) and [ADR 0001 — historical authority design](docs/ADR-0001-FORGE-SCIENTIFIC-AUTHORITY.md). The newer ADR takes precedence over older designs.

## What is actually demonstrated

The source snapshot used for this overview is [`f5a6bcf5b84d85ff178a6597db399ab3a54d91fb`](https://github.com/spoonman136668-ai/FORGE/commit/f5a6bcf5b84d85ff178a6597db399ab3a54d91fb), incorporating [PR #1929](https://github.com/spoonman136668-ai/FORGE/pull/1929) on November 25, 2026.

### Engineering

The Gate 22 source PR (head `51848e08c481d6af068fbafde173a05bc64b4bd4`) had three successful GitHub workflow runs:

- [Public Linux and Windows qualification — run 45698444169](https://github.com/spoonman136668-ai/FORGE/actions/runs/45698444169)
- [F139 native Windows controller qualification — run 45698444229](https://github.com/spoonman136668-ai/FORGE/actions/runs/45698444229)
- [F139-D hosted development rehearsal — run 45698445156](https://github.com/spoonman136668-ai/FORGE/actions/runs/45698445156)

The [Gate 22 end-to-end test](f139/test_nci04_gate22_lab_cli_and_report_export.py) checks a two-generation starter sweep, at least six verified development trials, a nonempty Pareto frontier, CLI output, and deterministic HTML report generation with chain validation. These are test expectations and passing engineering workflow evidence, not measured gains against a trained real-world AI baseline.

### Scientific

FORGE's history explicitly includes results that did not justify promotion. For example, the [F85 dual-lane negative evidence report](docs/F85-DUAL-LANE-FIT-NEGATIVE-OPTIMIZER-QUARANTINE.md) records the following historical diagnostic comparisons:

| Historical evaluation | Candidate | Comparison | Disposition recorded by F85 |
| --- | ---: | ---: | --- |
| Wingless F61B FIT | 104/128 | 102/128 strongest fair comparison | +1.5625 percentage points; below frozen +5-point criterion |
| Yggdrasil F63C FIT | 11/32 | 24/32 frozen comparison | -40.625 percentage points |

F85 records two diagnostic negatives, zero scientific training labels, zero accepted originals and zero optimizer policy gains. These figures come from the historical FORGE report, not a new execution or independent re-audit of the underlying archives for this README. That distinction is precisely why FORGE retains provenance and negative evidence.

The latest development lab adds useful experimental machinery. It does not by itself establish cumulative native learning, cold-restart retention, unfamiliar transfer, improved decision-making, superior research-policy selection, or AGI. Each of those requires a suitable prospective experiment and independent qualification.

### Deployment

The public repository is not a distribution of the private owner runtime, secrets or sealed evaluation archives. The exact running workstation release, installed controller state, real hardware utilization and operational scientific authority are not established by this source review. The local lab can be used for authorized development without assuming the owner controller or protected scientific services are activated.

## Getting started with the public source

The repository uses Go 1.23 or newer for the Go components and Python 3.11+ for the F139 tooling. The following commands are intended for an authorized, disposable development checkout, not a running owner installation. Review repository instructions and license boundaries first.

### Build and qualify source

```sh
go test -count=1 ./...
go test -race -count=1 ./...
go vet ./...
go build ./...
python -B -m unittest discover -s f139 -p 'test_*.py' -v
```

The repository includes Linux and Windows GitHub qualification workflows. Run the applicable complete regression and verify the exact candidate source before considering acceptance. Tests may launch subprocesses; do not point them at live controller state.

### Inspect the offline planners

```sh
go run ./cmd/forge-plan -h
go run ./cmd/replay -h
```

These commands describe the offline advisory tools; they do not launch a scientific experiment.

### Try a bounded local development lab

From the repository root, choose a new disposable state directory. The following example deliberately uses the built-in starter blueprints, not an unknown custom script:

```sh
python -B -m f139.nci04_lab_cli --state-dir ./demo-lab --generations 2 --wave-size 3 --markdown
python -B -m f139.nci04_report_export --state-dir ./demo-lab --out ./demo-report.html
python -B -m f139.nci04_status_cli --store ./demo-lab/research_evidence.jsonl --human
```

Open `demo-report.html` in a browser to inspect the results. The lab writes experimental evidence and checkpoint files under the selected state directory. It does not install or activate the workstation controller or grant scientific first-use. Do not reuse an uncertain protected trial or place this development output inside an accepted model's state directory.

For custom JSON blueprints and available flags, see:

```sh
python -B -m f139.nci04_lab_cli --help
python -B -m f139.nci04_report_export --help
python -B -m f139.nci04_research_driver --help
```

Actual controller installation, deployment and source transitions follow the separate [Windows operations guide](f139/README-WINDOWS.md) and currently applicable owner qualification. They are not part of this demonstration.

## Source map and further reading

| Source | What to look for |
| --- | --- |
| [planner/plan.go](planner/plan.go), [engine.go](engine.go) | Frozen candidate ranking and deterministic, non-executing research state/replay primitives. |
| [evoportfolio/](evoportfolio/), [optimizerbridge/](optimizerbridge/) | Diverse candidate portfolios, optimizer integration and advisory evidence checks. |
| [f139/local_controller.py](f139/local_controller.py) | Workstation controller, queue and receipt handling. |
| [f139/nci04_experiment_runner.py](f139/nci04_experiment_runner.py), [hardware trainer](f139/nci04_hardware_trainer.py) | Bounded development execution and resource-aware budgeting. |
| [f139/nci04_multi_lane_scheduler.py](f139/nci04_multi_lane_scheduler.py), [research driver](f139/nci04_research_driver.py) | Research allocation recommendations and the local development tick. |
| [f139/nci04_evidence_store.py](f139/nci04_evidence_store.py), [checkpoint vault](f139/nci04_checkpoint_vault.py) | Recorded outcomes and exact saved experiment state. |
| [f139/nci04_blueprint_lab.py](f139/nci04_blueprint_lab.py), [lab CLI](f139/nci04_lab_cli.py), [Pareto comparator](f139/nci04_pareto_comparator.py) | Configurable trials, finite evolutionary search and trade-off analysis. |
| [f139/nci04_self_improvement_loop.py](f139/nci04_self_improvement_loop.py), [PR proposer](f139/nci04_self_pr_proposer.py) | Bounded improvement of research tooling, with review rather than self-merge. |
| [f139/nci04_status_cli.py](f139/nci04_status_cli.py), [report exporter](f139/nci04_report_export.py) | Read-only inspection and local research reporting. |
| [docs/research-steering/CORE-NATIVE-INTELLIGENCE.md](docs/research-steering/CORE-NATIVE-INTELLIGENCE.md) | Research direction: learning from consequences, retention, transfer, native model integration. |
| [docs/F139-EXISTING-OPTIMIZER-SHADOW-RUNNER.md](docs/F139-EXISTING-OPTIMIZER-SHADOW-RUNNER.md) | Five optimizer methods, required original inputs, and activation limits. |
| [docs/F139-UNIFIED-FORGE-CONTROLLER.md](docs/F139-UNIFIED-FORGE-CONTROLLER.md) | Single-controller design, crash recovery and qualified development progression. |
| [PUBLIC_SOURCE_BOUNDARY.md](PUBLIC_SOURCE_BOUNDARY.md) | Publication restrictions and protected material exclusions; historical descriptions of implementation status must be read in their source-version context. |

## Public source and licensing

No private scientific evidence archives, credentials, runner secrets, sealed evaluation data or private production authority records are distributed as part of this public source. The source includes historical reference material; public visibility does not grant authority to use any private system.

**Licensing:** no general reuse license has yet been granted. Public visibility does not automatically authorize redistribution.

---

**The aim of FORGE is not simply to make experiments run faster. It is to make research cumulative: try an idea, measure it fairly, preserve the truth about the result, and use that result to make the next research decision better. The ultimate test is whether this produces independently demonstrated improvements in the learners and in the research process itself.**
