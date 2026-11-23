"""Guarded receipt-only reconciliation and source maintenance on the original owner.

One fixed completed run, no dispatcher, loop, queue submission or model call.
The existing installer supplies the owner's DPAPI key only in process memory.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess

from f139.local_controller import Database, GitHub, SingleOwner, native_original_owner_profile, legacy_windows_task_disabled
from f139.nci04_native_contract import canonical
from f139.nci04_model_owner_bridge import inspect_policy, FORGE_REPO, POLICY_ISSUE
from f139.nci04_owner_ledger import activate_native, APPROVAL_SCHEMA, verify_native_activation
from f139.nci04_g38_owner_terminal import settle_original_v2
from f139.nci04_v31_source_transition import FROM_V30, RUN, TICKET, build_proof, commit_transition, validate_waiting, need

def git(root, *args):
    p=subprocess.run(['git','-C',str(root),*args],capture_output=True,timeout=20,check=False)
    need(p.returncode==0,'SOURCE_GIT_READ_DENIED')
    return p.stdout.decode('utf-8','strict').strip()

def reactivate(db,target):
    need(activate_native(db,dict(schema=APPROVAL_SCHEMA,source_sha=target,
         expected_event_head_sha256=db.meta()['head_hash'],native_development_approved=True,
         scientific_first_use=False,create_controller=False,paid_api_calls=0)), 'NATIVE_REACTIVATION_DENIED')
    db.verify()
    need(verify_native_activation(db),'NATIVE_REACTIVATION_NOT_AUTHENTIC')

def reconcile(db,api,path,key):
    started=validate_waiting(db)
    result=settle_original_v2(db,api,path,ticket=TICKET,run_id=RUN,started_at=started,owner_key=key)
    need(result['outcome']=='VERIFIED' and db.meta()['head_seq']==382,'ORIGINAL_RECEIPTS_NOT_BOTH_QUALIFIED')
    return result

def guarded_transition(path,backup,target,event_id):
    need(os.name=='nt' and re.fullmatch(r'[a-f0-9]{40}',target)
         and type(event_id) is int and event_id>0,'WINDOWS_EXACT_TARGET_REQUIRED')
    root=Path(__file__).resolve().parent.parent
    need(git(root,'rev-parse','HEAD')==target and not git(root,'status','--porcelain','--untracked-files=all'),
         'EXACT_CLEAN_QUALIFIED_CHECKOUT_REQUIRED')
    need(backup.is_file() and not backup.is_symlink() and backup.resolve()!=path.resolve(), 'COLD_BACKUP_REQUIRED')
    native_original_owner_profile(path)
    legacy_windows_task_disabled()
    key=os.environ.get('F139_WORKER_HMAC_KEY','')
    need(32<=len(key)<=4096,'ORIGINAL_DPAPI_KEY_REQUIRED')
    api=GitHub()
    protected=api.protected_main()
    compare=api.native_repo_get('repos/'+FORGE_REPO+'/compare/'+target+'...'+protected)
    need(compare.get('status') in ('ahead','identical') and compare.get('behind_by')==0
         and compare.get('merge_base_commit',{}).get('sha')==target,'QUALIFIED_RELEASE_NOT_IN_MAIN')
    policy=api.native_repo_get('repos/'+FORGE_REPO+'/issues/'+str(POLICY_ISSUE))
    need(inspect_policy(policy,FROM_V30)['enabled'] is False,'ORIGINAL_POLICY_NOT_PAUSED')
    release=api.native_repo_get('repos/'+FORGE_REPO+'/branches/f139-owner-release-'+target)
    need(release.get('protected') is True and release.get('commit',{}).get('sha')==target,'IMMUTABLE_RELEASE_REF_REQUIRED')
    api.legacy_dispatchers_disabled()
    db=Database(path)
    try:
        with SingleOwner(path.with_suffix('.lock')):
            validate_waiting(db)
            before=db.meta().copy()
            cold=Database.open_readonly(backup)
            rehearsal=backup.with_name('v31-authenticated-receipt-rehearsal.sqlite')
            try:
                cold.verify()
                need(cold.meta()==before and not rehearsal.exists(),'BACKUP_OR_REHEARSAL_DRIFT')
                dst=sqlite3.connect(str(rehearsal))
                try: cold.conn.backup(dst)
                finally: dst.close()
            finally:
                cold.close()
            copy=Database(rehearsal)
            try:
                with SingleOwner(rehearsal.with_suffix('.lock')):
                    reconcile(copy,api,rehearsal,key)
                    proof=build_proof(copy,target,event_id)
                    commit_transition(copy,proof,owner_witness=lambda:True)
                    reactivate(copy,target)
                copy.close()
                reopened=Database.open_readonly(rehearsal)
                try: reopened.verify()
                finally: reopened.close()
            finally:
                copy.close()
            print('F139_V31_AUTHENTICATED_RECEIPT_AND_TRANSITION_REHEARSAL=PASS')
            need(db.meta()==before and native_original_owner_profile(path),'ORIGINAL_STATE_OR_OWNER_MOVED')
            need(api.protected_main()==protected,'PROTECTED_MAIN_MOVED')
            current=api.native_repo_get('repos/'+FORGE_REPO+'/issues/'+str(POLICY_ISSUE))
            need(current.get('body')==policy.get('body'),'POLICY_MOVED_DURING_REHEARSAL')
            result=reconcile(db,api,path,key)
            print('F139_V31_EXISTING_ORIGINAL_V2_RECEIPTS_CUSTODIED=PASS')
            need(api.protected_main()==protected,'PROTECTED_MAIN_MOVED_AFTER_CUSTODY')
            need(api.native_repo_get('repos/'+FORGE_REPO+'/issues/'+str(POLICY_ISSUE)).get('body')==policy.get('body'),
                 'POLICY_MOVED_AFTER_CUSTODY')
            proof=build_proof(db,target,event_id)
            report=commit_transition(db,proof,owner_witness=lambda:native_original_owner_profile(path))
            reactivate(db,target)
            need(db.meta()['head_seq']==384,'FINAL_ORIGINAL_HEAD_DRIFT')
            return {**report,'activation_event_seq':384,'native_reactivated':True,
                    'event_head_sha256':db.meta()['head_hash'],'original_run_id':RUN,
                    'original_outcome':result['outcome'],'redispatches':0}
    finally:
        db.close()

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--db',type=Path,required=True)
    p.add_argument('--backup',type=Path,required=True)
    p.add_argument('--target',required=True)
    p.add_argument('--event-id',type=int,required=True)
    args=p.parse_args(argv)
    print(canonical(guarded_transition(args.db,args.backup,args.target,args.event_id)).decode('ascii'))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
