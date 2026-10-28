[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if($env:RUNNER_OS -cne 'Windows' -or $env:RUNNER_ENVIRONMENT -cne 'self-hosted' -or $env:RUNNER_NAME -cne 'FORGE-CODEX-REMOTE'){throw 'GUI_REQUIRES_EXACT_AUTHORIZED_WINDOWS_RUNNER'}
if(-not [Environment]::UserInteractive){throw 'GUI_NO_INTERACTIVE_DESKTOP'}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$exe=@(
 (Join-Path $env:LOCALAPPDATA 'Programs/Obsidian/Obsidian.exe'),
 (Join-Path $env:LOCALAPPDATA 'Obsidian/Obsidian.exe'),
 (Join-Path $env:ProgramFiles 'Obsidian/Obsidian.exe')
)|Where-Object{Test-Path -LiteralPath $_ -PathType Leaf}|Select-Object -First 1
if(-not $exe){throw 'GUI_OBSIDIAN_INSTALLED_EXE_REQUIRED'}
$existing=@(Get-Process -Name Obsidian -ErrorAction SilentlyContinue)
if($existing.Count -gt 0){throw 'GUI_OTHER_OBSIDIAN_PROCESS_NOT_SAFE_TO_ISOLATE'}
$who=(& gh api user --jq .login 2>$null | Out-String).Trim()
if($LASTEXITCODE -ne 0 -or $who -cne 'spoonman136668-ai'){throw 'GUI_WRONG_GITHUB_IDENTITY'}
$script=Join-Path $env:GITHUB_WORKSPACE 'tools/qualification/forge_current_obsidian_cdp.py'
if(-not(Test-Path -LiteralPath $script -PathType Leaf)){throw 'GUI_RENDERER_DRIVER_MISSING'}
$specs=@(
 [ordered]@{name='FORGE';short='f';repository='spoonman136668-ai/forge-knowledge';commit='3eaa9f770de2aef93efbefc6e4ea24a492c87570';source='d8bccc604f8607bf10f9d8bc6aa568d1f98af559';notes=7072;sha='b94fc532ed96dea7531cabcc974f99bb25e67e73f286924dcc9fab96fe41778e'}
)
$root=Join-Path $env:SystemDrive ('agui'+$env:GITHUB_RUN_ID)
if(Test-Path -LiteralPath $root){throw 'GUI_SCRATCH_COLLISION'}
$null=New-Item -ItemType Directory -Path $root
$env:GIT_TERMINAL_PROMPT='0'
$env:PYTHONDONTWRITEBYTECODE='1'
try{
 $projectIndex=0
 foreach($s in $specs){
  $projectIndex++
  $group=$s.name.ToUpperInvariant()
  $proj=Join-Path $root $s.short
  $null=New-Item -ItemType Directory -Path $proj
  $repo=Join-Path $proj 'knowledge'
  $log=Join-Path $proj 'private.log'
  $launchedIds=[System.Collections.Generic.HashSet[int]]::new()
  try{
   if(@(Get-Process -Name Obsidian -ErrorAction SilentlyContinue).Count -ne 0){throw 'GUI_OBSIDIAN_PREVIOUS_PROJECT_NOT_CLEANED'}
   $private=(& gh repo view $s.repository --json isPrivate --jq .isPrivate 2>$null | Out-String).Trim()
   if($LASTEXITCODE -ne 0 -or $private -cne 'true'){throw 'GUI_PRIVATE_REPOSITORY_NOT_VERIFIED'}
   & git -c core.longpaths=true -c 'credential.helper=!gh auth git-credential' clone --no-checkout --filter=blob:none ('https://github.com/'+$s.repository+'.git') $repo *> $log
   if($LASTEXITCODE -ne 0){throw 'GUI_PINNED_KNOWLEDGE_CLONE_FAILED'}
   & git -C $repo config core.longpaths true
   & git -C $repo sparse-checkout init --cone *> $log
   if($LASTEXITCODE -ne 0){throw 'GUI_SPARSE_INIT_FAILED'}
   & git -C $repo sparse-checkout set Graphify/Source Graphify/Obsidian *> $log
   if($LASTEXITCODE -ne 0){throw 'GUI_SPARSE_SET_FAILED'}
   & git -C $repo checkout --detach $s.commit *> $log
   if($LASTEXITCODE -ne 0 -or (git -C $repo rev-parse HEAD).Trim() -cne $s.commit){throw 'GUI_PINNED_KNOWLEDGE_COMMIT_DRIFT'}
   $vault=Join-Path $repo 'Graphify/Obsidian'
   $metadata=Join-Path $repo 'Graphify/Source/LAST-BUILD.json'
   $graph=Join-Path $repo 'Graphify/Source/graph.json'
   if(-not(Test-Path -LiteralPath $metadata -PathType Leaf) -or -not(Test-Path -LiteralPath $graph -PathType Leaf)){throw 'GUI_METADATA_OR_GRAPH_MISSING'}
   $info=Get-Content -LiteralPath $metadata -Raw | ConvertFrom-Json
   if($info.source_commit -cne $s.source -or $info.source_repo -cne ('spoonman136668-ai/'+$s.name) -or $info.mode -cne 'code-only' -or $info.scientific_authority -ne $false){throw 'GUI_SOURCE_OR_AUTHORITY_MISMATCH'}
   $hash=(Get-FileHash -LiteralPath $graph -Algorithm SHA256).Hash.ToLowerInvariant()
   if($hash -cne $s.sha -or $info.graph_sha256 -cne $hash){throw 'GUI_GRAPH_HASH_DRIFT'}
   $count=@(Get-ChildItem -LiteralPath $vault -Recurse -File -Filter '*.md').Count
   if($count -ne $s.notes){throw 'GUI_PINNED_VAULT_COUNT_DRIFT'}
   Write-Host ('ADVISORY_GUI_'+$group+'_PINNED_COMMIT='+$s.commit)
   Write-Host ('ADVISORY_GUI_'+$group+'_COMMITTED_VAULT=PASS')
   $roaming=Join-Path $proj 'profile/Roaming'
   $local=Join-Path $proj 'profile/Local'
   $userData=Join-Path $roaming 'obsidian'
   $null=New-Item -ItemType Directory -Force -Path $userData,$local
   $vaultId='0a4b9d2f0a4b9d2f'
   $cfg=[ordered]@{vaults=@{$vaultId=@{path=$vault;ts=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds();open=$true}}}
   ($cfg|ConvertTo-Json -Depth 8)|Set-Content -LiteralPath (Join-Path $userData 'obsidian.json') -Encoding utf8
   $psi=[System.Diagnostics.ProcessStartInfo]::new($exe)
   $psi.WorkingDirectory=Split-Path -Parent $exe
   $psi.UseShellExecute=$false
   $psi.Environment['APPDATA']=$roaming
   $psi.Environment['LOCALAPPDATA']=$local
   $port=40000+(([long]$env:GITHUB_RUN_ID+($projectIndex*7919))%15000)
   [void]$psi.ArgumentList.Add('--user-data-dir='+$userData)
   [void]$psi.ArgumentList.Add('--force-renderer-accessibility')
   [void]$psi.ArgumentList.Add('--remote-debugging-port='+$port)
   [void]$psi.ArgumentList.Add('--remote-debugging-address=127.0.0.1')
   $process=[System.Diagnostics.Process]::Start($psi)
   if($null -eq $process){throw 'GUI_START_FAILED'}
   [void]$launchedIds.Add($process.Id)
   $win=$null
   $watch=[Diagnostics.Stopwatch]::StartNew()
   while($watch.Elapsed.TotalSeconds -lt 90){
     foreach($p in @(Get-Process -Name Obsidian -ErrorAction SilentlyContinue)){
       if($p.SessionId -eq [Diagnostics.Process]::GetCurrentProcess().SessionId -and $p.MainWindowHandle -ne [IntPtr]::Zero){
         $win=$p
         [void]$launchedIds.Add($p.Id)
         break
       }
     }
     if($null -ne $win){break}
     Start-Sleep -Milliseconds 500
   }
   if($null -eq $win){throw 'GUI_REAL_OBSIDIAN_WINDOW_NOT_FOUND'}
   $uia=[System.Windows.Automation.AutomationElement]::FromHandle($win.MainWindowHandle)
   if($null -eq $uia){throw 'GUI_NO_UI_AUTOMATION_WINDOW'}
   Write-Host ('ADVISORY_GUI_'+$group+'_REAL_WINDOW=PASS')
   & python -B $script --project $s.name --port $port --notes $s.notes
   if($LASTEXITCODE -ne 0){throw ('GUI_'+$group+'_NOTE_OR_SEARCH_FAILED')}
   Write-Host ('ADVISORY_GUI_'+$group+'_FULL_DESKTOP=PASS')
  } finally {
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
   # All started processes were isolated to a disposable profile. Never close
   # or kill a process that was not recorded for this project.
   Remove-Item -LiteralPath $proj -Recurse -Force -ErrorAction SilentlyContinue
   Write-Host ('ADVISORY_GUI_'+$group+'_ISOLATED_CLEANUP_REQUESTED=TRUE')
  }
 }
 Write-Host 'FORGE_CURRENT_GUI_EXACT_PRIVATE_VAULT=PASS'
} finally {
 Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}