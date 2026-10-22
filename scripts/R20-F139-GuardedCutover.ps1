[CmdletBinding()]
param([switch]$Apply)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo='spoonman136668-ai/FORGE'
$source='536b91a392b7bbc50200a6e8842d152f2e23d8bb'
$candidate='129f8fd6fde579d001606039dff94cc812f9bd45'
$head68='ff4405b7a9c00e514708490787174ce5a77c19ac812bb59462363d6851896174'
$sealed='eea95c859f9a59f700612c3b7b39152abc78827981976e9d86567c29fa03ff87'
$taskName='FORGE-F139-UnifiedController'
$branch='refs/heads/proposal/f139-r20-guarded-live-cutover-20261022'
$stage='PREFLIGHT';$disabled=$false;$merged=$false;$transitioned=$false;$approvalFile=$null
if($env:GITHUB_REPOSITORY -cne $repo -or $env:GITHUB_REF -cne $branch -or
   $env:RUNNER_NAME -cne 'FORGE-CODEX-REMOTE' -or $env:OPENAI_API_KEY -or
   $env:F139_WORKER_HMAC_KEY -or $env:GH_TOKEN -or $env:GITHUB_TOKEN){
  throw 'R20_WRONG_OWNER_OR_INHERITED_CREDENTIALS'
}
function Get-Main {
  $v=(& gh api "repos/$repo/branches/main" --jq '.commit.sha' | Out-String).Trim()
  if($LASTEXITCODE -ne 0 -or $v -cnotmatch '^[a-f0-9]{40}$'){
    throw 'R20_PROTECTED_MAIN_NOT_VERIFIED'
  }
  return $v
}
function Get-Head([string]$dir){
  $v=(& git -C $dir rev-parse HEAD | Out-String).Trim()
  if($LASTEXITCODE -ne 0 -or $v -cnotmatch '^[a-f0-9]{40}$'){
    throw 'R20_ORIGINAL_CHECKOUT_NOT_AUTHENTICATED'
  }
  return $v
}
function Test-Clean([string]$dir){
  $v=(& git -C $dir status --porcelain --untracked-files=all | Out-String).Trim()
  if($LASTEXITCODE -ne 0 -or $v.Length -ne 0){throw 'R20_ORIGINAL_CHECKOUT_DIRTY'}
}
function Get-OwnerPython([string]$db){
  return @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction Stop |
    Where-Object { $_.CommandLine -and $_.CommandLine.Contains('f139.local_controller') -and
      $_.CommandLine.Contains($db) })
}
function Test-Evidence([string]$python,[string]$db,[string]$sha,[int]$event,[string]$head){
  $audit = @'
import contextlib, hashlib, json, pathlib, sqlite3, sys
source, expected, seq, sha = sys.argv[1:]
source=pathlib.Path(source).resolve(strict=True)
def require(ok, msg):
    if not ok: raise RuntimeError("R19_"+msg)
def canonical(obj):
    return (json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True)+"\n").encode()
