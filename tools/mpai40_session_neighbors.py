"""MP-AI40 source-only, fixed LoCoMo25 session-neighbor retrieval comparison."""
import argparse,hashlib,json,os,re,sys,tempfile
from collections import Counter
from pathlib import Path
import mpai37_external_memory_effect as p37
import mpai38_original_evidence_coverage_audit as p38
import mpai39_original_bm25_retrieval_comparison as p39
FROZEN="123411ed33446deded98c45dd3c5e54a98620b8565a8612b7bea1c594131c5b8"
ARMS=("idf","bm25","neighbor")
K=12
CAP=6500
SEEDS=8
RADIUS=2
STAGE="INIT"
def check(x,k):
 if not x:raise RuntimeError("MPAI40_"+k)
def jstr(x):return json.dumps(x,sort_keys=True,separators=(",",":"))
def sha(x):return hashlib.sha256(jstr(x).encode()).hexdigest()
def manifest(cases):
 return sha({"source":p37.source.LOCOMO_BLOB,"case_sha":FROZEN,"cases":cases,
  "source_script_blobs":["f1305323279cf56c1fdda068a5d14933dfbe6ca7","bae5ddce69e17b8f3b5682799840405828784e63","3b892d8ccdf0316990a06ed353b565be864a55cd"],
  "methods":ARMS,"max_k":K,"char_cap":CAP,
  "neighbor":"eight original BM25 seeds; four nearest turns in same conversation session; fallback next ranked BM25",
  "same_session_radius":RADIUS,"bm25_seed_count":SEEDS,
  "gold_labels_for_ranking":False,"model_calls":0,
  "first_use":False,"accepted_memory_writes":0})
def session_ids(turns):
 values=[]
 for t in turns:
  m=re.match(r"^Session (\d+) ",t)
  check(m is not None,"SESSION_MARKER")
  values.append(int(m.group(1)))
 return values
def neighbors(turns,q):
 rank=sorted(p39.rank_bm25(turns,q))
 sess=session_ids(turns)
 got=[];used=set();spent=0
 def add(i):
  nonlocal spent
  if i in used:return False
  n=len(turns[i])+1
  if spent+n>CAP:return False
  got.append(i);used.add(i);spent+=n
  return True
 for _,i in rank:
  if len(got)==SEEDS:break
  add(i)
 check(len(got)==SEEDS,"SEED_COUNT")
 seeds=tuple(got)
 suggested={}
 for r,i in enumerate(seeds):
  for delta in (-1,1,-2,2):
   v=i+delta
   if v<0 or v>=len(turns) or sess[v]!=sess[i] or v in used:continue
   key=(abs(delta),r,delta>0,v)
   if v not in suggested or key<suggested[v]:suggested[v]=key
 added=0
 for idx,_ in sorted(suggested.items(),key=lambda x:x[1]):
  if len(got)==K or added==4:break
  if add(idx):added+=1
 for _,i in rank:
  if len(got)==K:break
  add(i)
 check(4<=len(got)<=K,"TURN_LIMIT")
 text="\n".join(turns[i] for i in sorted(got))
 check(len(text)<=CAP,"CHAR_LIMIT")
 return set(got),len(text),added
def stats(rows,arm,cat):
 z=[v for v in rows if v["cat"]==cat]
 check(len(z)==(5 if cat=="5" else 10),"CAT_COUNT")
 n=sum(x["n"] for x in z);hit=sum(x[arm] for x in z)
 return {"cases":len(z),"evidence":n,"retrieved":hit,"recall":round(hit/n,4),
   "any":sum(x[arm]>0 for x in z),"all":sum(x[arm]==x["n"] for x in z),
   "zero":sum(x[arm]==0 for x in z),
   "chars":sum(x[arm+"_chars"] for x in z),
   "turns":sum(x[arm+"_turns"] for x in z)}
