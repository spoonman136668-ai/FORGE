"""Bounded, zero-agent native source-search development rehearsal.
Only public FORGE qualification inventory is used. No owner/worker/source edits,
no scientific first-use, no production activation or accepted RSI claim.
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
import time
import unittest

TARGET='f139/check_test_discovery_inventory.py'
SCHEMA='forge.f139.agentless-native-code-rsi-development.v1'
LOOPS=512
SPEEDUP_MIN=1.03
G1={
 'closure': """def case_ids(suite):
    result=[]
    def visit(group):
        for item in group:
            if isinstance(item,unittest.TestSuite):
                visit(item)
            else:
                if isinstance(item,unittest.loader._FailedTest):
                    raise ValueError('Profile cannot qualify import failure: '+item.id()) from item._exception
                result.append(item.id())
    visit(suite)
    return result
""",
 'stack': """def case_ids(suite):
    result=[]
    pending=[iter(suite)]
    while pending:
        try:
            item=next(pending[-1])
        except StopIteration:
            pending.pop()
            continue
        if isinstance(item,unittest.TestSuite):
            pending.append(iter(item))
        else:
            if isinstance(item,unittest.loader._FailedTest):
                raise ValueError('Profile cannot qualify import failure: '+item.id()) from item._exception
            result.append(item.id())
    return result
"""
}
G2={
 'closure': """def case_ids(suite):
    result=[]
    append=result.append
    suite_type=unittest.TestSuite
    failed_type=unittest.loader._FailedTest
    def visit(group):
        for item in group:
            if isinstance(item,suite_type):
                visit(item)
            else:
                if isinstance(item,failed_type):
                    raise ValueError('Profile cannot qualify import failure: '+item.id()) from item._exception
                append(item.id())
    visit(suite)
    return result
""",
 'stack': """def case_ids(suite):
    result=[]
    append=result.append
    suite_type=unittest.TestSuite
    failed_type=unittest.loader._FailedTest
    pending=[iter(suite)]
    while pending:
        try:
            item=next(pending[-1])
        except StopIteration:
            pending.pop()
            continue
        if isinstance(item,suite_type):
            pending.append(iter(item))
        else:
            if isinstance(item,failed_type):
                raise ValueError('Profile cannot qualify import failure: '+item.id()) from item._exception
            append(item.id())
    return result
