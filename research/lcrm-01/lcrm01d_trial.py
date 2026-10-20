"""Frozen source-only 20/4 FIT-local sequence diagnostic. No CHECK/heldout."""
import argparse,torch,json,hashlib,random
from lcrm01d_public import episode_tensor,public_digest
from lcrm01d_sourceonly import fixture
from lcrm01d_candidate import Candidate
from lcrm01d_peer import Peer
from lcrm01d_symbolic import fit as fit_symbolic, score as score_symbolic

EPOCHS=80;LR=0.02

def train(cls,eps):
    torch.set_num_threads(1);torch.manual_seed(412)
    model=cls(); opt=torch.optim.Adam(model.parameters(),lr=LR)
    batch=episode_tensor(eps)
    for _ in range(EPOCHS):
      opt.zero_grad(set_to_none=True)
      logits,ret=model(batch,teacher=True)
      y=(batch['y']+1)/2
      # Public-state retention target, prefix-only. Same objective for both arms.
      prior=(torch.stack([((batch['prior'] >> b)&1).float() for b in range(4)],dim=-1)*2-1)
      # Request delayed memory with current-nibble twice, generic public prefix only.
      aux=torch.cat((prior,prior),dim=-1)
      loss=torch.nn.functional.binary_cross_entropy_with_logits(logits,y)+.3*torch.nn.functional.binary_cross_entropy_with_logits(ret,(aux+1)/2)
      loss.backward();opt.step()
    return model

def score(model,eps,ablate=False):
    batch=episode_tensor(eps)
    with torch.no_grad():
      logits,_=model(batch,teacher=False,ablate=ablate)
      outputs=(logits>=0).int()
      actual=(batch['y']>0).int()
      exact=((outputs==actual).all(-1)).all(-1).sum().item()
      errs=(outputs!=actual).sum().item()
    return {'exact_episodes':int(exact),'bit_errors':int(errs),'episodes':len(eps)}

def main(arm):
    seqs=fixture()
    if arm == 'symbolic':
       s=score_symbolic(fit_symbolic(seqs[:20]),seqs[20:])
       return {'schema':'mass.lcrm01.d.sourceonly-sequence-qualification.v1','arm':arm,'FIT_episodes':24,'FIT_internal_train':20,'FIT_local_validation':4,'FIT_sha256':public_digest(seqs),'epochs':None,'parameters':None,'CV':s,'original_scientific_firstuse':0,'counterfactual_admitted':False,'source_only':True}
    cls=Candidate if arm in ('candidate','ablation') else Peer
    trained=train(cls,seqs[:20]);expected=sum(p.numel() for p in trained.parameters())
    a=score(trained,seqs[20:],ablate=arm=='ablation')
    return {'schema':'mass.lcrm01.d.sourceonly-sequence-qualification.v1','arm':arm,'FIT_episodes':24,'FIT_internal_train':20,'FIT_local_validation':4,
            'FIT_sha256':public_digest(seqs),'epochs':EPOCHS,'parameters':expected,'CV':a,'original_scientific_firstuse':0,'counterfactual_admitted':False,'source_only':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--arm',choices=['candidate','peer','ablation','symbolic'],required=True);print(json.dumps(main(p.parse_args().arm),sort_keys=True))
