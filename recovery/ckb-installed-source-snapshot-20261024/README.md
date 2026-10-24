# CKB installed source recovery snapshot

This branch preserves the exact Go source bytes recovered read-only from the installed CKB-plane workstation source on 2026-10-24.

It is recovery custody only. It grants no execution, merge, acceptance, or live-install authority.

Source scope: go.mod, go.sum, cmd/ckb-plane/**/*.go, internal/plane/**/*.go.
Excluded: live config, SQLite state, credentials, tokens, evidence directories, binaries, workspaces.
