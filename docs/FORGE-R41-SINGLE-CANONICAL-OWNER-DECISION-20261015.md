# R41 — one canonical owner signature, one immutable D1 claim tuple

Existing R30 and R36 both verified valid signed decisions, but with **different signed domains and different frozen fields**. Trying to transcode the R30 signature to R36 without genuine owner/witness countersigning is cryptographically invalid.

R41 retains **the more complete R30 signed predecision as the ONLY prospective canonical source** and projects it after exact `originalclaim.VerifyPredecision` verification into the R35/R38 claim tuple using `preusebinding.FromOwnerPredecision`. It does not forge an R36 signed record or claim both signed formats equivalent. The exact R30 signed digest binds experiment, sealed source, intent, worker, run, policy, four baselines, candidate, probability, randomization proof, owner epoch and sequence. The derived original key SHA256 uses the unchanged R30 lane+experiment convention; original source and epoch occupy separate D1 columns; same ordered key pin digest as R36.

The existing native R32 CLI now reports this **non-authorizing candidate** only after successful trusted-local write-once first-use. It preserves all false authority fields. Invalid signatures, different owner/worker/source/experiment, stale controls and SQLite signed-integer overflows fail closed. Negative tests ensure candidate derivation does not mutate D1 or dispatch a worker.

**Authentic release remains denied:** these still are test-only signing keys, not independently controlled owner/witness credentials; the user has confirmed no separate signing credentials. Existing GitHub-held Cloudflare access is for the archived D1 resources and does not by itself authorize science. No live D1 CAS, owner-pinned issuer key, current owner high-water, scientific worker-side permit, real interrupted worker, or new original exists here. R36 historical Verify is retained for backwards compatibility but is NOT a second authority requirement on the canonical R41 pathway.

No Cloudflare D1/Worker changes, new credentials/controllers/schedules, repository main merge, paid API/Codex review, CKB/KTRADE changes or running Wingless/Yggdrasil research disruption.
