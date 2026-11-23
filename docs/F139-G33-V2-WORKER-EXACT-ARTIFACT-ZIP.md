# F139 G33 — Exact V2 ZIP packaging from development worker

G32 independent original-ledger + dual-OS ZIP custody review PR #942:
six Linux/Windows checks PASS. This is a new source-only packaging gate.

Before G33, the credential-free G30 Python API wrote two development-only
canonical files named f139-v2-development-{receipt,report}.json.
The separately frozen G14 provider V2 reader requires an actual ZIP with
exactly f139-v2-receipt.json, f139-v2-receipt.sha256 and
f139-v2-native-report.json. Nothing connected those paths.

G33 adds a bounded, deterministic ZIP packager and calls it after a successful
or negative G30 V2 diagnostic. It re-verifies canonical report bytes and the
signed admission-bound V2 receipt BEFORE touching the archive path, then
creates f139-v2-development-provider.zip with the three frozen members.
A negative outcome is packaged faithfully and remains NOT QUALIFIED.

The ZIP can now pass the unchanged G14 strict V2 reader's exact member
inventory, checksum, schema, source/run/OS and signed-admission checks.
Tests exercise the entire G30 Python worker API to G14 provider reader path,
not only independently fabricated ZIPs. Fixtures remain synthetic; no
genuine independent original-owner GitHub provider evidence is claimed.

Important boundaries:
- The ORIGINAL live Actions workflow still calls execute V1, not this
  developmental API. G33 does NOT add a V2 CLI verb, Actions upload job,
  run authorization, new controller, queue, scheduler or owner ledger event.
- The package's local SHA-256/digest is NOT provider-authenticated metadata.
  Original-owner custody needs authenticated workflow ID, run attempt, jobs,
  artifact ID, repository source and signed V2 permit under the same mutex.
- No connection to the actual GitHub Actions upload-artifact step yet:
  the ZIP is staged on a local development worker output path only.
- No replay of G1/G3 historical negatives including issue #907. No live
  activation, paid API, scientific first use, source acceptance or merge.

Next G34: separately qualify the existing native worker workflow's
explicit V2-only job and actual GitHub artifact upload, with permission
bound to the G31 original-owner V2 signature and G32 original SQLite
custody. Fail closed and preserve the V1 workflow, then full cross-platform
regression and guarded original-owner approval. Do not change production
source merely because a local synthetic ZIP roundtrip passes.