def main():
 global STAGE
 p=argparse.ArgumentParser()
 p.add_argument("--phase",choices=("freeze","audit"),required=True)
 p.add_argument("--expected",default="")
 args=p.parse_args()
 check(os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE","REPO")
 check(os.getenv("GITHUB_RUN_ATTEMPT")=="1","RUN_ATTEMPT")
 check(not os.getenv("OPENAI_API_KEY"),"PAID_API")
 if args.phase=="audit":check(re.fullmatch("[0-9a-f]{64}",args.expected or ""),"PROTOCOL")
 with tempfile.TemporaryDirectory(prefix="mpai40-") as td:
  STAGE="AUTHENTIC_SOURCE"
  data=p37.get_data(Path(td));cases,p37sha=p37.freeze(data)
  check(p37sha==FROZEN and len(cases)==25,"ORIGINAL_25")
  protocol=manifest(cases)
  print("MPAI40_PROTOCOL_SHA256="+protocol,flush=True)
  print("MPAI40_ORIGINAL_25_SHA256="+p37sha,flush=True)
  if args.phase=="freeze":
   print("MPAI40_METADATA_ONLY_PREREG=PASS",flush=True)
   print("MPAI40_MODEL_CALLS=0",flush=True)
   return
  check(protocol==args.expected,"PREREG_MISMATCH")
  STAGE="RETRIEVE_BEFORE_GOLD"
  cache={i:p38.reconstructed(s) for i,s in enumerate(data)}
  chosen=[]
  for item in cases:
   turns,ids,_=cache[item["sample"]]
   q=data[item["sample"]]["qa"][item["index"]]["question"]
   a,at=p39.original_retriever_indexes(turns,q)
   b,bt=p39.select_context(turns,p39.rank_bm25(turns,q))
   c,ct,n=neighbors(turns,q)
   check(len(a)==K and len(b)==K,"BASELINE_K")
   check(max(len(at),len(bt),ct)<=CAP,"MATCHED_CHAR")
   chosen.append({"item":item,"ids":ids,"sets":{"idf":set(a),"bm25":set(b),"neighbor":c},
                  "chars":{"idf":len(at),"bm25":len(bt),"neighbor":ct},
                  "turns":{"idf":len(a),"bm25":len(b),"neighbor":len(c)},"extra":n})
  check(len(chosen)==25,"ALL_CASES")
  print("MPAI40_ALL_75_CONTEXTS_SELECTED_BEFORE_EVIDENCE=PASS",flush=True)
  print("MPAI40_P37_EXACT_25_CONTEXTS_VERIFIED=PASS",flush=True)
  STAGE="AUDIT_HUMAN_ANNOTATIONS"
  rows=[]
  for c in chosen:
   item=c["item"]
   qa=data[item["sample"]]["qa"][item["index"]]
   raw=qa["evidence"]
   check(isinstance(raw,list) and len(raw)>0 and all(isinstance(x,str) for x in raw),"EVIDENCE_SCHEMA")
   gold=set(raw);check(len(gold)==len(raw) and gold.issubset(set(c["ids"])),"EVIDENCE_ID")
   row={"cat":item["category"],"n":len(gold)}
   for arm in ARMS:
    ids={c["ids"][i] for i in c["sets"][arm]}
    row[arm]=len(ids&gold)
    row[arm+"_chars"]=c["chars"][arm]
    row[arm+"_turns"]=c["turns"][arm]
   rows.append(row)
  for cat in ("1","2","5"):
   for arm in ARMS:print("MPAI40_"+arm.upper()+"_CATEGORY_"+cat+"="+jstr(stats(rows,arm,cat)),flush=True)
  ans=[r for r in rows if r["cat"]!="5"]
  check(len(ans)==20 and sum(r["n"] for r in ans)==38,"ANSWERABLE_GOLD_COUNT")
  totals={}
  for arm in ARMS:
   hit=sum(r[arm] for r in ans)
   totals[arm]=(hit,sum(r[arm]>0 for r in ans),sum(r[arm]==r["n"] for r in ans),sum(r[arm]==0 for r in ans))
   print("MPAI40_"+arm.upper()+"_ANSWERABLE="+jstr({
    "cases":20,"citations":38,"hits":hit,"recall":round(hit/38,4),
    "any":totals[arm][1],"all":totals[arm][2],"none":totals[arm][3],
    "chars":sum(r[arm+"_chars"] for r in ans),
    "turns":sum(r[arm+"_turns"] for r in ans)}),flush=True)
  check(totals["idf"]==(22,15,10,5) and totals["bm25"]==(22,15,10,5),"PRIOR_RESULT_NOT_REPRODUCED")
  print("MPAI40_NEIGHBOR_MINUS_BM25_EVIDENCE_IDS="+str(totals["neighbor"][0]-22),flush=True)
  print("MPAI40_NEIGHBOR_MINUS_BM25_FULL_CASES="+str(totals["neighbor"][2]-10),flush=True)
  print("MPAI40_NEIGHBOR_BETTER_CASES="+str(sum(r["neighbor"]>r["bm25"] for r in ans)),flush=True)
  print("MPAI40_NEIGHBOR_WORSE_CASES="+str(sum(r["neighbor"]<r["bm25"] for r in ans)),flush=True)
  print("MPAI40_NEIGHBOR_TURNS_ADDED="+str(sum(c["extra"] for c in chosen)),flush=True)
  print("MPAI40_SOURCE_ORACLE_NOT_USED_FOR_RANKING=PASS",flush=True)
  print("MPAI40_NO_MODEL_INFERENCE=TRUE",flush=True)
  print("MPAI40_NOT_DEPLOYED_MINDPALACE=TRUE",flush=True)
  print("MPAI40_SCIENTIFIC_ADMISSION=BLOCKED",flush=True)
  print("MPAI40_PRODUCTION_MEMORY_WRITES=0",flush=True)
 print("MPAI40_SOURCE_SCRATCH_CLEAN=PASS",flush=True)
if __name__=="__main__":
 try:main()
 except Exception as e:
  msg=str(e);code=msg if re.fullmatch("MPAI40_[A-Z0-9_]+",msg) else "MPAI40_EXCEPTION"
  print("MPAI40_SAFE_FAILURE="+code,flush=True)
  print("MPAI40_SAFE_STAGE="+STAGE,flush=True)
  print("MPAI40_SAFE_TYPE="+type(e).__name__,flush=True)
  sys.exit(2)
