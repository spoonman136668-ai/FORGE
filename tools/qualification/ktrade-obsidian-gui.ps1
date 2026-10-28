[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$KnowledgeCommit,
  [Parameter(Mandatory=$true)][string]$KtradeSource
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$expectedTree='01c75c3f7d6f3ad5428e8694cd51e6c224ac9357'
$expectedSource='a359e86d05e5ba24b71a1f4bdd8a5e36ebd31b58'
if($KtradeSource -cne $expectedSource){throw 'GUI_SOURCE_IDENTITY_DRIFT'}
if($env:RUNNER_OS -cne 'Windows' -or $env:RUNNER_ENVIRONMENT -cne 'self-hosted'){throw 'GUI_WRONG_RUNNER'}
if(-not [Environment]::UserInteractive){throw 'GUI_NONINTERACTIVE_SESSION'}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$before=@(Get-Process -Name Obsidian -ErrorAction SilentlyContinue)
if($before.Count -ne 0){throw 'GUI_OBSIDIAN_ALREADY_RUNNING_NOT_SAFE_TO_ISOLATE'}
$knownPaths=@(
  (Join-Path $env:LOCALAPPDATA 'Programs/Obsidian/Obsidian.exe'),
  (Join-Path $env:LOCALAPPDATA 'Obsidian/Obsidian.exe'),
  (Join-Path $env:ProgramFiles 'Obsidian/Obsidian.exe')
)
$app=@($knownPaths|Where-Object{Test-Path -LiteralPath $_ -PathType Leaf}|Select-Object -First 1)
if($app.Count -ne 1){throw 'GUI_OBSIDIAN_INSTALLED_EXE_REQUIRED'}
$exe=$app[0]
$version=(Get-Item -LiteralPath $exe).VersionInfo.ProductVersion
$exeHash=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
if([string]::IsNullOrWhiteSpace($version)){throw 'GUI_OBSIDIAN_VERSION_UNKNOWN'}
Write-Host 'KTRADE_GUI_OBSIDIAN_INSTALLED=PASS'
Write-Host ('KTRADE_GUI_OBSIDIAN_VERSION='+$version)
Write-Host ('KTRADE_GUI_OBSIDIAN_EXE_SHA256='+$exeHash)
$root=Join-Path $env:SystemDrive ('kgui'+$env:GITHUB_RUN_ID)
if(Test-Path -LiteralPath $root){throw 'GUI_SCRATCH_COLLISION'}
$null=New-Item -ItemType Directory -Path $root
$repo=Join-Path $root 'k'
$log=Join-Path $root 'checkout.log'
$launchedIds=[System.Collections.Generic.HashSet[int]]::new()
try{
  $env:GIT_TERMINAL_PROMPT='0'
  & git -c core.longpaths=true -c 'credential.helper=!gh auth git-credential' clone --no-checkout --filter=blob:none 'https://github.com/spoonman136668-ai/ktrade-knowledge.git' $repo *> $log
  if($LASTEXITCODE -ne 0){throw 'GUI_KNOWLEDGE_CLONE_FAILED'}
  & git -C $repo config core.longpaths true
  & git -C $repo sparse-checkout init --cone *> $log
  if($LASTEXITCODE -ne 0){throw 'GUI_SPARSE_INIT_FAILED'}
  & git -C $repo sparse-checkout set Graphify/Obsidian *> $log
  if($LASTEXITCODE -ne 0){throw 'GUI_SPARSE_SET_FAILED'}
  & git -C $repo checkout --detach $KnowledgeCommit *> $log
  if($LASTEXITCODE -ne 0){throw 'GUI_PINNED_CHECKOUT_FAILED'}
  if((git -C $repo rev-parse HEAD).Trim() -cne $KnowledgeCommit){throw 'GUI_HEAD_IDENTITY_DRIFT'}
  $tree=(git -C $repo rev-parse ($KnowledgeCommit+':Graphify/Obsidian')).Trim()
  if($tree -cne $expectedTree){throw 'GUI_OBSIDIAN_TREE_DRIFT'}
  $vault=Join-Path $repo 'Graphify/Obsidian'
  $note=Join-Path $vault '002865cd06_test.go.md'
  if(-not(Test-Path -LiteralPath $note -PathType Leaf)){throw 'GUI_NOTE_NOT_IN_COMMITTED_VAULT'}
  if(-not ((Get-Content -LiteralPath $note -Raw).Contains('TestStrategy_Phase7_T764_ClosedTrades'))){throw 'GUI_KNOWN_NOTE_CONTENT_DRIFT'}
  $noteCount=@(Get-ChildItem -LiteralPath $vault -Recurse -File -Filter '*.md').Count
  if($noteCount -ne 39973){throw 'GUI_PINNED_VAULT_NOTE_COUNT_DRIFT'}
  Write-Host ('KTRADE_GUI_KNOWLEDGE_COMMIT='+$KnowledgeCommit)
  Write-Host ('KTRADE_GUI_OBSIDIAN_TREE='+$tree)
  Write-Host 'KTRADE_GUI_39973_COMMITTED_NOTES=PASS'

  $roaming=Join-Path $root 'profile/Roaming'
  $local=Join-Path $root 'profile/Local'
  $userData=Join-Path $roaming 'obsidian'
  $null=New-Item -ItemType Directory -Path $userData,$local -Force
  $vaultId='0a4b9d2f0a4b9d2f'
  $cfg=[ordered]@{vaults=@{$vaultId=@{path=$vault;ts=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds();open=$true}}}
  ($cfg|ConvertTo-Json -Depth 8)|Set-Content -LiteralPath (Join-Path $userData 'obsidian.json') -Encoding utf8
  $psi=[System.Diagnostics.ProcessStartInfo]::new($exe)
  $psi.WorkingDirectory=Split-Path -Parent $exe
  $psi.UseShellExecute=$false
  $psi.Environment['APPDATA']=$roaming
  $psi.Environment['LOCALAPPDATA']=$local
  $null=$psi.ArgumentList.Add('--user-data-dir='+$userData)
  $null=$psi.ArgumentList.Add('--force-renderer-accessibility')
  $port=40000+([int]$env:GITHUB_RUN_ID % 15000)
  $null=$psi.ArgumentList.Add('--remote-debugging-port='+$port)
  $null=$psi.ArgumentList.Add('--remote-debugging-address=127.0.0.1')
  $watch=[System.Diagnostics.Stopwatch]::StartNew()
  $launcher=[System.Diagnostics.Process]::Start($psi)
  if($null -eq $launcher){throw 'GUI_START_PROCESS_FAILED'}
  [void]$launchedIds.Add($launcher.Id)
  Write-Host 'KTRADE_GUI_ISOLATED_OBSIDIAN_LAUNCH=STARTED'

  $window=$null
  $windowWait=[System.Diagnostics.Stopwatch]::StartNew()
  while($windowWait.Elapsed.TotalSeconds -lt 180){
    $ps=@(Get-Process -Name Obsidian -ErrorAction SilentlyContinue)
    foreach($p in $ps){
      if($p.MainWindowHandle -ne [IntPtr]::Zero -and $p.SessionId -eq [Diagnostics.Process]::GetCurrentProcess().SessionId){
        $window=$p;[void]$launchedIds.Add($p.Id);break
      }
    }
    if($null -ne $window){break}
    Start-Sleep -Milliseconds 750
  }
  if($null -eq $window){throw 'GUI_NO_REAL_OBSIDIAN_WINDOW_180S'}
  $handle=$window.MainWindowHandle
  $uia=[System.Windows.Automation.AutomationElement]::FromHandle($handle)
  if($null -eq $uia){throw 'GUI_NO_OBSIDIAN_ACCESSIBLE_WINDOW'}
  Write-Host ('KTRADE_GUI_REAL_WINDOW_OPEN_SECONDS='+([Math]::Round($windowWait.Elapsed.TotalSeconds,2)))
  Write-Host 'KTRADE_GUI_REAL_DESKTOP_WINDOW=PASS'

  $cdp=Join-Path $env:GITHUB_WORKSPACE 'tools/qualification/ktrade_obsidian_cdp.py'
  if(-not (Test-Path -LiteralPath $cdp -PathType Leaf)){throw 'GUI_CDP_HARNESS_MISSING'}
  & python -B $cdp --port $port
  if($LASTEXITCODE -ne 0){throw 'GUI_ACTUAL_RENDERER_NAVIGATION_OR_SEARCH_FAILED'}
  Write-Host 'KTRADE_GUI_RENDERER_INTERACTION=PASS'
  Write-Host ('KTRADE_GUI_FULL_VAULT_SECONDS='+([Math]::Round($watch.Elapsed.TotalSeconds,2)))
  Write-Host 'KTRADE_GUI_TEST_PASS_READ_ONLY_REVIEW_ONLY'
}finally{
  foreach($p in @(Get-Process -Name Obsidian -ErrorAction SilentlyContinue)){
    if($launchedIds.Contains($p.Id)){
      try{$p.CloseMainWindow()|Out-Null}catch{}
    }
  }
  Start-Sleep -Seconds 2
  foreach($p in @(Get-Process -Name Obsidian -ErrorAction SilentlyContinue)){
    if($launchedIds.Contains($p.Id)){
      try{Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue}catch{}
    }
  }
  Remove-Item -LiteralPath $root -Force -Recurse -ErrorAction SilentlyContinue
  Write-Host 'KTRADE_GUI_TEMPORARY_VAULT_CLEANUP=REQUESTED'
}
