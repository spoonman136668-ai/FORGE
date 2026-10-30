#!/usr/bin/env python3
"""G58: preregistered scratch causal-LM partial backward on new authentic corpus."""
import argparse,hashlib,json,os,pathlib,resource,subprocess,sys,time,urllib.request
import g57_train as original
URL=("https://raw.githubusercontent.com/dakrone/corpus/"
     "f25de55809404f0173504d6853b7b6df93d51ae0/data/alice-in-wonderland.txt")
GIT_BLOB="6c89ee6db335fcd14ff756e5841aba7b9cd708d0"
G57_BLOB="be22df7d518cc9f195823bbf4d7901b1f449d1fd"
SIZE=167497
SEEDS=(2701,2703,2707)
ARMS=("baseline","top2_half","top2_two_thirds","top3_two_thirds")
STEPS=480
VAL_STEPS=(0,120,240,360,480)
ORDER={
2701:("baseline","top2_half","top2_two_thirds","top3_two_thirds"),
2703:("top3_two_thirds","top2_two_thirds","top2_half","baseline"),
2707:("top2_two_thirds","top3_two_thirds","baseline","top2_half")}
def sha(b):return hashlib.sha256(b).hexdigest()
def gitblob(b):
 return hashlib.sha1(b"blob "+str(len(b)).encode("ascii")+b"\0"+b).hexdigest()
def source(path):
 p=pathlib.Path(path)
 if not p.is_file():
  with urllib.request.urlopen(URL,timeout=50) as r: data=r.read(SIZE+1)
  if len(data)!=SIZE or gitblob(data)!=GIT_BLOB:raise RuntimeError("ORIGINAL_ALICE_SOURCE_DRIFT")
  p.write_bytes(data)
 data=p.read_bytes()
 if len(data)!=SIZE or gitblob(data)!=GIT_BLOB:raise RuntimeError("ORIGINAL_ALICE_SOURCE_DRIFT")
 return data
def strategy(arm,step):
 if arm not in ARMS or step<0 or step>=STEPS:raise ValueError("UNREGISTERED_SCHEDULE")
 if arm=="baseline":return (False,0)
 if arm=="top2_half":return (step%2==1,2)
 if arm=="top2_two_thirds":return (step%3!=0,2)
 return (step%3!=0,1)
def partial_loss(net,x,y,cut):
 """Same full forward; no graph below the cut; exact encoder top-depth only training."""
 import torch
 import torch.nn.functional as F
 if cut not in (1,2):raise ValueError("BAD_BACKWARD_CUT")
 with torch.no_grad():
  hidden=net.embedding(x)+net.position(torch.arange(x.shape[1],device=x.device))
  for i in range(cut):hidden=net.blocks[i](hidden)
 for i in range(cut,4):hidden=net.blocks[i](hidden)
 return F.cross_entropy(net.head(net.norm(hidden)).reshape(-1,256),y.reshape(-1))
