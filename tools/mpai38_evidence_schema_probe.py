"""MP-AI38 schema-only original LoCoMo evidence shape audit. No benchmark text."""
import json,os,re,sys,tempfile
from pathlib import Path
from collections import Counter
import mpai37_external_memory_effect as p37
def safe_shape(v):
 if v is None:return "null"
 if isinstance(v,list):
  return "list("+",".join(sorted({safe_shape(x) for x in v}))[:180]+")"
 if isinstance(v,dict):return "dict_keys("+",".join(sorted(v.keys()))[:120]+")"
 if isinstance(v,str):
  if re.fullmatch(r"[A-Za-z0-9:,. \-_\[\]]+",v or ""):
   return "string_"+("dia_id_shape" if re.fullmatch(r"[A-Za-z]?\d+[:\-]\d+(?:\s*,\s*[A-Za-z]?\d+[:\-]\d+)*",v.strip()) else "structured_or_text")
  return "other_string"
 return type(v).__name__
def main():
 if os.getenv("GITHUB_REPOSITORY")!="spoonman136668-ai/FORGE" or os.getenv("GITHUB_RUN_ATTEMPT")!="1":raise RuntimeError("MPAI38_OWNER")
 with tempfile.TemporaryDirectory(prefix="mpai38-private-probe-") as t:
  data=p37.get_data(Path(t));tasks,sha=p37.freeze(data)
  print("MPAI38_P37_ORIGINAL_FROZEN_SHA256="+sha)
  count=Counter();sample=Counter();dia=Counter();cats=Counter()
  for z in tasks:
   s=data[z["sample"]];q=s["qa"][z["index"]]
   v=q.get("evidence")
   count[safe_shape(v)]+=1;cats[z["category"]]+=1
   if isinstance(v,list):sample[len(v)]+=1
   elif isinstance(v,str):sample["string"]=1+sample["string"]
   for k,val in s["conversation"].items():
    if re.fullmatch(r"session_\d+",k) and isinstance(val,list):
     for turn in val:
      if isinstance(turn,dict):dia[safe_shape(turn.get("dia_id"))]+=1
  print("MPAI38_FROZEN_SELECTED_CATEGORIES="+json.dumps(cats,sort_keys=True))
  print("MPAI38_SELECTED_EVIDENCE_SHAPES="+json.dumps(count,sort_keys=True))
  print("MPAI38_SELECTED_LIST_SIZES="+json.dumps(sample,sort_keys=True))
  print("MPAI38_DIA_ID_SHAPES="+json.dumps(dia,sort_keys=True))
  print("MPAI38_PRIVATE_SOURCE_TEXT_LOGGED=FALSE")
  print("MPAI38_MODEL_CALLS=0")
  print("MPAI38_ACCEPTED_MEMORY_WRITES=0")
if __name__=="__main__":
 try:main()
 except Exception as e:
  print("MPAI38_SAFE_FAILURE="+type(e).__name__);sys.exit(2)
