[CmdletBinding()]
param(
    [string]$RepoPath = (Join-Path $PSScriptRoot '..'),
    [switch]$UseUv
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Root = (Resolve-Path -LiteralPath $RepoPath).Path
$Manifest = Join-Path $Root '.ice/manifest.json'
$Structure = Join-Path $Root '.ice/structure.json'
$Evidence = Join-Path $Root '.ice/evidence-index.json'
if (-not (Test-Path -LiteralPath (Join-Path $Root 'go.mod') -PathType Leaf) -or
    -not (Test-Path -LiteralPath $Manifest -PathType Leaf) -or
    -not (Test-Path -LiteralPath $Structure -PathType Leaf) -or
    -not (Test-Path -LiteralPath $Evidence -PathType Leaf)) {
    throw 'FORGE_ICE_PUBLIC_SOURCE_MANIFEST_MISSING'
}
$Ice = Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json
if ($Ice.project -cne 'FORGE' -or $Ice.authority -cne 'advisory-navigation-only' -or
    $Ice.graphify.mode -cne 'code-only' -or
    $Ice.graphify.package -cne 'graphifyy' -or
    $Ice.graphify.version -cne '0.9.53') {
    throw 'FORGE_ICE_FROZEN_GRAPHIFY_IDENTITY_MISMATCH'
}
if ((& git -C $Root rev-parse --is-inside-work-tree).Trim() -cne 'true' -or
    $LASTEXITCODE -ne 0) {
    throw 'FORGE_ICE_GIT_CHECKOUT_REQUIRED'
}
$UseInstalled = $false
$Installed = Get-Command graphify -ErrorAction SilentlyContinue
if (-not $UseUv -and $Installed) { $UseInstalled = $true }
elseif (-not $UseUv) {
    $Uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($Uv) {
        $ToolDir = (& $Uv.Source tool dir --bin).Trim()
        foreach ($Candidate in @('graphify.exe','graphify')) {
            $ToolPath = Join-Path $ToolDir $Candidate
            if (Test-Path -LiteralPath $ToolPath -PathType Leaf) {
                $Installed = $ToolPath
                $UseInstalled = $true
                break
            }
        }
    }
}
if (-not $UseInstalled -and -not (Get-Command uvx -ErrorAction SilentlyContinue)) {
    throw 'FORGE_GRAPHIFY_0_9_53_NOT_INSTALLED_UVX_UNAVAILABLE'
}
function Invoke-PinnedGraphify {
    param([Parameter(Mandatory)][string[]]$Arguments)
    if ($UseInstalled) {
        $Binary = if ($Installed -is [string]) { $Installed } else { $Installed.Source }
        $Reply = & $Binary @Arguments
    } else {
        $Reply = & uvx --from 'graphifyy==0.9.53' graphify @Arguments
    }
    if ($LASTEXITCODE -ne 0) {
        throw 'FORGE_PINNED_GRAPHIFY_COMMAND_FAILED'
    }
    return $Reply
}
$env:GRAPHIFY_QUERY_LOG_DISABLE = '1'
$env:GRAPHIFY_QUERY_LOG_RESPONSES = '0'
$Version = @(Invoke-PinnedGraphify -Arguments @('--version')) -join ' '
if ($Version -notmatch '0\.9\.53') { throw "FORGE_GRAPHIFY_VERSION_DRIFT: $Version" }
$Derived = Join-Path $Root '.ice/derived'
$Graph = Join-Path $Derived 'graphify'
$Vault = Join-Path $Derived 'obsidian'
New-Item -ItemType Directory -Force -Path $Graph,$Vault | Out-Null

Push-Location $Root
try {
    # Do not invoke semantic extraction. Code-only uses local syntax trees,
    # not model keys, private Mind-Palace retrieval, or paid model calls.
    Invoke-PinnedGraphify -Arguments @('extract','.','--code-only','--force') | Out-Null
    $Extracted = Join-Path $Root 'graphify-out/graph.json'
    if (-not (Test-Path -LiteralPath $Extracted -PathType Leaf)) {
        throw 'FORGE_GRAPHIFY_CODE_GRAPH_MISSING'
    }
    $GraphTarget = Join-Path $Graph 'graph.json'
    Copy-Item -LiteralPath $Extracted -Destination $GraphTarget -Force

    # Graphify's own Obsidian manifest controls its generated files; this is
    # a dedicated FORGE path and never the user's existing Obsidian vault.
    Invoke-PinnedGraphify -Arguments @('export','obsidian','--graph',$GraphTarget,'--dir',$Vault) | Out-Null
    $Files = @(Get-ChildItem -LiteralPath $Vault -Filter '*.md' -File -Recurse)
    if ($Files.Count -eq 0) { throw 'FORGE_GRAPHIFY_OBSIDIAN_EXPORT_EMPTY' }

    $SourceHead = (& git -C $Root rev-parse HEAD).Trim()
    $SourceTree = (& git -C $Root rev-parse 'HEAD^{tree}').Trim()
    if ($LASTEXITCODE -ne 0 -or $SourceHead -notmatch '^[0-9a-f]{40}$' -or
        $SourceTree -notmatch '^[0-9a-f]{40}$') {
        throw 'FORGE_GRAPHIFY_GIT_SOURCE_IDENTITY_MISSING'
    }
    $Digest = (Get-FileHash -LiteralPath $GraphTarget -Algorithm SHA256).Hash.ToLowerInvariant()
    $Record = [ordered]@{
        schema = 'forge.ice.graphify-derived.v1'
        source_commit = $SourceHead
        source_tree = $SourceTree
        graph_sha256 = $Digest
        version = $Version
        extraction = 'code-only'
        no_model_calls = $true
        evidence_authority = 'advisory_only'
        originals_archived = $false
        scientific_execution_authorized = $false
    }
    $Record | ConvertTo-Json -Depth 4 |
        Set-Content -LiteralPath (Join-Path $Graph 'build.json') -Encoding UTF8
    Write-Output "FORGE_ICE_GRAPHIFY_BUILD=PASS code_only=true graph_sha256=$Digest obsidian_notes=$($Files.Count) authority=false"
} finally {
    Pop-Location
}
