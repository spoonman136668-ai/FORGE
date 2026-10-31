"""NR-M1D: prospective, synthetic-only terminal-reward memory experiment.
Protocol frozen in protocol.json before this code. No source-world or science claims.
"""
import hashlib, json, math, random, statistics, time
from pathlib import Path

HERE=Path(__file__).parent
PROTOCOL_BYTES=(HERE/'protocol.json').read_bytes()
P=json.loads(PROTOCOL_BYTES)
SEEDS=P['seeds']; NTRAIN=P['train_episodes_per_seed']; NTEST=P['test_episodes_per_seed_per_split']
FEATURES=10
SPLITS=P['splits']


def make_episode(rng, split):
    # Generating valid tasks uses private ground truth for scoring but not for retention decisions.
    cues=(2,3) if split=='unseen_relevant_feature_ids_2_3' else (0,1)
    bits={f:rng.randrange(2) for f in cues}
    observed=[(f,bits[f]) for f in cues]
    noise_ids=[f for f in range(FEATURES) if f not in cues]
    noises=[(rng.choice(noise_ids),rng.randrange(2)) for _ in range(10 if split!='position_and_distractor_shift' else 16)]
    seq=noises[:4]+observed+noises[4:] if split=='position_and_distractor_shift' else observed+noises
    query=('xor',*cues) if split=='xor_of_both_0_1' else rng.choice(cues)
    target= (bits[cues[0]] ^ bits[cues[1]]) if isinstance(query,tuple) else bits[query]
    return (seq,query,target)


def phi(item,method):
    f,b,t=item
    if method=='feature':
        d=[0.0]*FEATURES; d[f]=1.0;return d
    if method=='position':
        return [float(t<2),t/18.0]
    raise ValueError(method)


def sample_keep(candidates, w, rng, method, temp):
    xs=[phi(o,method) for o in candidates]
    logits=[sum(v*a for v,a in zip(x,w))/temp for x in xs]
    remaining=[0,1,2]
    picked=[]; grad=[0.0]*len(w)
    for _ in range(2):
        m=max(logits[i] for i in remaining)
        z=[math.exp(logits[i]-m) for i in remaining]
        denom=sum(z); probs=[p/denom for p in z]
        roll=rng.random();cum=0.;chosen=remaining[-1]
        for i,p in zip(remaining,probs):
            cum+=p
            if roll<cum:
                chosen=i;break
        xchosen=xs[chosen]
        for j in range(len(w)):
            grad[j]+=(xchosen[j]-sum(p*xs[i][j] for i,p in zip(remaining,probs)))/temp
        picked.append(chosen);remaining.remove(chosen)
    return [candidates[i] for i in picked],grad


def retain(seq, method, rng, w=None, train=False, temperature=1.):
    memory=[];grad=[0.0]*(len(w) if w is not None else 0)
    for t,(f,b) in enumerate(seq):
        item=(f,b,t)
        if len(memory)<2:
            memory.append(item);continue
        if method in ('feature','position'):
            candidates=memory+[item]
            if train:
                memory,g=sample_keep(candidates,w,rng,method,temperature)
                grad=[a+b for a,b in zip(grad,g)]
            else:
                scored=[sum(v*a for v,a in zip(phi(o,method),w)) for o in candidates]
                keep=sorted(range(3),key=lambda i:(-scored[i], candidates[i][2]))[:2]
                memory=[candidates[i] for i in keep]
        elif method=='fifo':memory.pop(0);memory.append(item)
        elif method=='reservoir':
            if rng.random()<2/(t+1):memory[rng.randrange(2)]=item
        elif method=='symbolic':
            # Rule-informed ceiling; knows cue identities for each new source family.
            # NOT a comparable trained or same-prior-information policy.
            if f in (0,1,2,3) and f not in [m[0] for m in memory]:
                # Existing first 2 memory entries already contain the episode's cue pair.
                pass
        else:raise ValueError(method)
    return memory,grad


def action(memory,query,rng):
    if isinstance(query,tuple):
        bits=[next((v for f,v,t in memory if f==q),None) for q in query[1:]]
        return bits[0]^bits[1] if None not in bits else rng.randrange(2)
    bits=[b for f,b,t in memory if f==query]
    return bits[-1] if bits else rng.randrange(2)


