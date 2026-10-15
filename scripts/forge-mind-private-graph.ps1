#requires -Version 5.1
<#
FORGE private .ice -> provenance graph -> Obsidian and optional Graphify.
No scheduler, controller, mutation, paid API or external graph calls by default.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PrivateOutput,
    [switch]$RunGraphify,
    [switch]$ExplicitlyAllowExternalSemanticAnalysis
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not [System.IO.Path]::IsPathRooted($PrivateOutput)) {
    throw 'FORGE_GRAPH_OUTPUT_MUST_BE_ABSOLUTE'
}
if (Test-Path -LiteralPath $PrivateOutput) {
    throw 'FORGE_GRAPH_EXISTING_VAULT_NEVER_OVERWRITTEN'
}
if (-not (Get-Command 'go' -ErrorAction SilentlyContinue)) {
    throw 'FORGE_GRAPH_GO_NOT_INSTALLED'
}
if ([string]::IsNullOrWhiteSpace($env:FORGE_MIND_PALACE_READ_TOKEN)) {
    throw 'FORGE_GRAPH_FINE_GRAINED_MIND_PALACE_READ_TOKEN_REQUIRED'
}
& go run ./cmd/forge-mind-graph -out $PrivateOutput
if ($LASTEXITCODE -ne 0) {
    throw ('FORGE_GRAPH_PRIVATE_READ_OR_EXPORT_FAILED exit=' + $LASTEXITCODE)
}
Write-Output 'FORGE_PRIVATE_ICE_AND_OBSIDIAN_READY=PASS'
Write-Output ('FORGE_OBSIDIAN_VAULT=' + (Join-Path $PrivateOutput 'obsidian'))
Write-Output ('FORGE_GRAPHIFY_PRIVATE_INPUT=' + (Join-Path $PrivateOutput 'graphify-input'))

if ($RunGraphify) {
    if (-not $ExplicitlyAllowExternalSemanticAnalysis) {
        throw 'FORGE_GRAPHIFY_REQUIRES_EXPLICIT_BACKEND_PRIVACY_APPROVAL'
    }
    $bin = Get-Command 'graphify' -ErrorAction SilentlyContinue
    if (-not $bin) {
        throw 'FORGE_GRAPHIFY_NOT_INSTALLED_USE_OFFICIAL_GRAPHIFYY_LOCAL_INSTALL'
    }
    # Important: vendor CLI has no need for private GitHub credentials.
    Remove-Item Env:FORGE_MIND_PALACE_READ_TOKEN -ErrorAction SilentlyContinue
    $source = Join-Path $PrivateOutput 'graphify-input'
    & graphify $source --no-viz --no-label
    if ($LASTEXITCODE -ne 0) { throw 'FORGE_GRAPHIFY_PRIVATE_GRAPH_BUILD_FAILED' }
    $graph = Join-Path (Join-Path $source 'graphify-out') 'graph.json'
    if (-not (Test-Path -LiteralPath $graph)) {
        throw 'FORGE_GRAPHIFY_GRAPH_JSON_MISSING'
    }
    # Never merge into an existing personal Obsidian vault. Keep third-party
    # generated notes isolated from the native, independently verified notes.
    $vault = Join-Path $PrivateOutput 'graphify-obsidian'
    if (Test-Path -LiteralPath $vault) {
        throw 'FORGE_GRAPHIFY_EXISTING_VAULT_NEVER_OVERWRITTEN'
    }
    & graphify export obsidian --graph $graph --dir $vault
    if ($LASTEXITCODE -ne 0) { throw 'FORGE_GRAPHIFY_OBSIDIAN_EXPORT_FAILED' }
    Write-Output ('FORGE_OPTIONAL_GRAPHIFY_OBSIDIAN_VAULT=' + $vault)
}
