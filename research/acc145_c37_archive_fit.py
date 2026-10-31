"""ACC-145: authenticate consumed C35/C37 archives and reconstruct FIT-only numerical model.

No original world resets/steps, trained policy evaluations, or protected first use.
This diagnostic must NOT be treated as a native-owner qualification receipt.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import platform
import zipfile
import numpy as np

ZIP_SHA = {
    'fit': '4e35aef3238b6ba2b9d83c4e9e288ff2d8dd3edd23177974b9deb088cca66ca3',
    'first': '091d87ad5be235798ec857c6adee3aacf390773ffba71ddafce116eea378d5e1',
    'second': '8b18bba6f71397d33713d8299fd036661afb27c02c45d0a7d6b6e842942e8d3d',
}
SHA_FIRST = '6f313e662a8ef3c5fc582f01da3e5af186aea32df5d0a28bd8af80e5f19ab102'
SHA_SECOND = '3b2d35de98ad6abcb65ed85f01ad26da262f409f5abac17e5db32683c3eb7600'

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def sha256(x):
    return hashlib.sha256(x).hexdigest()

def fetch(path, role):
    data = path.read_bytes()
    assert sha256(data) == ZIP_SHA[role], 'IMMUTABLE_ZIP_SHA_MISMATCH: '+role
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None, 'CORRUPT_ZIP: '+role
        a = json.loads(archive.read('process-a.json'))
        b = json.loads(archive.read('process-b.json'))
    a2 = dict(a); b2 = dict(b)
    a2.pop('resources', None); b2.pop('resources', None)
    a2.pop('resource_observation', None); b2.pop('resource_observation', None)
    assert canonical(a2) == canonical(b2), 'SAME_RUN_INDEPENDENT_PROCESS_DISAGREEMENT: '+role
    return a2

def reconstruct(c35):
    assert c35['result'] == 'NO_C35_TWO_STEP_CAUSAL_SOURCE_EFFECT_PREDICTIVE_ADVANTAGE'
    assert c35['FIT_source_original_fitted_intervention_pairs'] == 279
    rows = c35['source_original_fit_real_two_action_forks']
    assert len(rows) == 31
    motors = defaultdict(Counter)
    prior = defaultdict(lambda: [0., 0])
    conditional = defaultdict(lambda: [0., 0])
    pairs = ((0,2),(1,2),(2,2))
    X = []; Y = []
    for row in rows:
        for branch in row['all_nine_original_physical_pairs'].values():
            assert branch['completed_two_original_actions']
            for event in branch['actual_selected_source_actions']:
                s,n = event['before'],event['after']
                if event['action'] == 2:
                    dx,dy = n['x']-s['x'],n['y']-s['y']
                    if abs(dx)+abs(dy) == 1:
                        motors[s['direction']][(dx,dy)] += 1
    assert set(motors) == set(range(4))
    for row in rows:
        fam = row['family']; s = row['public_initial']
        for pair in pairs:
            branch = row['all_nine_original_physical_pairs'][f'{pair[0]}{pair[1]}']
            assert [e['action'] for e in branch['actual_selected_source_actions']] == list(pair)
            gain = branch['real_two_step_goal_distance_improvement']
            z = prior[(fam,*pair)]; z[0] += gain; z[1] += 1
            z = conditional[(fam,s['direction'],int(s['front_blocked']),*pair)]
            z[0] += gain; z[1] += 1
            vals = [1., float(fam == 'MiniGrid-Dynamic-Obstacles-8x8-v0'),
                    s['x']/20., s['y']/20.,
                    max(-8,min(8,s['goal_x']-s['x']))/8.,
                    max(-8,min(8,s['goal_y']-s['y']))/8.]
            vals.extend(float(s['direction'] == d) for d in range(4))
            vals.append(float(s['front_blocked']))
            vals.extend(float(pair == a) for a in pairs)
            X.append(vals); Y.append(gain)
    x = np.array(X); y = np.array(Y)
    reg = np.eye(x.shape[1])*10; reg[0,0] = 0
    ridge = np.linalg.solve(x.T@x + reg, x.T@y).tolist()
    model = {
        'prior': [[list(k),v] for k,v in sorted(prior.items())],
        'condition': [[list(k),v] for k,v in sorted(conditional.items())],
        'ridge': ridge,
        'motors': {str(d): {f'{dx},{dy}':n for (dx,dy),n in motors[d].items()} for d in range(4)},
    }
    digest = sha256(canonical(model))
    snapshot = {**model, 'fitted':len(Y), 'model_sha':digest}
    return {'model_sha256':digest, 'model_serialized_bytes':len(canonical(snapshot)),
            'num_ridge_coefficients':len(ridge), 'num_fitted_options':len(Y),
            'condition_number':float(np.linalg.cond(x.T@x + reg))}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--fit', required=True, type=__import__('pathlib').Path)
    p.add_argument('--first', required=True, type=__import__('pathlib').Path)
    p.add_argument('--second', required=True, type=__import__('pathlib').Path)
    p.add_argument('--output', type=__import__('pathlib').Path)
    args = p.parse_args()
    fit = fetch(args.fit,'fit'); first = fetch(args.first,'first'); second = fetch(args.second,'second')
    assert first['original_FIT_model_sha256'] == SHA_FIRST
    assert second['original_FIT_model_sha256'] == SHA_SECOND
    assert first['precommitted_protocol_sha256'] == second['precommitted_protocol_sha256']
    assert first['FIT_trained_two_action_original_forks'] == second['FIT_trained_two_action_original_forks'] == 93
    assert first['factorial_source_actor_summaries'] == second['factorial_source_actor_summaries']
    assert first['criteria'] == second['criteria']
    def clean(d):
        d=json.loads(json.dumps(d))
        d.pop('original_FIT_model_sha256')
        for e in d['original_source_true_physical_actor_episodes']:
            e['real_step3_process_cold'].pop('fitted_model_bytes')
        return d
    assert clean(first) == clean(second), 'UNEXPECTED_SCIENCE_OR_TRAJECTORY_DRIFT'
    bytes_first = sorted({e['real_step3_process_cold']['fitted_model_bytes'] for e in first['original_source_true_physical_actor_episodes']})
    bytes_second = sorted({e['real_step3_process_cold']['fitted_model_bytes'] for e in second['original_source_true_physical_actor_episodes']})
    assert bytes_first == [1740] and bytes_second == [1743]
    fitted = reconstruct(fit)
    output = {
       'schema':'forge.acc145.c37.immutable-fit-only-numerical-fingerprint.v1',
       'source_zips_sha256':ZIP_SHA,
       'same_run_independent_producer_custody':'PASS_3_OF_3_ARCHIVES',
       'cross_run_original_physical_and_science_fields_excluding_model_identity':'PASS_IDENTICAL',
       'archived_model_sha256':{'first':SHA_FIRST,'second':SHA_SECOND},
       'archived_snapshot_size_bytes':{'first':1740,'second':1743},
       'local_fit_reconstruction':fitted,
       'matches_second_archive':fitted['model_sha256']==SHA_SECOND and fitted['model_serialized_bytes']==1743,
       'matches_first_archive':fitted['model_sha256']==SHA_FIRST and fitted['model_serialized_bytes']==1740,
       'numerical_environment':{'python':platform.python_version(),'numpy':np.__version__},
       'root_cause':'UNVERIFIED_NUMERIC_BACKEND_OR_FLOAT_SERIALIZATION_CANDIDATE',
       'limits':['No original-world import/reset/step','No owner Python 3.11/NumPy 1.26.4 cross-run requalification',
                 'Identical actual source actions do not prove trained model byte identity',
                 'No scientific acceptance, model promotion or owner source edits'],
    }
    raw = json.dumps(output,sort_keys=True,indent=2).encode()+b'\n'
    if args.output:
        args.output.write_bytes(raw)
    print('ACC145_C37_ARCHIVE_FIT_ONLY=' + json.dumps(output,sort_keys=True))
    print('ACC145_REPORT_SHA256=' + sha256(raw))

if __name__=='__main__':
    main()
