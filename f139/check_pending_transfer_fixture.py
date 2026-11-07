"""Bounded fixture parity and ABBA measurement in existing hosted qualification.

No controller, intake, scientific evidence, deployment or acceptance authority.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

BASE = '243707c1c7f7a0745e9c1803843daf89b638259e'
TARGET = 'f139/test_nci04_v30_source_transition.py'
BLOB = 'd8cbf54f8f5ad1ef41812734be2b80a7c9aad607'
PROBE = r'''
import hashlib, json, sqlite3, tempfile
from contextlib import closing
from pathlib import Path
from f139.test_nci04_v30_source_transition import PendingTransferTests as Case
from f139.local_controller import Database, F139Error

def snapshot(db):
    schema=[tuple(r) for r in db.conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name")]
    tables={name:sorted([tuple(r) for r in db.conn.execute('SELECT * FROM "'+name+'"')],key=repr)
        for (name,) in db.conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}
    return dict(schema=schema,tables=tables)

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

Case.setUpClass()
a=Case('test_exact_unclaimed_identity_is_read_only_and_does_not_reissue')
b=Case('test_exact_unclaimed_identity_is_read_only_and_does_not_reissue')
try:
    a.setUp(); b.setUp()
    first=snapshot(a.db); other=snapshot(b.db)
    assert first==other
    assert a.path!=b.path and a.db.conn is not b.db.conn
    assert a.db.meta()['head_seq']==376
    assert a.db.conn.execute('PRAGMA synchronous').fetchone()[0]==2
    assert a.db.conn.execute('PRAGMA journal_mode').fetchone()[0]=='wal'
    assert a.db.conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    # The original fixture deliberately has an incomplete native admission.
    # Preserve its exact rejection rather than pretending it is an A6 ledger.
    try: a.db.verify()
    except ValueError as e:
        rejection=str(e)
        assert rejection=='F139_NCI04_A6_ADMISSION_FIELDS', rejection
    else: raise AssertionError('Synthetic admission unexpectedly accepted')
    # Independently verify all 376 event hashes, including synthetic tail.
    from f139.local_controller import canonical, hash_bytes
    prior='0'*64
    for row in a.db.conn.execute('SELECT * FROM events ORDER BY seq'):
        assert row['prior_sha']==prior
        value=dict(seq=row['seq'],prior_sha=prior,kind=row['kind'],payload=json.loads(row['payload']))
        prior=hash_bytes(canonical(value)); assert prior==row['sha']
    assert prior==a.db.meta()['head_hash']
    template=getattr(Case,'_fixture_bytes',None)
    a.db.event('UNTRUSTED_TEST_FIXTURE',{'independence':True})
    assert snapshot(b.db)==other
    assert getattr(Case,'_fixture_bytes',None)==template
    if template is not None:
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'corrupt.sqlite'; path.write_bytes(template)
            # Reuse the actual constructor; retain its object to close even
            # when verification raises (important for Windows file custody).
            cold=object.__new__(Database)
            try:
                Database.__init__(cold,path)
                assert cold.meta()['head_seq']==374
            finally:
                if hasattr(cold,'conn'): cold.close()
            with closing(sqlite3.connect(path, isolation_level=None)) as conn:
                triggers=list(conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name='events'"))
                for name, sql in triggers: conn.execute('DROP TRIGGER "'+name+'"')
                conn.execute("UPDATE events SET payload=? WHERE seq=2", (canonical({}).decode(),))
                for name, sql in triggers: conn.execute(sql)
            broken=object.__new__(Database)
            try:
                try: Database.__init__(broken,path)
                except F139Error as e:
                    assert str(e)=='F139_EVIDENCE_CHAIN_TAMPERED', str(e)
                else: raise AssertionError('Corrupted prefix was accepted')
            finally:
                if hasattr(broken,'conn'): broken.close()
    print('F139_PENDING_CHILD='+json.dumps(dict(state_sha256=digest(first),head_hash=other['tables']['meta'][0][-1],
        semantic_rejection=rejection,independent_files=True,full_sync=True,wal=True,
        chain_verified=True,prefix_corruption_rejected=template is not None),sort_keys=True))
finally:
    a.doCleanups(); b.doCleanups(); Case.tearDownClass()
'''
RUN = r'''
import json, sys
from pathlib import Path
from f139.check_test_discovery_inventory import collect, discover_profile_suite, profile_suite
root=Path.cwd()
inventory=collect(root)
suite=discover_profile_suite(root)
report=profile_suite(suite,inventory['ids'])
report['ids']=inventory['ids']; report['declared_skipped_ids']=inventory['skipped']
print('F139_PENDING_CHILD='+json.dumps(report,sort_keys=True))
if not report['successful']: sys.exit(1)
'''


def git(root, *args):
    return subprocess.check_output(['git','-C',str(root),*args],timeout=60).decode().strip()


def child(root, code, timeout=600):
    started=time.perf_counter()
    result=subprocess.run([sys.executable,'-B','-c',code],cwd=root,
        env={**os.environ,'PYTHONPATH':os.pathsep.join([str(root),str(root/'f139')]),
             'PYTHONDONTWRITEBYTECODE':'1'},text=True,stdout=subprocess.PIPE,timeout=timeout)
    if result.returncode: raise ValueError('Fixture qualification subprocess failed')
    # Full regression fixtures emit their own diagnostics on stdout.
    # Parse exactly one explicitly framed result, never the whole log.
    records=[line.removeprefix('F139_PENDING_CHILD=') for line in result.stdout.splitlines()
             if line.startswith('F139_PENDING_CHILD=')]
    if len(records)!=1: raise ValueError('Missing or ambiguous child receipt')
    value=json.loads(records[0])
    value['process_seconds']=time.perf_counter()-started
    return value


def unchanged_tests(before, after):
    def strip(source):
        tree=ast.parse(source)
        for node in tree.body:
            if isinstance(node,ast.ClassDef) and node.name=='PendingTransferTests':
                node.body=[method for method in node.body if not (
                    isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef)) and
                    method.name in ('setUp','setUpClass','tearDownClass'))]
        return ast.dump(tree,include_attributes=False)
    if strip(before)!=strip(after): raise ValueError('Original tests or other module code changed')
    # Ensure assertion/skip mutations cannot hide inside normalization.
    for corrupt in (after.replace("value['ticket'],route.TICKET", "value['ticket'],'wrong'"),
                    after.replace('    def test_exact_', '    @unittest.skip("invented")\n    def test_exact_')):
        if strip(before)==strip(corrupt): raise ValueError('AST negative control accepted')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--expected-source')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--preflight',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    source=git(root,'rev-parse','HEAD')
    if not args.preflight:
        if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REPOSITORY')!='spoonman136668-ai/FORGE':
            raise ValueError('ABBA requires existing FORGE hosted qualification')
        if source!=args.expected_source or git(root,'status','--porcelain','--untracked-files=all'):
            raise ValueError('Exact clean candidate required')
        args.output.resolve().relative_to(Path(os.environ['RUNNER_TEMP']).resolve())
    if git(root,'merge-base',BASE,source)!=BASE: raise ValueError('Accepted baseline ancestry drift')
    if git(root,'rev-parse',BASE+':'+TARGET)!=BLOB: raise ValueError('Original target blob drift')
    changed=git(root,'diff','--name-only',BASE).splitlines()
    allowed={TARGET,'f139/check_pending_transfer_fixture.py','.github/workflows/qualify.yml'}
    if set(changed)-allowed: raise ValueError('Out-of-scope source change')
    before=git(root,'show',BASE+':'+TARGET)
    unchanged_tests(before,(root/TARGET).read_text())
    receipt=dict(preflight_only=args.preflight, schema='forge.f139.pending-transfer-fixture-abba.v1',baseline_sha=BASE,
        candidate_sha=source,candidate_tree=git(root,'rev-parse','HEAD^{tree}'),
        python=sys.version,platform=platform.platform(),workflow_run=os.environ.get('GITHUB_RUN_ID'),
        workflow_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),
        checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scientific_first_use=False,autonomous_proposal=False,controller_mutations=0,
        full_ci_speedup_proven=False,criterion='PER_PLATFORM_STRICT aggregate>=1.03 and both pairs>=1.0',
        original_draft_sha256='9111f94505489bfb0c04896a7e3065a14bc65470a15ac03e9e853ece2f0d2e25',
        original_draft_result='FAIL: full synthetic376 audit F139_NCI04_A6_ADMISSION_FIELDS',
        measurements=[])
    with tempfile.TemporaryDirectory(prefix='f139-pending-',dir=os.environ.get('RUNNER_TEMP')) as directory:
        base=Path(directory)/'baseline'
        try:
            git(root,'worktree','add','--detach',str(base),BASE)
            a=child(base,PROBE); b=child(root,PROBE)
            if a['state_sha256']!=b['state_sha256'] or a['semantic_rejection']!=b['semantic_rejection']:
                raise ValueError('Logical fixture parity failed')
            if not b['prefix_corruption_rejected']: raise ValueError('Candidate prefix control absent')
            receipt['parity']={'baseline':a,'candidate':b}
            if not args.preflight:
                for label in ('baseline','candidate','candidate','baseline'):
                    print('F139_PENDING_ABBA_START='+label,flush=True)
                    execution_root=base if label=='baseline' else root
                    expected=BASE if label=='baseline' else source
                    if git(execution_root,'rev-parse','HEAD')!=expected or git(execution_root,'status','--porcelain','--untracked-files=all'):
                        raise ValueError('Measured source is not exact and clean')
                    value=child(execution_root,RUN,1200)
                    if git(execution_root,'rev-parse','HEAD')!=expected or git(execution_root,'status','--porcelain','--untracked-files=all'):
                        raise ValueError('Measured source drifted')
                    if value['tests_run']!=1414: raise ValueError('Frozen 1414-case inventory drift')
                    if receipt['measurements']:
                        first=receipt['measurements'][0]
                        for key in ('ids','skipped_ids','declared_skipped_ids','tests_run'):
                            if value[key]!=first[key]: raise ValueError('Full test/skip inventory changed')
                    value['label']=label
                    receipt['measurements'].append(value)
                    print('F139_PENDING_ABBA_RESULT='+json.dumps(dict(label=label,seconds=value['process_seconds'],tests=value['tests_run'])),flush=True)
        finally:
            git(root,'worktree','remove','--force',str(base))
    receipt['source_stable']=source==git(root,'rev-parse','HEAD') and (args.preflight or not git(root,'status','--porcelain','--untracked-files=all'))
    if not receipt['source_stable']: raise ValueError('Source drift')
    if not args.preflight:
        a,b,c,d=[v['process_seconds'] for v in receipt['measurements']]
        receipt['pair_speedups']=[a/b,d/c]
        receipt['aggregate_speedup']=(a+d)/(b+c)
        receipt['development_benefit_pass']=receipt['aggregate_speedup']>=1.03 and min(receipt['pair_speedups'])>=1.0
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as stream: json.dump(receipt,stream,sort_keys=True,indent=2)
    print('F139_PENDING_RECEIPT='+str(args.output),flush=True)


if __name__=='__main__': main()
