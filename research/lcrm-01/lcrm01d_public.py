"""LCRM-D public 3-role, 4-bit, eight-event tensors. No source oracle imported."""
from __future__ import annotations
import hashlib,json,torch
ROLES=('alpha','beta','gamma')

def bits(v, width=4):
    return torch.stack([((v >> i) & 1).float() for i in range(width)],dim=-1)*2-1

def episode_tensor(episodes):
    if len(episodes) not in (20,24,4):raise ValueError('FIT local split only')
    for e in episodes:
        if set(e)!= {'initial','events'} or len(e['events'])!=8 or set(e['initial'])!=set(ROLES):raise ValueError('episode schema')
    b=len(episodes)
    init=torch.tensor([[ep['initial'][r] for r in ROLES] for ep in episodes],dtype=torch.long)
    initial=bits(init,4).reshape(b,3,8)
    target=torch.tensor([[ROLES.index(ev['target']) for ev in ep['events']] for ep in episodes],dtype=torch.long)
    source=torch.tensor([[ROLES.index(ev['source']) for ev in ep['events']] for ep in episodes],dtype=torch.long)
    event=torch.tensor([[ev['event'] for ev in ep['events']] for ep in episodes],dtype=torch.long)
    output=torch.tensor([[ev['observed'] for ev in ep['events']] for ep in episodes],dtype=torch.long)
    state=init[:,:,0].clone()
    prior=[]
    for j in range(8):
        prior.append(state.gather(1,target[:,j:j+1])[:,0])
        state=state.scatter(1,target[:,j:j+1],output[:,j:j+1])
    assert len(prior)==8
    return dict(initial=initial,target=target,source=source,event=bits(event),y=bits(output),y_uint=output,prior=torch.stack(prior,1))

def public_digest(episodes):
    return hashlib.sha256(json.dumps(episodes,sort_keys=True,separators=(',',':')).encode()).hexdigest()
