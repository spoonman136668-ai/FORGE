# RC2-F isolated, non-promoting, Windows diagnostic-package build.
# This script may run only after the exact RC2-E Windows acceptance run succeeds.
# It NEVER executes the application, copies user financial data, or accesses a broker.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Repo,
    [Parameter(Mandatory=$true)][string]$Destination,
    [long]$QualifiedRunId = 39499832159
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$candidate = 'b8c2052d530cdff93462dfccc21b28f3824e5531'
$forgeSha = 'cbfb548cb92c8a153514176f564a655979e4f95d'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'WINDOWS_REQUIRED' }
if (-not $env:GITHUB_TOKEN) { throw 'AUTHENTICATED_QUALIFICATION_RECEIPT_REQUIRED' }
if ($QualifiedRunId -ne 39499832159) { throw 'QUALIFICATION_RUN_IDENTITY_DRIFT' }
$uri = 'https://api.github.com/repos/spoonman136668-ai/FORGE/actions/runs/' + $QualifiedRunId
$headers = @{ Authorization = ('Bearer ' + $env:GITHUB_TOKEN); Accept='application/vnd.github+json'; 'X-GitHub-Api-Version'='2022-11-28'; 'User-Agent'='K-Terminal-RC2F-Qualification' }
$run = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers -ErrorAction Stop
if ($run.status -cne 'completed' -or $run.conclusion -cne 'success' -or $run.head_sha -cne $forgeSha -or $run.id -ne $QualifiedRunId) {
    throw 'EXACT_FULL_WINDOWS_REGRESSION_NOT_QUALIFIED'
}
$repoFull = (Resolve-Path -LiteralPath $Repo -ErrorAction Stop).Path
$sha = (& git -C $repoFull rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $sha -cne $candidate) { throw 'KTERMINAL_CANDIDATE_IDENTITY_DRIFT' }
$dirty = @(& git -C $repoFull status --porcelain)
if ($LASTEXITCODE -ne 0 -or $dirty.Count -gt 0) { throw 'DIRTY_KTERMINAL_SOURCE' }
$goVersion = (& go version)
if ($LASTEXITCODE -ne 0 -or -not $goVersion.Contains('go1.26.5 windows/amd64')) { throw 'GO_TOOLCHAIN_DRIFT' }
foreach ($name in @('COINBASE_API_KEY','COINBASE_API_SECRET','CDP_API_KEY_NAME','CDP_API_KEY_PRIVATE_KEY','K_TERMINAL_API_KEY','K_TERMINAL_API_SECRET')) {
    if (-not [string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable($name))) { throw 'BROKER_CREDENTIAL_PRESENT' }
}
if (-not $env:RUNNER_TEMP) { throw 'ISOLATED_RUNNER_TEMP_REQUIRED' }
$runnerRoot = (Resolve-Path -LiteralPath $env:RUNNER_TEMP -ErrorAction Stop).Path
if (Test-Path -LiteralPath $Destination) { throw 'OUTPUT_ALREADY_EXISTS' }
$outFull = [IO.Path]::GetFullPath($Destination)
if ($outFull.StartsWith($repoFull + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'OUTPUT_INSIDE_SOURCE_FORBIDDEN' }
[void][IO.Directory]::CreateDirectory($outFull)
$work = Join-Path $runnerRoot ('kterm-rc2f-' + [guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($work)
$source = Join-Path $work 'source'
$stage = Join-Path $work 'diagnostic-package'
[void][IO.Directory]::CreateDirectory($source)
[void][IO.Directory]::CreateDirectory($stage)
try {
    $archive = Join-Path $work 'candidate-source.zip'
    & git -C $repoFull archive --format=zip HEAD -o $archive
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $archive)) { throw 'SOURCE_ARCHIVE_FAILED' }
    Expand-Archive -LiteralPath $archive -DestinationPath $source -ErrorAction Stop
    $env:GOTOOLCHAIN = 'local'
    $env:GOTELEMETRY = 'off'
    $env:CGO_ENABLED = '0'
    $env:K_TERMINAL_EXECUTION_MODE = 'PAPER'
    # All original compilation takes place in a discarded temporary source copy.
    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File (Join-Path $source 'BUILD.ps1') *> (Join-Path $work 'private-build.log')
    if ($LASTEXITCODE -ne 0) { throw 'ORIGINAL_COMPLETE_WINDOWS_BUILD_FAILED' }
    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File (Join-Path $source 'verification\build-ui-runtime.ps1') *> (Join-Path $work 'private-ui-build.log')
    if ($LASTEXITCODE -ne 0) { throw 'ORIGINAL_UI_RUNTIME_BUILD_FAILED' }
    $executables = @(
        'K-Terminal.exe','K-Terminal-Engine.exe','K-Terminal-Account-Lookup.exe',
        'K-Terminal-Chart.exe','K-Terminal-Chart-History.exe',
        'K-Terminal-Subminute-Chart.exe','K-Terminal-Intelligence.exe',
        'K-Terminal-Notifications.exe'
    )
    foreach ($name in $executables) {
        $full = Join-Path $source $name
        if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw ('EXPECTED_BINARY_MISSING: ' + $name) }
        Copy-Item -LiteralPath $full -Destination (Join-Path $stage $name) -ErrorAction Stop
    }
    Copy-Item -LiteralPath (Join-Path $source 'KTerminal.UI.dll') -Destination $stage -ErrorAction Stop
    Copy-Item -LiteralPath (Join-Path $source 'ui-runtime-manifest.json') -Destination $stage -ErrorAction Stop
    Copy-Item -LiteralPath (Join-Path $source 'edition.json') -Destination $stage -ErrorAction Stop
    # Runtime script inventory only: no test, build, update or legacy naming.
    foreach ($file in Get-ChildItem -LiteralPath $source -Filter '*.ps1' -File) {
        if ($file.Name -match '^(BUILD|HEALTH|UPDATE-PROGRAM-FILES|apply-staged-update|launch-ktrade|test-)' ) { continue }
        Copy-Item -LiteralPath $file.FullName -Destination $stage -ErrorAction Stop
    }
    $readme = @'
RC2-F PORTABLE DIAGNOSTIC CANDIDATE — NOT APPROVED FOR USER EXECUTION
This is an isolated, source-pinned candidate, not a production upgrade.
No user data, Coinbase credentials, API secrets, order history, or active config
is included. The original installation must remain untouched.
Do not execute this package or add live credentials until runtime isolation is separately verified.
The private native full Windows regression was required to pass before build.
Original owner's desktop/UI acceptance and field latency measurements remain
separate requirements. Do not promote, auto-update, or submit live orders.
'@
    [IO.File]::WriteAllText((Join-Path $stage 'DIAGNOSTIC-READ-ME.txt'),$readme,[Text.UTF8Encoding]::new($false))
    $entries = @(Get-ChildItem -LiteralPath $stage -File | Sort-Object Name | ForEach-Object {
        [ordered]@{ file=$_.Name; bytes=$_.Length; sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant() }
    })
    $receipt = [ordered]@{
        schema='forge.kterminal.rc2f.portable-diagnostic.v1'
        candidate_sha=$candidate
        qualified_forge_workflow_sha=$forgeSha
        qualifying_run_id=$QualifiedRunId
        qualifying_conclusion='success'
        build_host='windows'
        go_version=$goVersion
        mode='UNINSTALLED_RUNTIME_NOT_QUALIFIED'
        desktop_acceptance='NOT_YET_QUALIFIED'
        runtime_no_live_order_guard='NOT_YET_QUALIFIED'
        release_approved=$false
        broker_credentials_used=$false
        user_data_copied=$false
        entries=$entries
    }
    $manifest = Join-Path $stage 'RC2F-MANIFEST.json'
    $receipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifest -Encoding UTF8 -ErrorAction Stop
    $destinationZip = Join-Path $outFull 'K-Terminal-RC2F-Portable-Diagnostic.zip'
    Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $destinationZip -CompressionLevel Optimal -ErrorAction Stop
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $destinationZip).Hash.ToLowerInvariant()
    $summary = [ordered]@{ zip=$destinationZip; sha256=$hash; source_sha=$candidate; files=($entries.Count+1); disposition='BUILT_NOT_RELEASED' }
    $summary | ConvertTo-Json -Compress
}
finally {
    # Remove transient build source, private compiler logs and transient package
    # after the output is produced. Never touch the original checkout or user's data.
    if (Test-Path -LiteralPath $work) { Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue }
}
