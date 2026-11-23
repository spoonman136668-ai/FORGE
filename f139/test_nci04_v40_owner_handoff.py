"""Fail-closed V40 operator authority, custody and original handoff boundaries."""
from contextlib import closing
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from f139 import nci04_v40_owner_handoff_approval as a
from f139 import check_v40_release_source as scope
from f139 import nci04_v40_guarded_owner_handoff as cli
from f139.nci04_native_contract import canonical, digest
from f139.nci04_autonomy_feed import POLICY_SCHEMA, TITLE_PREFIX
from f139.local_controller import Database
from f139.nci04_v38_original_owner_transition_cli import rollback_view
from f139.test_v40_readonly_workflow_scope import V40ReadonlyWorkflowScopeTests, FROZEN
from scripts import check_rar_g145_pr_scope as guard

ROOT=Path(__file__).resolve().parents[1]
TARGET='d'*40
CANDIDATE='e'*40
TREE='f'*40
BRANCH='engineering/f139-v40-explicit-owner-handoff-20261109'
BASE=scope.BASELINE
BASE_TREE='548dd8a0cc7b9ea3db278aa82dc6a22e0c350929'
P='repos/'+a.REPO+'/'


def approval():
    return dict(schema=a.SCHEMA,source_sha=TARGET,from_source_sha=a.FROM,
        binary_sha256=a.BINARY_SHA256,expected_original_head_seq=a.HEAD,
        expected_original_head_sha256=a.HEAD_SHA256,qualification_run_id=500,
        qualification_artifact_id=600,qualification_artifact_sha256='a'*64,
        owner_source_transition=True,owner_policy_source_update=True,
        pause_resume_existing_task=True,create_immutable_owner_release_ref=True,
        hybrid_admission=False,scientific_first_use=False,new_controller=False,
        new_scheduler=False,new_queue=False,paid_model_calls=0)


def body(doc): return a.PREFIX+canonical(doc).decode('ascii')


def fixture(paused=True):
    policy=dict(schema=POLICY_SCHEMA,enabled=not paused,source_sha=a.FROM,
        title_prefix=TITLE_PREFIX,lanes=['Wingless','Yggdrasil'],
        max_issue_creations_per_cycle=2,require_owner_authored_pr=True,
        require_single_head_commit_delta=True,require_single_allowed_source_file=True,
        scientific_first_use=False,paid_model_calls=0,accepted_ref_mutations=0,
        new_controller=False,new_scheduler=False,new_queue=False)
    comment=dict(id=700,user=dict(login=a.OWNER),author_association='OWNER',
        issue_url='https://api.github.com/repos/'+a.REPO+'/issues/807',body=body(approval()))
    table={P+'issues/comments/700':comment,
        P+'issues/807':dict(state='open',number=807,user=dict(login=a.OWNER),
            author_association='OWNER',body=json.dumps(policy)),
        P+'issues/807/comments?per_page=100&page=1':[comment],
        P+'branches/main':dict(protected=True,commit=dict(sha=TARGET)),
        P+'branches/f139-owner-release-'+TARGET:dict(protected=True,commit=dict(sha=TARGET)),
        P+'git/commits/'+TARGET:dict(sha=TARGET,parents=[dict(sha=BASE),dict(sha=CANDIDATE)],
            verification=dict(verified=True),tree=dict(sha=TREE)),
        P+'git/commits/'+CANDIDATE:dict(sha=CANDIDATE,tree=dict(sha=TREE)),
        P+'rulesets/'+str(a.RULESET):dict(id=a.RULESET,name='FORGE F139 immutable owner release refs',
            target='branch',enforcement='active',bypass_actors=[],
            conditions=dict(ref_name=dict(include=['refs/heads/f139-owner-release-*'],exclude=[])),
            rules=[dict(type='update'),dict(type='deletion')]),
        P+'actions/runs/500':dict(id=500,head_sha=TARGET,
            path='.github/workflows/f139-g54-v9-owner-cutover.yml',event='issue_comment',
            head_branch='main',status='completed',conclusion='success',run_attempt=1,
            actor=dict(login=a.OWNER)),
        P+'actions/artifacts/600':dict(id=600,expired=False,size_in_bytes=1_700_000,
            name='f139-v40-source-bound-copy-build-'+TARGET+'-r500',digest='sha256:'+'a'*64,
            workflow_run=dict(id=500,head_sha=TARGET,repository_id=a.REPO_ID,head_repository_id=a.REPO_ID))}
    native_jobs=[dict(id=501,name='v40-invocation-qualification',run_id=500,status='completed',conclusion='success'),
        dict(id=502,name='v40-owner-readonly',run_id=500,status='completed',conclusion='success',
            runner_name='FORGE-CODEX-REMOTE',labels=['self-hosted','Windows','forge-codex-isolated']),
        dict(id=503,name='unrelated-legacy',status='completed',conclusion='skipped')]
    table[P+'actions/runs/500/jobs?per_page=100']=dict(total_count=3,jobs=native_jobs)
    run_id=1000
    for source,event,specs in ((CANDIDATE,'pull_request',(a.PUBLIC,a.CONTROLLER,a.DEVELOPMENT)),
                               (TARGET,'push',(a.PUBLIC,a.ORIGIN))):
        rows=[]
        for spec in specs:
            run_id+=1
            rows.append(dict(id=run_id,workflow_id=spec[0],name=spec[1],head_sha=source,event=event,
                status='completed',conclusion='success',run_attempt=1,actor=dict(login=a.OWNER)))
            if len(spec)==3:
                jobs=[dict(id=run_id*100+i,name=name,run_id=run_id,status='completed',conclusion='success')
                      for i,name in enumerate(sorted(spec[2]))]
                table[P+'actions/runs/'+str(run_id)+'/jobs?per_page=100']=dict(total_count=len(jobs),jobs=jobs)
        table[P+'actions/runs?head_sha='+source+'&event='+event+'&per_page=30']=dict(total_count=len(rows),workflow_runs=rows)
    return table


