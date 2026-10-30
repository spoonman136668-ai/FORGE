"""MP-AI37: externally authored LoCoMo paired memory-retrieval development.
Never use original QA gold in retrieval, task selection, or model prompts.
This tests a source-conversation retrieval prototype, NOT deployed Mind-Palace.
Free text strict exact is a lower bound, NOT official LoCoMo semantic scoring.
No scientific first use, no weights trained, no production memory changes.
"""
import argparse,hashlib,json,math,os,re,shutil,sys,tempfile,time
from pathlib import Path
from collections import Counter
import mpai27_external_source_custody as source
import mpai28_external_task_freeze_and_scorer as score
import mpai30_real_semantic_judge_canaries as original
ARMS=("none","unrelated_token_matched","retrieved_conversation")
SEED="mpai37-categories-1-2-per-10-plus-5-for-first-5"
PHASE="INIT"
def check(ok,s):
 if not ok: raise RuntimeError("MPAI37_"+s)
def digest(b):return hashlib.sha256(b).hexdigest()
def canon(a):return json.dumps(a,sort_keys=True,separators=(",",":"))
def get_data(private):
 spec=source.FILES[0]
 path,n=source.file_bytes(spec,private)
 source.inspect(spec,path,n)
 v=json.loads(path.read_text("utf-8"))
 check(len(v)==10,"SOURCE_SIZE")
 return v
def freeze(data):
 items=[]
 for i,s in enumerate(data):
  for cat in (("1","2","5") if i<5 else ("1","2")):
   options=[j for j,x in enumerate(s["qa"]) if str(x.get("category"))==cat]
   check(bool(options),"MISSING_SOURCE_CATEGORY")
   j=min(options,key=lambda k:digest((SEED+"|"+str(s["sample_id"])+"|"+cat+"|"+str(k)).encode()))
   items.append({"sample":i,"sample_id":str(s["sample_id"]),"index":j,"category":cat})
 check(len(items)==25 and Counter(z["category"] for z in items)=={"1":10,"2":10,"5":5},"ORIGINAL_SELECTION")
 proto={"scheme":"mpai37-memory-recall-v1","source":source.LOCOMO_BLOB,
  "model":original.MODEL_SHA,"seed":137,"arms":ARMS,
  "task_selection":items,"retriever":"unsupervised-lexical-idf-top12",
  "scorer":"strict-exact-short-answer-lower-bound+category5-unknown",
  "first_use":False,"production_mindpalace":False}
 return items,digest(canon(proto).encode())
STOP=set("a an the what where when which who how is are was were and or of for by on at to in did do does with that this from have has had about they their he she her it its why".split())
def terms(x):return set(z for z in re.findall(r"[a-z0-9]+",x.casefold()) if len(z)>1 and z not in STOP)
def source_turns(sample):
 conv=sample["conversation"];chunks=[]
 sessions=sorted((int(k[8:]),k) for k,v in conv.items() if re.fullmatch(r"session_\d+",k) and isinstance(v,list))
 for num,key in sessions:
  day=conv.get(key+"_date_time","")
  day=day[:45] if isinstance(day,str) else ""
  for turn in conv[key]:
   if not isinstance(turn,dict) or not isinstance(turn.get("text"),str):continue
   text=turn["text"].strip()
   if text:
    chunks.append((f"Session {num} {day} | "+str(turn.get("speaker",""))[:70]+": "+text)[:700])
 check(len(chunks)>30,"CONVERSATION_EMPTY")
 return chunks
def retrieve(turns,q):
 query=terms(q);check(bool(query),"EMPTY_QUERY")
 docs=[terms(t) for t in turns];counts=Counter(x for d in docs for x in d)
 n=len(docs)
 ranks=[]
 for i,doc in enumerate(docs):
  weight=sum(math.log(1+(n-counts[x]+.5)/(counts[x]+.5)) for x in query&doc)
  ranks.append((-weight,i))
 order=sorted(ranks)
 idx=[];size=0
 for _,i in order:
  if size+len(turns[i])>6500:continue
  idx.append(i);size+=len(turns[i])+1
  if len(idx)==12:break
 check(len(idx)>=4,"RETRIEVAL_TOO_SMALL")
 return "\n".join(turns[i] for i in sorted(idx))
def messages(ctx,q):
 return [{"role":"system","content":"Use only supplied evidence. If unable to establish the answer, reply exactly UNKNOWN. Otherwise give one concise factual answer, without explanation."},
 {"role":"user","content":"Evidence:\n"+ctx+"\n\nQuestion: "+q}]
def tokens(m,ctx,q):
 return len(m.tokenize(("Evidence:\n"+ctx+"\n\nQuestion: "+q).encode(),add_bos=False))
