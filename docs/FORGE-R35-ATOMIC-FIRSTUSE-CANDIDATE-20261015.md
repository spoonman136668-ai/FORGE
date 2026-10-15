# R35 — minimal atomic first-use candidate in existing Cloudflare D1

R33/R34 authenticated the existing Cloudflare Worker and D1 archive in [run 38793665655](https://github.com/spoonman136668-ai/FORGE/actions/runs/38793665655): one serving Worker version, one D1 binding, zero Durable Object or service bindings, six frozen archived originals/six seals. It did **not** prove independent signing credentials, an original-permit system, or distributed first-use custody.

R35 creates an **isolated, additive SQLite/D1 migration candidate**, `d1retention/r35_atomic_preuse_candidate.sql`. An original identity hash becomes a PRIMARY KEY and a positive authority-sequence is UNIQUE; additional fields freeze lane, epoch, source commit, predecision hash and external owner/witness pin digest. Rows are append-only; updates and deletes are rejected and `scientific_authorized` is constrained to 0. Existing archived research rows and sealing triggers are untouched. A bounded GitHub-hosted test runs competing SQLite clients against a single file, accepts one winner, rejects a duplicate or reused sequence and verifies that an unrelated table is unchanged.

**No schema migration was executed in Cloudflare.** No new Worker, Durable Object, Cloudflare token, signer, service, controller or separate FSA was created. Installing this *candidate* would still not establish real scientific authority.

## Essential scientific and security boundary

An atomic INSERT into the existing database can ensure one row wins for a particular original identity *in that database*. It does not authenticate the worker/owner, guarantee that signatures were made by independently controlled services, prove that its logging was genuinely randomized before outcome, or give an atomic permit that cannot be raced against the worker launch. Existing R30–R32 signed local predecision and first-use CLI remain draft, as do Wingless/Yggdrasil R31 owner-call-site drafts. Do not automatically merge or activate these against running science.

**Next true gate:** identify existing authorized owner/witness credential holders and independently pinned public keys, then bind an authenticated signer-verified predecision to a D1 transaction with monotonic sequence and a release token whose execution-side consumption is independently enforced. Demonstrate the real once-only claimant and interrupted-worker recovery on one owner-approved fresh scientific original. Without a genuine authenticated source, any green R35 SQL test remains a data-store property, not a science result.

**No extra paid API, no Codex routine review, no Cloudflare archival-schema modifications, no source acceptance promotion or existing research interruption.**
