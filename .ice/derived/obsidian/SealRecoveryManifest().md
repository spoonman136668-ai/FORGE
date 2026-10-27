---
source_file: "watchdog/manifest.go"
type: "code"
community: "Community 75"
location: "L46"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_75
---

# SealRecoveryManifest()

## Connections
- [[AssessedIncident]] - `references` [EXTRACTED]
- [[DurableIncident]] - `references` [EXTRACTED]
- [[ImportIncidentChain()]] - `calls` [INFERRED]
- [[PrepareRecoveryBatch()]] - `calls` [INFERRED]
- [[RecoveryManifest]] - `references` [EXTRACTED]
- [[Run()_42]] - `calls` [EXTRACTED]
- [[TestAttestedObservationsToNoReplayOutboxIntegration()]] - `calls` [EXTRACTED]
- [[TestEndToEndShadowRepairIntakeAndNoOriginalDispatch()]] - `calls` [EXTRACTED]
- [[TestSealedRecoveryRequiresPersistedIncidentIdentity()]] - `calls` [INFERRED]
- [[VerifyIncidentChain()]] - `calls` [INFERRED]
- [[buildManifest()]] - `calls` [EXTRACTED]
- [[manifest.go]] - `contains` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_75