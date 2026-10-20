# F139-D2P: READ ONLY. Authenticated historic custody and one controller-owned D2K terminal.
# Never starts/stops task, dispatches, writes original DB, or activates science.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$Repo='spoonman136668-ai/FORGE'
$Source='34ca99c1b5b063225566082aee5aa180a15d093b'
$Seal='eea95c859f9a59f700612c3b7b39152abc78827981976e9d86567c29fa03ff87'
$Run=39414572565
$Ticket='f139-d2k-i671-34ca99c1b5b0-afd83773'
$TaskName='FORGE-F139-UnifiedController'
function Demand([bool]$test,[string]$reason){if(!$test){throw ('F139_D2P_BLOCKED_'+$reason)}}
Demand ($env:RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE' -and $env:GITHUB_REPOSITORY -ceq $Repo -and $env:RUNNER_OS -ceq 'Windows') 'WRONG_LOCAL_RUNNER'
$task=Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
Demand ($task.State -eq 'Running' -and [string]$task.Principal.LogonType -eq 'Interactive' -and @($task.Actions).Count -eq 1) 'ORIGINAL_CONTROLLER_NOT_RUNNING'
$owner=([Security.Principal.NTAccount]::new([string]$task.Principal.UserId)).Translate([Security.Principal.SecurityIdentifier])
Demand ($owner.Value -ceq [Security.Principal.WindowsIdentity]::GetCurrent().User.Value) 'NOT_CONTROLLER_OWNER'
$arguments=[string]$task.Actions[0].Arguments
$paths=@{}
foreach($n in @('RepositoryRoot','Database','PythonExe')){
  $m=[regex]::Match($arguments,'(?i)(?:^|\s)-'+$n+'\s+"([^"]+)"')
  Demand $m.Success ('MISSING_TASK_ARGUMENT_'+$n)
  $paths[$n]=$m.Groups[1].Value
}
Demand (Test-Path -LiteralPath $paths.PythonExe -PathType Leaf) 'OWNER_PYTHON_MISSING'
$tree=(& git -C $paths.RepositoryRoot rev-parse HEAD).Trim()
Demand ($LASTEXITCODE -eq 0 -and $tree -ceq $Source) 'QUALIFIED_TASK_SOURCE_DRIFT'
$main=(& gh api -X GET repos/spoonman136668-ai/FORGE/branches/main)|ConvertFrom-Json
Demand ($LASTEXITCODE -eq 0 -and $main.protected -eq $true -and $main.commit.sha -ceq $Source) 'PROTECTED_MAIN_DRIFT'
$issue=(& gh api -X GET repos/spoonman136668-ai/FORGE/issues/671)|ConvertFrom-Json
Demand ($LASTEXITCODE -eq 0 -and $issue.number -eq 671 -and $issue.id -eq 5940729559 -and
  $issue.user.login -ceq 'spoonman136668-ai' -and $issue.author_association -ceq 'OWNER') 'OWNER_ISSUE_ORIGIN_DRIFT'
$issueBody=$issue.body|ConvertFrom-Json
Demand ($issueBody.schema -ceq 'forge.f139.d2k.owner-development.v1' -and
  $issueBody.source_sha -ceq $Source -and $issueBody.kind -ceq 'go-package-test-diagnostic' -and
  $issueBody.target_package -ceq './optimizerstages' -and $issueBody.lane -ceq 'Qualification' -and
  $issueBody.scientific_first_use -eq $false -and $issueBody.paid_model_calls -eq 0) 'OWNER_ISSUE_CHANGED'
$provider=(& gh api -X GET ('repos/spoonman136668-ai/FORGE/actions/runs/'+$Run))|ConvertFrom-Json
Demand ($LASTEXITCODE -eq 0 -and $provider.status -ceq 'completed' -and $provider.conclusion -ceq 'success' -and
  $provider.id -eq $Run -and $provider.head_sha -ceq $Source -and
  $provider.workflow_id -eq 388797257 -and $provider.event -ceq 'workflow_dispatch' -and
  $provider.run_attempt -eq 1 -and $provider.display_title -ceq ('F139 '+$Ticket)) 'AUTHENTIC_WORKER_RUN_DRIFT'

$verify=@'
import json,sys,sqlite3,tempfile
from pathlib import Path
from f139.local_controller import Database,GitHub,canonical,hash_bytes,receipt_from_zip
from f139.audit_d2k_custody import verify_chain,verify_evidence,load_provider_anchor,verify_d2j_task_bindings
dbpath=Path(sys.argv[1]); src=sys.argv[2]; seal=sys.argv[3]
ticket=sys.argv[4]; run_id=int(sys.argv[5]); issue_number=671; issue_id=5940729559
with tempfile.TemporaryDirectory(prefix='f139-d2p-verify-') as folder:
    snapshot=Path(folder)/'snapshot.sqlite'
    original=sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True,timeout=15)
    try:
        original.execute('PRAGMA query_only=ON')
        copy=sqlite3.connect(snapshot)
        try:original.backup(copy)
        finally:copy.close()
    finally:original.close()
    db=Database(snapshot)
    try:
        db.verify()
        meta=db.meta()
        assert meta['source_sha']==src and meta['enabled']==1 and meta['legacy_suspended']==1
        events=list(db.conn.execute('SELECT * FROM events ORDER BY seq'))
        tasks=[dict(r) for r in db.conn.execute('SELECT * FROM tasks ORDER BY ticket')]
        assert len(events)==29 and len(tasks)==5 and meta['head_seq']==29, 'UNEXPECTED_EVENT_OR_TASK_COUNT'
        terminals,prefix_head,derived=verify_chain(events[:24],seal,qualified_main_sha=src)
        assert derived==src and events[23]['sha']==prefix_head,'D2N_ORIGINAL_SOURCE_TRANSITION_DRIFT'
        original_tasks=[r for r in tasks if r['ticket'] in terminals]
        assert len(original_tasks)==4 and all(r['stage']=='VERIFIED' for r in original_tasks),'FOUR_ORIGINAL_TASKS_DRIFT'
        verify_d2j_task_bindings(events[:24],original_tasks)
        anchor=load_provider_anchor()
        for original_task in original_tasks:
            verify_evidence(dbpath.parent,original_task,meta['epoch'],anchor)
        tail=events[24:]
        assert [r['kind'] for r in tail]==[
            'DEVELOPMENT_WORK_ADMITTED','TASK_INTAKE',
            'BEFORE_DISPATCH_INTENT','DISPATCH_POST_RETURNED',
            'PROVIDER_VERIFIED_TERMINAL'],'D2P_EVENT_SUFFIX_INVALID'
        admission=json.loads(tail[0]['payload'])
        assert admission['issue_number']==issue_number and admission['issue_id']==issue_id
        assert admission['ticket']==ticket and admission['source_sha']==src
        assert admission['kind']=='go-package-test-diagnostic' and admission['target_package']=='./optimizerstages'
        assert admission['scientific_first_use'] is False and admission['prior_event_head_sha256']==events[23]['sha']
        active=[r for r in tasks if r['ticket']==ticket]
        assert len(active)==1 and active[0]['stage']=='VERIFIED' and active[0]['run_id']==run_id,'D2P_NOT_VERIFIED'
        row=active[0]
        assert row['source_sha']==src and row['lane']=='Qualification' and row['manifest_sha']==admission['manifest_sha256']
        fields=db.d2k_fields(ticket)
        api=GitHub()
        assert api.protected_main()==src,'PROTECTED_SOURCE_DRIFT'
        result=api.candidates(ticket,row['started_at'])
        assert result is not None and result['id']==run_id,'AUTHENTIC_RUN_NOT_FOUND'
        proof=api.run_proof(result,ticket,src,row['started_at'])
        assert proof is not None and proof[0]==run_id,'AUTHENTIC_PROVIDER_PROOF_UNAVAILABLE'
        artifacts=proof[1]
        expected={a['name']:a for a in artifacts}
        assert set(expected)=={'forge-f139-dev-receipt-ubuntu-latest','forge-f139-dev-receipt-windows-latest'},'WORKER_ARTIFACT_SET_DRIFT'
        for platform in ('ubuntu-latest','windows-latest'):
            art=expected['forge-f139-dev-receipt-'+platform]
            provider_bytes=api.artifact(art['id'])
            receipt_from_zip(provider_bytes,art,row,run_id,platform,meta['epoch'],d2k_fields=fields)
            evidence=Path(row['evidence_dir'])/(platform+'.zip')
            assert evidence.is_file() and evidence.read_bytes()==provider_bytes, 'STORED_PROVIDER_BYTES_DRIFT'
        manifest=Path(row['evidence_dir'])/'manifest.json'
        assert manifest.is_file() and hash_bytes(manifest.read_bytes())==row['evidence_sha'],'MANIFEST_DIGEST_DRIFT'
        report=json.loads(manifest.read_bytes())
        assert report['scientific_originals']==0 and report['approved_science'] is False, 'SCIENCE_GRANT_DRIFT'
        assert json.loads(tail[-1]['payload'])['run_id']==run_id,'TERMINAL_EVENT_NOT_AUTHENTIC'
        assert all(e['kind']!='ATTEMPT_QUARANTINED' for e in tail),'QUARANTINED_WORK'
        print(json.dumps({'source':src,'event_count':29,'original_prefix':24,
                          'original_tasks':4,'original_archives':8,'development_tasks':1,
                          'd2p_run_id':run_id,'d2p_stage':'VERIFIED',
                          'independently_checked_artifacts':2,
                          'scientific_first_use':False,
                          'event_head_sha256':meta['head_hash']},sort_keys=True))
    finally:db.close()