def placebo(m,ctx,other,q):
 seed="Unrelated source conversation:\n"+"\n".join(other[:80])+"\n"
 target=tokens(m,ctx,q)
 def txt(n):return (seed*(1+n//len(seed)))[:n]
 lo,hi=1,17000
 while lo<hi:
  mid=(lo+hi)//2
  if tokens(m,txt(mid),q)<target:lo=mid+1
  else:hi=mid
 width=range(max(1,lo-50),min(17000,lo+51))
 size=min(width,key=lambda z:abs(tokens(m,txt(z),q)-target))
 control=txt(size)
 check(abs(tokens(m,control,q)-target)<=3,"PLACEBO_TOKEN_MATCH")
 return control
def strict(gold,answer,category):
 if category=="5":return int(gold is None and answer.strip().upper()=="UNKNOWN")
 if not isinstance(gold,str) or not gold.strip():return None
 if answer.strip().upper()=="UNKNOWN":return 0
 return int(score.normalize(answer)==score.normalize(gold))
def run_eval(data,chosen,private):
 global PHASE
 check(os.name=="nt" and os.getenv("RUNNER_NAME")=="FORGE-CODEX-REMOTE","ORIGINAL_WINDOWS_ONLY")
 check(shutil.disk_usage(private.parent).free>3500000000,"DISK_BOUND")
 PHASE="MODEL_AUTH"
 original.download_model(private/original.MODEL_NAME)
 print("MPAI37_AUTHENTIC_MODEL_SHA256=PASS",flush=True)
 os.environ["HF_HUB_OFFLINE"]="1"
 import socket
 socket.socket=lambda *a,**kw:(_ for _ in ()).throw(RuntimeError("MPAI37_OFFLINE_REQUIRED"))
 from llama_cpp import Llama
 m=Llama(model_path=str(private/original.MODEL_NAME),n_ctx=4096,n_threads=4,n_gpu_layers=0,n_batch=128,seed=137,verbose=False)
 PHASE="SOURCE_ONLY_MEMORY_RETRIEVAL"
 texts=[source_turns(x) for x in data]
 tasks=[]
 for one in chosen:
  idx=one["sample"];q=data[idx]["qa"][one["index"]]["question"]
  check(isinstance(q,str) and q.strip(),"ORIGINAL_QUESTION")
  mem=retrieve(texts[idx],q)
  unrelated=placebo(m,mem,texts[(idx+5)%10],q)
  tasks.append((one,q,{"none":"","unrelated_token_matched":unrelated,"retrieved_conversation":mem}))
 print("MPAI37_ORIGINAL_GOLD_USED_BY_RETRIEVAL=FALSE",flush=True)
 PHASE="REAL_INFERENCE"
 trials=[]
 for i,(src,q,contexts) in enumerate(tasks):
  order=ARMS[i%3:]+ARMS[:i%3]
  for arm in order:
   t0=time.perf_counter()
   response=m.create_chat_completion(messages=messages(contexts[arm],q),temperature=0,top_p=1,max_tokens=48)
   choice=response["choices"];usage=response["usage"]
   answer=choice[0]["message"]["content"]
   pt=int(usage["prompt_tokens"]);ct=int(usage["completion_tokens"])
   check(0<pt<=4000 and 0<ct<=48 and isinstance(answer,str),"INFERENCE_CONTRACT")
   trials.append({"task":i,"category":src["category"],"arm":arm,"answer":answer,
                  "tokens":pt,"completion":ct,"wall_ms":max(1,int((time.perf_counter()-t0)*1000))})
 check(len(trials)==75,"ACTUAL_CALL_COUNT")
 PHASE="POST_MODEL_SOURCE_GOLD_SCORING"
 for t in trials:
  src=tasks[t["task"]][0]
  answer=data[src["sample"]]["qa"][src["index"]].get("answer")
  t["correct"]=strict(answer,t["answer"],src["category"])
 paired=[]
 for i in range(25):
  arms={a["arm"]:a for a in trials if a["task"]==i}
  check(len(arms)==3,"TASK_ARM_COVERAGE")
  check(abs(arms["unrelated_token_matched"]["tokens"]-
            arms["retrieved_conversation"]["tokens"])<=5,"PROMPT_TOKEN_MATCH")
  if all(arms[a]["correct"] is not None for a in ARMS):paired.append(arms)
 check(len(paired)>=20,"SCORABLE_TASK_COUNT")
 print("MPAI37_ORIGINAL_FULL_PROMPT_PLACEBO_TOKEN_PARITY=PASS",flush=True)
 for arm in ARMS:
  z=[x for x in trials if x["arm"]==arm]
  scorable=[x for x in z if x["correct"] is not None]
  print("MPAI37_ARM_"+arm.upper()+"="+canon({
   "n":25,"scorable":len(scorable),"strict_correct":sum(x["correct"] for x in scorable),
   "unknown":sum(x["answer"].strip().upper()=="UNKNOWN" for x in z),
   "prompt_tokens":sum(x["tokens"] for x in z),
   "completion_tokens":sum(x["completion"] for x in z),
   "wall_ms":sum(x["wall_ms"] for x in z)}),flush=True)
 for cat in ("1","2","5"):
  z={arm:[x for x in trials if x["arm"]==arm and x["category"]==cat] for arm in ARMS}
  print("MPAI37_CATEGORY_"+cat+"="+canon({
     arm:{"n":len(z[arm]),"scorable":sum(x["correct"] is not None for x in z[arm]),
          "strict_correct":sum(x["correct"] or 0 for x in z[arm])} for arm in ARMS}),flush=True)
 for comparison in ("none","unrelated_token_matched"):
  better=sum(x["retrieved_conversation"]["correct"]==1 and x[comparison]["correct"]==0 for x in paired)
  worse=sum(x["retrieved_conversation"]["correct"]==0 and x[comparison]["correct"]==1 for x in paired)
  print("MPAI37_RETRIEVED_VS_"+comparison.upper()+"="+canon(
     {"paired":len(paired),"better":better,"worse":worse}),flush=True)
 # Temporary receipt never published to GitHub artifacts or Library.
 (private/"private_exact_evaluation.json").write_text(canon({"trials":trials,
   "is_scientific_acceptance":False}),encoding="utf-8")
 print("MPAI37_REAL_LOCAL_MODEL_CALLS=75",flush=True)
 print("MPAI37_ORIGINAL_25_TASK_SELECTION_PRESERVED=PASS",flush=True)
 print("MPAI37_SOURCE_QUESTION_OR_GOLD_LOGGED=FALSE",flush=True)
 print("MPAI37_SEMANTIC_FREE_TEXT_SCORER=NOT_QUALIFIED",flush=True)
 print("MPAI37_DEPLOYED_MINDPALACE_EFFECT=NOT_EVALUATED",flush=True)
 print("MPAI37_INDEPENDENT_HIDDEN_FIRST_USE=NOT_ATTESTED",flush=True)
 print("MPAI37_SCIENTIFIC_ACCEPTANCE=FALSE",flush=True)
 print("MPAI37_ACCEPTED_MEMORY_WRITES=0",flush=True)
def main():
 global PHASE
 a=argparse.ArgumentParser()
 a.add_argument("--phase",choices=("freeze","evaluate"),required=True)
 a.add_argument("--expected-sha",default="")
 args=a.parse_args()
 check(os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE" and os.getenv("GITHUB_RUN_ATTEMPT")=="1","REPO")
 check(not os.getenv("OPENAI_API_KEY"),"NO_PAID_API")
 check(original.MODEL_SHA=="e4165e3a71af97f1b4820da61079826d8752a2088e313af0c7d346796c38eff5","MODEL_PIN")
 if args.phase=="evaluate":
  check(re.fullmatch("[a-f0-9]{64}",args.expected_sha or ""),"PREREG_SHA")
  private=Path(os.environ["MPAI37_SCRATCH"])
  check(not private.exists(),"SCRATCH_COLLISION")
  private.mkdir()
 else:private=Path(tempfile.mkdtemp(prefix="mpai37-first-job-"))
 try:
  PHASE="ORIGINAL_SOURCE_CUSTODY"
  data=get_data(private);items,frozen=freeze(data)
  print("MPAI37_FROZEN_SELECTION_SHA256="+frozen,flush=True)
  print("MPAI37_SELECTION_ORIGINAL_25=PASS",flush=True)
  print("MPAI37_CAT1_CAT2_CAT5_COUNTS=10_10_5",flush=True)
  if args.phase=="freeze":
   print("MPAI37_ORIGINAL_GOLD_NOT_READ_BY_SELECTOR=TRUE",flush=True)
   print("MPAI37_PREMODEL_REGISTRATION=PASS",flush=True)
  else:
   check(frozen==args.expected_sha,"SEPARATE_JOB_SOURCE_MISMATCH")
   print("MPAI37_SEPARATE_JOB_SELECTION=PASS",flush=True)
   run_eval(data,items,private)
 finally:
  if args.phase=="freeze":
   shutil.rmtree(private);print("MPAI37_LINUX_SOURCE_SCRATCH_CLEAN=PASS",flush=True)
  else:print("MPAI37_OWNER_CLEANUP_REQUIRED=TRUE",flush=True)
if __name__=="__main__":
 try:main()
 except Exception as e:
  msg=str(e)
  code=msg if re.fullmatch(r"MPAI37_[A-Z0-9_]{3,100}",msg) else "MPAI37_PRIVATE_EXCEPTION"
  print("MPAI37_SAFE_FAILURE="+code,flush=True)
  print("MPAI37_SAFE_PHASE="+PHASE,flush=True)
  print("MPAI37_SAFE_TYPE="+type(e).__name__,flush=True)
  sys.exit(2)
