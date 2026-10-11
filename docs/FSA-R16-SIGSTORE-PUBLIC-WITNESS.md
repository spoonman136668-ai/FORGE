# FORGE R16 — independent public Sigstore transparency, no new spending

**Status:** one public GitHub-hosted qualification + Sigstore provenance witness for a **source-only, read-only diagnostic binary**. This does not deploy the FORGE Scientific Authority (FSA).

## Why this matters

R15 proved the existing FORGE `main` branch is unprotected and has no repository rulesets, so GitHub source commits alone are not an independently controlled monotonic scientific checkpoint. However, a *public* GitHub Actions artifact attestation uses the Sigstore public-good service, publishing cryptographically signed build provenance to an independently operated, append-only public transparency log. Unlike a plain Git ref under the owner's administrative control, log inclusion is externally auditable.

R16 creates **no FSA scientific signing key or credential**. After both Linux and native Windows qualifications succeed on the exact bounded source SHA/tree, a dedicated job builds the existing `forge-fsa-github-audit` executable, requests a short-lived GitHub Actions OIDC identity, publishes its GitHub build attestation using `actions/attest@v4`, and verifies that signed attestation with `gh attestation verify`. The only attested subject is the public diagnostic binary, never private research inputs or future experiment cohorts. No new secret, private data or permanent provider account is needed.

The workflow deliberately makes the verification job **dependent on both native full regressions**; no green Linux-only attestations masquerade as Windows qualification. Attested binary hash + workflow identity + source Git SHA provide public supply-chain provenance, not scientific truth.

## Non-negotiable limitations

- **Not a monotonic first-use CAS.** Sigstore is an append-only witness; it cannot atomically reserve a cohort or prohibit two competing scientific dispatch requests.
- **Not protected FSA key custody.** GitHub OIDC build certificates prove workflow identity, not that the FORGE scientific signing/approval keys are independently controlled.
- **Not raw scientific persistence.** A build attestation records an executable digest, not original measurement data or terminal/negative classifications.
- **Not an irreversible GitHub API record.** Repo operators can remove GitHub-side attestations; independently retained Sigstore transparency evidence offers a separate audit trail but needs independent checkpoint monitoring. A log inclusion cannot validate self-asserted claims about science.
- **No original science, FSA activation, accepted-ref mutation, KTRADE or CKB-plane work**, no private sources and no new workflow-triggered experiment execution.

## Qualification and use

The new public GitHub-hosted workflow on the R16 proposal branch performs exact foundation check, focused tests, one complete native Linux/Windows Go regression/vet/build, full Linux race, then a **single real** Sigstore public-good attestation of a compiled diagnostic binary. It runs once per push and cancels obsolete overlapping runs to stay within free public CI use.

Use the workflow run and its public attestation to verify the build/provenance property independently. **Do not** mark [physical FSA custody issue #20](https://github.com/spoonman136668-ai/FORGE/issues/20) or [original science issue #25](https://github.com/spoonman136668-ai/FORGE/issues/25) complete. Their remaining mandatory gates are independently held scientific key custody, off-host atomic first-use CAS, immutable original retention, fault/restart verification, authenticated randomized histories, and two unattended generations.

All costs remain **$0 incremental**. R16 is an evidence-building step, not a substitute for the final authority.
