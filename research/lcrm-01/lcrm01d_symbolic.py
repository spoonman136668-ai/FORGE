"""Independent source-neutral GF(2) complete FIT-only control, no toy law import."""
from __future__ import annotations
from lcrm01d_public import ROLES

def vector(x):
    return 1 | sum(((v >> bit) & 1) << (1+4*i+bit) for i,v in enumerate(x) for bit in range(4))

def fit(episodes):
    if len(episodes)!=20: raise ValueError('FIT only 20')
    rows=[]
    for ep in episodes:
      state={r:list(ep['initial'][r]) for r in ROLES}
      for event in ep['events']:
        t,s=event['target'],event['source'];own,other=state[t],state[s];ev=event['event'];y=event['observed']
        rows.append((vector((own[0],own[1],other[0],other[1],ev)),y))
        state[t]=[y,own[0]]
    pivot={}
    for x,y in rows:
      merged=x | (y<<21)
      while x:
        p=(x&-x).bit_length()-1
        if p not in pivot:
          pivot[p]=merged
          break
        merged^=pivot[p]; x=merged&((1<<21)-1)
      if not x and merged >> 21: return None
    return pivot

def infer(pivot,x):
    acc=vector(x)
    encoded=acc
    while acc:
      p=(acc&-acc).bit_length()-1
      if p not in pivot: return None
      encoded ^= pivot[p]
      acc=encoded&((1<<21)-1)
    return (encoded >> 21)&15

def score(pivot,episodes):
    exact=0; abstained=0; biterr=0
    for ep in episodes:
      state={r:list(ep['initial'][r]) for r in ROLES};good=True
      for event in ep['events']:
        t,s=event['target'],event['source'];own,other=state[t],state[s]
        y=infer(pivot,(own[0],own[1],other[0],other[1],event['event'])) if pivot else None
        if y is None:
          abstained+=1;good=False;break
        biterr+=(y ^ event['observed']).bit_count()
        if y!=event['observed']: good=False
        state[t]=[y,own[0]]
      exact+=int(good)
    return {'exact_episodes':exact,'abstained_events':abstained,'bit_errors':biterr}
