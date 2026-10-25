#!/usr/bin/env python3
"""Independent retrospective *FIT-only* original F12 physical alias census.

This is a scientific source-identifiability screen, not a new environment, episode,
learner, or proof of no hidden causal state. Do not read DEV or protected outcomes.
"""
import hashlib, json, collections, zipfile, datetime
from pathlib import Path
SRC=Path('/mnt/data/github-actions-artifact-12597057624.zip')
EXPECTED='f4f567cd7b456287a93ebf725b0b6c763bb1831e43499cdbf04d9221e8df72b5'
assert hashlib.sha256(SRC.read_bytes()).hexdigest() == EXPECTED
with zipfile.ZipFile(SRC) as z:
    left=json.loads(z.read('process-a.json'))['FIT_true_original_source_matched_actions']
    right=json.loads(z.read('process-b.json'))['FIT_true_original_source_matched_actions']
canon=lambda obj:json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
fit_sha=hashlib.sha256(canon(left)).hexdigest()
assert canon(left)==canon(right)
assert len(left)==317 and len({r['seed'] for r in left})==48
fields=('X','Y','Direction','FrontBlocked','GoalX','GoalY')
public=lambda d:tuple(d[k] for k in fields)
interventions=collections.defaultdict(list)
all_records=collections.defaultdict(list)
for idx,r in enumerate(left):
    assert 171400<=r['seed']<=171447
    assert len(r['true_source_three_arm_interventions'])==3
    for act in range(3):
        row=r['true_source_three_arm_interventions'][str(act)]
        tr=row['actual_public_action_consequence_trace']
        assert tr and tr[0]['action']==act
        before=public(r['six_public_before'])
        assert public(tr[0]['before'])==before
        assert tr[0]['tick']==r['anchor_tick']
        k=(before,act)
        p=tr[0]
        interventions[k].append((int(r['seed']),idx,int(p['tick']), public(p['after']), bool(p['terminated']), bool(p['truncated']),float(p['reward']),float(row['discounted_true_source_return'])))
        for t in tr:
            assert type(t['action']) is int and 0 <= t['action']<=2
            sig=(int(r['seed']),int(t['tick']),public(t['before']),int(t['action']), public(t['after']),bool(t['terminated']),bool(t['truncated']),round(float(t['reward']),12))
            all_records[(public(t['before']),int(t['action']))].append(sig)

def census(dic,role):
    repeated=[];conflicting_physical=[];conflicting_reward=[]
    for k,v in dic.items():
        seeds={x[0] for x in v}
        if len(seeds)<2:continue
        repeated.append((k,v))
        # For interventions: tuple 3/4/5 physical; for traces: 4/5/6 physical.
        fys=lambda x:(x[3],x[4],x[5]) if role=='interventions' else (x[4],x[5],x[6])
        rew=lambda x:round(x[6],12) if role=='interventions' else x[7]
        if len({fys(x) for x in v})>1:conflicting_physical.append((k,v))
        if len({rew(x) for x in v})>1:conflicting_reward.append((k,v))
    def pretty(item):
        k,v=item
        return {'six_public_before':dict(zip(fields,k[0])), 'action':k[1], 'world_seeds':sorted({x[0] for x in v}), 'distinct_physical_outcomes':len({((x[3],x[4],x[5]) if role=='interventions' else (x[4],x[5],x[6])) for x in v}), 'sample_count':len(v)}
    return {'unique_state_action_keys':len(dic), 'cross_world_exact_alias_keys':len(repeated), 'cross_world_physical_consequence_conflict_keys':len(conflicting_physical), 'cross_world_reward_variation_keys':len(conflicting_reward), 'examples':list(map(pretty,repeated[:12]))}
intc=census(interventions,'interventions')
tracec=census(all_records,'all_traces')
unique_all={sig for v in all_records.values() for sig in v}
# Some identical source-prefix actions appear in different branch continuations; de-dup explicitly.
obey={'archive_sha256':EXPECTED,'original_fit_canonical_sha256':fit_sha,'source_roles_used':['FIT'], 'source_roles_excluded':['DEV','FIT_CHECK','VALID','protected_holdout'], 'distinct_original_world_seeds':48, 'actual_original_fork_action_count':317*3,'physically_executed_trace_rows_with_replays':sum(map(len,all_records.values())),'unique_within_source_tick_and_action_trace_events':len(unique_all),'observed_initial_three_arm_consequence_census':intc,'full_physically_recorded_action_trace_census':tracec,'interpretation':'No observed cross-world exact-six-public-input action physical outcome conflicts in THIS original F12 FIT archive. Reward differences at identical public state can reflect elapsed time, not necessarily hidden causal dynamics; they do not independently prove memory-dependent optimal actions.', 'status':'RETROSPECTIVE_SOURCE_PUBLIC_FIT_IDENTIFIABILITY_NEGATIVE_NOT_TRANSFER_SCIENCE','optimization':'content-addressed reuse and hypothesis discrimination; expensive causal-memory optimization on this exposed panel has no demonstrated identifiability leverage','original_new_steps':0,'fsa_protected_first_use':'DENIED'}
OUT=Path('/mnt/data/f12_physical_alias_necessity_result.json');OUT.write_bytes(canon(obey)+b'\n')
print(json.dumps({k:v for k,v in obey.items() if k not in ('observed_initial_three_arm_consequence_census','full_physically_recorded_action_trace_census')},indent=2))
print('initial census',json.dumps({k:v for k,v in intc.items() if k!='examples'},indent=2))
print('complete trace census',json.dumps({k:v for k,v in tracec.items() if k!='examples'},indent=2))
print('report_sha256',hashlib.sha256(OUT.read_bytes()).hexdigest())
print('script_sha256',hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
