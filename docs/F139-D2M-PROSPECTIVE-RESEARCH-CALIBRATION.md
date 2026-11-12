# F139-D2M — prospective research-value calibration

## Scope

This source-only candidate extends the merged `infogain` advisory introduced by
PR #590. It measures **proper forecast scores and actual compute costs** for
prospective experiment outcomes from individually frozen Wingless, Yggdrasil,
or Mass Research proposals. It neither originates nor runs experiments.

The input supplies one signature-pinned, source-bound cohort with:
- Exact prior frozen selector digest, named proposal identity and source SHA;
- Preregistration, first-use witness **references**, source and evidence SHA;
- Observed result classified as SUPPORT, NEGATIVE, LIMITATION, or INDETERMINATE;
- Full CPU time, actual compute units, peak memory and memory-byte-time;
- A reported transfer class, including genuine regression/negative claims.

The library verifies an Ed25519 signature against a **separately supplied**
public-key pin, content-addresses the frozen cohort, preserves negatives,
rejects source/experiment replay and observations of candidates that were not
selected prospectively, and computes Brier and logarithmic forecast loss,
estimated-versus-observed resource overrun and counts of reported limitations
and transfer. A zero-probability result is explicitly represented as an
infinite-surprise sentinel rather than hidden or backfilled.

## Trust boundary

A signature can establish consistency with a pinned external public key; it
does **not** by itself establish the key's independent origin, a legitimate
pre-outcome witness, that an experiment was never used previously, comparable
controls, or scientifically accepted transfer. This module's outputs must
therefore have all these fields **false**: scientific acceptance, witnessed
first-use, genuine transfer established, optimizer promotion, execution grant.

Caller-side independent evidence-custody verification must be qualified
separately before taking a signed claim as science. Frozen forecast validation
is not repeated on the same used outcome; reported wins and negatives both
stay in the content-addressed historical record.

No network, data store, active worker, GitHub branch, scientific source,
scheduler, Cloudflare worker, or paid model is changed by this source package.

## Required acceptance

- Exact-head Windows/Linux source qualifications with positive and negative
  signature, tampering, source reuse, candidate exclusion and resource tests;
- Independently sourced prospective cohorts; no synthetic fixture is accepted
  as prospective scientific evidence;
- Forecast calibration on unfamiliar experiment families, including failure
  and limitation outcomes, with strong comparator and measured complete cost;
- Preservation of Wingless, Yggdrasil and Mass Research separate scientific
  authority and first-use boundaries;
- Full source-bound host transition **once**, without disturbing four D2C/D2J
  verified worker receipts, before claiming deployment.

This is scientific-information optimization, **not experiments per hour**.