"""
}
def sha(x):
    return hashlib.sha256(x.encode('utf-8') if isinstance(x,str) else x).hexdigest()

def flatten(suite):
    for x in suite:
        if isinstance(x,unittest.TestSuite):
            yield from flatten(x)
        else:
            yield x

def compile_native(fragment):
    tree=ast.parse(fragment)
    if len(tree.body)!=1 or not isinstance(tree.body[0],ast.FunctionDef) or tree.body[0].name!='case_ids':
        raise ValueError('INVALID_FROZEN_OPERATOR')
    scope={'unittest':unittest}
    # Only the source fragments fixed in this audited file can reach exec.
    exec(compile(tree,'<frozen-internal-case-ids>','exec'),scope)
    return scope['case_ids']

def nested(rows):
    return unittest.TestSuite([unittest.TestSuite(rows[i:i+17]) for i in range(0,len(rows),17)])

def parity(original,new,suites):
    for name,suite in suites.items():
        expected=original(suite)
        actual=new(suite)
        if expected!=actual or len(actual)!=len(set(actual)):
            raise ValueError('TEST_IDENTITY_DRIFT_'+name)
    failed=unittest.loader._FailedTest('missing',ImportError('fixed control'))
    for fn in (original,new):
        try:
            fn(nested([failed]))
        except ValueError as exc:
            if 'Profile cannot qualify import failure' not in str(exc):
                raise ValueError('NEGATIVE_CONTROL_MESSAGE') from exc
        else:
            raise ValueError('IMPORT_FAILURE_FALSE_ACCEPT')

def timed(fn,suite):
    for _ in range(8):
        fn(suite)
    start_cpu=time.process_time()
    start_wall=time.perf_counter()
    for _ in range(LOOPS):
        fn(suite)
    return {'cpu_seconds':time.process_time()-start_cpu,'wall_seconds':time.perf_counter()-start_wall}

def abba(parent,child,suite):
    a=timed(parent,suite)
    b=timed(child,suite)
    c=timed(child,suite)
    d=timed(parent,suite)
    ratios=[a['cpu_seconds']/b['cpu_seconds'],d['cpu_seconds']/c['cpu_seconds']]
    ratio=(a['cpu_seconds']+d['cpu_seconds'])/(b['cpu_seconds']+c['cpu_seconds'])
    return {'cpu_seconds':[a['cpu_seconds'],b['cpu_seconds'],c['cpu_seconds'],d['cpu_seconds']],
       'wall_seconds':[a['wall_seconds'],b['wall_seconds'],c['wall_seconds'],d['wall_seconds']],
       'paired_cpu_ratios':ratios,'aggregate_cpu_ratio':ratio,
       'threshold_pass':ratio>=SPEEDUP_MIN and all(x>=1 for x in ratios)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--expected-source',required=True)
    p.add_argument('--output',required=True)
    args=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    source=(root/TARGET).read_bytes()
    tree=ast.parse(source)
    definitions=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='case_ids']
    if len(definitions)!=1:
        raise ValueError('SOURCE_FUNCTION_MISSING')
    lines=source.decode('utf-8').splitlines()
    original='\n'.join(lines[definitions[0].lineno-1:definitions[0].end_lineno])+'\n'
    baseline=compile_native(original)
    git=lambda *a:subprocess.check_output(['git',*a],cwd=root,text=True).strip()
    if git('rev-parse','HEAD')!=args.expected_source or git('status','--porcelain','--untracked-files=all'):
        raise ValueError('SOURCE_DRIFT_OR_DIRTY_CHECKOUT')
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REPOSITORY')!='spoonman136668-ai/FORGE':
        raise ValueError('HOSTED_FORGE_QUALIFICATION_ONLY')
    full=unittest.defaultTestLoader.discover(str(root/'f139'),pattern='test_*.py')
    cases=list(flatten(full))
    if any(isinstance(x,unittest.loader._FailedTest) for x in cases):
        raise ValueError('BASELINE_IMPORT_FAILURE')
    train,hold=[],[]
    for x in cases:
        (hold if int(sha(type(x).__module__)[:8],16)%4==0 else train).append(x)
    if not train or not hold or len(cases)!=len(train)+len(hold):
        raise ValueError('FROZEN_COHORT_SPLIT_INVALID')
    suites={'train':nested(train),'holdout':nested(hold),'empty':nested([])}
    for group in (G1,G2):
        for v in group.values():
            parity(baseline,compile_native(v),suites)
    train_g1={key:abba(baseline,compile_native(G1[key]),suites['train']) for key in sorted(G1)}
    # Only TRAIN evaluation chooses the generation-one parent.
    best=min(sorted(G1),key=lambda key:(-train_g1[key]['aggregate_cpu_ratio'],key))
    gen1,gen2=compile_native(G1[best]),compile_native(G2[best])
    train_g2=abba(gen1,gen2,suites['train'])
    heldout_g1=abba(baseline,gen1,suites['holdout'])
    heldout_g2=abba(gen1,gen2,suites['holdout'])
    go=(train_g1[best]['threshold_pass'] and train_g2['threshold_pass']
        and heldout_g1['threshold_pass'] and heldout_g2['threshold_pass'])
    report={'schema':SCHEMA,'status':'DEV_PASS_PENDING_ACTUAL_SOURCE_QUALIFICATION' if go else 'DEV_NO_GO',
       'candidate_sha':args.expected_source,'repo_tree':git('rev-parse','HEAD^{tree}'),
       'target':TARGET,'target_sha256':sha(source),'baseline_function_sha256':sha(original),
       'g1_operator':best,'g1_generated_source_sha256':sha(G1[best]),
       'g2_generated_source_sha256':sha(G2[best]),
       'generation_two_chosen_from_generation_one_training_feedback':True,
       'train_g1_candidates':train_g1,'train_g2':train_g2,
       'heldout_baseline_to_g1':heldout_g1,'heldout_g1_to_g2':heldout_g2,
       'inventory_total':len(cases),'train_cases':len(train),'heldout_cases':len(hold),
       'split':'module_sha256_mod4','heldout_used_for_selection':False,
       'fixed_loops':LOOPS,'fixed_cpu_ratio_threshold':SPEEDUP_MIN,
       'python':sys.version,'platform':platform.platform(),
       'model_inference_calls':0,'paid_api_calls':0,'checked_out_source_mutations':0,
       'owner_mutations':0,'scientific_first_use':False,'science_accepted':False,
       'accepted_ref_mutations':0,'general_recursive_self_improvement_proven':False}
    output=Path(args.output).resolve()
    output.relative_to(Path(os.environ['RUNNER_TEMP']).resolve())
    output.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('FORGE_NATIVE_CODE_RSI='+json.dumps({key:report[key] for key in
       ('candidate_sha','status','inventory_total','g1_operator','train_cases','heldout_cases',
        'fixed_cpu_ratio_threshold','model_inference_calls')},sort_keys=True))

if __name__=='__main__':
    main()
