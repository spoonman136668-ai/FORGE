# ONE bounded F139 original-owner cutover, executed only by the existing SID-matched
# Windows self-hosted runner. Default is read-only. No manual worker dispatch.
[CmdletBinding()]
param([switch]$Apply)
$ErrorActionPreference='Stop'
$old='5662e3586bc9d12c90033b7c0344ca65ea1ad2a0'
$new='09f3d7447900f99dd3d532c5d3d90ed7e8c20ac3'
$tree='995ee30ad858b53c6734d8af3c0b305651dbf8d2'
$head47='75b24554b43cf1ea807810d9d98bd28a3f2c08585f8a9b811ae62f0c2ad74c4b'
$prefix23='eea95c859f9a59f700612c3b7b39152abc78827981976e9d86567c29fa03ff87'
$repo='spoonman136668-ai/FORGE'
$name='FORGE-F139-UnifiedController'
$db=Join-Path $env:LOCALAPPDATA 'FORGE-F139\state.sqlite'
$dest=Join-Path $env:LOCALAPPDATA ('FORGE-F139-A8\source-'+$new.Substring(0,12))
$transitionApproval=$null
$stopped=$false
function Arg([string]$all,[string]$n) {
  $m=[regex]::Matches($all,'(?i)(?:^|\s)-'+[regex]::Escape($n)+'\s+"([^"]+)"')
  if($m.Count -ne 1) { throw 'F139_A8_TASK_ARG_INVALID' }
  return $m[0].Groups[1].Value
}
function Status([string]$python,[string]$root) {
  Push-Location $root
  try {
    $data=& $python -B -m f139.local_controller --db $db status
    if($LASTEXITCODE -ne 0) { throw 'F139_A8_LEDGER_STATUS_INVALID' }
    return (($data -join [Environment]::NewLine) | ConvertFrom-Json).status
  } finally {Pop-Location}
}
function RequireStatus($state,[string]$expected,[int]$count) {
  if($state.meta.source_sha -cne $expected -or
     [int]$state.meta.head_seq -ne $count -or
     [int]$state.meta.enabled -ne 1 -or
     [int]$state.meta.legacy_suspended -ne 1) {
    throw 'F139_A8_SOURCE_OR_LEDGER_SEQUENCE_DRIFT'
  }
}
try {
  if([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'F139_A8_WINDOWS_ONLY' }
  $task=Get-ScheduledTask -TaskName $name -ErrorAction Stop
  $who=[Security.Principal.WindowsIdentity]::GetCurrent()
  $principal=[string]$task.Principal.UserId
  $sid=try { (New-Object Security.Principal.NTAccount($principal)).Translate(
    [Security.Principal.SecurityIdentifier]).Value } catch { '' }
  if($principal -ine $who.Name -and $sid -ne $who.User.Value) { throw 'F139_A8_NOT_OWNER_SID' }
  if(@($task.Actions).Count -ne 1 -or $task.State -notin @('Ready','Running')) {throw 'F139_A8_ORIGINAL_TASK_INCORRECT'}
  if([IO.Path]::GetFileName([string]$task.Actions[0].Execute) -ine 'powershell.exe') {
    throw 'F139_A8_WRONG_ORIGINAL_WRAPPER'
  }
  $opts=[string]$task.Actions[0].Arguments
  $oldRoot=Arg $opts 'RepositoryRoot'
  $python=Arg $opts 'PythonExe'
  $key=Arg $opts 'EncryptedKeyFile'
  $boundDb=Arg $opts 'Database'
  if([IO.Path]::GetFullPath($db) -ine [IO.Path]::GetFullPath($boundDb) -or
     !(Test-Path -LiteralPath $python -PathType Leaf) -or
     !(Test-Path -LiteralPath $key -PathType Leaf)) {
    throw 'F139_A8_ORIGINAL_DB_OR_DPAPI_ABSENT'
  }
  $originalGit=(& git -C $oldRoot rev-parse HEAD).Trim()
  if($LASTEXITCODE -ne 0 -or $originalGit -cne $old) {throw 'F139_A8_ORIGINAL_SOURCE_CHANGED'}
  $state=Status $python $oldRoot
  RequireStatus $state $old 47
  if($state.meta.head_hash -cne $head47 -or
     @($state.tasks).Count -ne 8 -or
     @($state.tasks | Where-Object {$_.stage -eq 'VERIFIED'}).Count -ne 7 -or
     @($state.tasks | Where-Object {
       $_.ticket -like 'f139-nci04-i696-*' -and $_.stage -eq 'QUARANTINED'
     }).Count -ne 1) {throw 'F139_A8_ORIGINAL_NEGATIVE_HISTORY_CHANGED'}
  $branch=(& gh api ('repos/'+$repo+'/branches/main')) | ConvertFrom-Json
  if($LASTEXITCODE -ne 0 -or $branch.commit.sha -cne $new -or $branch.protected -ne $true) {
    throw 'F139_A8_PROTECTED_SOURCE_UNVERIFIED'
  }
  $commit=(& gh api ('repos/'+$repo+'/git/commits/'+$new)) | ConvertFrom-Json
  if($LASTEXITCODE -ne 0 -or $commit.tree.sha -cne $tree) {throw 'F139_A8_SOURCE_TREE_UNVERIFIED'}
  if(Test-Path -LiteralPath $dest) {throw 'F139_A8_DESTINATION_ALREADY_EXISTS_RECONCILE'}
  Write-Host 'F139_A8_OWNER_SID_AND_ORIGINAL_LEDGER=PASS'
  Write-Host 'F139_A8_PROTECTED_MAIN_SOURCE_AND_TREE=PASS'
  if(!$Apply) { Write-Host 'F139_A8_DRY_RUN=PASS_NO_MUTATIONS'; return }

  New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
  & gh repo clone $repo $dest -- --branch main --single-branch
  if($LASTEXITCODE -ne 0) {throw 'F139_A8_CLONE_FAILED'}
  $cloned=(& git -C $dest rev-parse HEAD).Trim()
  $clonedTree=(& git -C $dest rev-parse 'HEAD^{tree}').Trim()
  $dirty=@(& git -C $dest status --porcelain --untracked-files=all)
  if($LASTEXITCODE -ne 0 -or $cloned -cne $new -or $clonedTree -cne $tree -or $dirty.Count -gt 0) {
    throw 'F139_A8_CLONE_NOT_EXACT_CLEAN_PROTECTED_SOURCE'
  }
  Write-Host 'F139_A8_CLONE_SOURCE_IDENTITY=PASS'
  # From this line the existing task is intentionally left disabled on failure.
  $stopped=$true
  Disable-ScheduledTask -TaskName $name -ErrorAction Stop | Out-Null
  Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
  $workers=@()
  for($attempt=0;$attempt -lt 15;$attempt++) {
    $workers=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
      Where-Object {$_.CommandLine -and
        $_.CommandLine.Contains('f139.local_controller') -and
        $_.CommandLine.Contains($db)})
    if((Get-ScheduledTask -TaskName $name).State -eq 'Disabled' -and $workers.Count -eq 0) {break}
    Start-Sleep -Seconds 1
  }
  if((Get-ScheduledTask -TaskName $name).State -ne 'Disabled' -or $workers.Count -ne 0) {
    throw 'F139_A8_ORIGINAL_CONTROLLER_NOT_QUIESCED'
  }
  Write-Host 'F139_A8_SINGLE_ORIGINAL_CONTROLLER_QUIESCED=PASS'

  $installer=Join-Path $dest 'scripts\Install-FORGE-F139.ps1'
  & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $installer -Apply -RepositoryRoot $dest -PythonExe $python -StateDirectory (Split-Path -Parent $db)
  if($LASTEXITCODE -ne 0) {throw 'F139_A8_EXISTING_TASK_REBIND_FAILED'}
  Disable-ScheduledTask -TaskName $name -ErrorAction Stop | Out-Null
  $rebound=Get-ScheduledTask -TaskName $name
  if($rebound.State -ne 'Disabled' -or
     [IO.Path]::GetFullPath((Arg ([string]$rebound.Actions[0].Arguments) 'RepositoryRoot')) -ine [IO.Path]::GetFullPath($dest)) {
    throw 'F139_A8_REGISTERED_TASK_SOURCE_MISMATCH'
  }
  Write-Host 'F139_A8_SAME_TASK_NEW_SOURCE_REBOUND_DISABLED=PASS'
  # Existing DPAPI launcher, no controller loop, no manual worker dispatch.
  $launcher=Join-Path $dest 'scripts\Run-FORGE-F139.ps1'
  & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $launcher -PythonExe $python -RepositoryRoot $dest -Database $db -EncryptedKeyFile $key -CustodyOriginalNativeNegative
  if($LASTEXITCODE -ne 0) {throw 'F139_A8_AUTHENTIC_NEGATIVE_NOT_CUSTODIED'}
  $custody=Status $python $dest
  RequireStatus $custody $old 48
  Write-Host 'F139_A8_ORIGINAL_NEGATIVE_DURABLE_EVENT48=PASS'
  $transitionApproval=Join-Path $env:TEMP ('f139-a8-owner-'+[guid]::NewGuid().ToString('N')+'.json')
  $approval=@{schema='forge.f139.nci04.owner-source-transition-approval.v1';
    from_source_sha=$old;to_source_sha=$new;expected_event_head_sha256=$custody.meta.head_hash;
    sealed_23_event_head_sha256=$prefix23;native_development_only=$true;
    scientific_first_use=$false;new_controller=$false;paid_api_calls=0}
  [IO.File]::WriteAllText($transitionApproval,($approval|ConvertTo-Json -Compress),
    (New-Object Text.UTF8Encoding($false)))
  Push-Location $dest
  try {
    & $python -B -m f139.local_controller --db $db transition-qualified-native --approval $transitionApproval
    if($LASTEXITCODE -ne 0) {throw 'F139_A8_CERTIFIED_SOURCE_TRANSITION_FAILED'}
    $mid=Status $python $dest
    RequireStatus $mid $new 49
    Write-Host 'F139_A8_PROTECTED_SOURCE_TRANSITION_EVENT49=PASS'
    $next=@{schema='forge.f139.nci04.owner-native-approval.v1';
      source_sha=$new;expected_event_head_sha256=$mid.meta.head_hash;
      native_development_approved=$true;scientific_first_use=$false;
      create_controller=$false;paid_api_calls=0}
    [IO.File]::WriteAllText($transitionApproval,($next|ConvertTo-Json -Compress),
      (New-Object Text.UTF8Encoding($false)))
    & $python -B -m f139.local_controller --db $db activate-native --approval $transitionApproval
    if($LASTEXITCODE -ne 0) {throw 'F139_A8_NATIVE_SOURCE_ACTIVATION_FAILED'}
  } finally {Pop-Location}
  $done=Status $python $dest
  RequireStatus $done $new 50
  if(@($done.tasks | Where-Object {
    $_.ticket -like 'f139-nci04-i696-*' -and $_.stage -eq 'QUARANTINED'
  }).Count -ne 1) {throw 'F139_A8_HISTORIC_NEGATIVE_DISCARDED'}
  Enable-ScheduledTask -TaskName $name -ErrorAction Stop | Out-Null
  Write-Host 'F139_A8_SINGLE_TASK_REENABLED=PASS'
  Write-Host 'F139_A8_NO_MANUAL_CONTROLLER_START=TRUE'
  Write-Host 'F139_A8_NO_MANUAL_WORKFLOW_DISPATCH=TRUE'
  Write-Host 'F139_A8_NEXT_SCHEDULED_WAKE=PENDING'
  Write-Host 'F139_SCIENTIFIC_FIRST_USE=FALSE'
} catch {
  Write-Host 'F139_A8_OWNER_CUTOVER=BLOCKED'
  if($stopped) {
    Write-Host 'F139_A8_STOPPED_EXISTING_TASK_REMAINS_DISABLED'
    Write-Host 'F139_A8_NEVER_RERUN_WITHOUT_RECONCILIATION'
  }
  throw
} finally {
  if($transitionApproval -and (Test-Path -LiteralPath $transitionApproval)) {
    Remove-Item -LiteralPath $transitionApproval -Force -ErrorAction SilentlyContinue
  }
}