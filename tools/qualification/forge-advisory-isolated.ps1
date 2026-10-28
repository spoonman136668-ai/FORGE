[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$owner='spoonman136668-ai'
$source='3775bed30891ff748197a539afe5b92813680e26'
$destination='spoonman136668-ai/forge-knowledge'
if($env:RUNNER_OS -cne 'Windows' -or $env:RUNNER_ENVIRONMENT -cne 'self-hosted'){throw 'FORGE_WRONG_RUNNER'}
$who=(& gh api user --jq .login 2>$null | Out-String).Trim()
if($LASTEXITCODE -ne 0 -or $who -cne $owner){throw 'FORGE_WRONG_ACCOUNT'}
& gh repo view $destination --json nameWithOwner *> $null
if($LASTEXITCODE -eq 0){throw 'FORGE_DESTINATION_ALREADY_PRESENT_STOP_NO_OVERWRITE'}
$env:GRAPHIFY_QUERY_LOG_DISABLE='1'
$env:GRAPHIFY_QUERY_LOG_RESPONSES='0'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:GIT_TERMINAL_PROMPT='0'
foreach($k in @('COINBASE_API_KEY','COINBASE_API_SECRET','API_KEY','API_SECRET')){
  [Environment]::SetEnvironmentVariable($k,$null,'Process')
}
$root=Join-Path $env:SystemDrive ('fka'+$env:GITHUB_RUN_ID)
if(Test-Path -LiteralPath $root){throw 'FORGE_SCRATCH_EXISTS'}
$null=New-Item -ItemType Directory -Path $root
$s=Join-Path $root 's'
$d=Join-Path $root 'd'
$log=Join-Path $root 'private.log'
try{
  & git clone --no-checkout --filter=blob:none 'https://github.com/spoonman136668-ai/FORGE.git' $s *> $log
  if($LASTEXITCODE -ne 0){throw 'FORGE_CLONE_FAILED'}
  & git -C $s config core.longpaths true
  & git -C $s checkout --detach $source *> $log
  if($LASTEXITCODE -ne 0 -or (git -C $s rev-parse HEAD).Trim() -cne $source){throw 'FORGE_SOURCE_PIN_FAILED'}
  $main=((& git -C $s ls-remote origin refs/heads/main | Out-String).Trim() -split '\s+')[0]
  if($main -cne $source){throw 'FORGE_MAIN_MOVED'}
  if(@(git -C $s status --porcelain --untracked-files=no).Count -gt 0){throw 'FORGE_SOURCE_DIRTY'}
  Write-Host 'FORGE_SOURCE_MAIN_EXACT_PIN=PASS'
  $uvx=Get-Command uvx -ErrorAction SilentlyContinue
  if($uvx){$exe=$uvx.Source}else{
    $u=Join-Path $root 'uv'
    $null=New-Item -ItemType Directory -Path $u
    & python -m pip install --disable-pip-version-check --no-input --target $u 'uv==0.9.7' *> $log
    if($LASTEXITCODE -ne 0){throw 'FORGE_UV_INSTALL_FAILED'}
    $tool=Get-ChildItem -LiteralPath $u -Recurse -File -Filter uvx.exe | Select-Object -First 1
    if($null -eq $tool){throw 'FORGE_UVX_MISSING'}
    $exe=$tool.FullName
  }
  $ver=(& $exe --from 'graphifyy==0.9.53' graphify --version 2>$null | Out-String).Trim()
  if($LASTEXITCODE -ne 0 -or $ver -notmatch '0\.9\.53'){throw 'FORGE_GRAPHIFY_VERSION_MISMATCH'}
  Push-Location $s
  try{
    & $exe --from 'graphifyy==0.9.53' graphify extract . --code-only --force *> $log
    if($LASTEXITCODE -ne 0){throw 'FORGE_EXTRACT_FAILED'}
    $graph=Join-Path $s 'graphify-out/graph.json'
    if(-not(Test-Path -LiteralPath $graph -PathType Leaf)){throw 'FORGE_GRAPH_MISSING'}
    $vault=Join-Path $root 'vault'
    & $exe --from 'graphifyy==0.9.53' graphify export obsidian --graph $graph --dir $vault *> $log
    if($LASTEXITCODE -ne 0){throw 'FORGE_EXPORT_FAILED'}
  }finally{Pop-Location}
  $notes=@(Get-ChildItem -LiteralPath $vault -Recurse -File -Filter '*.md')
  $bytes=($notes|Measure-Object -Property Length -Sum).Sum
  if($notes.Count -lt 1 -or $notes.Count -gt 10000 -or $bytes -gt 100000000 -or (Get-Item -LiteralPath $graph).Length -gt 100000000){throw 'FORGE_OUTPUT_BOUNDS'}
  $manifest=Join-Path $vault '.graphify_obsidian_manifest.json'
  if(-not(Test-Path -LiteralPath $manifest -PathType Leaf)){throw 'FORGE_MANIFEST_MISSING'}
  $null=Get-Content -LiteralPath $manifest -Raw|ConvertFrom-Json
  $null=Get-Content -LiteralPath $graph -Raw|ConvertFrom-Json
  $pattern='-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|github_pat_[A-Za-z0-9_]{70,}|ghp_[A-Za-z0-9]{36}|AKIA[0-9A-Z]{16}'
  foreach($file in (@($notes)+@((Get-Item -LiteralPath $graph)))){
    if((Get-Content -LiteralPath $file.FullName -Raw) -match $pattern){throw 'FORGE_PRIVATE_CONTENT_REJECTED'}
  }
  $hash=(Get-FileHash -LiteralPath $graph -Algorithm SHA256).Hash.ToLowerInvariant()
  $main=((& git -C $s ls-remote origin refs/heads/main | Out-String).Trim() -split '\s+')[0]
  if($main -cne $source){throw 'FORGE_MAIN_CHANGED_DURING_GENERATION'}
  Write-Host 'FORGE_GRAPHIFY_CURRENT_MAIN_CODE_ONLY=PASS'
  Write-Host ('FORGE_GRAPHIFY_GRAPH_SHA256='+$hash)
  Write-Host ('FORGE_GRAPHIFY_NOTE_COUNT='+$notes.Count)
  & gh repo create $destination --private --disable-issues --disable-wiki --description 'Read-only source-pinned FORGE Graphify navigation' *> $log
  if($LASTEXITCODE -ne 0){throw 'FORGE_PRIVATE_REPO_CREATE_FAILED'}
  $private=(& gh repo view $destination --json isPrivate --jq .isPrivate 2>$null | Out-String).Trim()
  if($LASTEXITCODE -ne 0 -or $private -cne 'true'){throw 'FORGE_DESTINATION_NOT_PRIVATE'}
  Write-Host 'FORGE_INDEPENDENT_PRIVATE_DESTINATION=PASS'
  $null=New-Item -ItemType Directory -Force (Join-Path $d 'Graphify/Source'),(Join-Path $d 'Graphify/Obsidian')
  Copy-Item -LiteralPath $graph -Destination (Join-Path $d 'Graphify/Source/graph.json')
  Copy-Item -Path (Join-Path $vault '*') -Destination (Join-Path $d 'Graphify/Obsidian') -Recurse -Force
  foreach($name in @('.graphify_obsidian_manifest.json','.obsidian')){
    $p=Join-Path $vault $name
    if(Test-Path -LiteralPath $p){Copy-Item -LiteralPath $p -Destination (Join-Path $d 'Graphify/Obsidian') -Recurse -Force}
  }
  $record=[ordered]@{schema='research.advisory-graphify.v1';source_repo='spoonman136668-ai/FORGE';source_branch='main';source_commit=$source;graphify_version='0.9.53';mode='code-only';model_calls=0;graph_sha256=$hash;obsidian_notes=$notes.Count;authority='advisory_navigation_only';scientific_authority=$false;promotion_authorized=$false}
  $record|ConvertTo-Json -Depth 4|Set-Content -LiteralPath (Join-Path $d 'Graphify/Source/LAST-BUILD.json') -Encoding utf8
  $readme=@('# FORGE read-only code knowledge','',('Source main commit: '+$source),('Graph SHA-256: '+$hash),('Obsidian notes: '+$notes.Count),'','Generated code-only advisory navigation. No scientific, execution, release, model-training, or native ICE Atlas authority. Independent artifact/link/GUI qualification remains outstanding.')
  $readme|Set-Content -LiteralPath (Join-Path $d 'README.md') -Encoding utf8
  & git -C $d init --initial-branch=main *> $log
  if($LASTEXITCODE -ne 0){throw 'FORGE_GIT_INIT_FAILED'}
  & git -C $d config core.longpaths true
  & git -C $d add -A *> $log
  if($LASTEXITCODE -ne 0){throw 'FORGE_STAGE_FAILED'}
  & git -C $d -c user.name='FORGE advisory qualifier' -c user.email='41898282+github-actions[bot]@users.noreply.github.com' commit -m ('Pin FORGE main advisory Graphify '+$source) *> $log
  if($LASTEXITCODE -ne 0){throw 'FORGE_COMMIT_FAILED'}
  & git -C $d remote add origin ('https://github.com/'+$destination+'.git')
  & git -C $d -c 'credential.helper=!gh auth git-credential' push -u origin main *> $log
  if($LASTEXITCODE -ne 0){throw 'FORGE_PUSH_FAILED'}
  $local=(& git -C $d rev-parse HEAD | Out-String).Trim()
  $remote=((& git -C $d -c 'credential.helper=!gh auth git-credential' ls-remote origin refs/heads/main | Out-String).Trim() -split '\s+')[0]
  if($local -cne $remote){throw 'FORGE_REMOTE_SHA_MISMATCH'}
  Write-Host ('FORGE_PRIVATE_KNOWLEDGE_HEAD='+$remote)
  Write-Host 'FORGE_PRIVATE_KNOWLEDGE_PUBLISHED=PASS'
  Write-Host 'FORGE_NATIVE_ATLAS_AND_MAIN_UNMODIFIED=PASS'
}finally{
  Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
  Write-Host 'FORGE_TEMPORARY_SCRATCH_CLEANUP_REQUESTED=TRUE'
}