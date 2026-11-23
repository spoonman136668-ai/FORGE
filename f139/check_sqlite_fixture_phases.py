"""Same-source private-fixture ABBA diagnosis, never benefit acceptance."""
import argparse
import hashlib
import json
import os
import platform
import sqlite3
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BASE='3f7514e2a132fbdb181a22b53d36d8a29e715de6'
SELECTED=('test_nci04_prospective_journal','test_nci04_provider_negative_custody_v2',
          'test_nci04_v30_source_transition')
PRIMARY={'sqlite_execute_COMMIT','sqlite_commit_method','sqlite_context_exit',
         'sqlite_execute_INSERT','sqlite_execute_UPDATE','sqlite_execute_DELETE',
         'sqlite_executemany_INSERT','sqlite_executemany_UPDATE','sqlite_executemany_DELETE'}


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],timeout=60).decode().strip()


def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite): yield from flatten(item)
        else: yield item


def child(root, mode):
    from f139.check_test_discovery_inventory import discover_profile_suite,profile_suite,case_ids
    from f139.profile_resources import ResourceSampler
    from f139.profile_sqlite_phases import PhaseRecorder,private_sqlite_probe
    full=discover_profile_suite(root)
    selected=unittest.TestSuite(case for case in flatten(full) if type(case).__module__ in SELECTED)
    ids=case_ids(selected)
    if len(ids)!=26: raise ValueError('Frozen 26-case cohort drift')
    with tempfile.TemporaryDirectory(prefix='f139-private-phases-') as directory:
        private=Path(directory).resolve()
        old=tempfile.tempdir
        tempfile.tempdir=str(private)
        recorder=PhaseRecorder(private,enabled=mode=='instrumented')
        try:
            with private_sqlite_probe(recorder):
                report=profile_suite(selected,ids,resource_sampler=ResourceSampler())
        finally:
            tempfile.tempdir=old
        report['phases']=recorder.snapshot()
        report['unmeasured_factory_or_copy_entries']=recorder.bypasses
        report['observed_threads']=len(recorder.threads)
        report['phase_observation_status']={kind:('OBSERVED' if kind in report['phases'] else 'UNVERIFIED_NOT_OBSERVED')
            for kind in ('sqlite_execute_COMMIT','sqlite_close','sqlite_backup','file_copy','file_copy2')}
    report['private_root_cleanup_complete']=not private.exists()
    report['mode']=mode; report['ids']=ids
    print('F139_SQLITE_CHILD='+json.dumps(report,sort_keys=True))
    if not report['successful']: raise SystemExit(1)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--child',choices=('plain','instrumented'))
    parser.add_argument('--expected-source')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    if args.child:
        child(root,args.child)
        return
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REPOSITORY')!='spoonman136668-ai/FORGE':
        raise ValueError('Parent diagnosis requires existing FORGE hosted qualification')
    source=git(root,'rev-parse','HEAD')
    if args.expected_source!=source or git(root,'status','--porcelain','--untracked-files=all'):
        raise ValueError('Exact clean diagnostic source required')
    if git(root,'merge-base',BASE,source)!=BASE: raise ValueError('Accepted baseline ancestry drift')
    for line in git(root,'diff','--name-only',BASE,'--','f139/test_*.py').splitlines():
        raise ValueError('Original test changed: '+line)
    output=args.output.resolve()
    output.relative_to(Path(os.environ['RUNNER_TEMP']).resolve())
    from f139.profile_resources import telemetry_identity
    report=dict(python=sys.version,platform=platform.platform(),sqlite_version=sqlite3.sqlite_version,resource_identity=telemetry_identity(),schema='forge.f139.private-sqlite-phase-diagnosis.v1',
        candidate_sha=source,candidate_tree=git(root,'rev-parse','HEAD^{tree}'),baseline_sha=BASE,
        workflow_run=os.environ.get('GITHUB_RUN_ID'),workflow_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),
        selected_modules=SELECTED,selection_performed=True,full_regression_evidence=False,
        primary_hypothesis='Observed write/commit API elapsed >=50% cohort suite elapsed in BOTH instrumented runs',
        primary_threshold=0.5,primary_operations=sorted(PRIMARY),
        operation_scope='Outermost intercepted Python API call per thread',
        unmeasured=['cursor fetch/direct cursor execute','SQLite internals/fsync duration',
                    'destructor closes','pre-bound copy aliases','child processes'],
        sampling_overhead_independently_measured=False,scientific_first_use=False,
        speedup_proven=False,autonomous_proposal=False,owner_mutations=0,
        module_sha256=hashlib.sha256((root/'f139/profile_sqlite_phases.py').read_bytes()).hexdigest(),
        checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),measurements=[])
    for mode in ('plain','instrumented','instrumented','plain'):
        print('F139_SQLITE_PHASE_START='+mode,flush=True)
        if git(root,'rev-parse','HEAD')!=source or git(root,'status','--porcelain','--untracked-files=all'):
            raise ValueError('Source drift before cohort')
        result=subprocess.run([sys.executable,'-B',str(Path(__file__)), '--child',mode],cwd=root,
            env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(root)},
            stdout=subprocess.PIPE,text=True,timeout=240)
        records=[line.removeprefix('F139_SQLITE_CHILD=') for line in result.stdout.splitlines()
                 if line.startswith('F139_SQLITE_CHILD=')]
        if result.returncode or len(records)!=1: raise ValueError('Cohort child failed or ambiguous receipt')
        value=json.loads(records[0])
        if not value['private_root_cleanup_complete'] or not value['complete_inventory_and_order']:
            raise ValueError('Private cleanup or original cohort completeness failed')
        if report['measurements']:
            first=report['measurements'][0]
            for key in ('ids','skipped_ids','tests_run'):
                if value[key]!=first[key]: raise ValueError('Mode changed original case/skip inventory')
        report['measurements'].append(value)
    if git(root,'rev-parse','HEAD')!=source or git(root,'status','--porcelain','--untracked-files=all'):
        raise ValueError('Source drift after cohort')
    report['source_stable']=True
    instrumented=[r for r in report['measurements'] if r['mode']=='instrumented']
    fractions=[]
    for value in instrumented:
        measured=sum(row['seconds'] for kind,row in value['phases'].items() if kind in PRIMARY)
        fraction=measured/value['suite_seconds']
        value['write_commit_api_seconds']=measured; value['write_commit_api_fraction']=fraction
        fractions.append(fraction)
    coverage=all(v['observed_threads']==1 and v['unmeasured_factory_or_copy_entries']==0 for v in instrumented)
    report['hypothesis_status']=('UNVERIFIED_SCOPE_GAP' if not coverage else
        'SUPPORTED_FOR_THIS_DIAGNOSTIC_COHORT' if min(fractions)>=0.5 else 'NOT_DEMONSTRATED')
    a,b,c,d=[v['suite_seconds'] for v in report['measurements']]
    report['instrumented_to_plain_elapsed_ratios']=[b/a,c/d]
    report['ratio_interpretation']='Diagnostic overhead and host variation are confounded; NOT a benefit comparison'
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as stream: json.dump(report,stream,sort_keys=True,indent=2)
    print('F139_SQLITE_PHASE_RESULT='+json.dumps(dict(hypothesis_status=report['hypothesis_status'],fractions=fractions)),flush=True)


if __name__=='__main__': main()