def hashed(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()
require(source.name=="state.sqlite" and not source.is_symlink(),"OWNER_DB_PATH_INVALID")
with contextlib.closing(sqlite3.connect(source.as_uri()+"?mode=ro",uri=True,timeout=10)) as db:
    db.row_factory=sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    meta=dict(db.execute("SELECT * FROM meta WHERE id=1").fetchone())
    rows=[dict(x) for x in db.execute("SELECT * FROM tasks ORDER BY ticket")]
    stages=[x["stage"] for x in rows]
    print("R19_OBSERVED_STAGE_INVENTORY="+",".join(
        str(stage)+":"+str(stages.count(stage)) for stage in sorted(set(stages))),flush=True)
    print("R19_OBSERVED_TASK_COUNT="+str(len(rows)),flush=True)
    require(meta["source_sha"]==expected and meta["head_seq"]==int(seq)
            and meta["head_hash"]==sha and meta["enabled"]==1
            and meta["legacy_suspended"]==1,"OWNER_EVENT_OR_SOURCE_DRIFT")
    previous="0"*64
    count=0
    for e in db.execute("SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq"):
        count+=1
        require(e["seq"]==count and e["prior_sha"]==previous,
                "EVENT_SEQUENCE_OR_LINK_TAMPERED")
        payload=json.loads(e["payload"])
        require(canonical(payload).decode()==e["payload"],"NONCANONICAL_EVENT")
        previous=hashed({"seq":count,"prior_sha":previous,
                         "kind":e["kind"],"payload":payload})
        require(previous==e["sha"],"EVENT_CHAIN_HASH_TAMPERED")
    require(count==int(seq) and previous==sha,"ORIGINAL_EVENT68_HEAD_DRIFT")
require(stages.count("VERIFIED")==9 and stages.count("QUARANTINED")==2
        and len(rows)==11,"OWNER_TASKS_PENDING_UNVERIFIED_OR_MISSING")
negatives={x["ticket"] for x in rows if x["stage"]=="QUARANTINED"}
require(negatives=={"f139-nci04-i696-5662e3586bc9-7bb8f27f",
                   "f139-nci04-i706-09f3d7447900-09dc99f4"},
        "OWNER_CERTIFIED_NEGATIVES_DRIFT")
for t in rows:
    if t["stage"]=="QUARANTINED":
        require(t["run_id"] is None and t["evidence_sha"] is None and
                not t["evidence_dir"],"HISTORICAL_NEGATIVE_CUSTODY_DRIFT")
evidence_root=(source.parent/"evidence").resolve(strict=True)
count_archives=0
for t in rows:
    if t["stage"]!="VERIFIED":continue
    run_id=t["run_id"]
    require(type(run_id) is int and run_id>0 and
            type(t["evidence_sha"]) is str and len(t["evidence_sha"])==64
            and t["evidence_dir"],"HISTORICAL_VERIFIED_ROW_INCOMPLETE")
    directory=pathlib.Path(t["evidence_dir"]).resolve(strict=True)
    require(directory.is_dir() and not directory.is_symlink()
            and directory.parent.parent==evidence_root
            and directory.name==str(run_id)
            and directory.parent.name==t["ticket"],
            "HISTORICAL_EVIDENCE_OUTSIDE_OWNER_CUSTODY")
    members={p.name:p for p in directory.iterdir()}
    require(set(members)=={"manifest.json","ubuntu-latest.zip","windows-latest.zip"}
            and all(p.is_file() and not p.is_symlink() for p in members.values()),
            "HISTORICAL_PROVIDER_ARCHIVE_SET_DRIFT")
    manifest_raw=members["manifest.json"].read_bytes()
    require(hashlib.sha256(manifest_raw).hexdigest()==t["evidence_sha"],
            "HISTORICAL_RECEIPT_DIGEST_DRIFT")
    manifest=json.loads(manifest_raw)
    require(manifest["ticket"]==t["ticket"] and manifest["run_id"]==run_id
            and manifest["scientific_originals"]==0
            and manifest["approved_science"] is False,
            "HISTORICAL_RECEIPT_AUTHORITY_DRIFT")
    for osname in ("ubuntu-latest","windows-latest"):
        require(hashlib.sha256(members[osname+".zip"].read_bytes()).hexdigest()
                ==manifest["sha256"][osname],"PROVIDER_ZIP_DIGEST_DRIFT")
        count_archives+=1
require(count_archives==18,"HISTORICAL_PROVIDER_ARCHIVE_COUNT_DRIFT")
print("R19_ORIGINAL_EVENT68_HASH_CHAIN=PASS")
print("R19_VERIFIED_ORIGINAL_TASKS=9")
print("R19_QUARANTINED_NEGATIVES=2")
print("R19_PROVIDER_ORIGINAL_ZIPS=18_OF_18_PASS")
print("R19_NO_READY_WAIT_PROVIDER_OR_START_RISK=PASS")
print("R19_OWNER_DATABASE_WRITES=0")
'@
  $output=& $python -B -c $audit $db $sha ([string]$event) $head
  if($LASTEXITCODE -ne 0){
    $output | Where-Object {$_ -match '^R19_OBSERVED_'} | ForEach-Object {Write-Output $_}
    throw 'R20_ORIGINAL_LEDGER_OR_EVIDENCE_REJECTED'
  }
  Write-Output ('R20_OWNER_CUSTODY_EVENT'+[string]$event+'=PASS')
}
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
$admin=New-Object Security.Principal.WindowsPrincipal($who)
if(-not $admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
  throw 'R20_OWNER_ELEVATION_REQUIRED'
}
$task=Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
if(@($task.Actions).Count -ne 1 -or [string]$task.State -eq 'Disabled'){
  throw 'R20_ORIGINAL_TASK_NOT_ACTIVE'
}
$owner=[string]$task.Principal.UserId
$sid=if($owner -match '^S-1-'){$owner}else{
  (New-Object Security.Principal.NTAccount($owner)).Translate(
    [Security.Principal.SecurityIdentifier]).Value
}
if($sid -cne $who.User.Value){throw 'R20_ORIGINAL_OWNER_SID_DRIFT'}
$opts=@{}
foreach($key in @('File','PythonExe','RepositoryRoot','Database','EncryptedKeyFile')){
  $match=[regex]::Match([string]$task.Actions[0].Arguments,
    '(?i)(?:^|\s)-'+$key+'\s+"([^"]+)"')
  if(-not $match.Success){throw ('R20_TASK_ARG_ABSENT_'+$key)}
  $opts[$key]=$match.Groups[1].Value
}
$state=Join-Path $env:LOCALAPPDATA 'FORGE-F139'
if([IO.Path]::GetFileName($opts['File']) -cne 'Run-FORGE-F139.ps1' -or
   [IO.Path]::GetFullPath($opts['Database']) -ine
     [IO.Path]::GetFullPath((Join-Path $state 'state.sqlite')) -or
   [IO.Path]::GetFullPath($opts['EncryptedKeyFile']) -ine
     [IO.Path]::GetFullPath((Join-Path $state 'worker-hmac.dpapi.xml'))){
  throw 'R20_ORIGINAL_TASK_DB_AND_KEY_ROUTE_DRIFT'
}
$root=$opts['RepositoryRoot'];$db=$opts['Database'];$python=$opts['PythonExe']
foreach($key in @('Database','PythonExe','EncryptedKeyFile')){
  if(-not (Test-Path -LiteralPath $opts[$key] -PathType Leaf)){
    throw ('R20_OWNER_CUSTODY_FILE_MISSING_'+$key)
  }
}
if((Get-Main) -cne $source -or (Get-Head $root) -cne $source){
  throw 'R20_OWNER_OR_MAIN_SOURCE_CHANGED'
}
Test-Clean $root
$pr=(& gh api "repos/$repo/pulls/722" | Out-String | ConvertFrom-Json)
if($LASTEXITCODE -ne 0 -or $pr.head.sha -cne $candidate -or $pr.base.sha -cne $source -or
   $pr.draft -ne $false -or $pr.merged -eq $true -or $pr.mergeable -ne $true){
  throw 'R20_EXACT_PR_722_INVALID'
}
$checks=(& gh api "repos/$repo/commits/$candidate/check-runs?per_page=100" | Out-String | ConvertFrom-Json)
if($LASTEXITCODE -ne 0 -or $checks.total_count -ne 13 -or
   @($checks.check_runs | Where-Object {
     $_.head_sha -cne $candidate -or $_.status -cne 'completed' -or
     $_.conclusion -cne 'success'}).Count -ne 0){
  throw 'R20_FULL_13_CHECK_QUALIFICATION_FAILED'
}
$permissions=(& gh api "repos/$repo" | Out-String | ConvertFrom-Json)
if($LASTEXITCODE -ne 0 -or $permissions.permissions.push -ne $true){
  throw 'R20_ORIGINAL_OWNER_MERGE_PERMISSION_UNAVAILABLE'
}
$env:GIT_TERMINAL_PROMPT='0';$env:GCM_INTERACTIVE='Never'
$remote=(& git -C $root ls-remote origin refs/heads/main | Out-String).Trim()
if($LASTEXITCODE -ne 0 -or $remote -cne ($source+[char]9+'refs/heads/main')){
  throw 'R20_ORIGINAL_SOURCE_REMOTE_ACCESS_UNQUALIFIED'
}
if(@(Get-OwnerPython $db).Count -ne 1){
  throw 'R20_ORIGINAL_CONTROLLER_PROCESS_COUNT_DRIFT'
}
Test-Evidence $python $db $source 68 $head68
Write-Output 'R20_PREMERGE_ORIGINAL_OWNER_AND_SOURCE=PASS'
if(-not $Apply){
  Write-Output 'R20_MODE=READ_ONLY_QUALIFICATION'
  Write-Output 'R20_PROTECTED_MAIN_CHANGES=0'
  Write-Output 'R20_ORIGINAL_CONTROLLER_CHANGES=0'
  Write-Output 'R20_SCIENTIFIC_FIRST_USE=FALSE'
  return
}
try{
  $stage='SINGLE_OWNER_STOP'
  Disable-ScheduledTask -TaskName $taskName -ErrorAction Stop | Out-Null
  $disabled=$true
  Stop-ScheduledTask -TaskName $taskName -ErrorAction Stop
  $quiet=$false
  for($i=0;$i -lt 30;$i++){
    if(@(Get-OwnerPython $db).Count -eq 0){$quiet=$true;break}
    Start-Sleep -Seconds 2
  }
  if(-not $quiet -or [string](Get-ScheduledTask -TaskName $taskName).State -cne 'Disabled'){
    throw 'R20_SINGLE_ORIGINAL_OWNER_DID_NOT_QUIESCE'
  }
  if((Get-Main) -cne $source -or (Get-Head $root) -cne $source){
    throw 'R20_PROTECTED_REF_CHANGED_DURING_CUTOVER'
  }
  Test-Clean $root
  Test-Evidence $python $db $source 68 $head68
  Write-Output 'R20_ORIGINAL_CONTROLLER_QUIESCED=PASS'
  $stage='MERGE_722'
  $response=(& gh api -X PUT "repos/$repo/pulls/722/merge" -f "sha=$candidate" -f 'merge_method=merge' -f 'commit_title=F139 R18 unified guarded recovery admission' | Out-String)
  if($LASTEXITCODE -ne 0){throw 'R20_PROTECTED_MERGE_REJECTED'}
  $merge=$response | ConvertFrom-Json
  $newsha=[string]$merge.sha
  if($merge.merged -ne $true -or $newsha -cnotmatch '^[a-f0-9]{40}$' -or
     (Get-Main) -cne $newsha){throw 'R20_PROTECTED_MERGE_IDENTITY_INVALID'}
  $merged=$true
  Write-Output ('R20_GITHUB_MERGE_SHA='+$newsha)
  $stage='ORIGINAL_CHECKOUT'
  & git -C $root fetch --no-tags origin main
  if($LASTEXITCODE -ne 0){throw 'R20_GIT_FETCH_NEW_PROTECTED_SOURCE_FAILED'}
  & git -C $root checkout --detach $newsha
  if($LASTEXITCODE -ne 0){throw 'R20_EXACT_CHECKOUT_CUTOVER_FAILED'}
  if((Get-Head $root) -cne $newsha){throw 'R20_ORIGINAL_CHECKOUT_COMMIT_DRIFT'}
  Test-Clean $root
  $known=[ordered]@{
    'f139/nci04_native_worker.py'='c92d0002a2882bc171a66526da64f24962369847'
    'f139/test_nci04_output_capture.py'='d8bfcbd88a71e7bd2cde827ab2cc90a9705c4a91'
    'f139/r15_isolated_autorepair.py'='0898dc8e26818f8dcc117cfcb2baeb8ceace9748'
    'f139/r15_provider_failure_repair.py'='3deeba788d0838f24935866347c816f17d8d2f36'
    'f139/r16_semantic_repair.py'='2b2aee0aa3556546b3f38176f7e9db8b0e234032'
    'f139/test_r16_semantic_repair.py'='2b42fc60a6db1e64430c6a4b0162733145bc7468'
  }
  foreach($item in $known.GetEnumerator()){
    $observed=(& git -C $root rev-parse ('HEAD:'+$item.Key) | Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or $observed -cne $item.Value){
      throw ('R20_MERGED_SOURCE_BLOB_DRIFT_'+$item.Key)
    }
  }
  Write-Output 'R20_MERGED_SOURCE_BLOBS=6_OF_6_PASS'
  $stage='NATIVE_OWNER_TRANSITION'
  $approval=[ordered]@{
    schema='forge.f139.nci04.owner-source-transition-approval.v1'
    from_source_sha=$source;to_source_sha=$newsha
    expected_event_head_sha256=$head68;sealed_23_event_head_sha256=$sealed
    native_development_only=$true;scientific_first_use=$false
    new_controller=$false;paid_api_calls=0
  }
  $approvalFile=Join-Path $env:TEMP ('f139-r20-'+$env:GITHUB_RUN_ID+'-approval.json')
  if(Test-Path -LiteralPath $approvalFile){throw 'R20_APPROVAL_PATH_NOT_UNIQUE'}
  [IO.File]::WriteAllText($approvalFile,($approval|ConvertTo-Json -Compress -Depth 4),
    (New-Object System.Text.UTF8Encoding($false)))
  Push-Location -LiteralPath $root
  try{
    $out=(& $python -B -m f139.local_controller --db $db transition-qualified-native --approval $approvalFile | Out-String).Trim()
    if($LASTEXITCODE -ne 0){throw 'R20_ORIGINAL_OWNER_NATIVE_CLI_REJECTED'}
    $tr=$out | ConvertFrom-Json
    if($tr.native_source_transition -cne 'PASS' -or $tr.source_sha -cne $newsha -or
       $tr.scientific_first_use -ne $false -or $tr.head_sha256 -cnotmatch '^[a-f0-9]{64}$'){
      throw 'R20_OWNER_SOURCE_TRANSITION_RESULT_INVALID'
    }
    $head69=[string]$tr.head_sha256
    $transitioned=$true
    Test-Evidence $python $db $newsha 69 $head69
    $status=(& $python -B -m f139.local_controller --db $db status | Out-String | ConvertFrom-Json).status
    if($LASTEXITCODE -ne 0 -or $status.meta.source_sha -cne $newsha -or
       [int]$status.meta.head_seq -ne 69 -or $status.meta.head_hash -cne $head69){
      throw 'R20_ORIGINAL_OWNER_POST_COMMIT_STATUS_INVALID'
    }
  } finally {Pop-Location}
  Write-Output ('R20_AUTHENTIC_OWNER_EVENT69='+$head69)
  Write-Output 'R20_HISTORICAL_PROVIDER_ARCHIVES=18_OF_18_PASS'
  $stage='RESTART_ORIGINAL_CONTROLLER'
  Enable-ScheduledTask -TaskName $taskName -ErrorAction Stop | Out-Null
  Start-ScheduledTask -TaskName $taskName -ErrorAction Stop
  $running=$false
  for($i=0;$i -lt 25;$i++){
    Start-Sleep -Seconds 2
    if([string](Get-ScheduledTask -TaskName $taskName).State -ceq 'Running' -and
       @(Get-OwnerPython $db).Count -eq 1){$running=$true;break}
  }
  if(-not $running){throw 'R20_NEW_SOURCE_CONTROLLER_DID_NOT_RESTART'}
  Write-Output 'R20_GUARDED_MERGE_SOURCE_TRANSITION_AND_RESTART=PASS'
  Write-Output 'R20_SCIENTIFIC_FIRST_USE=FALSE'
}catch{
  Write-Output ('R20_STOPPED_AT='+$stage)
  if($disabled){
    $safe=$false
    try{
      $safe=((-not $merged) -and (-not $transitioned) -and
             (Get-Main) -ceq $source -and (Get-Head $root) -ceq $source)
      if($safe){Test-Evidence $python $db $source 68 $head68}
    }catch{$safe=$false}
    if($safe){
      Enable-ScheduledTask -TaskName $taskName -ErrorAction Stop | Out-Null
      Start-ScheduledTask -TaskName $taskName -ErrorAction Stop
      Write-Output 'R20_ORIGINAL_PREMERGE_SOURCE_RESTORED=PASS'
    }else{
      Disable-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue | Out-Null
      Write-Output 'R20_FAIL_CLOSED_OWNER_TASK_DISABLED_UNTIL_QUALIFIED_RECOVERY'
    }
  }
  throw
}finally{
  if($approvalFile -and (Test-Path -LiteralPath $approvalFile)){
    Remove-Item -LiteralPath $approvalFile -Force -ErrorAction SilentlyContinue
  }
}
