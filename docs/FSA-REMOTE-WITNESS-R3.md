# FORGE R3 — remote FSA checkpoint protocol and independent witness

**Status: source-only client and synthetic integration tests. NOT a
deployed service or authenticated production trust authority.**

This milestone introduces the `fsaremote` package, a limited client-side
implementation of `fsatrust.Authority`, with two disjoint interfaces:

- **FSA checkpoint authority:** HTTPS GET of the current archive head,
  HTTPS GET of an independently provisioned archive binding, and exactly
  one HTTPS POST for a monotonic compare-and-swap (CAS).
- **Independent rollback witness:** separately authenticated HTTPS GET of
  an Ed25519-signed high-water statement. Its signer must be distinct
  from the FSA scientific signing key and is pinned by the operator.

A signed witness binds the fixed `FORGE_FSA_REMOTE_HIGHWATER_V1`
domain, archive ID, FSA key ID, authority epoch, binding commitment,
scientific-record sequence, complete head SHA-256 and independently
monotonic witness revision. The client validates its signature,
operator-pinned witness public key, identity, record head and minimum
revision. The two remote endpoints must use independently provisioned
TLS roots, mutual TLS client identities, server-SPKI SHA-256 pins and
distinct URLs; redirect and unencrypted HTTP are forbidden.

The only protocol routes are:

| Peer | Method and route | Purpose |
|---|---|---|
| FSA authority | `GET /v1/fsa/anchor` | Read current FSA-controlled head |
| FSA authority | `GET /v1/fsa/binding?archive_id=...` | Confirm provisioned physical archive binding commitment |
| FSA authority | `POST /v1/fsa/cas` | Compare and atomically advance exact previously witnessed anchor |
| Independent witness | `GET /v1/fsa/highwater?archive_id=...` | Read independently signed latest witnessed head |

All response JSON and signed field names are explicitly versioned.
A CAS request includes exact prior and proposed archive head.
A successful response **must** be followed by a fresh independent
witnessed readback. A network timeout, invalid response, witness lag,
witness outage or uncertain commit fails closed. The client cannot
dispatch, repeat, or accept experiments.

**Critical distinction:** Signed statements alone cannot prove a
service has not rolled back to an older *validly signed* statement.
The independent witness must actually retain its latest revision in a
separately governed, monotonic failure domain, and the FORGE operator
must preserve the minimum accepted revision across process restarts.
The reader checks a caller-pinned minimum and rejects lower revisions
seen within one client process. A compromised witness service, colluding
providers, weak physical binding, or rollback of all independently
stored pins is **not** defeated by this source package.

## Qualification and deployment barriers

Source-only GitHub-hosted Linux/Windows tests use deterministic
synthetic signer keys and mock HTTP transports. They check exact
request paths, signature substitution, binding refusal, CAS ambiguity,
readback, stale/replayed heads, independent witness outage, TLS
configuration prerequisites, and integration through the existing
FORGE private scientific archive + `fsatrust` verifier.

**Tests do not prove actual mutual-TLS connectivity, external-service
durability, independent witness persistence, deployment credential
custody, real physical archive binding or fault tolerance under
host-wide and power-loss failure.** Those must be qualified with
independently hosted private services before FORGE activation.

Both services must be provisioned under FORGE-only identities, write
permissions and resource budgets. Do not deploy them onto a shared
CKB controller, research runner, KTRADE account or service principal.
KTRADE's broker, settlement, live activation and production permission
boundary is absolute. No public workflow has access to real private
credentials, sealed science, raw Mind-Palace data or installed runners.

Mind-Palace remains a direct read-only advisory input and cannot act
as a scientific authority or checkpoint writer. CKB data, if imported,
requires independent read-only authentication and never gives FORGE
permission to use CKB queues, runners, accepted refs or historical
scientific cohorts.

**Next:** independently implement and qualify the two remote services,
their storage/checkpoint signing, rollback witness retention and
provisioned physical identity in private segregated failure domains;
then exercise real mTLS, crash/power-loss, network partitions,
signer rotation and simultaneous CKB/KTRADE isolation. Until then:
**no live FORGE scientific controller or research primary.**
