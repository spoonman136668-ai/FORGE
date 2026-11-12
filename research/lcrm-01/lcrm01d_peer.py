"""Independent fully trained additive recurrent-role peer with exact parameter parity."""
import torch
from torch import nn
from lcrm01d_public import bits

class Peer(nn.Module):
 def __init__(self):
    super().__init__()
    self.encoder=nn.Linear(8,8)
    self.target_map=nn.Linear(8,8)
    self.source_map=nn.Linear(8,8)
    self.event_map=nn.Linear(4,8)
    self.memory_map=nn.Linear(8,8)
    self.decode=nn.Linear(8,4)
    self.memory_probe=nn.Linear(8,8)
 def forward(self,p,teacher=True,ablate=False):
    n=p['initial'].shape[0]; indices=torch.arange(n)
    memory=torch.tanh(self.encoder(p['initial']))
    pred=[]; recall=[]
    for k in range(8):
      dst=p['target'][:,k]; origin=p['source'][:,k]
      at_dest=memory[indices,dst]; at_source=memory[indices,origin]
      # Additive trained recurrent interaction, not the candidate's product.
      other=at_dest if ablate else at_source
      joint=torch.tanh(self.target_map(at_dest)+self.source_map(other)+self.event_map(p['event'][:,k]))
      out=self.decode(joint)
      pred.append(out)
      recall.append(self.memory_probe(at_dest))
      observed=p['y'][:,k] if teacher else (out.detach()>=0).float()*2-1
      older=(bits(p['prior'][:,k]) if teacher else
             (self.memory_probe(at_dest)[:,:4].detach()>=0).float()*2-1)
      updated=torch.tanh(self.memory_map(at_dest)+self.encoder(torch.cat([observed,older],-1)))
      mask=torch.nn.functional.one_hot(dst,3).unsqueeze(-1).float()
      memory=memory*(1-mask)+updated[:,None,:]*mask
    return torch.stack(pred,1),torch.stack(recall,1)