def context():
    env=dict(GITHUB_REPOSITORY=a.REPO,GITHUB_ACTOR=a.OWNER,RUNNER_NAME='FORGE-CODEX-REMOTE',
        GITHUB_EVENT_NAME='push',GITHUB_RUN_ATTEMPT='1',GITHUB_SHA=TARGET,
        GITHUB_REF='refs/heads/f139-owner-release-'+TARGET,GITHUB_RUN_ID='800')
    event=dict(created=True,deleted=False,forced=False,before='0'*40,after=TARGET,
        sender=dict(login=a.OWNER),repository=dict(full_name=a.REPO))
    return env,event


class OwnerApprovalTests(unittest.TestCase):
    def verify(self, table, paused=True):
        reads=[]
        def get(route):
            self.assertTrue(route.startswith(P))
            reads.append(route)
            return deepcopy(table[route])
        result=a.verify_owner_approval(get,TARGET,a.BINARY_SHA256,700,700,paused=paused)
        self.assertEqual(result['schema'],'forge.f139.v40.owner-handoff-plan.v1')
        self.assertEqual(result['comment_id'],700)
        self.assertEqual(len(result['candidate_qualification_runs']),3)
        self.assertEqual(len(result['main_qualification_runs']),2)
        return result

    def test_complete_authority_requires_twelve_candidate_jobs_eight_main_and_origin(self):
        self.verify(fixture())
        table=fixture(False)
        self.assertEqual(a.find_owner_approval(lambda r:deepcopy(table[r]),TARGET)['comment_id'],700)

    def test_approval_encoding_scope_types_source_head_and_binary_fail_closed(self):
        self.assertEqual(a.decode_body(body(approval())),approval())
        edits=dict(schema='other',source_sha=a.FROM,from_source_sha=TARGET,binary_sha256='0'*64,
            expected_original_head_seq=True,expected_original_head_sha256='0'*64,
            qualification_run_id=True,qualification_artifact_id=0,qualification_artifact_sha256='a',
            owner_source_transition=False,owner_policy_source_update=False,pause_resume_existing_task=False,
            create_immutable_owner_release_ref=False,hybrid_admission=True,scientific_first_use=True,
            new_controller=True,new_scheduler=True,new_queue=True,paid_model_calls=True)
        for key,value in edits.items():
            doc=approval();doc[key]=value
            with self.subTest(key=key),self.assertRaises(a.HandoffDenied):a.decode_body(body(doc))
        for text in (body(approval())+'\n',a.PREFIX+json.dumps(approval()),a.PREFIX+'{}',
                     body({**approval(),'extra':False}),a.PREFIX+'null',a.PREFIX+'{'):
            with self.subTest(text=text[:40]),self.assertRaises(a.HandoffDenied):a.decode_body(text)

    def test_provider_drift_is_never_authority(self):
        mutations=[
            ('issues/comments/700',('user','login'),'foreign'),
            ('issues/comments/700',('author_association',),'CONTRIBUTOR'),
            ('issues/comments/700',('issue_url',),'https://api.github.com/repos/'+a.REPO+'/issues/808'),
            ('actions/runs/500',('run_attempt',),2),
            ('actions/runs/500',('head_sha',),CANDIDATE),
            ('actions/runs/500',('conclusion',),'failure'),
            ('actions/artifacts/600',('expired',),True),
            ('actions/artifacts/600',('digest',),'sha256:'+'b'*64),
            ('actions/artifacts/600',('name',),'foreign'),
            ('actions/artifacts/600',('workflow_run','head_sha'),CANDIDATE),
            ('actions/artifacts/600',('workflow_run','repository_id'),1),
            ('branches/main',('commit','sha'),CANDIDATE),
            ('branches/main',('protected',),False),
            ('git/commits/'+TARGET,('verification','verified'),False),
            ('git/commits/'+CANDIDATE,('tree','sha'),'0'*40),
            ('branches/f139-owner-release-'+TARGET,('protected',),False),
            ('rulesets/'+str(a.RULESET),('bypass_actors',),[dict(actor_id=1)]),
            ('rulesets/'+str(a.RULESET),('rules',),[dict(type='deletion')]),
            ('rulesets/'+str(a.RULESET),('conditions','ref_name','exclude'),['refs/heads/*'])]
        for route,keys,value in mutations:
            table=fixture(); node=table[P+route]
            for key in keys[:-1]:node=node[key]
            node[keys[-1]]=value
            with self.subTest(route=route,keys=keys),self.assertRaises(a.HandoffDenied):self.verify(table)
        for key in ('bypass_actors','conditions'):
            table=fixture();del table[P+'rulesets/'+str(a.RULESET)][key]
            with self.assertRaises(a.HandoffDenied):self.verify(table)
        with self.assertRaises(a.HandoffDenied):self.verify(fixture(False))
        with self.assertRaises(a.HandoffDenied):a.verify_owner_approval(lambda r:None,TARGET,a.BINARY_SHA256,701,700,paused=True)

    def test_job_failure_missing_duplicate_replay_or_wrong_runner_denied(self):
        for route in [r for r in fixture() if '/jobs?' in r]:
            for mode in ('failed','missing','duplicate','wrongrun','truncated'):
                table=fixture(); data=table[route];jobs=data['jobs']
                if mode=='failed':jobs[0]['conclusion']='skipped'
                elif mode=='missing':jobs.pop(0);data['total_count']-=1
                elif mode=='duplicate':jobs.append(deepcopy(jobs[0]));data['total_count']+=1
                elif mode=='wrongrun':jobs[0]['run_id']=0
                else:data['total_count']+=1
                with self.subTest(route=route,mode=mode),self.assertRaises(a.HandoffDenied):self.verify(table)
        table=fixture();table[P+'actions/runs/500/jobs?per_page=100']['jobs'][1]['runner_name']='other'
        with self.assertRaises(a.HandoffDenied):self.verify(table)
        for route in [r for r in fixture() if 'actions/runs?' in r]:
            for mode in ('attempt','missing','duplicate','truncated'):
                table=fixture();data=table[route];rows=data['workflow_runs']
                if mode=='attempt':rows[0]['run_attempt']=2
                elif mode=='missing':rows.pop(0);data['total_count']-=1
                elif mode=='duplicate':rows.append(deepcopy(rows[0]));data['total_count']+=1
                else:data['total_count']+=1
                with self.subTest(route=route,mode=mode),self.assertRaises(a.HandoffDenied):self.verify(table)

    def test_comments_must_be_unique_and_complete(self):
        table=fixture(False);route=P+'issues/807/comments?per_page=100&page=1'
        for rows in ([],[table[route][0],table[route][0]],
                     [table[route][0],{**table[route][0],'id':701}]):
            data=deepcopy(table);data[route]=rows
            with self.assertRaises(a.HandoffDenied):a.find_owner_approval(lambda r:data[r],TARGET)
        with self.assertRaises(a.HandoffDenied):
            a.find_owner_approval(lambda r:[dict(id=1000*int(r.rsplit('=',1)[1])+i) for i in range(100)],TARGET)

    def test_create_only_original_context_precedes_every_live_call(self):
        env,event=context();a.verify_runtime_context(TARGET,env,event)
        for key,value in dict(GITHUB_ACTOR='foreign',RUNNER_NAME='other',GITHUB_EVENT_NAME='workflow_dispatch',
                GITHUB_RUN_ATTEMPT='2',GITHUB_SHA=CANDIDATE,GITHUB_REF='refs/heads/main',GITHUB_RUN_ID='0').items():
            with self.subTest(key=key),self.assertRaises(a.HandoffDenied):a.verify_runtime_context(TARGET,{**env,key:value},event)
        for key,value in dict(created=False,deleted=True,forced=True,before=a.FROM,after=CANDIDATE).items():
            with self.subTest(key=key),self.assertRaises(a.HandoffDenied):a.verify_runtime_context(TARGET,env,{**event,key:value})
        with patch.dict(os.environ,{},clear=True),patch.object(cli,'guarded_transition') as live:
            with self.assertRaises(a.HandoffDenied):cli.main(['--target',TARGET])
            live.assert_not_called()
        with patch.object(cli,'verify_runtime_context'),patch.object(cli,'guarded_transition') as live:
            with self.assertRaises(ValueError):cli.main(['--target',TARGET,'--plan-only','--event-id','700'])
            live.assert_not_called()


