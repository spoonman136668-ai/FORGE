"""Candidate sequence-learned bilinear interaction, source-neutral public FIT only."""
import torch
from torch import nn
from lcrm01d_public import bits

class Candidate(nn.Module):
 def __init__(self):
    super().__init__()
    self.init=nn.Linear(8,8)
    self.target=nn.Linear(8,8)
    self.source=nn.Linear(8,8)
    self.event=nn.Linear(4,8)
    self.write=nn.Linear(8,8)
    self.read=nn.Linear(8,4)
    self.retain=nn.Linear(8,8)
 def forward(self,p,teacher=True,ablate=False):
    B=p['initial'].shape[0]; batch=torch.arange(B)
    h=torch.tanh(self.init(p['initial']))
    preds=[]; retain=[]
    for step in range(8):
      t=p['target'][:,step]; s=p['source'][:,step]
      target=h[batch,t]; src=h[batch,s]
      # Learned role interaction; no known source operator template.
      src_rep=self.source(target if ablate else src)
      context=torch.tanh(self.target(target)*src_rep + self.event(p['event'][:,step]))
      logits=self.read(context)
      preds.append(logits)
      retain.append(self.retain(target))
      y = p['y'][:,step] if teacher else (logits.detach().ge(0).float()*2-1)
      if teacher:
        priorbits=bits(p['prior'][:,step])
      else:
        # memory state is not exposed during rollout; use last predicted target
        # old target readout as approximate previous nibble.
        priorbits=self.retain(target)[:,:4].detach().ge(0).float()*2-1
      h_new=torch.tanh(self.write(target)+self.init(torch.cat((y,priorbits),dim=-1)))
      h=h*(1-torch.nn.functional.one_hot(t,3)[:,:,None].float())+h_new[:,None,:]*torch.nn.functional.one_hot(t,3)[:,:,None].float()
    return torch.stack(preds,1),torch.stack(retain,1)
