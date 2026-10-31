# G84 final qualification retry — 2026-10-31

The first exact-receipt final-regression attempt, run `41204859970`, correctly verified the result JSON digest, source blobs, and result schema, but its baseline ancestry assertion could not resolve G70 because the workflow used a two-commit shallow checkout. This was a **qualification workflow infrastructure/configuration defect**, not a failing experiment, changed model source, or failed research test.

The final-regression workflow has been corrected to fetch full Git history (`fetch-depth: 0`) on both OS jobs. The original Windows benchmark receipt is unchanged:

- Result commit: `4359211ed0b71d55a541f3baa951775db4c17ee6`
- Result blob: `a4a57e1e68d46c10c13f2d81a16092aa8af38d75`
- Result SHA-256: `b84c0c0e520dc20415cad9e8f6d9ffcd0e81eaacaf2a527a9ebf8bdd2bf2040b`
- Frozen scientific classification: `TRANSFER_FAIL`; engineering and exact-output correctness PASS.

This separate trigger requests a rerun of the mandatory exact-receipt Linux/Windows qualification after the infrastructure-only correction. No result bytes, measurements, thresholds, baseline sources, or scientific interpretation are changed.