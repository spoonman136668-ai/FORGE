---
source_file: "fsaservice/read_only_test.go"
type: "code"
community: "Community 18"
location: "L82"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_18
---

# testService()

## Connections
- [[TestDurableCheckpointAndWitnessCoherenceThroughMutualTLS()]] - `calls` [INFERRED]
- [[TestDurableWitnessRestartThroughIndependentMutualTLSServers()]] - `calls` [INFERRED]
- [[TestIndependentReadOnlyHandlersThroughRealMutualTLSClient()]] - `calls` [EXTRACTED]
- [[TestRSH03SixLaneReadOnlyAuthenticatedDualTLSWitness()]] - `calls` [INFERRED]
- [[TestSignedCheckpointHTTPRejectsMalformedForgedAndUnwitnessedWrites()]] - `calls` [INFERRED]
- [[TestSignedCheckpointWriteRequiresDistinctWriterMTLSAndWitness()]] - `calls` [INFERRED]
- [[cryptotls.Certificate]] - `references` [EXTRACTED]
- [[cryptox509.CertPool]] - `references` [EXTRACTED]
- [[nethttp.Handler]] - `references` [EXTRACTED]
- [[nethttphttptest.Server]] - `references` [EXTRACTED]
- [[newGateFixture()]] - `calls` [INFERRED]
- [[newStepHTTPFixture()]] - `calls` [INFERRED]
- [[read_only_test.go]] - `contains` [EXTRACTED]
- [[testing.T]] - `references` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_18