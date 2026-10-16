# FORGE backup recovery key custody

The operator has approved retaining the **private decryption identity** outside GitHub on protected Windows storage. Only the matching **public age recipient** may be supplied to FORGE.

## One-time Windows key creation

Install the open-source age utility from its verified official distribution, then run the following in Windows PowerShell **on your own workstation**:

```powershell
$ErrorActionPreference = 'Stop'
$dir = Join-Path $env:USERPROFILE 'Documents\FORGE-Recovery'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
age-keygen -o (Join-Path $dir 'rbackup-age-identity.txt')
Get-Content (Join-Path $dir 'rbackup-age-identity.txt') | Select-String '^# public key:'
```

Copy the **public** `age1...` recipient only to a FORGE Actions variable named `RBACKUP_AGE_RECIPIENT`. Never upload or share the `AGE-SECRET-KEY...` private identity. Keep an independent protected offline copy of the private identity; access to the Windows Documents folder alone is not adequate disaster recovery.

## Non-negotiable acceptance

1. Reject missing or malformed public recipients and any private key in a public variable.
2. Encrypt on the working runner **before** transferring a database archive to private `spoonman136668-ai/rbackup`.
3. No live D1 export until the user-controlled private identity can decrypt a synthetic archive independently and an isolated restoration verifies it.
4. Check source-commit identity, original archive digest, backup retention and fresh restore; refuse dispatch or database writes on any mismatch.
5. The private identity must never enter FORGE, rbackup, GitHub Secrets, CI logs or artifacts.

This document is guidance only, not proof of encryption or recovery qualification. No production backup was exported or uploaded.
