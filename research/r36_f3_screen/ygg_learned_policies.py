"""F3 development-trained observation policies, no sealed inputs or oracle at inference.

The first three scheduled episodes retain the pinned public anchor reads.
C1 learns a fixed late-sentinel ordering. C2/C3/C4 use only previously
observed public scalars to adapt the two remaining probe pairs, under ten
reads total. Their implementation fidelity requires independent review.
"""
from ygg_methods import METHODS, fit_candidate, DevelopmentTrial
from ygg_public_instrument import READ_EPISODES, validate_schedule

def fit_all(trials):
    return {key:fit_candidate(key,tuple(trials)) for key in METHODS}

def choose(method, ranking, episode, history):
    if method not in METHODS or episode not in READ_EPISODES:
        raise ValueError("F3_POLICY_OR_EPISODE")
    if len(ranking)!=10 or len(set(ranking))!=10 or any(not isinstance(x,int) or x<0 or x>15 for x in ranking):
        raise ValueError("F3_POLICY_RANKING")
    if episode in (0,1,3):
        return (0,1)
    already=set()
    for previous in (5,):
        if previous>=episode:continue
        already.update(history.get(previous,{}))
    # Recompute priorities exclusively from public values that already
    # existed before this episode; never inspect the current true swap.
    last={}
    prior={}
    for e in sorted(history):
        for a,v in history[e].items():
            prior[a]=last.get(a,v)
            last[a]=v
    if method=="YF3-C1":
        ordered=list(ranking)
    elif method=="YF3-C2":
        ordered=sorted(ranking,key=lambda a:(-abs(last.get(a,0)),ranking.index(a)))
    elif method=="YF3-C3":
        ordered=sorted(ranking,key=lambda a:(-abs(last.get(a,0)-prior.get(a,0)),ranking.index(a)))
    else:
        # Bounded sparse adaptive gate: favor unobserved candidate sensors.
        seen={a for readings in history.values() for a in readings}
        ordered=sorted(ranking,key=lambda a:(a in seen,ranking.index(a)))
    chosen=[a for a in ordered if a not in already][:2]
    if len(chosen)!=2 or chosen[0]==chosen[1]:
        raise ValueError("F3_POLICY_PAIR")
    return tuple(chosen)

def frozen_schedule(method,ranking):
    """Development reproducibility witness; adaptive policies use their own history at runtime."""
    history={}
    pairs=[]
    for episode in READ_EPISODES:
        addresses=choose(method,ranking,episode,history)
        pairs.append(addresses)
        history[episode]={a:0.0 for a in addresses}
    return validate_schedule(tuple(pairs))
