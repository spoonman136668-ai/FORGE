# RSI R12-E — actual original entrypoint parity and issued-job evidence

Baseline FORGE protected main: `b28ed7c74a1ace56096df6fb47d2ccc6b710e47a`.
Original Windows installed source remains `42c70d74dd93ef90d0f4618fefefe2206b81eafe`.

## Corrected concrete original runtime defect

Original Windows launch `python -m f139.local_controller` creates its
`Database` class in `__main__`, not `f139.local_controller`. R11 and
R12-C already accept that real Python module split, but R12-A and R12-B
erroneously required `type(db) is Database` imported from another module.
An otherwise valid original owner would always reject an R12-A candidate
binding, and therefore also reject R12-B signed validation. R12-E shares
the R11-accepted exact Database class-name/module and live SQLite
connection predicate. Full original SHA-chain, historical R11/R12-C audit,
source pin and native authorization are **still mandatory**; lookalikes
cannot qualify through class identity alone.

R12-E also introduces one read-only *credentialed original issuance witness*
that accepts original cold SQLite ledger and R11/R12-C one-spend event,
verifies original R12-B HMAC and authenticated provider run/job/source,
checks immutable issuance/reservation event digests, and returns **no secret,
no usable ticket, no credential-free worker authorization**.

## Operational boundary

The original installed owner is unchanged. Existing F139 signed worker
allowlists remain unchanged and continue to reject FORGE-self. Live policy
#807 remains pinned to original installed source and only native
Wingless/Yggdrasil. The real credential-free execution job, original
source-cutover/atomic policy activation and independently authenticated
receipt channel are NOT implemented by this source-only gate. No scheduled
task, provider dispatch, original SQLite mutation, promotion, paid model
API or scientific first-use is authorized or executed.

## Qualification

Use existing focused, adversarial, original F139 Windows and full original
Linux/Windows regression/build on the exact candidate SHA. A simulated
positive projection mocks the original ledger and explicitly does NOT prove
genuine original-owner authorization. Full RSI requires a fresh, eligible
failure, original-owner unattended source change, authentic separate
qualification and G0/G1/G2 benefit against frozen untouched controls.
