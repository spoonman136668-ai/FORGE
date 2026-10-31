"""G82B synthetic structural screen, NOT an authentic model activation measurement."""
import json
import torch

torch.manual_seed(82)
N,D,B=128,2048,128
# Proxy for independently continuous gate/up projections; no model weights or prompts.
gate=torch.randn(N,D,dtype=torch.float32)
up=torch.randn(N,D,dtype=torch.float32)
results=[]
for dtype in (torch.float32,torch.float16):
    g=gate.to(dtype); u=up.to(dtype)
    for name,values in [('relu',torch.relu(g)*u),('swiglu',torch.nn.functional.silu(g)*u)]:
        blocks=values.reshape(N,D//B,B)
        zero=(blocks==0).all(dim=-1)
        zero_elements=(values==0).sum().item()
        results.append(dict(activation=name,dtype=str(dtype),vectors=N,dimension=D,block=B,
                            zero_elements=zero_elements,total_elements=N*D,
                            zero_blocks=int(zero.sum().item()),total_blocks=N*(D//B)))
print(json.dumps(results,indent=2))
with open('/mnt/data/g82b/result.json','w') as f:json.dump({'kind':'synthetic_structural_screen','authentic_model':False,'cuda':False,'torch':torch.__version__,'results':results},f,indent=2)
