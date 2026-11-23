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
import unittest

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


def case_ids(suite):
    result=[]
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            result.extend(case_ids(item))
        else:
            if isinstance(item, unittest.loader._FailedTest):
                raise ValueError('Profile cannot qualify import failure: '+item.id()) from item._exception
            result.append(item.id())
    return result


class ProfileResult(unittest.TextTestResult):
    """Time the unchanged serial unittest lifecycle; never select or reorder."""
    def __init__(self, *args, clock=time.perf_counter, resource_sampler=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.clock=clock
        self.resource_sampler=resource_sampler
        self.rows=[]
        self.outcomes={}

    def startTest(self, test):
        super().startTest(test)
        self.started=self.clock()
        if self.resource_sampler is not None:
            self.resource_started=self.resource_sampler.sample()

    def stopTest(self, test):
        if self.resource_sampler is not None:
            from f139.profile_resources import resource_delta
            resources=resource_delta(self.resource_started, self.resource_sampler.sample())
        elapsed=self.clock()-self.started
        self.rows.append(dict(id=test.id(), module=type(test).__module__, seconds=elapsed,
                              outcome=self.outcomes.get(test.id(), 'unknown')))
        if self.resource_sampler is not None:
            self.rows[-1]['resources']=resources
        super().stopTest(test)

    def addSuccess(self, test):
        self.outcomes.setdefault(test.id(), 'success')
        super().addSuccess(test)

    def addFailure(self, test, err):
        self.outcomes[test.id()]='failure'
        super().addFailure(test, err)

    def addError(self, test, err):
        self.outcomes[test.id()]='error'
        super().addError(test, err)

    def addSkip(self, test, reason):
        self.outcomes[test.id()]='skipped'
        super().addSkip(test, reason)

    def addExpectedFailure(self, test, err):
        self.outcomes[test.id()]='expected_failure'
        super().addExpectedFailure(test, err)

    def addUnexpectedSuccess(self, test):
        self.outcomes[test.id()]='unexpected_success'
        super().addUnexpectedSuccess(test)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.outcomes[test.id()]='subtest_failure'
        super().addSubTest(test, subtest, err)


def profile_suite(suite, expected_ids, *, stream=None, clock=time.perf_counter, resource_sampler=None):
    observed=case_ids(suite)
    if observed != expected_ids or len(observed) != len(set(observed)):
        raise ValueError('Profile inventory/order mismatch or duplicate identities')
    started=clock()
    runner=unittest.TextTestRunner(stream=stream, verbosity=1,
        resultclass=lambda *a, **kw: ProfileResult(*a, clock=clock, resource_sampler=resource_sampler, **kw))
    result=runner.run(suite)
    elapsed=clock()-started
    seen=[row['id'] for row in result.rows]
    complete=(seen == expected_ids and result.testsRun == len(expected_ids))
    modules={}
    for row in result.rows:
        module=row['module']
        record=modules.setdefault(module, dict(module=module, cases=0, seconds=0.0))
        record['cases']+=1
        record['seconds']+=row['seconds']
    return dict(successful=result.wasSuccessful() and complete,
        complete_inventory_and_order=complete, tests_run=result.testsRun,
        failures=len(result.failures), errors=len(result.errors),
        skipped_ids=[test.id() for test, _reason in result.skipped],
        unexpected_successes=len(result.unexpectedSuccesses),
        expected_failures=len(result.expectedFailures),
        suite_seconds=elapsed,
        outside_case_seconds=max(0.0, elapsed-sum(row['seconds'] for row in result.rows)),
        cases=result.rows,
        modules=sorted(modules.values(), key=lambda row: (-row['seconds'], row['module'])))


def discover_profile_suite(root):
    # A file entry point starts with f139/ on sys.path, whereas the ordinary
    # `python -m unittest` starts with the repository root. Preserve both paths
    # so package imports and flat discovery imports retain their usual meaning.
    root=Path(root).resolve()
    start=str(root/'f139')
    # Let discover insert the start directory first, just as the ordinary
    # module entry point does. The root must follow it, before other paths.
    sys.path[:]=[entry for entry in sys.path if entry not in (str(root), start)]
    sys.path.insert(0, str(root))
    return unittest.defaultTestLoader.discover(str(root/'f139'), pattern='test_*.py')


def profile_current(root, args):
    """A single instrumented full regression in the existing hosted job."""
    if (os.environ.get('GITHUB_ACTIONS') != 'true' or
            os.environ.get('GITHUB_REPOSITORY') != 'spoonman136668-ai/FORGE'):
        raise ValueError('Full profile requires existing FORGE hosted qualification')
    candidate=git(root, 'rev-parse', 'HEAD').decode().strip()
    if args.expected_source != candidate:
        raise ValueError('Profile requires the exact independently supplied candidate SHA')
    if git(root, 'status', '--porcelain', '--untracked-files=all').strip():
        raise ValueError('Exact clean source required before profiling')
    output=args.output.resolve()
    output.relative_to(Path(os.environ['RUNNER_TEMP']).resolve())
    # -B applies to this process; preserve the same no-bytecode behavior in
    # subprocess fixtures too, without editing or deleting their outputs.
    os.environ['PYTHONDONTWRITEBYTECODE']='1'
    inventory=collect(root)
    began=time.perf_counter()
    suite=discover_profile_suite(root)
    collection_seconds=time.perf_counter()-began
    sampler=None
    if getattr(args, 'resource_diagnostics', False):
        from f139.profile_resources import ResourceSampler
        sampler=ResourceSampler()
    report=profile_suite(suite, inventory['ids'], resource_sampler=sampler)
    if sampler is not None:
        from f139.profile_resources import telemetry_identity
        report['resource_diagnostics']=telemetry_identity()
        report['resource_diagnostics']['module_sha256']=hashlib.sha256(
            (root/'f139/profile_resources.py').read_bytes()).hexdigest()
        report['resource_diagnostics']['coverage']={
            group:sum(row['resources'][group]['status']=='VERIFIED' for row in report['cases'])
            for group in ('self_cpu','process_io','host_cpu_100ns')}

    source_stable=(git(root, 'rev-parse', 'HEAD').decode().strip() == candidate and
                   not git(root, 'status', '--porcelain', '--untracked-files=all').strip())
    report.update(schema='forge.f139.serial-test-profile.v1',
        candidate_sha=candidate, candidate_tree=git(root, 'rev-parse', 'HEAD^{tree}').decode().strip(),
        source_stable=source_stable, python=sys.version, platform=platform.platform(),
        checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        unique_test_ids_sha256=hashlib.sha256(('\n'.join(sorted(inventory['ids']))+'\n').encode()).hexdigest(),
        execution_order_sha256=hashlib.sha256(('\n'.join(inventory['ids'])+'\n').encode()).hexdigest(),
        declared_skipped_ids=inventory['skipped'], collection_seconds=collection_seconds,
        workflow_run=os.environ.get('GITHUB_RUN_ID'), workflow_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),
        test_selection_performed=False, test_reordering_performed=False,
        additional_full_suite_executions=0, profiling_overhead_independently_measured=False,
        speedup_proven=False, autonomous_proposal=False, controller_mutations=0,
        scientific_first_use=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, sort_keys=True, indent=2); stream.write('\n')
    print('F139_SERIAL_PROFILE='+json.dumps({key:report[key] for key in
        ('candidate_sha','source_stable','successful','tests_run','suite_seconds','outside_case_seconds',
         'complete_inventory_and_order','speedup_proven','autonomous_proposal')}, sort_keys=True))
    for row in report['modules'][:15]:
        print('F139_PROFILE_MODULE='+json.dumps(row, sort_keys=True))
    if not source_stable or not report['successful']:
        raise SystemExit('F139_PROFILE_FULL_REGRESSION_FAILED_SEE_RETAINED_RECEIPT')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--full-regression', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--profile-current', action='store_true')
    parser.add_argument('--resource-diagnostics', action='store_true')
    parser.add_argument('--expected-source')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    if args.profile_current:
        if args.baseline or args.full_regression or args.verbose:
            raise ValueError('Current profile cannot be mixed with historical comparison')
        profile_current(root, args)
        return
    if args.resource_diagnostics:
        raise ValueError('Resource diagnostics requires current hosted profile')
    if args.expected_source is not None:
        raise ValueError('Expected source is only valid for the current profile')
    if args.baseline is None:
        raise ValueError('Exact baseline SHA required')
    if re.fullmatch('[a-f0-9]{40}', args.baseline) is None:
        raise ValueError('Exact baseline SHA required')
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
