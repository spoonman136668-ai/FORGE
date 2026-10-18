# G31: read-only private source AND derived-artifact qualification on an
# existing FORGE-isolated Windows runner. Does not call Codex or write memory.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:GITHUB_REPOSITORY -cne 'spoonman136668-ai/FORGE' -or
    $env:RUNNER_NAME -cne 'FORGE-CODEX-REMOTE' -or
    $env:RUNNER_OS -cne 'Windows') {
  throw 'G31_FORGE_RUNNER_IDENTITY_MISMATCH'
}
Remove-Item Env:GH_TOKEN, Env:GITHUB_TOKEN -ErrorAction SilentlyContinue
$env:GIT_TERMINAL_PROMPT = '0'
$env:GCM_INTERACTIVE = 'Never'
$env:GH_PROMPT_DISABLED = '1'
$cases = @(
  @{ id='mind'; repo='spoonman136668-ai/Mind-Palace'; branch='graphify/g31-mind-advisory-source-20261018';
     head='8c78f9f59dc7a2e92f46d8bc678ba17068e3ec9b'; base='7ae81a209fa77e5381a669eb3cc0d736ef60ecd9'; artifactRoot='docs/graphify/g31-atlas' },
  @{ id='plane'; repo='spoonman136668-ai/ckb-plane'; branch='graphify/g31-plane-advisory-source-20261018';
     head='c802637b344241c64f4eb73375dd292aa8ce6da8'; base='fab36e7c488f930505fcbaeb5f5bf04806e50c5b'; artifactRoot='.ice/navigation/g31-atlas' },
  @{ id='ktrade'; repo='spoonman136668-ai/KTRADE'; branch='graphify/g31-ktrade-historical-file-inventory-20261018';
     head='02f25a1c16c477a85295838981effe6c6664028f'; base='a3b2e1a53a8b714bbdca1b33a6db71e128f32fa1'; artifactRoot='.ice/navigation/g31-atlas' }
)
$tool = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
$arguments = @()
if (-not $tool) {
  $tool = (Get-Command py.exe -ErrorAction SilentlyContinue).Source
  $arguments = @('-3')
}
if (-not $tool) { throw 'G31_FORGE_RUNNER_PYTHON_MISSING' }
$scratch = Join-Path $env:RUNNER_TEMP ('g31-qual-' + $env:GITHUB_RUN_ID + '-' + $env:GITHUB_RUN_ATTEMPT)
if (Test-Path -LiteralPath $scratch) { throw 'G31_SCRATCH_COLLISION' }
New-Item -ItemType Directory -Path $scratch -ErrorAction Stop | Out-Null
$errors = @()
try {
  foreach ($c in $cases) {
    $id = [string]$c.id
    $url = 'https://github.com/' + [string]$c.repo + '.git'
    $path = Join-Path $scratch $id
    try {
      $remote = @(& git.exe ls-remote --exit-code $url ('refs/heads/' + $c.branch))
      if ($LASTEXITCODE -ne 0 -or $remote.Count -ne 1 -or
          (([string]$remote[0] -split '\s+')[0]) -cne [string]$c.head) {
        throw 'PRIVATE_BRANCH_NOT_ACCESSIBLE_OR_HEAD_CHANGED'
      }
      $remoteMain = @(& git.exe ls-remote --exit-code $url 'refs/heads/main')
      if ($LASTEXITCODE -ne 0 -or $remoteMain.Count -ne 1 -or
          (([string]$remoteMain[0] -split '\s+')[0]) -cne [string]$c.base) {
        throw 'PROTECTED_MAIN_MOVED'
      }
      # Blobless and single-file sparse checkout: do not materialize any
      # memory record, operational state database, broker config or science data.
      & git.exe clone --quiet --filter=blob:none --no-checkout --depth 16 --single-branch --branch ([string]$c.branch) $url $path
      if ($LASTEXITCODE -ne 0) { throw 'PRIVATE_BLOBLESS_CLONE_FAILED' }
      $filter = (& git.exe -C $path config --get remote.origin.partialclonefilter | Out-String).Trim()
      if ($filter -cne 'blob:none') { throw 'BLOBLESS_CLONE_NOT_NEGOTIATED' }
      $expectedPaths = @(
        'tools/graphify/g31_source_inventory.py',
        ([string]$c.artifactRoot + '.json'),
        ([string]$c.artifactRoot + '.html'),
        ([string]$c.artifactRoot + '.ice')
      )
      $patterns = @($expectedPaths | ForEach-Object { '/' + $_ })
      & git.exe -C $path sparse-checkout set --no-cone @patterns
      if ($LASTEXITCODE -ne 0) { throw 'SPARSE_CHECKOUT_CONFIG_FAILED' }
      & git.exe -C $path checkout --quiet --detach ([string]$c.head)
      if ($LASTEXITCODE -ne 0) { throw 'PINNED_CHECKOUT_FAILED' }
      $head = (& git.exe -C $path rev-parse HEAD | Out-String).Trim()
      if ($head -cne [string]$c.head) { throw 'PINNED_HEAD_IDENTITY_MISMATCH' }
      $tracked = @(& git.exe -C $path ls-files)
      $present = @($tracked | Where-Object { Test-Path -LiteralPath (Join-Path $path $_) -PathType Leaf })
      if (@($present).Count -ne 4 -or
          @($present | Where-Object { $expectedPaths -cnotcontains [string]$_ }).Count -ne 0) {
        throw 'UNEXPECTED_PRIVATE_WORKTREE_CONTENT'
      }
      $delta = @(& git.exe -C $path diff --name-only ([string]$c.base) ([string]$c.head))
      if ($LASTEXITCODE -ne 0 -or $delta.Count -ne 4 -or
          @($delta | Where-Object { $expectedPaths -cnotcontains [string]$_ }).Count -gt 0) {
        throw 'UNAUTHORIZED_SOURCE_DELTA'
      }
      foreach ($file in $expectedPaths) {
        $filePath = Join-Path $path $file
        $actualBlob = (& git.exe -C $path hash-object -- $filePath | Out-String).Trim()
        $expectedBlob = (& git.exe -C $path rev-parse ('HEAD:' + $file) | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or $actualBlob -cne $expectedBlob) {
          throw 'G31_QUALIFIED_GIT_BLOB_DRIFT'
        }
      }
      $script = Join-Path $path 'tools/graphify/g31_source_inventory.py'
      $result = @(& $tool @arguments $script --check-if-present 2>&1)
      if ($LASTEXITCODE -ne 0 -or
          -not (@($result) -match 'G31_COMMITTED_SOURCE_ATLAS_PASS') -or
          -not (@($result) -match ('G31_SOURCE_IDENTITY_PASS ' + [regex]::Escape([string]$c.repo)))) {
        throw 'G31_REPO_ARTIFACT_QUALIFICATION_FAILED'
      }
      $dirty = @(& git.exe -C $path status --porcelain=v1)
      if ($dirty.Count -ne 0) { throw 'PRIVATE_CHECKOUT_DIRTY' }
      $after = @(& git.exe ls-remote --exit-code $url ('refs/heads/' + $c.branch))
      if ($LASTEXITCODE -ne 0 -or $after.Count -ne 1 -or
          (([string]$after[0] -split '\s+')[0]) -cne [string]$c.head) {
        throw 'PR_HEAD_MOVED_DURING_QUALIFICATION'
      }
      Write-Host ('G31_FORGE_RUNNER_' + $id.ToUpperInvariant() + '=PASS')
    } catch {
      $errors += ($id + ':' + $_.Exception.Message)
      Write-Host ('G31_FORGE_RUNNER_' + $id.ToUpperInvariant() + '=BLOCKED')
    } finally {
      if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction Stop
      }
      if (Test-Path -LiteralPath $path) { throw 'PRIVATE_SCRATCH_CLEANUP_FAILED' }
    }
  }
} finally {
  if (Test-Path -LiteralPath $scratch) {
    Remove-Item -LiteralPath $scratch -Recurse -Force -ErrorAction Stop
  }
}
if ($errors.Count -gt 0) {
  foreach ($e in $errors) { Write-Host ('G31_QUALIFICATION_BLOCKER=' + $e) }
  throw 'G31_FORGE_PRIVATE_SOURCE_QUALIFICATION_INCOMPLETE'
}
Write-Host 'G31_FORGE_PRIVATE_SOURCE_QUALIFICATION=PASS'
