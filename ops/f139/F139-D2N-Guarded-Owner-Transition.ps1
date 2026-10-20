# F139-D2N: exact protected-main owner-controlled source-only transition.
# Default: READ ONLY. -Apply: one owner-only guarded source event, verified backup,
# post-append custody proof and inert task source rebind. NO task startup/dispatch.
# Existing native Windows owner profile, controller and GitHub credentials only.
[CmdletBinding()]
param([switch]$Apply)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$Repo='spoonman136668-ai/FORGE'
$Prior='4a5665d9d01b6e68effc00be244ac39b6794a222'
$Next='34ca99c1b5b063225566082aee5aa180a15d093b'
$Sealed='eea95c859f9a59f700612c3b7b39152abc78827981976e9d86567c29fa03ff87'
$TaskName='FORGE-F139-UnifiedController'
$StateRoot=Join-Path $env:LOCALAPPDATA 'FORGE-F139'
$DB=Join-Path $StateRoot 'state.sqlite'
$Key=Join-Path $StateRoot 'worker-hmac.dpapi.xml'
$NewRoot=Join-Path $env:LOCALAPPDATA 'FORGE-F139-D2N'
$NewTree=Join-Path $NewRoot ('source-'+$Next.Substring(0,12))
$Case=$null; $MutationAttempted=$false; $Mutated=$false; $DisabledByUs=$false
function StopGate([bool]$Test,[string]$Reason){if(-not $Test){throw ('F139_D2N_STOP_'+$Reason)}}
function InvokeNative([string]$Program,[string[]]$Arguments){
  $priorPreference=$ErrorActionPreference
  try {
    $ErrorActionPreference='Continue'
    $result=@(& $Program @Arguments 2>&1);$rc=$LASTEXITCODE
  } finally {$ErrorActionPreference=$priorPreference}
  if($rc -ne 0){throw ('F139_D2N_STOP_NATIVE_ERROR_'+$Program+'_'+$rc+': '+(@($result|ForEach-Object{[string]$_}) -join ' '))}
  return (@($result|Where-Object{$_ -isnot [Management.Automation.ErrorRecord]}|ForEach-Object{[string]$_}) -join "`n").Trim()
}
function API([string]$Path){return ((InvokeNative 'gh' @('api','-X','GET',$Path))|ConvertFrom-Json)}
function SID([string]$Name){
  if($Name -match '^S-\d+(?:-\d+)+$'){return ([Security.Principal.SecurityIdentifier]::new($Name)).Value}
  return ([Security.Principal.NTAccount]::new($Name).Translate([Security.Principal.SecurityIdentifier])).Value
}
function CheckController([string[]]$Allowed){
  $t=Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
  StopGate ($t.State -in $Allowed) 'TASK_STATE_DRIFT'
  StopGate ([string]$t.Principal.LogonType -eq 'Interactive' -and
      [string]$t.Principal.RunLevel -eq 'Limited') 'TASK_SECURITY_POLICY_DRIFT'
  StopGate (@($t.Actions).Count -eq 1) 'TASK_ACTION_COUNT_DRIFT'
  $action=$t.Actions[0]
  StopGate ([IO.Path]::GetFileName([string]$action.Execute) -ieq 'powershell.exe') 'TASK_PROGRAM_DRIFT'
  StopGate ($action.Arguments -match '(?i)-WindowStyle\s+Hidden' -and
      $action.Arguments -match '(?i)-NonInteractive' -and
      $action.Arguments.Contains('Run-FORGE-F139.ps1')) 'TASK_START_POLICY_DRIFT'
  $values=@{}
  foreach($name in @('RepositoryRoot','Database','PythonExe','EncryptedKeyFile')){
    $match=[regex]::Match([string]$action.Arguments,'(?i)(?:^|\s)-'+$name+'\s+"([^"]+)"')
    StopGate $match.Success ('TASK_ARGUMENT_MISSING_'+$name)
    $values[$name]=$match.Groups[1].Value
  }
  StopGate ([IO.Path]::GetFullPath($values.Database) -ieq [IO.Path]::GetFullPath($DB)) 'TASK_DATABASE_DRIFT'
  StopGate ([IO.Path]::GetFullPath($values.EncryptedKeyFile) -ieq [IO.Path]::GetFullPath($Key)) 'TASK_KEY_PATH_DRIFT'
  StopGate (Test-Path -LiteralPath $values.PythonExe -PathType Leaf) 'REGISTERED_PYTHON_MISSING'
  StopGate (Test-Path -LiteralPath (Join-Path $values.RepositoryRoot 'f139\local_controller.py') -PathType Leaf) 'OLD_CONTROLLER_SOURCE_MISSING'
  return @{task=$t;arguments=$values;ownerSid=(SID ([string]$t.Principal.UserId))}
}
function NoControllerProcess{
  $found=@(Get-CimInstance Win32_Process -ErrorAction Stop|Where-Object{
    $_.CommandLine -and $_.CommandLine -match '(?i)(f139[.\\/]local_controller|Run-FORGE-F139\.ps1)' -and
    $_.CommandLine.IndexOf($DB,[StringComparison]::OrdinalIgnoreCase) -ge 0
  })
  StopGate ($found.Count -eq 0) 'CONTROLLER_PROCESS_ACTIVE'
}
function CheckPath([string]$Path){
  $cursor=[IO.Path]::GetFullPath($Path)
  while($true){
    if(Test-Path -LiteralPath $cursor){
      $item=Get-Item -LiteralPath $cursor -Force -ErrorAction Stop
      StopGate (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'PATH_REPARSE_DETECTED'
    }
    $parent=[IO.Path]::GetDirectoryName($cursor)
    if([string]::IsNullOrEmpty($parent) -or $parent -ceq $cursor){break}
    $cursor=$parent
  }
}
function Remote{
  $main=API ('repos/'+$Repo+'/branches/main')
  StopGate ($main.protected -eq $true -and $main.commit.sha -ceq $Next) 'PROTECTED_MAIN_MOVED'
  $pr=API ('repos/'+$Repo+'/pulls/665')
  StopGate ($pr.merged -eq $true -and $pr.merge_commit_sha -ceq $Next -and
      $pr.head.sha -ceq '0c1aa8ecbb96d874fcd979afd574ffa15216ea42') 'MERGE_PROVENANCE_DRIFT'
  foreach($id in @(39395732481,39395732543)){
    $run=API ('repos/'+$Repo+'/actions/runs/'+$id)
    StopGate ($run.head_sha -ceq $Next -and $run.status -ceq 'completed' -and
        $run.conclusion -ceq 'success') ('POST_MERGE_CI_NOT_SUCCESS_'+$id)
  }
  StopGate ((API 'user').login -ceq 'spoonman136668-ai') 'GITHUB_OWNER_IDENTITY_DRIFT'
}
function Legacy{
  foreach($name in @('forge-development-succession.yml','forge-integrated-synthetic-cycle.yml')){
    $w=API ('repos/'+$Repo+'/actions/workflows/'+$name)
    StopGate ($w.state -ceq 'disabled_manually') ('LEGACY_WORKFLOW_ACTIVE_'+$name)
    $runs=API ('repos/'+$Repo+'/actions/workflows/'+$name+'/runs?per_page=100')
    StopGate (@($runs.workflow_runs|Where-Object {$_.status -in @('queued','requested','in_progress','waiting','pending')}).Count -eq 0) ('LEGACY_JOB_ACTIVE_'+$name)
  }
  StopGate ((Get-ScheduledTask -TaskName 'FORGE-F137-WakeProbe' -ErrorAction Stop).State -eq 'Disabled') 'LEGACY_F137_TASK_ACTIVE'
}
function NativeAudit([string]$Source,[bool]$Transitioned){
  $old=(Get-Location).Path
  try{
    Set-Location -LiteralPath $NewTree
    $args=@('-B','-m','f139.audit_d2k_custody','--db',$DB,
            '--expected-source-sha',$Source,'--sealed-event-head-sha256',$Sealed)
    if($Transitioned){$args+=@('--qualified-protected-main-sha',$Next)}
    $out=InvokeNative $script:Python $args
    $v=$out|ConvertFrom-Json
    StopGate ($v.schema -ceq 'forge.f139.d2k-custody.readonly-audit.v1' -and
        $v.sealed_event_head_sha256 -ceq $Sealed -and
        $v.expected_source_sha -ceq $Source -and
        $v.historical_prefix_event_count -eq 23 -and
        $v.task_count -eq 4 -and $v.archive_count -eq 8 -and
        $v.external_provider_anchor_records -eq 4 -and
        $v.external_provider_artifacts_checked -eq 8 -and
        $v.d2j_task_bindings_verified -eq 2 -and
        $v.original_database_writes -eq 0 -and
        $v.controller_actions -eq 0 -and $v.scientific_first_use -eq $false) 'CUSTODY_REPORT_INVALID'
    if($Transitioned){
      StopGate ($v.event_count -eq 24 -and $v.source_only_suffix_count -eq 1 -and
        $v.live_main_source_suffix_verified -eq $true -and
        $v.qualified_protected_main_sha -ceq $Next) 'POST_TRANSITION_CUSTODY_FAILED'
    }else{
      StopGate ($v.event_count -eq 23 -and $v.source_only_suffix_count -eq 0 -and
        $v.observed_current_head_sha256 -ceq $Sealed) 'HISTORIC_PREFIX_CHANGED'
    }
    return $v
  }finally{Set-Location -LiteralPath $old}
}
try{
  StopGate ($env:OS -ceq 'Windows_NT' -and $PSVersionTable.PSEdition -ceq 'Desktop' -and
    $PSVersionTable.PSVersion.Major -eq 5) 'NATIVE_POWERSHELL_51_REQUIRED'
  foreach($cmd in @('git','gh','Get-ScheduledTask','Get-CimInstance')){
    StopGate ($null -ne (Get-Command $cmd -ErrorAction SilentlyContinue)) ('COMMAND_MISSING_'+$cmd)
  }
  StopGate (Test-Path -LiteralPath $DB -PathType Leaf) 'CONTROLLER_DB_MISSING'
  StopGate (Test-Path -LiteralPath $Key -PathType Leaf) 'OWNER_DPAPI_KEY_MISSING'
  CheckPath $DB
  $binding=CheckController @('Ready','Disabled')
  StopGate ((InvokeNative 'git' @('-C',$binding.arguments.RepositoryRoot,'rev-parse','HEAD')) -ceq $Prior) 'INSTALLED_PREDECESSOR_SOURCE_DRIFT'
  StopGate ([string]::IsNullOrWhiteSpace((InvokeNative 'git' @('-C',$binding.arguments.RepositoryRoot,'status','--porcelain')))) 'INSTALLED_PREDECESSOR_TREE_DIRTY'
  if($Apply){
    StopGate ($binding.ownerSid -ceq [Security.Principal.WindowsIdentity]::GetCurrent().User.Value) 'OWNER_ACCOUNT_REQUIRED_FOR_WRITE'
  }
  $script:Python=[string]$binding.arguments.PythonExe
  NoControllerProcess
  Remote;Legacy
  if(!(Test-Path -LiteralPath $NewTree -PathType Container)){
    New-Item -ItemType Directory -Path $NewTree -Force -ErrorAction Stop|Out-Null
  }
  if(!(Test-Path -LiteralPath (Join-Path $NewTree '.git') -PathType Container)){
    StopGate (@(Get-ChildItem -LiteralPath $NewTree -Force).Count -eq 0) 'FOREIGN_NON_GIT_CHECKOUT'
    $null=InvokeNative 'git' @('-C',$NewTree,'init','--quiet')
  }
  $remoteUrl='https://github.com/' + $Repo + '.git'
  $existingRemotes=InvokeNative 'git' @('-C',$NewTree,'remote')
  if([string]::IsNullOrWhiteSpace($existingRemotes)){
    $null=InvokeNative 'git' @('-C',$NewTree,'remote','add','origin',$remoteUrl)
  }else{
    StopGate ($existingRemotes -ceq 'origin') 'UNEXPECTED_GIT_REMOTES'
    StopGate ((InvokeNative 'git' @('-C',$NewTree,'remote','get-url','origin')) -ceq $remoteUrl) 'REMOTE_URL_DRIFT'
  }
  $null=InvokeNative 'git' @('-C',$NewTree,'fetch','--quiet','--depth','1','origin',$Next)
  $null=InvokeNative 'git' @('-C',$NewTree,'-c','advice.detachedHead=false','checkout','--quiet','--detach',$Next)
  StopGate ((InvokeNative 'git' @('-C',$NewTree,'rev-parse','HEAD')) -ceq $Next) 'NEW_TREE_SHA_DRIFT'
  StopGate ([string]::IsNullOrWhiteSpace((InvokeNative 'git' @('-C',$NewTree,'status','--porcelain')))) 'NEW_TREE_NOT_CLEAN'
  CheckPath $NewTree
  StopGate (Test-Path -LiteralPath (Join-Path $NewTree 'scripts\Install-FORGE-F139.ps1') -PathType Leaf) 'NEW_INSTALLER_MISSING'
  $pre=NativeAudit $Prior $false
  Write-Output 'F139_D2N_POST_MERGE_FULL_REGRESSION=PASS'
  Write-Output 'F139_D2N_PROTECTED_MAIN_AND_OWNER=PASS'
  Write-Output 'F139_D2N_SEALED_23_EVENT_HISTORY=PASS'
  Write-Output 'F139_D2N_FOUR_TASKS_EIGHT_ZIPS=PASS'
  if(!$Apply){Write-Output 'F139_D2N_DISPOSITION=READ_ONLY_PREFLIGHT_PASS_NO_TRANSITION';return}
  # Final owner-only recheck; all source changes and preflight are complete.
  Remote;Legacy
  [void](CheckController @('Ready','Disabled'))
  NoControllerProcess
  if((Get-ScheduledTask -TaskName $TaskName).State -eq 'Ready'){
    Disable-ScheduledTask -TaskName $TaskName -ErrorAction Stop|Out-Null
    $DisabledByUs=$true
  }
  [void](CheckController @('Disabled'))
  NoControllerProcess
  $Case=Join-Path $NewRoot ('custody-'+(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ'))
  New-Item -ItemType Directory -Path $Case -ErrorAction Stop|Out-Null
  $Backup=Join-Path $Case 'pre-d2n-state.sqlite'
  StopGate (-not (Test-Path -LiteralPath $Backup)) 'BACKUP_ALREADY_EXISTS'
  # Existing controller's native source transition, under its sole Windows owner.
  # The Python operation holds the same SQLite mutex as the live controller.
  $script:TransitionCode=@'
import hashlib, json, pathlib, sqlite3, sys
from f139.local_controller import Database, SingleOwner
from f139.audit_d2k_custody import audit
p=pathlib.Path(sys.argv[1]);old,new,seal=sys.argv[2:5];backup=pathlib.Path(sys.argv[5])
assert p.is_file() and not p.is_symlink(), 'PRODUCTION_DB_INVALID'
assert backup.parent.is_dir() and not backup.exists(), 'BACKUP_ALREADY_PRESENT'
with SingleOwner(p.with_suffix('.lock')):
    before=audit(p,old,seal)
    assert before['event_count']==23 and before['archive_count']==8 and before['task_count']==4, 'PREIMAGE_CUSTODY_DRIFT'
    db=Database(p)
    try:
        meta=db.meta();tasks=[dict(x) for x in db.conn.execute('SELECT * FROM tasks ORDER BY ticket')]
        assert meta['source_sha']==old and meta['head_seq']==23 and meta['head_hash']==seal and meta['epoch']==1, 'PREIMAGE_SOURCE_DRIFT'
        assert len(tasks)==4 and all(x['stage']=='VERIFIED' and x['run_id'] and x['evidence_sha'] for x in tasks), 'TASK_NOT_VERIFIED'
        sink=sqlite3.connect(str(backup))
        try:db.conn.backup(sink)
        finally:sink.close()
        with sqlite3.connect(backup.as_uri()+'?mode=ro',uri=True) as frozen:
            assert frozen.execute('PRAGMA integrity_check').fetchone()[0]=='ok', 'BACKUP_INTEGRITY_FAILED'
            assert frozen.execute('SELECT head_hash FROM meta WHERE id=1').fetchone()[0]==seal,'BACKUP_HEAD_DRIFT'
        backup_sha=hashlib.sha256(backup.read_bytes()).hexdigest()
        assert db.meta()['head_hash']==seal,'DATABASE_MOVED_DURING_BACKUP'
        db.transition_source(new)
        assert db.meta()['head_seq']==24 and db.meta()['source_sha']==new, 'SOURCE_TRANSITION_FAILED'
        updated=[dict(x) for x in db.conn.execute('SELECT * FROM tasks ORDER BY ticket')]
        assert tasks==updated, 'HISTORIC_TASK_REWRITE'
    finally:db.close()
    post=audit(p,new,seal,qualified_main_sha=new)
    assert post['event_count']==24 and post['source_only_suffix_count']==1,'APPEND_COUNT_INCORRECT'
    assert post['live_main_source_suffix_verified'] is True, 'NEW_HEAD_NOT_PROTECTED'
    assert post['task_count']==4 and post['archive_count']==8 and post['scientific_first_use'] is False,'ORIGINALS_DRIFT'
    print(json.dumps({'schema':'forge.f139.d2n.owner-source-transition.v1',
      'pre_head':seal,'head':post['observed_current_head_sha256'],'event_count':24,
      'source':new,'backup':str(backup),'backup_sha256':backup_sha,
      'task_count':post['task_count'],'archive_count':post['archive_count'],
      'scientific_first_use':False,'dispatches':0},sort_keys=True))
'@
  $oldDir=(Get-Location).Path
  try{
    Set-Location -LiteralPath $NewTree
    $MutationAttempted=$true
    $mutation=InvokeNative $script:Python @('-B','-c',$script:TransitionCode,$DB,$Prior,$Next,$Sealed,$Backup)
    $Mutated=$true
  }finally{Set-Location -LiteralPath $oldDir}
  $result=$mutation | ConvertFrom-Json
  StopGate ($result.event_count -eq 24 -and $result.source -ceq $Next -and
    $result.task_count -eq 4 -and $result.archive_count -eq 8 -and
    $result.scientific_first_use -eq $false) 'TRANSITION_RECEIPT_INVALID'
  $post=NativeAudit $Next $true
  Remote;Legacy;NoControllerProcess
  # Rebind ONLY the existing task to the exact accepted tree. Never start it.
  & (Join-Path $NewTree 'scripts\Install-FORGE-F139.ps1') -Apply `
    -PythonExe $script:Python -RepositoryRoot $NewTree `
    -StateDirectory $StateRoot -TaskName $TaskName
  StopGate $? 'SOURCE_TASK_REBIND_FAILED'
  Disable-ScheduledTask -TaskName $TaskName -ErrorAction Stop|Out-Null
  $binding=CheckController @('Disabled')
  StopGate ([IO.Path]::GetFullPath($binding.arguments.RepositoryRoot) -ieq
    [IO.Path]::GetFullPath($NewTree)) 'REBOUND_TASK_SOURCE_INVALID'
  NoControllerProcess
  $Receipt=Join-Path $Case 'f139-d2n-owner-transition.json'
  $saved=[ordered]@{schema='forge.f139.d2n.owner-source-transition.v1';
    disposition='SOURCE_ONLY_TRANSITION_ACCEPTED_CONTROLLER_DISABLED';
    from_source=$Prior;to_source=$Next;original_head=$Sealed;
    current_event_head=$post.observed_current_head_sha256;
    event_count=24;original_verified_tasks=4;original_archives=8;
    backup_sha256=$result.backup_sha256;backup_path=$result.backup;
    controller_task_state='Disabled';controller_started=$false;
    new_dispatches=0;scientific_first_use=$false;
    observed_at_utc=(Get-Date).ToUniversalTime().ToString('o')}
  [IO.File]::WriteAllText($Receipt,($saved|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
  Write-Output 'F139_D2N_24TH_SOURCE_EVENT=PASS'
  Write-Output 'F139_D2N_ORIGINAL_23_EVENT_PREFIX=PASS'
  Write-Output 'F139_D2N_HISTORIC_TASKS=4_OF_4_PASS'
  Write-Output 'F139_D2N_ORIGINAL_ZIPS=8_OF_8_PASS'
  Write-Output 'F139_D2N_EXACT_SOURCE_TASK_REBOUND_DISABLED=PASS'
  Write-Output 'F139_D2N_CONTROLLER_RESTART=NONE'
  Write-Output 'F139_D2N_SCIENTIFIC_FIRST_USE=BLOCKED'
  Write-Output 'F139_D2N_DISPOSITION=SOURCE_ONLY_TRANSITION_ACCEPTED_CONTROLLER_DISABLED'
  Write-Output ('F139_D2N_RECEIPT='+$Receipt)
}catch{
  $message=$_.Exception.Message
  if($MutationAttempted -or $DisabledByUs){
    try{Disable-ScheduledTask -TaskName $TaskName -ErrorAction Stop|Out-Null}catch{}
  }
  Write-Output ('F139_D2N_BLOCKED='+$message)
  Write-Output ('F139_D2N_DISPOSITION='+$(if($MutationAttempted){'MUTATION_ATTEMPTED_INSPECTION_REQUIRED_CONTROLLER_DISABLED'}else{'PRETRANSITION_BLOCKED'}))
  throw
}
