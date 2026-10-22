# One-shot R18 replacement of the existing CKB-plane controller task, with
# byte-pinned preimages, a frozen owner-only release, durable rollback, and
# strict fail-closed post-start status verification. Never registers a new task.
[CmdletBinding()]
param([switch]$Execute)
$ErrorActionPreference='Stop'
Set-StrictMode -Version 3.0

$wid=[Security.Principal.WindowsIdentity]::GetCurrent()
$wp=[Security.Principal.WindowsPrincipal]::new($wid)
if($env:RUNNER_NAME -cne 'FORGE-CODEX-REMOTE' -or
   $env:GITHUB_REPOSITORY -cne 'spoonman136668-ai/FORGE' -or
   $env:GITHUB_REF -cne 'refs/heads/operate/ckb-r18-guarded-owner-cutover-20261022' -or
   $wid.Name -ine 'LINKDEADKB\camar' -or
   !$wp.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'R18_OWNER_ELEVATION_OR_EXECUTION_SCOPE_CHANGED'
}
$root='C:\Users\camar\GolandProjects\ckb-plane'
$config=Join-Path $root 'config\autonomy.yaml'
$db=Join-Path $root 'state\autonomy.db'
$rootExe=Join-Path $root 'bin\ckb-plane.exe'
$oldExe='C:\ProgramData\CKBR\release-store\ckb-plane\releases\PLANE-THROUGHPUT-R1P\bin\ckb-plane.exe'
$oldLauncher='C:\ProgramData\CKBR\cutover\PLANE-THROUGHPUT-R1P\Start-R1P-Controller.ps1'
$oldExeSha='3398be05eaed752234f3ede4978eba4052a7410f1ce1ccde3c537ccdabd4dedf'
$rootExeSha='70e815f8e0399aeabb3291fd140b250039b6993f9d2d60e1b7563c56971c19e6'
$configSha='6ff5310bf343a72c07343874f06ba9060567549d1ddbb8dd5e4c17691201967c'
$launcherSha='66774821081965230ac7265202a9346b17b41af3770b016ca7323db230f9ffce'
$candidateSha='63dce408b8f7d5ba5db64a47f3e40041dc411802a500060873f6d850fdae8f50'
$taskName='CKB-plane Controller'
function AssertSha([string]$path,[string]$expected) {
    if (!(Test-Path -LiteralPath $path -PathType Leaf)) {
        throw 'R18_PROTECTED_FILE_MISSING'
    }
    $actual=(Get-FileHash -LiteralPath $path -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
    if ($actual -cne $expected) {throw 'R18_PROTECTED_FILE_PREIMAGE_DRIFT'}
}
function NativeProcesses {
    return @(Get-CimInstance Win32_Process -Filter "Name='ckb-plane.exe'" -ErrorAction Stop)
}
function WaitStopped {
    for($i=0;$i -lt 60;$i++) {
        if (@(NativeProcesses).Count -eq 0) {return $true}
        Start-Sleep -Milliseconds 500
    }
    return $false
}
function WaitNewController([string]$path) {
    for($i=0;$i -lt 90;$i++) {
        $list=@(NativeProcesses)
        if ($list.Count -eq 1 -and [string]$list[0].ExecutablePath -ieq $path) {
            return $true
        }
        if ($list.Count -gt 1) {throw 'R18_CONCURRENT_CONTROLLERS_OBSERVED'}
        Start-Sleep -Milliseconds 500
    }
    return $false
}
function CheckReadOnlyQuiescence {
    $py=(Get-Command python.exe -ErrorAction Stop).Source
    $qfile=Join-Path $env:RUNNER_TEMP ('R18Query-'+$env:GITHUB_RUN_ID+'.py')
    if (Test-Path -LiteralPath $qfile) {throw 'R18_READONLY_QUERY_TEMP_REUSED'}
    $src=@'
import sqlite3,sys,json
from pathlib import Path
db=Path(sys.argv[1]).resolve(strict=True)
conn=sqlite3.connect("file:"+db.as_posix()+"?mode=ro",uri=True,timeout=3)
try:
    conn.execute("PRAGMA query_only=ON")
    total=conn.execute("SELECT count(*) FROM work_orders").fetchone()[0]
    active=conn.execute("SELECT count(*) FROM work_orders WHERE state IN ('PENDING','QUEUED','RUNNING','RETRY_WAIT','FINALIZING','ACCEPTING')").fetchone()[0]
    leases=conn.execute("SELECT count(*) FROM worker_leases").fetchone()[0]
    print(json.dumps({"total":total,"active":active,"leases":leases},separators=(",",":")))
finally: conn.close()
'@
    [IO.File]::WriteAllText($qfile,$src,(New-Object Text.UTF8Encoding($false)))
    try {
        $out=@(& $py -B $qfile $db)
        if ($LASTEXITCODE -ne 0 -or $out.Count -ne 1) {throw 'R18_SQLITE_READONLY_FAILURE'}
        $scan=$out[0]|ConvertFrom-Json
    } finally {Remove-Item -LiteralPath $qfile -Force -ErrorAction SilentlyContinue}
    if ($scan.total -ne 198 -or $scan.active -ne 0 -or $scan.leases -ne 0) {
        throw ('R18_WORKER_OR_QUEUE_NOT_QUIESCENT:'+($scan|ConvertTo-Json -Compress))
    }
}
AssertSha $oldExe $oldExeSha
AssertSha $rootExe $rootExeSha
AssertSha $config $configSha
AssertSha $oldLauncher $launcherSha
$task=Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
if ($task.State -ne 'Running' -or
    [string]$task.Principal.UserId -notin @('camar','LINKDEADKB\camar') -or
    @($task.Actions).Count -ne 1 -or
    @($task.Triggers).Count -ne 1) {
    throw 'R18_ORIGINAL_CONTROLLER_TASK_DRIFT'
}
$oldAction=$task.Actions[0]
$oldArgs=[string]$oldAction.Arguments
if ($oldArgs -notlike '*PLANE-THROUGHPUT-R1P*' -or
    $oldArgs -notlike '*Start-R1P-Controller.ps1*') {
    throw 'R18_ORIGINAL_TASK_ACTION_DRIFT'
}
$procs=@(NativeProcesses)
if ($procs.Count -ne 1 -or [string]$procs[0].ExecutablePath -ine $oldExe) {
    throw 'R18_ORIGINAL_CONTROLLER_SINGLETON_REQUIRED'
}
CheckReadOnlyQuiescence
$switcher=Get-ScheduledTask -TaskName 'CKB-RB1-ReleaseSwitcher' -ErrorAction Stop
if ($switcher.State -ne 'Ready') {throw 'R18_OLD_RB1_SWITCHER_IDENTITY_DRIFT'}
Write-Host 'R18_FINAL_OWNER_ADMIN_PREFLIGHT=PASS'

# Always inspect the exact private artifact. Use only the credential already
# available to the original owner runner, never dispatch worker commands.
$gh=(Get-Command gh -ErrorAction Stop).Source
$env:GH_PROMPT_DISABLED='1'
$scratch=Join-Path $env:RUNNER_TEMP ('R18Sealed-'+$env:GITHUB_RUN_ID)
if (Test-Path -LiteralPath $scratch) {throw 'R18_ARTIFACT_SCRATCH_COLLISION'}
New-Item -ItemType Directory -Path $scratch -ErrorAction Stop | Out-Null
$cutoverAttempted=$false
$taskChanged=$false
$controllerStopped=$false
$dbSnapshotComplete=$false
$releaseDir=$null
$cutoverDir=$null
$rollbackDir=$null
try {
    & $gh run download 39766883139 --repo spoonman136668-ai/ckb-plane --name r18-sealed-nondeployable-candidate-39766883139 --dir $scratch
    if ($LASTEXITCODE -ne 0) {throw 'R18_PRIVATE_GITHUB_ARTIFACT_UNAVAILABLE'}
    $artifactExe=Join-Path $scratch 'ckb-plane-status-candidate.exe'
    $receiptPath=Join-Path $scratch 'receipt.json'
    if (!(Test-Path -LiteralPath $receiptPath -PathType Leaf)) {throw 'R18_CANDIDATE_RECEIPT_MISSING'}
    AssertSha $artifactExe $candidateSha
    $receipt=Get-Content -LiteralPath $receiptPath -Raw -ErrorAction Stop|ConvertFrom-Json
    if ($receipt.schema -cne 'ckb-plane.r18.status-candidate-seal.v1' -or
        $receipt.executable_sha256 -cne $candidateSha -or
        $receipt.release_approved -ne $false -or
        $receipt.native_windows_full_go_regression -cne 'PASS' -or
        $receipt.native_windows_vet -cne 'PASS' -or
        $receipt.native_windows_build -cne 'PASS' -or
        $receipt.install_target_original_sha256 -cne $rootExeSha -or
        $receipt.install_config_original_sha256 -cne $configSha) {
        throw 'R18_SEALED_CANDIDATE_PROVENANCE_INVALID'
    }
    $oldText=[IO.File]::ReadAllText($oldLauncher)
    if (!$oldText.Contains($oldExe)) {throw 'R18_OLD_LAUNCHER_NOT_BOUND_TO_R1P'}
    # The exact original launcher SHA256 is verified above; this historical
    # launcher computes its configuration path rather than embedding it.
    # Configuration identity is independently pinned at each cutover boundary.
    # Syntax-check the intended launcher before any persistent writes.
    $predictedRelease='C:\ProgramData\CKBR\release-store\ckb-plane\releases\PLANE-R18-OWNER-STATUS\bin\ckb-plane.exe'
    $newText=$oldText.Replace($oldExe,$predictedRelease)
    $tokens=$null;$parseErrors=$null
    [void][Management.Automation.Language.Parser]::ParseInput($newText,[ref]$tokens,[ref]$parseErrors)
    if ($parseErrors.Count -gt 0) {throw 'R18_NEW_LAUNCHER_PARSE_INVALID'}
    if (!$Execute) {
        Write-Host 'R18_DEDICATED_SWITCHER_PREFLIGHT=PASS'
        Write-Host 'R18_CANDIDATE_SHA256=VERIFIED'
        Write-Host 'R18_TASK_CHANGE=NOT_ATTEMPTED'
        Write-Host 'R18_DB_MUTATION=NONE'
        return
    }
    $cutoverAttempted=$true
    $releaseName='PLANE-R18-OWNER-STATUS'
    $releaseDir=Join-Path 'C:\ProgramData\CKBR\release-store\ckb-plane\releases' $releaseName
    $cutoverDir=Join-Path 'C:\ProgramData\CKBR\cutover' ('PLANE-R18-OWNER-CUTOVER-'+$env:GITHUB_RUN_ID)
    $rollbackDir=Join-Path $cutoverDir 'rollback'
    if ((Test-Path -LiteralPath $releaseDir) -or (Test-Path -LiteralPath $cutoverDir)) {
        throw 'R18_RELEASE_OR_ROLLBACK_DESTINATION_ALREADY_EXISTS'
    }
    New-Item -ItemType Directory -Path (Join-Path $releaseDir 'bin') -ErrorAction Stop | Out-Null
    New-Item -ItemType Directory -Path $rollbackDir -ErrorAction Stop | Out-Null
    $newExe=Join-Path $releaseDir 'bin\ckb-plane.exe'
    Copy-Item -LiteralPath $artifactExe -Destination $newExe -ErrorAction Stop
    AssertSha $newExe $candidateSha
    $newLauncher=Join-Path $cutoverDir 'Start-R18-Controller.ps1'
    $newText=$oldText.Replace($oldExe,$newExe)
    [IO.File]::WriteAllText($newLauncher,$newText,(New-Object Text.UTF8Encoding($false)))
    $taskXml=Export-ScheduledTask -TaskName $taskName -ErrorAction Stop
    [IO.File]::WriteAllText((Join-Path $rollbackDir 'original-task.xml'),$taskXml)
    Copy-Item -LiteralPath $config -Destination (Join-Path $rollbackDir 'original-autonomy.yaml') -ErrorAction Stop
    Copy-Item -LiteralPath $oldLauncher -Destination (Join-Path $rollbackDir 'original-launcher.ps1') -ErrorAction Stop
    $newArgs=$oldArgs.Replace('PLANE-THROUGHPUT-R1P',(Split-Path -Leaf $cutoverDir)).Replace('Start-R1P-Controller.ps1','Start-R18-Controller.ps1')
    if ($newArgs -ceq $oldArgs -or $newArgs -like '*Start-R1P-Controller.ps1*' -or
        $newArgs -notlike '*Start-R18-Controller.ps1*') {
        throw 'R18_TASK_ACTION_REPLACEMENT_INVALID'
    }
    if ($oldAction.WorkingDirectory) {
        $newAction=New-ScheduledTaskAction -Execute $oldAction.Execute -Argument $newArgs -WorkingDirectory $oldAction.WorkingDirectory
    } else {
        $newAction=New-ScheduledTaskAction -Execute $oldAction.Execute -Argument $newArgs
    }
    # Retain the original task, principal, triggers and user context. No
    # additional schedule or new controller can be created by this workflow.
    Stop-ScheduledTask -TaskName $taskName -ErrorAction Stop
    $controllerStopped=$true
    if (!(WaitStopped)) {throw 'R18_OLD_CONTROLLER_DID_NOT_STOP'}
    # Snapshot the original SQLite + WAL/SHM only after it is closed.
    foreach($suffix in @('','-wal','-shm')) {
        $src=$db+$suffix
        if (Test-Path -LiteralPath $src -PathType Leaf) {
            Copy-Item -LiteralPath $src -Destination (Join-Path $rollbackDir ('autonomy.db'+$suffix)) -ErrorAction Stop
        }
    }
    if (!(Test-Path -LiteralPath (Join-Path $rollbackDir 'autonomy.db') -PathType Leaf)) {
        throw 'R18_ORIGINAL_DATABASE_SNAPSHOT_MISSING'
    }
    $dbSnapshotComplete=$true
    Set-ScheduledTask -TaskName $taskName -Action $newAction -ErrorAction Stop | Out-Null
    $taskChanged=$true
    Start-ScheduledTask -TaskName $taskName -ErrorAction Stop
    if (!(WaitNewController $newExe)) {throw 'R18_NEW_CONTROLLER_NOT_SINGLETON'}
    $newTask=Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
    if ($newTask.State -ne 'Running' -or [string]$newTask.Actions[0].Arguments -cne $newArgs) {
        throw 'R18_NEW_TASK_ACTION_OR_STATE_INVALID'
    }
    $raw=@(& $newExe controller status --config $config 2>&1)
    if ($LASTEXITCODE -ne 0) {throw 'R18_NEW_CONTROLLER_STATUS_PARSE_OR_EXECUTION_FAILED'}
    $status=$raw|Out-String|ConvertFrom-Json -ErrorAction Stop
    if ($status.authority -ne 'plane' -or $status.paused -eq $true -or
        $status.heartbeat_stale -eq $true -or
        [string]$status.controller_status -notlike 'IDLE:*') {
        throw 'R18_NEW_CONTROLLER_NATIVE_STATUS_UNHEALTHY'
    }
    if (@(NativeProcesses).Count -ne 1) {throw 'R18_CONTROLLER_SINGLETON_POST_START_FAILED'}
    AssertSha $newExe $candidateSha
    AssertSha $config $configSha
    # Preserve the original task XML and the complete DB snapshot for later audit.
    $record=[ordered]@{
        schema='ckb-plane.r18.owner-guarded-cutover.v1'
        result='PASS'
        run_id=$env:GITHUB_RUN_ID
        qualified_source_artifact_sha256=$candidateSha
        original_release_sha256=$oldExeSha
        previous_controller_pid=[int]$procs[0].ProcessId
        active_release_path=$newExe
        task_original_xml=(Join-Path $rollbackDir 'original-task.xml')
        rollback_path=$rollbackDir
        restored_historical_rows=0
        config_sha256=$configSha
        authority='plane'
        status='IDLE'
        ktrade_registered=$false
        trading_action_performed=$false
    }
    [IO.File]::WriteAllText((Join-Path $cutoverDir 'cutover-receipt.json'),($record|ConvertTo-Json -Depth 4),(New-Object Text.UTF8Encoding($false)))
    Write-Host 'R18_LIVE_CONTROLLER_CUTOVER=PASS'
    Write-Host 'R18_LIVE_STATUS_AND_SINGLETON=PASS'
    Write-Host 'R18_DATABASE_AND_CONFIG_PRESERVED=PASS'
    Write-Host 'R18_KTRADE_REGISTRATION=NOT_ATTEMPTED'
} catch {
    $errorCause=$_.Exception.Message
    Write-Host ('R18_CUTOVER_BLOCKED_OR_FAILED='+$errorCause)
    if ($controllerStopped) {
        try {
            Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
            if (!(WaitStopped)) {throw 'R18_ROLLBACK_BLOCKED_BY_RUNNING_CONTROLLER'}
            if ($taskChanged) {
                Set-ScheduledTask -TaskName $taskName -Action $oldAction -ErrorAction Stop | Out-Null
            }
            if ($dbSnapshotComplete) {
                foreach($suffix in @('','-wal','-shm')) {
                    $target=$db+$suffix
                    $original=Join-Path $rollbackDir ('autonomy.db'+$suffix)
                    if (Test-Path -LiteralPath $target -PathType Leaf) {
                        Remove-Item -LiteralPath $target -Force -ErrorAction Stop
                    }
                    if (Test-Path -LiteralPath $original -PathType Leaf) {
                        Copy-Item -LiteralPath $original -Destination $target -ErrorAction Stop
                    }
                }
            }
            Start-ScheduledTask -TaskName $taskName -ErrorAction Stop
            $restored=WaitNewController $oldExe
            if (!$restored) {throw 'R18_ORIGINAL_CONTROLLER_RESTART_NOT_VERIFIED'}
            AssertSha $oldExe $oldExeSha
            AssertSha $config $configSha
            Write-Host 'R18_R1P_ROLLBACK=PASS'
        } catch {
            Write-Host ('R18_R1P_ROLLBACK=FAILED:'+ $_.Exception.Message)
            throw 'R18_MANUAL_RECOVERY_REQUIRED_ORIGINAL_CONTROLLER_UNVERIFIED'
        }
    }
    throw ('R18_CUTOVER_NOT_ADMITTED:'+ $errorCause)
} finally {
    if (Test-Path -LiteralPath $scratch) {
        Remove-Item -LiteralPath $scratch -Recurse -Force -ErrorAction SilentlyContinue
    }
}