class BackupCustodyTests(unittest.TestCase):
    def bundle(self, root):
        path=root/'state.sqlite';backup=root/'f139-v40-before-800'/'state.sqlite'
        db=Database.initialize(path,a.FROM)
        backup.parent.mkdir()
        with closing(sqlite3.connect(str(backup))) as out:db.conn.backup(out)
        (backup.parent/'evidence').mkdir();(backup.parent/'evidence'/'negative.zip').write_bytes(b'preserved negative')
        manifest={'state.sqlite':digest(backup.read_bytes()),'evidence/negative.zip':digest(b'preserved negative')}
        (backup.parent/'manifest.sha256.json').write_bytes(canonical(manifest))
        receipt=dict(schema='forge.f139.v40.original-cold-backup.v1',source_sha=a.FROM,target_source_sha=TARGET,
            expected_original_head_seq=db.meta()['head_seq'],expected_original_head_sha256=db.meta()['head_hash'],
            sqlite_sha256=manifest['state.sqlite'],logical_view_sha256=digest(canonical(rollback_view(db.conn))),
            archive_manifest_sha256=digest(canonical(manifest)))
        (backup.parent/'v40-backup-receipt.json').write_bytes(canonical(receipt))
        return db,backup,receipt

    def test_readonly_full_logical_and_archive_backup_with_original_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,GITHUB_RUN_ID='800'):
            db,backup,receipt=self.bundle(Path(tmp))
            try:
                before=db.meta().copy();changes=db.conn.total_changes
                self.assertEqual(a.verify_original_backup(db,backup,TARGET,receipt),receipt)
                self.assertEqual(db.meta(),before);self.assertEqual(db.conn.total_changes,changes)
                (backup.parent/'evidence'/'negative.zip').write_bytes(b'changed')
                with self.assertRaises(a.HandoffDenied):a.verify_original_backup(db,backup,TARGET,receipt)
                self.assertEqual(db.meta(),before)
            finally:db.close()

    def test_manifest_escape_and_symlink_cannot_replace_original_backup(self):
        for mode in ('escape','absolute','backslash','symlink','logical'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,GITHUB_RUN_ID='800'):
                db,backup,receipt=self.bundle(Path(tmp))
                try:
                    manifest=json.loads((backup.parent/'manifest.sha256.json').read_bytes())
                    if mode=='logical':receipt['logical_view_sha256']='0'*64
                    elif mode=='symlink':
                        path=backup.parent/'evidence'/'negative.zip';path.unlink();path.symlink_to(db.filename)
                    else:manifest[{'escape':'../state.sqlite','absolute':'/state.sqlite','backslash':'bad\\path'}[mode]]=digest(db.filename.read_bytes())
                    (backup.parent/'manifest.sha256.json').write_bytes(canonical(manifest))
                    receipt['archive_manifest_sha256']=digest(canonical(manifest))
                    (backup.parent/'v40-backup-receipt.json').write_bytes(canonical(receipt))
                    with self.assertRaises(a.HandoffDenied):a.verify_original_backup(db,backup,TARGET,receipt)
                finally:db.close()


