"""Additional exploratory trained recurrent comparator. Protocol: gru_addendum.json.
All labels are reconstructed from terminal chosen action and observed 0/1 reward.
"""
import hashlib, json, math, time, random
from pathlib import Path
import torch
from torch import nn
from experiment import make_episode,SPLITS,SEEDS,NTRAIN,NTEST

HERE=Path(__file__).parent
torch.set_num_threads(1)

def tensors(episodes):
    maxlen=max(len(e[0]) for e in episodes)
    x=torch.zeros(len(episodes),maxlen,11,dtype=torch.float32)
    q=torch.zeros(len(episodes),5,dtype=torch.float32)
    lengths=[]
    for i,(seq,query,y) in enumerate(episodes):
        lengths.append(len(seq))
        for t,(f,b) in enumerate(seq):
            x[i,t,f]=1
            x[i,t,10]=float(b)
        q[i,4 if isinstance(query,tuple) else query]=1
    return x,q,torch.tensor(lengths)

class Recurrent(nn.Module):
    def __init__(self):
        super().__init__()
        self.gru=nn.GRU(11,8,batch_first=True)
        self.head=nn.Sequential(nn.Linear(13,16),nn.Tanh(),nn.Linear(16,1))
    def forward(self,x,q,lengths):
        packed=nn.utils.rnn.pack_padded_sequence(x,lengths.cpu(),batch_first=True,enforce_sorted=False)
        _,h=self.gru(packed)
        return self.head(torch.cat((h[-1],q),dim=1)).flatten()

def evaluate(model,seed,split):
    envrng=random.Random(seed*829+SPLITS.index(split)*1000003+17)
    episodes=[make_episode(envrng,split) for _ in range(NTEST)]
    x,q,l=tensors(episodes)
    model.eval()
    with torch.no_grad():
        z=model(x,q,l); a=(z>=0).long().tolist()
    return sum(int(pred==ep[2]) for pred,ep in zip(a,episodes))/len(episodes)

def run(seed):
    torch.manual_seed(seed)
    rng=random.Random(seed+700)
    data=[make_episode(rng,'in_distribution') for _ in range(NTRAIN)]
    model=Recurrent()
    optim=torch.optim.Adam(model.parameters(),lr=.01)
    t0=time.process_time()
    model.train()
    for i in range(0,NTRAIN,25):
        batch=data[i:i+25];x,q,l=tensors(batch)
        logits=model(x,q,l)
        # Only terminal action and binary reward are exposed to training.
        action=(logits.detach()>=0).long()
        reward=torch.tensor([int(int(a)==ep[2]) for a,ep in zip(action.tolist(),batch)],dtype=torch.long)
        inferred_label=torch.where(reward==1,action,1-action).float()
        loss=nn.functional.binary_cross_entropy_with_logits(logits,inferred_label)
        optim.zero_grad();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.0);optim.step()
    cpu=time.process_time()-t0
    return {'seed':seed,'train_cpu_s':cpu,'parameter_count':sum(t.numel() for t in model.parameters()),
            'transient_state_bits':8*32,
            'eval':{split:evaluate(model,seed,split) for split in SPLITS}}

def main():
    rows=[run(seed) for seed in SEEDS]
    out={'addendum_sha256':hashlib.sha256((HERE/'gru_addendum.json').read_bytes()).hexdigest(),
         'results':rows,'torch_version':torch.__version__,
         'warning':'single-epoch exploratory recurrent baseline with higher memory allowance; no first use or scientific admission'}
    (HERE/'gru_results.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
