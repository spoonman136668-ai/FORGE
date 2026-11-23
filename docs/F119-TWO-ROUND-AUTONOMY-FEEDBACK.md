# F119 — Two real autonomous development decision rounds per GitHub run

## Purpose

F118 is already merged into protected `main`, operating inside FORGE's existing six-hour GitHub Actions research-development worker. F118 automatically picks **one** untested model-free proposal from each independent Wingless and Yggdrasil advisory lane, runs one allowlisted native Go *development readiness* test per lane, archives results, and can consume authentic prior **scheduled** run feedback.

F119 closes the **within-run second-decision gap**. It reads the actual **just-executed** F118 state and takes an additional bounded decision in each lane. This provides **four real development actions per GitHub run**, in two feedback-dependent rounds, without a second scheduler, CodeX or paid inference. A candidate's Go package readiness score **does not measure the scientific hypothesis's validity**.

## Frozen experiment and implementation

First preimplementation freeze: `1b8c3ea25c1319a578ced394f18ed2b4de24551f`, based on protected `main` `50a4639b0f2218caed713f27f0e602821a74d49f`. Freeze Git blob `d8491705e61ddd1e8b49751641b90d9e6fec91f4`. F118 engine must remain unmodified at Git blob `9ed9127a06d1a22b5ef8519e67730f3dc90e1c6c`.

1. F118 chooses and executes one source-bound proposal readiness check per lane. Its output, `forge-f118-autonomy/state.json`, must match this GitHub run SHA, event, run ID, the current advisory receipt and the existing F118 frozen protocol.
2. F119 checks that the first two actual actions and their retained history are consistent; untrusted input or science-authority drift fails closed.
3. It chooses a second candidate *per lane*. If the immediate previous test failed or timed out and has exactly one consecutive failure, the second round makes one bounded retry. Otherwise, it picks the least-tested **different** candidate. Ties go to the smallest index.
4. It executes two further allowlisted **real** `go test -count=1` package checks with hard 90-second limits. Every PASS, FAIL and TIMEOUT, stdout SHA-256, exit code, selected proposal ID and selection reason is retained.
5. It saves an immutable first-round copy plus an independent F119 source-bound two-round audit. It replaces only the scheduled-carry **F118-compatible state artifact** with updated history representing **all four executed actions**; it does not modify the original F118 software, accepted research refs, protected scientific first-use, or optimizer policies.
6. The next *genuine scheduled main* run of the already-existing workflow can consume the now richer history, subject to the unchanged prior GitHub-run metadata and exact SHA-256 evidence checks.

## Scientific and autonomy qualification

F119 does **not** require waiting for two six-hour time slots to execute two feedback-dependent decision rounds. A passing pull request verifies actual within-run decision and execution on Ubuntu/Windows and full Go regression.

**Genuine repeated unattended cross-run continuity is still separately unproven** until at least two new successful scheduled **main** invocations show real previous-artifact consumption. PR, push and synthetic tests do not replace that evidence.

Model-free advisory proposal IDs are untested structural hypotheses derived from a fixed development corpus. Running a passing native Go package test is **not** evaluating the proposed scientific mechanism, nor a prospective causal test of Dream-RSI, Pareto, ThetaEvolve or actual research discovery. F119 advances FORGE's autonomous **engineering development loop**, while science promotion and original research remain separately controlled.

No Codex, paid GPT API, Work automation, added schedule, CKB-plane, Cloudflare write, Mind-Palace write, Wingless/Yggdrasil repo mutation, accepted ref change, unauthorized native science dispatch or first-use consumption. Keep independently accepted scientific claims at zero.
