"""Compare collection identities, not scientific evidence or test outcomes.

Only the existing qualification jobs call this development receipt generator.
Both source trees are collected in separate Python processes; no tests run here.
"""
import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tarfile
import tempfile
import time

COLLECT = r'''
import json, unittest
suite=unittest.defaultTestLoader.discover('f139', pattern='test_*.py')
def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite): yield from cases(item)
        else: yield item
ids=[]; skipped=[]
for case in cases(suite):
    if isinstance(case, unittest.loader._FailedTest):
        raise RuntimeError('Inventory cannot qualify an import failure: '+case.id())
    identity=case.id(); ids.append(identity)
    method=getattr(case, case._testMethodName)
    if getattr(type(case), '__unittest_skip__', False) or getattr(method, '__unittest_skip__', False):
        skipped.append(identity)
print(json.dumps(dict(ids=ids, skipped=sorted(set(skipped))), sort_keys=True))
'''


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], timeout=60)


def collect(root):
    start=time.perf_counter()
    output=subprocess.check_output([sys.executable, '-B', '-c', COLLECT],
        cwd=root, env={**os.environ, 'PYTHONPATH':str(root)}, timeout=60, text=True)
    result=json.loads(output)
    result['collection_seconds']=time.perf_counter()-start
    return result


def compare(baseline, candidate):
    before=set(baseline['ids']); after=set(candidate['ids'])
    if before != after:
        raise ValueError('Test identities changed: '+json.dumps(dict(
            missing=sorted(before-after), added=sorted(after-before))))
    if baseline['skipped'] != candidate['skipped']:
        raise ValueError('Existing platform/authority skip identities changed')
    if len(candidate['ids']) != len(after):
        raise ValueError('Candidate still discovers duplicate test identities')
    return hashlib.sha256(('\n'.join(sorted(after))+'\n').encode()).hexdigest()


def fixture_normalized_ast(source):
    """Ignore only fixture imports and resolve their unchanged qualified uses."""
    tree=ast.parse(source)
    names={}; body=[]
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split('.')[-1].startswith('test_'):
            kept=[]
            for alias in node.names:
                if alias.name[:1].isupper() and not alias.name.isupper():
                    names[alias.asname or alias.name]=node.module+'.'+alias.name
                else: kept.append(alias)
            if kept:
                node.names=kept; body.append(node)
        elif isinstance(node, ast.Import) and all(
                alias.asname and alias.name.split('.')[-1].startswith('test_') for alias in node.names):
            for alias in node.names: names[alias.asname]=alias.name
        else: body.append(node)
    tree.body=body
    for node in ast.walk(tree):
        if ((isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and node.id in names)
                or isinstance(node, ast.arg) and node.arg in names):
            raise ValueError('Fixture alias shadowing requires separate review')
    class Resolve(ast.NodeTransformer):
        def visit_Name(self, node):
            return ast.parse(names[node.id], mode='eval').body if node.id in names else node
    return ast.dump(Resolve().visit(tree), include_attributes=False)


def compare_test_bodies(baseline_root, candidate_root):
    before={p.name:p for p in (baseline_root/'f139').glob('test_*.py')}
    after={p.name:p for p in (candidate_root/'f139').glob('test_*.py')}
    if before.keys()!=after.keys(): raise ValueError('Test module paths changed')
    hashes={}
    for name in sorted(before):
        left=fixture_normalized_ast(before[name].read_text(encoding='utf-8'))
        right=fixture_normalized_ast(after[name].read_text(encoding='utf-8'))
        if left!=right: raise ValueError('Test body, assertion or fixture behavior changed: '+name)
        hashes[name]=hashlib.sha256(right.encode()).hexdigest()
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def semantic_negative_controls():
    original='from test_fixture import FixtureTests\nclass Example:\n def check(self):\n  FixtureTests.setUp(self)\n  self.assertEqual(1, 1)\n'
    alias='import test_fixture as fixture_base\nclass Example:\n def check(self):\n  fixture_base.FixtureTests.setUp(self)\n  self.assertEqual(1, 1)\n'
    expected=fixture_normalized_ast(original)
    if fixture_normalized_ast(alias)!=expected:
        raise ValueError('Mechanical fixture alias control changed semantics')
    for corrupted in (alias.replace('assertEqual(1, 1)', 'assertEqual(1, 2)'),
            alias.replace('.setUp(self)', '.tearDown(self)'),
            alias.replace(' def check', ' @unittest.skip("invented")\n def check')):
        if fixture_normalized_ast(corrupted)==expected:
            raise ValueError('Semantic negative control was accepted')