def run_worker(seed,arm,path):
 import torch
 torch.set_num_threads(2)
 torch.use_deterministic_algorithms(True)
 torch.manual_seed(seed)
 raw=source(path)
 train,val,_=original.split(raw)
 tr=torch.tensor(list(train),dtype=torch.long);va=torch.tensor(list(val),dtype=torch.long)
 net=original.build()
 opt=torch.optim.AdamW(net.parameters(),lr=0.002,weight_decay=0.01)
 initial=original.validate(torch,net,va)
 curve=[{"update":0,"nats_per_byte":initial}]
 start=time.perf_counter();cpu_start=time.process_time()
 active_backwards=0;partial_updates=0
 for step in range(STEPS):
  inputs,targets=original.batch_at(torch,tr,step,seed)
  ispartial,cut=strategy(arm,step)
  opt.zero_grad(set_to_none=True)
  loss=partial_loss(net,inputs,targets,cut) if ispartial else net(inputs,targets)
  if not torch.isfinite(loss):raise RuntimeError("NONFINITE_TRAIN_LOSS")
  loss.backward()
  if ispartial:
   partial_updates+=1
   active_backwards+=4-cut
  else:active_backwards+=4
  opt.step()
  if step+1 in VAL_STEPS:
   score=original.validate(torch,net,va)
   curve.append({"update":step+1,"nats_per_byte":score})
 wall=time.perf_counter()-start;cpu=time.process_time()-cpu_start
 return {"seed":seed,"arm":arm,"updates":STEPS,"tokens_seen":STEPS*original.BATCH*original.SEQ,
  "param_count":sum(p.numel() for p in net.parameters()),
  "training_wall_seconds":wall,"training_cpu_seconds":cpu,
  "cpu_peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
  "executed_block_backwards":active_backwards,
  "max_block_backwards":STEPS*4,"partial_updates":partial_updates,
  "full_updates":STEPS-partial_updates,"final_val_nats":curve[-1]["nats_per_byte"],
  "initial_val_nats":initial,"validation_curve":curve,
  "corpus_sha256":sha(raw),"corpus_git_blob":gitblob(raw),
  "scientific_acceptance":"NOT_GRANTED"}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--worker",action="store_true")
 p.add_argument("--dataset",default="g58_authentic_alice.txt")
 p.add_argument("--seed",type=int,choices=SEEDS)
 p.add_argument("--arm",choices=ARMS)
 args=p.parse_args()
 old=pathlib.Path(original.__file__).read_bytes()
 if gitblob(old)!=G57_BLOB:raise RuntimeError("FROZEN_G57_MODEL_SOURCE_DRIFT")
 data=source(args.dataset)
 if args.worker:
  if args.seed is None or args.arm is None:raise RuntimeError("MISSING_ARM")
  print(json.dumps(run_worker(args.seed,args.arm,args.dataset),sort_keys=True),flush=True)
  return
 rows=[]
 for seed in SEEDS:
  for arm in ORDER[seed]:
   t=time.perf_counter()
   proc=subprocess.run([sys.executable,str(pathlib.Path(__file__).resolve()),"--worker",
     "--dataset",args.dataset,"--seed",str(seed),"--arm",arm],
     text=True,capture_output=True,env={**os.environ,"OMP_NUM_THREADS":"2","MKL_NUM_THREADS":"2"},
     timeout=180,check=False)
   if proc.returncode:raise RuntimeError(f"WORKER_FAILED seed={seed} arm={arm} "
      f"rc={proc.returncode} stderr={proc.stderr[-1800:]}")
   output=json.loads(proc.stdout.strip().splitlines()[-1])
   output["whole_worker_wall_seconds"]=time.perf_counter()-t
   rows.append(output)
   print("G58_ARM seed="+str(seed)+" arm="+arm+" val="+
    format(output["final_val_nats"],".6f")+" wall="+
    format(output["whole_worker_wall_seconds"],".3f"),flush=True)
 paired={}
 for seed in SEEDS:
  groups={r["arm"]:r for r in rows if r["seed"]==seed}
  baseline=groups["baseline"]
  paired[str(seed)]={}
  for arm in ARMS[1:]:
   candidate=groups[arm]
   ratio=baseline["whole_worker_wall_seconds"]/candidate["whole_worker_wall_seconds"]
   entry={"val_delta_nats":candidate["final_val_nats"]-baseline["final_val_nats"],
       "wall_speedup":ratio,
       "rss_ratio":candidate["cpu_peak_rss_kib"]/baseline["cpu_peak_rss_kib"],
       "quality_pass":candidate["final_val_nats"]<=baseline["final_val_nats"]+0.05,
       "speed_pass":ratio>=1.15,
       "rss_pass":candidate["cpu_peak_rss_kib"]<=baseline["cpu_peak_rss_kib"]*1.10}
   paired[str(seed)][arm]=entry
 accepted={arm:all(all(paired[str(seed)][arm][k]
             for k in ("quality_pass","speed_pass","rss_pass")) for seed in SEEDS)
           for arm in ARMS[1:]}
 import torch
 result={"schema":"forge.acc.g58.partial-backward-authentic-corpus.v1",
  "git_source_blob":GIT_BLOB,"source_url":URL,"source_bytes":SIZE,
  "source_sha256":sha(data),"g57_model_source_git_blob":G57_BLOB,
  "torch":torch.__version__,"device":"CPU","seeds":SEEDS,"arms":ARMS,"steps":STEPS,
  "split":"contiguous 80% train, 10% validation, last 10% sealed/unread",
  "quality_tolerance_nats":0.05,"min_end_to_end_speedup":1.15,
  "max_rss_ratio":1.10,"results":rows,"paired":paired,"qualified":accepted,
  "scientific_acceptance":"NOT_GRANTED","general_acceleration_proven":False}
 pathlib.Path("g58_result.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print("G58_QUALIFIED="+json.dumps(accepted,sort_keys=True),flush=True)
if __name__=="__main__":main()