def train(seed,method):
    rng=random.Random(seed+700)
    d=FEATURES if method=='feature' else 2
    w=[0.]*d; m=[0.]*d; v=[0.]*d;baseline=0.5
    lr=P['candidate_hyperparameters']['adam_step']; beta1=.9; beta2=.999
    total_reward=0
    start=time.process_time()
    for n in range(1,NTRAIN+1):
        seq,query,y=make_episode(rng,'in_distribution')
        temp=1.0-0.4*(n-1)/(NTRAIN-1)
        mem,grad=retain(seq,method,rng,w,True,temp)
        reward=int(action(mem,query,rng)==y)
        total_reward+=reward
        advantage=reward-baseline
        # Terminal-reward policy gradient only. Never directly update a queried feature.
        for i in range(d):
            g=max(-10.,min(10.,advantage*grad[i]-P['candidate_hyperparameters']['l2']*w[i]))
            m[i]=beta1*m[i]+(1-beta1)*g
            v[i]=beta2*v[i]+(1-beta2)*g*g
            w[i]+=lr*(m[i]/(1-beta1**n))/(math.sqrt(v[i]/(1-beta2**n))+1e-8)
        baseline=(1-.025)*baseline+.025*reward
    return w,total_reward/NTRAIN,time.process_time()-start


def evaluate(seed,split,method,weights):
    envrng=random.Random(seed*829+SPLITS.index(split)*1000003+17)
    episodes=[make_episode(envrng,split) for _ in range(NTEST)]
    total=0;coverage=0
    t0=time.process_time()
    for idx,(seq,query,y) in enumerate(episodes):
        rng=random.Random(seed*31337+SPLITS.index(split)*8999+idx)
        if method=='symbolic':
            cues=(2,3) if split=='unseen_relevant_feature_ids_2_3' else (0,1)
            memory=[(f,b,t) for t,(f,b) in enumerate(seq) if f in cues][:2]
        else:
            memory,_=retain(seq,method,rng,weights)
        need=query[1:] if isinstance(query,tuple) else (query,)
        coverage+=all(any(f==q for f,_,_ in memory) for q in need)
        total+=int(action(memory,query,rng)==y)
    return {'accuracy':total/NTEST,'cue_coverage':coverage/NTEST,'evaluation_cpu_s':time.process_time()-t0}


def main():
    rows=[];trained=[];tstart=time.process_time()
    for seed in SEEDS:
        wfeature,rfeature,cfeature=train(seed,'feature')
        wposition,rposition,cposition=train(seed,'position')
        trained.append({'seed':seed,'method':'feature','weights':wfeature,'train_reward':rfeature,'train_cpu_s':cfeature})
        trained.append({'seed':seed,'method':'position','weights':wposition,'train_reward':rposition,'train_cpu_s':cposition})
        for split in SPLITS:
            for method in ('feature','position','fifo','reservoir','symbolic'):
                weights=wfeature if method=='feature' else (wposition if method=='position' else None)
                rows.append({'seed':seed,'split':split,'method':method,**evaluate(seed,split,method,weights)})
    out={'protocol_sha256':hashlib.sha256(PROTOCOL_BYTES).hexdigest(), 'protocol':P['schema'],
         'training':trained,'results':rows, 'total_process_cpu_s':time.process_time()-tstart,
         'warning':'Synthetic terminal-reward diagnostic, not authentic causal transfer or scientific superiority.'}
    (HERE/'results.json').write_text(json.dumps(out,indent=2)+'\n')
    print('protocol SHA256',out['protocol_sha256'])
    print('total CPU seconds',round(out['total_process_cpu_s'],2))
    for split in SPLITS:
        print('\n',split)
        for method in ('feature','position','fifo','reservoir','symbolic'):
            rs=[r for r in rows if r['split']==split and r['method']==method]
            print(f" {method:10s} accuracy={statistics.mean(r['accuracy'] for r in rs):.3f} cover={statistics.mean(r['cue_coverage'] for r in rs):.3f} seeds={[round(r['accuracy'],3) for r in rs]}")
    print('training',[(r['seed'],r['method'],round(r['train_reward'],3)) for r in trained])
if __name__=='__main__':main()
