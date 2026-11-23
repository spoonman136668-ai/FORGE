# Native task feedback

Read exact source-pinned original receipts with:

    python nativeevidence/native_task_feedback.py --receipt ORIGINAL.json --lane Yggdrasil --source-sha EXACT_SHA --receipt-sha256 EXACT_DIGEST

This read-only adapter consumes existing MG90 task receipts, complete Wingless exact-exposure receipts, and incomplete Wingless evidence from the qualified repair. It emits per-role actual steps, return, completed goals and observed wall time. Unknown costs, retention and transfer remain unverified. It never dispatches, changes an optimizer, or feeds a reward to either native learner. Existing native architectures and raw rewards remain untouched.

Use the existing custodian to authenticate run/source/artifact identity before consumption; a caller-supplied matching SHA is integrity, not independent provenance. For MG90, role step totals, unique episode identities, selected ledger digests and summed rewards must reconcile. Source canonical JSON has no trailing newline; FORGE report canonical JSON retains its existing newline. The adapter has a 4 MiB read ceiling because the original MG90 training receipt is 2,459,877 bytes. Oversized, duplicate-key, nonfinite and wrong-schema data fail closed.

Only complete train-phase observations are marked development training feedback available. MG90 heldout is report-only and never optimization input. Wingless evaluation fields are excluded; incomplete arms retain their exposure deficit with no invented performance metrics. No learning benefit, budget parity, live integration, causal advantage or scientific acceptance is inferred.

The accompanying historical MG90 readback was computed from existing artifact12971287227, run41043184251, sourceb0c7e75f7c996f7cb04359c13f404907ccf4a35e. No experiment was rerun. Native MG90 completed0/6train and0/3heldout goals; the engineered MG86 diagnostic completed4/6 and3/3. Keep these negative task outcomes separate from source-only engineering PASS. No efficacy ranking against a strong trained agent is supported.

Scope: source-only optional input seam for existing FORGE feedback consumers. Live owner source5680e744/policy807 remains unchanged; do not substitute this summary for authenticated optimizer histories or the separately required release/integration gates.
