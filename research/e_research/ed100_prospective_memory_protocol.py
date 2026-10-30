"""E-D100: prospective, engineering-only MiniGrid Memory evaluation plan.

NO Gymnasium execution, training, benchmark score, or independent FSA acceptance.
"""
from __future__ import annotations
import hashlib
import json

UPSTREAM_SHA = '7f5853792ea7f04f75614661006d87fcf949f26d'
MEMORY_BLOB = '660b0a1b769948034c87bb421759c2b9a4f24548'
SPLITS = {
    'fit': {'env': 'MiniGrid-MemoryS11-v0', 'seeds': list(range(10000, 10100))},
    'validation': {'env': 'MiniGrid-MemoryS13-v0', 'seeds': list(range(20000, 20030))},
    'dev_shift': {'env': 'MiniGrid-MemoryS13Random-v0', 'seeds': list(range(30000, 30030))},
    'holdout': {'env': 'MiniGrid-MemoryS17Random-v0', 'seeds': list(range(40000, 40060))},
}
CONTROLS = ['reactive_no_memory', 'last_cue_memory', 'history_window', 'conventional_recurrent']

def manifest():
    # Budget values are PROPOSED ceilings, not evidence of matched usage.
    return {'status':'PROSPECTIVE_NOT_AUTHORIZED_OR_FROZEN',
            'upstream_sha':UPSTREAM_SHA,'memory_blob':MEMORY_BLOB,
            'splits':SPLITS, 'controls':CONTROLS,
            'max_training_episodes_per_model':100,
            'max_evaluation_steps_per_episode':1500,
            'native_wingless_yggdrasil':'INTEGRATION_NOT_PROVEN',
            'holdout_access':'PROHIBITED_UNTIL_INDEPENDENT_APPROVAL'}

def verify(m):
    seen = set()
    for name, group in m['splits'].items():
        assert len(group['seeds']) == len(set(group['seeds'])), name
        assert not seen.intersection(group['seeds']), 'seed overlap: '+name
        seen.update(group['seeds'])
    assert m['splits']['holdout']['env'] != m['splits']['fit']['env']
    assert m['status'] == 'PROSPECTIVE_NOT_AUTHORIZED_OR_FROZEN'
    assert m['holdout_access'] == 'PROHIBITED_UNTIL_INDEPENDENT_APPROVAL'
    return True

if __name__ == '__main__':
    m=manifest()
    assert verify(m)
    data=json.dumps(m,sort_keys=True,separators=(',',':')).encode()
    print(json.dumps({'status':'PASS_STATIC_MANIFEST_ONLY','sha256':hashlib.sha256(data).hexdigest(), 'split_sizes':{k:len(v['seeds']) for k,v in m['splits'].items()}},sort_keys=True))
