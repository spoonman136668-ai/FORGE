---
source_file: "fsaservice/read_only_test.go"
type: "code"
community: "Community 18"
location: "L33"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_18
---

# testCA()

## Connections
- [[TestDurableCheckpointAndWitnessCoherenceThroughMutualTLS()]] - `calls` [INFERRED]
- [[TestDurableWitnessRestartThroughIndependentMutualTLSServers()]] - `calls` [INFERRED]
- [[TestIndependentReadOnlyHandlersThroughRealMutualTLSClient()]] - `calls` [EXTRACTED]
- [[TestRSH03SixLaneReadOnlyAuthenticatedDualTLSWitness()]] - `calls` [INFERRED]
- [[cryptoed25519.PrivateKey]] - `references` [EXTRACTED]
- [[cryptox509.CertPool]] - `references` [EXTRACTED]
- [[cryptox509.Certificate]] - `references` [EXTRACTED]
- [[newGateFixture()]] - `calls` [INFERRED]
- [[read_only_test.go]] - `contains` [EXTRACTED]
- [[testKey()]] - `calls` [EXTRACTED]
- [[testing.T]] - `references` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_18