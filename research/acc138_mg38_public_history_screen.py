"""ACC-138: exposed-MG38 public-next-front predictive support; archival DEV diagnostic ONLY.

Does not import MiniGrid, execute source actions, train native policies, or open sealed data.
Source entries and role/seed split are fixed independently of outcomes.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import zipfile

try:
    import orjson
    def loads(raw): return orjson.loads(raw)
    def canon(obj): return orjson.dumps(obj, option=orjson.OPT_SORT_KEYS)
except ImportError:
    def loads(raw): return json.loads(raw)
    def canon(obj): return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')

EXPECTED_ARCHIVE = '0e3800d2ba42c2cdfa41e3cb13430e624482291e21b7d1d78322d2a0375dd556'
EXPECTED_SOURCE = '42faea659d94c5527530f7a932d1fa0c4a409213e06733f4a9216f2db65b1fc7'
ARMS=('action', 'front', 'exact0', 'prev_action', 'coarse1', 'coarse2', 'coarse4', 'coarse8', 'exact2')
MAX_K=8

def sha(x): return hashlib.sha256(x).hexdigest()

def episode_records(ep):
    past=[]
    prev_hash=ep['public_start_sha256']
    for seq,e in enumerate(ep['source_events'],1):
        before,after=e['before'],e['after']
        assert e['index']==seq and e['before_sha256']==prev_hash
        assert sha(canon(before))==e['before_sha256']
        assert sha(canon(after))==e['after_sha256']
        assert e['external_actions']==0 and before['mission']==after['mission']
        assert before['mission']==e['mission']
        assert 0<=e['action']<=6
        prev_hash=e['after_sha256']
        a=e['action']
        fr=tuple(before['image'][3][5])
        prior=tuple(reversed(past[-MAX_K:]))
        # Exact full public history and compressed public front history are both prior-only.
        k_action=('a',a)
        k_front=('f',a,before['direction'],fr)
        k_exact=('e',a,e['before_sha256'])
        k_prev=('p',a,before['direction'],fr,prior[0][1] if prior else -1)
        keys={'action':(k_action,), 'front':(k_front,k_action),
              'exact0':(k_exact,k_front,k_action),
              'prev_action':(k_prev,k_front,k_action)}
        for k in (1,2,4,8):
            stages=[]
            for j in range(min(k,len(prior)),0,-1):
                # A suffix is used only when that many actual previous events exist.
                if j in (1,2,4,8,k):
                    stages.append(('h',a,before['direction'],fr,tuple(x[2:] for x in prior[:j])))
            keys['coarse'+str(k)]=tuple(stages)+(k_front,k_action)
        keys['exact2']=tuple([('x',a,e['before_sha256'],tuple(x[:2] for x in prior[:j]))
                               for j in range(min(2,len(prior)),0,-1)])+(k_exact,k_front,k_action)
        # Evaluate observable front-change only. This is NOT verified movement or task progress.
        if a in (2,3,4,5):
            label=int(tuple(after['image'][3][5])!=fr)
            yield (keys,label,ep['family'],ep['role'],ep['seed_dev_exposed'],a)
        past.append((e['before_sha256'],a,before['direction'],fr))
    assert seq==ep['original_source_actions']

def evaluate(source):
    episodes=source['original_120_episodes']
    roster=defaultdict(list)
    for ep in episodes: roster[(ep['family'],ep['role'])].append(ep)
    assert len(episodes)==120 and len(roster)==40
    rows=[]
    for key,eps in sorted(roster.items()):
        eps=sorted(eps,key=lambda e:e['seed_dev_exposed'])
        assert len(eps)==3 and len({e['seed_dev_exposed'] for e in eps})==3
        fit_eps,score_ep=eps[:2],eps[2]
        fit_rows=[v for ep in fit_eps for v in episode_records(ep)]
        score_rows=list(episode_records(score_ep))
        assert all(v[4]!=score_ep['seed_dev_exposed'] for v in fit_rows)
        counts={arm:defaultdict(lambda:[0,0]) for arm in ARMS}
        # Arm-specific count maps, but all arms have exactly the same 2 source-seed fit rows.
        for keys,y,*_ in fit_rows:
            for arm in ARMS:
                for prefix in keys[arm]:
                    counts[arm][prefix][0]+=1
                    counts[arm][prefix][1]+=y
        for keys,y,family,role,seed,action in score_rows:
            pred={};coverage={}
            for arm in ARMS:
                match=None;used=None
                for pos,keying in enumerate(keys[arm]):
                    n,hits=counts[arm].get(keying,(0,0))
                    if n>=2 or pos==len(keys[arm])-1:
                        match=(n,hits);used=pos;break
                n,hits=match
                pred[arm]=(hits+1)/(n+2)
                coverage[arm]=int(used==0 and n>=2)
            rows.append((family,role,seed,action,y,pred,coverage))
    assert rows
    # Independent per-family source seeds but several roles share the same world seed.
    def aggreg(wanted):
        out={}
        for arm in ARMS:
            vals=[v for v in rows if wanted(v)]
            if not vals:
                out[arm]={'n':0};continue
            brier=sum((v[5][arm]-v[4])**2 for v in vals)/len(vals)
            ll=sum(-(v[4]*math.log(v[5][arm])+(1-v[4])*math.log(1-v[5][arm])) for v in vals)/len(vals)
            right=sum((v[5][arm]>=.5)==bool(v[4]) for v in vals)/len(vals)
            cover=sum(v[6][arm] for v in vals)
            out[arm]={'n':len(vals),'front_change_rate':round(sum(v[4] for v in vals)/len(vals),6),
                      'brier':round(brier,6),'log_loss':round(ll,6),'accuracy_at_half':round(right,6),
                      'highest_specificity_supported_n':cover,
                      'highest_specificity_supported_fraction':round(cover/len(vals),6)}
        return out
    return {
        'schema':'forge.acc138.mg38.exposed-dev-next-front-history-control-screen.v1',
        'archive_sha256':EXPECTED_ARCHIVE,'source_sha256':EXPECTED_SOURCE,
        'split':'Per family and role: sort three original exposed development seeds; 2 lower seeds FIT, upper seed SCORE; no updates on score; repeated source worlds across roles are NOT independent trials.',
        'outcome':'Original returned public front [3][5] triple changes after source-selected action 2/3/4/5; not physical movement, hidden-state proof, or mission reward',
        'models':'All conventional Beta(1,1) conditional frequency backoff; choose most specific condition with >=2 FIT rows, otherwise less specific, fallback action-only; public current/front and up to 8 prior BEFORE/public-action records only.',
        'n_score_events':len(rows),'n_groups':len(roster),'n_fit_source_episodes':80,'n_score_source_episodes':40,
        'all_nonturn':aggreg(lambda v:True),
        'forward_only':aggreg(lambda v:v[3]==2),
        'pickup_toggle_only':aggreg(lambda v:v[3] in (3,5)),
        'family':{f:aggreg(lambda v:v[0]==f) for f in sorted({v[0] for v in rows})},
        'limits':['Archive is already exposed DEV, neither new source first-use nor sealed heldout',
                  'Prediction uses the original behavior-policy action, not a newly chosen action or intervention',
                  'Exact public camera equality is not hidden-state identity',
                  'Multiple roles test on the same environment seed; no independent world count inflated',
                  'The outcome is public front change only, not task success, causal consequences, or learned native policy',
                  'No variance estimate or model-selection claim from this one fixed retrospective split',
                  'No native model, code, source runner, workflow or controller changed']
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('archive',type=Path)
    ap.add_argument('--out',type=Path,default=Path('acc138-report.json'))
    args=ap.parse_args()
    assert sha(args.archive.read_bytes())==EXPECTED_ARCHIVE,'ARCHIVE_IDENTITY_FAIL'
    with zipfile.ZipFile(args.archive) as z:
        assert z.testzip() is None
        a=loads(z.read('first.json'))
        b=loads(z.read('second.json'))
    for v in (a,b):
        assert v['canonical_source_sha256']==EXPECTED_SOURCE
        assert sha(canon(v['source']))==EXPECTED_SOURCE,'SOURCE_DIGEST_FAIL'
        assert v['source']['original_selected_action_count']==22307
    assert a['source']==b['source'],'ORIGINAL_REPRODUCTIONS_DIFFER'
    result=evaluate(a['source'])
    args.out.write_bytes(json.dumps(result,sort_keys=True,indent=2).encode('utf-8')+b'\n')
    print('PASS',result['n_score_events'],'SCORE_EVENTS',sha(args.out.read_bytes()))
    for name in ('all_nonturn','forward_only','pickup_toggle_only'):
        print(name,[(k,v['brier'],v['highest_specificity_supported_n']) for k,v in result[name].items()])

if __name__=='__main__': main()