def full_regression(root, verbose):
    start=time.perf_counter()
    command=[sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'f139', '-p', 'test_*.py']
    if verbose: command.append('-v')
    result=subprocess.run(command, cwd=root, timeout=1100)
    return dict(returncode=result.returncode, seconds=time.perf_counter()-start)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--full-regression', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    args=parser.parse_args()
    if re.fullmatch('[a-f0-9]{40}', args.baseline) is None:
        raise ValueError('Exact baseline SHA required')
    root=Path(__file__).resolve().parents[1]
    candidate_sha=git(root, 'rev-parse', 'HEAD').decode().strip()
    started=time.perf_counter()
    if args.full_regression and os.environ.get('GITHUB_ACTIONS')!='true':
        raise ValueError('Paired full regression is restricted to existing hosted qualification')
    if git(root, 'status', '--porcelain', '--untracked-files=all').strip():
        raise ValueError('Exact clean candidate required')
    if git(root, 'merge-base', args.baseline, candidate_sha).decode().strip()!=args.baseline:
        raise ValueError('Baseline must be the accepted ancestor')
    archive=git(root, 'archive', '--format=tar', args.baseline)
    measurements={}; order=[]
    with tempfile.TemporaryDirectory(prefix='f139-discovery-', dir=os.environ.get('RUNNER_TEMP')) as directory:
        base_root=Path(directory)
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            for member in source:
                target=base_root/member.name
                target.resolve().relative_to(base_root.resolve())
                if member.isdir(): target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.extractfile(member) as content:
                        target.write_bytes(content.read())
                else: raise ValueError('Nonregular baseline archive entry')
        baseline=collect(base_root)
        semantic_hash=compare_test_bodies(base_root, root)
    candidate=collect(root)
    identity_hash=compare(baseline, candidate)
    semantic_negative_controls()
    # Falsification controls for the inventory comparison itself. They do not
    # modify or execute the original tests, fixtures or scientific contracts.
    corruptions=[{**candidate, 'ids':candidate['ids'][1:]},
        {**candidate, 'ids':candidate['ids']+[candidate['ids'][0]]},
        {**candidate, 'skipped':candidate['skipped']+['invented-authority-skip']}]
    for corrupted in corruptions:
        try: compare(baseline, corrupted)
        except ValueError: pass
        else: raise ValueError('Inventory negative control was accepted')
    # The real baseline needs its Git history for frozen transport controls.
    # Both suites run once in separate Python processes on the same host.
    if args.full_regression:
        with tempfile.TemporaryDirectory(prefix='f139-paired-', dir=os.environ.get('RUNNER_TEMP')) as directory:
            base_root=Path(directory)/'baseline'
            try:
                git(root, 'worktree', 'add', '--detach', str(base_root), args.baseline)
                order=['candidate','baseline'] if os.name=='nt' else ['baseline','candidate']
                for label in order:
                    print('F139_PAIRED_REGRESSION_START='+label, flush=True)
                    measurements[label]=full_regression(root if label=='candidate' else base_root, args.verbose)
                    print('F139_PAIRED_REGRESSION_RESULT='+json.dumps({label:measurements[label]}), flush=True)
            finally:
                git(root, 'worktree', 'remove', '--force', str(base_root))
    if git(root, 'rev-parse', 'HEAD').decode().strip()!=candidate_sha or git(
            root, 'status', '--porcelain', '--untracked-files=all').strip():
        raise ValueError('Candidate identity drifted during comparison')
    receipt=dict(schema='forge.f139.test-discovery-inventory.v1',
        baseline_sha=args.baseline,
        baseline_tree=git(root, 'rev-parse', args.baseline+'^{tree}').decode().strip(),
        candidate_sha=candidate_sha,
        candidate_tree=git(root, 'rev-parse', 'HEAD^{tree}').decode().strip(),
        clean=True, python=sys.version, platform=platform.platform(),
        checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        baseline_executions=len(baseline['ids']), candidate_executions=len(candidate['ids']),
        unique_test_count=len(set(candidate['ids'])), unique_test_ids_sha256=identity_hash,
        normalized_test_bodies_sha256=semantic_hash,
        unique_test_ids=sorted(set(candidate['ids'])), skipped_ids=candidate['skipped'],
        duplicate_executions_removed=len(baseline['ids'])-len(candidate['ids']),
        baseline_collection_seconds=baseline['collection_seconds'],
        candidate_collection_seconds=candidate['collection_seconds'],
        negative_controls_rejected=3, semantic_negative_controls_rejected=3,
        test_execution_performed=args.full_regression,
        full_regression=measurements, execution_order=order,
        paired_phase_seconds=time.perf_counter()-started,
        paired_suite_speedup=(measurements['baseline']['seconds']/measurements['candidate']['seconds']
            if measurements and all(v['returncode']==0 for v in measurements.values()) else None),
        repeated_or_general_speedup_proven=False,
        full_regression_required=True, scientific_first_use=False,
        cache_hits=0, controller_mutations=0,
        workflow_run=os.environ.get('GITHUB_RUN_ID'), workflow_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2); stream.write('\n')
    print('F139_UNIQUE_DISCOVERY='+json.dumps({k:v for k,v in receipt.items()
        if k not in ('unique_test_ids','skipped_ids','python','platform')}, sort_keys=True))
    if any(v['returncode']!=0 for v in measurements.values()):
        raise SystemExit('F139_PAIRED_FULL_REGRESSION_FAILED_SEE_RETAINED_RECEIPT')


if __name__ == '__main__':
    main()
