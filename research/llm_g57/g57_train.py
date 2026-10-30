#!/usr/bin/env python3
"""G57 bounded from-scratch LM CPU training-cost trial; immutable prereg in docs/research."""
import argparse,hashlib,json,os,pathlib,resource,subprocess,sys,time,urllib.request
SHA="86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed"
SIZE=1115394
URL="https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt"
STEPS=120;SEQ=48;BATCH=8;D=64;LAYERS=4;HEADS=4;EVAL_COUNT=96
SEEDS=(1901,1903,1907)
ARMS=("baseline","layerdrop","progressive","combined")
def digest(b):return hashlib.sha256(b).hexdigest()
def source(dest):
 p=pathlib.Path(dest)
 if not p.is_file():
  with urllib.request.urlopen(URL,timeout=40) as stream:data=stream.read(SIZE+1)
  if len(data)!=SIZE or digest(data)!=SHA:raise ValueError("DATA_DOWNLOAD_IDENTITY_DRIFT")
  p.write_bytes(data)
 data=p.read_bytes()
 if len(data)!=SIZE or digest(data)!=SHA:raise ValueError("DATA_SHA_DRIFT")
 return p
def split(b):
 t=int(len(b)*.8);v=int(len(b)*.9)
 return b[:t],b[t:v],b[v:]
def layers(arm,step,seed):
 if arm not in ARMS or not isinstance(step,int) or step<0 or step>=STEPS:raise ValueError("INVALID_ARM_STEP")
 all4=(0,1,2,3)
 if arm=="baseline":return all4
 if arm=="layerdrop":return tuple(x for x in all4 if step>=96 or x!=(step+seed)%4)
 if arm=="progressive":return (0,1) if step<54 else all4
 if step<54:return (0,1)
 if step<96:return tuple(x for x in all4 if x!=(step+seed)%4)
 return all4