'@
$oldDir=(Get-Location).Path
try{
  Set-Location -LiteralPath $paths.RepositoryRoot
  $accepted=$null
  for($i=0;$i -lt 18;$i++){
    $statusCode=@'
import sys,sqlite3
from pathlib import Path
p=Path(sys.argv[1]); ticket=sys.argv[2]; rid=int(sys.argv[3])
c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,timeout=15)
try:
    r=c.execute('SELECT stage,run_id FROM tasks WHERE ticket=?',(ticket,)).fetchone()
    if r is None or r[0]!='VERIFIED':
        raise SystemExit(73)
    assert r[1]==rid,'WRONG_TERMINAL_RUN_ID'
finally:c.close()
'@
    & $paths.PythonExe -B -c $statusCode $paths.Database $Ticket $Run 2>&1 | Out-Null
    $rc=$LASTEXITCODE
    if($rc -eq 0){$accepted=$true;break}
    Demand ($rc -eq 73) 'UNEXPECTED_D2P_LEDGER_STATE'
    Start-Sleep -Seconds 10
  }
  Demand ($accepted -eq $true) 'D2P_TERMINAL_NOT_YET_RECONCILED'
  for($check=1;$check -le 2;$check++){
    $value=@(& $paths.PythonExe -B -c $verify $paths.Database $Source $Seal $Ticket $Run 2>&1)
    Demand ($LASTEXITCODE -eq 0) ('PROVIDER_OR_CUSTODY_AUDIT_FAILED_SNAPSHOT_'+$check+': '+(($value|ForEach-Object{[string]$_}) -join ' ').Substring(0,[Math]::Min(500,(($value|ForEach-Object{[string]$_}) -join ' ').Length)))
    $json=($value -join [Environment]::NewLine)|ConvertFrom-Json
    Demand ($json.event_count -eq 29 -and $json.d2p_stage -ceq 'VERIFIED' -and $json.scientific_first_use -eq $false) 'D2P_PROOF_INVALID'
    if($check -eq 1){$firstHead=$json.event_head_sha256}
    else{Demand ($firstHead -ceq $json.event_head_sha256) 'LATE_DUPLICATE_OR_LEDGER_DRIFT'}
    Write-Output ('F139_D2P_INDEPENDENT_RECEIPT_SNAPSHOT_'+$check+'=PASS')
    if($check -eq 1){Start-Sleep -Seconds 48}
  }
  Demand ((Get-ScheduledTask -TaskName $TaskName).State -eq 'Running') 'CONTROLLER_STOPPED_DURING_PROOF'
  Write-Output 'F139_D2P_OWNER_ISSUE_671=AUTHENTIC'
  Write-Output 'F139_D2P_AUTONOMOUS_DISPATCH_ONCE=PASS'
  Write-Output 'F139_D2P_ORIGINAL_24_EVENT_CUSTODY=PASS'
  Write-Output 'F139_D2P_HISTORICAL_TASKS=4_OF_4_PASS'
  Write-Output 'F139_D2P_HISTORICAL_ZIPS=8_OF_8_PASS'
  Write-Output 'F139_D2P_GITHUB_PROVIDER_ARTIFACTS=2_OF_2_PASS'
  Write-Output 'F139_D2P_DURABLE_WORKER_TERMINAL=VERIFIED'
  Write-Output 'F139_D2P_DUPLICATE_DISPATCHES=0'
  Write-Output 'F139_D2P_SCIENTIFIC_FIRST_USE=BLOCKED'
  Write-Output 'F139_D2P_DISPOSITION=QUALIFIED_UNATTENDED_DEVELOPMENT_SUCCESSION_PASS'
}finally{Set-Location -LiteralPath $oldDir}