class SourceAndWorkflowTests(unittest.TestCase):
    def source_reads(self,*args):
        if args==('rev-parse','HEAD'):return TARGET
        if args==('status','--porcelain','--untracked-files=all'):return ''
        if args==('merge-base',BASE,TARGET):return BASE
        if args==('diff','--no-renames','--name-only',BASE,TARGET):return '\n'.join(sorted(scope.PATHS))
        return ''

    def test_source_manifest_and_original_consumed_jobs_remain_sealed(self):
        self.assertEqual(scope.verify(ROOT,get=self.source_reads),TARGET)
        for kind in ('dirty','base','extra','model'):
            def get(*args):
                if kind=='dirty' and args[0]=='status':return ' M dirty'
                if kind=='base' and args[0]=='merge-base':return '0'*40
                if kind=='extra' and args[:3]==('diff','--no-renames','--name-only'):return self.source_reads(*args)+'\nf139/local_controller.py'
                if kind=='model' and args[:2]==('diff','--name-only'):return 'genenv/unsafe.go'
                return self.source_reads(*args)
            with self.subTest(kind=kind),self.assertRaises(ValueError):scope.verify(ROOT,get=get)

    def test_frozen_owner_scope_and_cache_adapters_require_exact_base_tree(self):
        head=TARGET
        for mode in ('valid','foreign','base','extra'):
            base=BASE if mode!='base' else '0'*40
            request=dict(number=1,author_association='OWNER' if mode!='foreign' else 'CONTRIBUTOR',
                user=dict(login=a.OWNER),head=dict(sha=head,ref=BRANCH,repo=dict(full_name=a.REPO)),
                base=dict(sha=base,ref='main',repo=dict(full_name=a.REPO)))
            with tempfile.TemporaryDirectory() as tmp:
                event=Path(tmp)/'event.json';event.write_text(json.dumps(dict(number=1,pull_request=request)))
                paths=sorted(scope.PATHS)+(['f139/local_controller.py'] if mode=='extra' else [])
                reads={('diff','--no-renames','--name-only',BASE,head):'\n'.join(paths)}
                with patch.dict(os.environ,GITHUB_EVENT_NAME='pull_request',GITHUB_EVENT_PATH=str(event),GITHUB_HEAD_REF=BRANCH,GITHUB_BASE_REF='main'):
                    if mode=='valid':self.assertEqual(guard.admit_original_pr(head,lambda *a:reads[a]),FROZEN)
                    else:
                        with self.assertRaises(ValueError):guard.admit_original_pr(head,lambda *a:reads[a])
        V40ReadonlyWorkflowScopeTests().assert_cache_adapters(BRANCH,BASE,BASE_TREE)

    def test_plan_and_copy_precede_pause_backup_precedes_key_and_live_commit(self):
        text=(ROOT/scope.WORKFLOW).read_text();job=text.split('  handoff-v40:',1)[1]
        self.assertLess(job.index('--plan-only'),job.index('Disable-ScheduledTask'))
        self.assertLess(job.index('--preflight-only --rehearse-copy'),job.index('Disable-ScheduledTask'))
        self.assertLess(job.index('v40-backup-receipt.json'),job.index('Import-Clixml'))
        self.assertLess(job.index('F139_V40_COLD_BACKUP_LOGICAL_DRIFT'),job.index('f139.nci04_v40_guarded_owner_handoff --db'))
        for forbidden in ('Register-ScheduledTask','New-ScheduledTask','create_ref','workflow_dispatch:'):
            self.assertNotIn(forbidden,job)
        self.assertIn('F139_V40_POSTMUTATION_EXISTING_TASK_DISABLED_AND_QUIESCENT',job)
        self.assertIn('F139_V40_ORIGINAL_SOURCE_AND_EXECUTABLE_TRANSITION_DENIED',job)
        self.assertIn('Remove-Item Env:F139_WORKER_HMAC_KEY',job)

    @unittest.skipUnless(os.name=='nt' and shutil.which('powershell.exe'),'Windows inert PowerShell parser')
    def test_windows_parses_handoff_without_executing_it(self):
        text=(ROOT/scope.WORKFLOW).read_text().split('  handoff-v40:',1)[1].split('        run: |',1)[1]
        script='\n'.join(line[10:] if line.startswith('          ') else line for line in text.splitlines())
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'handoff.ps1';path.write_text(script,encoding='utf-8')
            command="$t=$null;$e=$null;[System.Management.Automation.Language.Parser]::ParseFile('"+str(path).replace("'","''")+"',[ref]$t,[ref]$e)>$null;if($e.Count){$e|ForEach-Object{Write-Error $_};exit 1}"
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__':unittest.main()