def build():
 import torch
 from torch import nn
 from torch.nn import functional as F
 class Block(nn.Module):
  def __init__(self):
   super().__init__()
   self.ln1=nn.LayerNorm(D);self.qkv=nn.Linear(D,3*D);self.proj=nn.Linear(D,D)
   self.ln2=nn.LayerNorm(D);self.ff=nn.Sequential(nn.Linear(D,2*D),nn.GELU(),nn.Linear(2*D,D))
  def forward(self,x):
   b,t,c=x.shape
   q,k,v=self.qkv(self.ln1(x)).reshape(b,t,3,HEADS,c//HEADS).unbind(2)
   q,k,v=(z.transpose(1,2) for z in (q,k,v))
   a=F.scaled_dot_product_attention(q,k,v,is_causal=True).transpose(1,2).contiguous().view(b,t,c)
   y=x+self.proj(a)
   return y+self.ff(self.ln2(y))
 class LM(nn.Module):
  def __init__(self):
   super().__init__()
   self.embedding=nn.Embedding(256,D);self.position=nn.Embedding(SEQ,D)
   self.blocks=nn.ModuleList([Block() for _ in range(LAYERS)])
   self.norm=nn.LayerNorm(D);self.head=nn.Linear(D,256,bias=False)
  def forward(self,x,y=None,active=None):
   z=self.embedding(x)+self.position(torch.arange(x.shape[1],device=x.device))
   for i in ((0,1,2,3) if active is None else active):z=self.blocks[i](z)
   logits=self.head(self.norm(z))
   return None if y is None else F.cross_entropy(logits.reshape(-1,256),y.reshape(-1))
 return LM()
def batch_at(torch,train,step,seed):
 rng=torch.Generator().manual_seed(seed*1000003+step*7919+149)
 idx=torch.randint(0,len(train)-SEQ-1,(BATCH,),generator=rng)
 block=train[idx[:,None]+torch.arange(SEQ+1)[None,:]]
 return block[:,:-1],block[:,1:]
def validate(torch,net,val):
 starts=torch.linspace(0,len(val)-SEQ-2,EVAL_COUNT,dtype=torch.int64)
 net.eval();total=0.
 with torch.inference_mode():
  for i in range(0,EVAL_COUNT,12):
   idx=starts[i:i+12]
   b=val[idx[:,None]+torch.arange(SEQ+1)[None,:]]
   total+=float(net(b[:,:-1],b[:,1:]))*len(idx)
 net.train();return total/EVAL_COUNT
def worker(seed,arm,datapath):
 import torch
 torch.set_num_threads(2);torch.use_deterministic_algorithms(True);torch.manual_seed(seed)
 raw=pathlib.Path(datapath).read_bytes()
 train,val,_sealed=split(raw)
 tr=torch.tensor(list(train),dtype=torch.long);va=torch.tensor(list(val),dtype=torch.long)
 net=build();opt=torch.optim.AdamW(net.parameters(),lr=.002,weight_decay=.01)
 initial=validate(torch,net,va);curve=[{"step":0,"val_loss":initial}]
 active_total=0
 begin=time.perf_counter();cpu_begin=time.process_time()
 for step in range(STEPS):
  x,y=batch_at(torch,tr,step,seed);active=layers(arm,step,seed);active_total+=len(active)
  opt.zero_grad(set_to_none=True)
  loss=net(x,y,active)
  loss.backward();opt.step()
  if (step+1)%30==0:curve.append({"step":step+1,"val_loss":validate(torch,net,va)})
 wall=time.perf_counter()-begin;cpu=time.process_time()-cpu_begin
 return {"seed":seed,"arm":arm,"param_count":sum(p.numel() for p in net.parameters()),
         "updates":STEPS,"train_tokens":STEPS*BATCH*SEQ,
         "executed_block_fraction":active_total/(STEPS*LAYERS),
         "initial_val_loss":initial,"final_val_loss":curve[-1]["val_loss"],
         "curve":curve,"training_wall_s":wall,"training_cpu_s":cpu,
         "peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
         "dataset_sha256":SHA}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--worker",action="store_true");p.add_argument("--dataset",default="g57_tinyshakespeare.txt")
 p.add_argument("--seed",type=int,choices=SEEDS);p.add_argument("--arm",choices=ARMS);a=p.parse_args()
 if a.worker:
  if a.seed is None or a.arm is None:raise ValueError("MISSING_ARM")
  data=pathlib.Path(a.dataset).read_bytes()
  if len(data)!=SIZE or digest(data)!=SHA:raise RuntimeError("WORKER_DATA_HASH_DRIFT")
  print(json.dumps(worker(a.seed,a.arm,a.dataset),sort_keys=True));return
 source(a.dataset)
 rows=[]
 for seed in SEEDS:
  for arm in ARMS:
   t=time.perf_counter()
   proc=subprocess.run([sys.executable,str(pathlib.Path(__file__).resolve()),
                       "--worker","--dataset",a.dataset,"--seed",str(seed),"--arm",arm],
                       capture_output=True,text=True,timeout=240,check=False,
                       env={**os.environ,"OMP_NUM_THREADS":"2","MKL_NUM_THREADS":"2"})
   if proc.returncode:raise RuntimeError("WORKER_FAILED seed="+str(seed)+" arm="+arm+
                        " stderr="+proc.stderr[-1800:])
   row=json.loads(proc.stdout.strip().splitlines()[-1])
   row["total_process_wall_s"]=time.perf_counter()-t;rows.append(row)
   print("G57_ARM seed="+str(seed)+" arm="+arm+" val="+str(round(row["final_val_loss"],6))+
         " wall="+str(round(row["total_process_wall_s"],3)),flush=True)
 matched={}
 for seed in SEEDS:
  s={x["arm"]:x for x in rows if x["seed"]==seed};baseline=s["baseline"]
  matched[str(seed)]={}
  for arm in ARMS[1:]:
   x=s[arm];speedup=baseline["total_process_wall_s"]/x["total_process_wall_s"]
   matched[str(seed)][arm]={"val_loss_delta":x["final_val_loss"]-baseline["final_val_loss"],
     "speedup":speedup,"quality_pass":x["final_val_loss"]<=baseline["final_val_loss"]+.05,
     "speed_pass":speedup>=1.15,"rss_pass":x["peak_rss_kib"]<=baseline["peak_rss_kib"]*1.10}
 admitted={arm:all(all(matched[str(seed)][arm][name] for name in ("quality_pass","speed_pass","rss_pass"))
               for seed in SEEDS) for arm in ARMS[1:]}
 import torch
 report={"schema":"forge.g57.training-cost-v1","scientific_acceptance":"NOT_GRANTED",
         "model_scope":"TINY_CPU_FROM_SCRATCH_SCREEN_ONLY",
         "dataset_url":URL,"dataset_sha256":SHA,"dataset_bytes":SIZE,
         "data_split":"train contiguous 80%, val 10%, untouched sealed test 10%",
         "device":"CPU","torch":torch.__version__,"seeds":SEEDS,"arms":ARMS,
         "training_steps":STEPS,"sequence_length":SEQ,"batch_size":BATCH,
         "quality_absolute_tolerance":.05,"minimum_speedup":1.15,
         "results":rows,"paired":matched,"qualified":admitted,
         "general_acceleration_proven":False}
 pathlib.Path("g57_result.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
 print("G57_DECISION="+json.dumps(admitted,sort_keys=True),flush=True)
if __name__=="__main__":main()
