"""Source-only original LoCoMo schema metadata, no question/answer/turn text."""
import json,os,re,sys,tempfile
from pathlib import Path
from collections import Counter
from mpai27_external_source_custody import FILES,file_bytes,inspect
def fail(s): raise RuntimeError("MPAI37_"+s)
def main():
 if os.getenv("GITHUB_REPOSITORY")!="spoonman136668-ai/FORGE" or os.getenv("GITHUB_RUN_ATTEMPT")!="1":fail("REPO")
 if os.getenv("OPENAI_API_KEY"):fail("PAID_API")
 with tempfile.TemporaryDirectory(prefix="mpai37-schema-") as t:
  spec=FILES[0];path,size=file_bytes(spec,Path(t));inspect(spec,path,size)
  data=json.loads(path.read_text("utf-8"))
  assert len(data)==10
  counts=Counter(); categories=Counter(); schemas=Counter(); qa_fields=Counter(); turn_kinds=Counter(); lens=[]; sample_counts=[]
  for i,s in enumerate(data):
   qa=s["qa"]; conv=s["conversation"]; assert isinstance(qa,list) and isinstance(conv,dict)
   sample_counts.append(len(qa))
   for question in qa:
    categories[str(question.get("category"))]+=1
    qa_fields.update(question.keys())
    if question.get("answer") is None:counts["null_answer"]+=1
    elif isinstance(question.get("answer"),str):counts["string_answer"]+=1
    else:counts["other_answer"]+=1
   for k,v in conv.items():
    if isinstance(v,list):
     counts["list_sessions"]+=1
     if v:
      turn_kinds[type(v[0]).__name__]+=1
      if isinstance(v[0],dict):
       schemas.update(v[0].keys())
       for turn in v:
        if isinstance(turn,dict):lens.append(len(str(turn.get("text",""))))
    elif isinstance(v,str):counts["str_session_meta"]+=1
    else:counts["other_session_meta"]+=1
  print("MPAI37_SOURCE_AUTHENTIC=PASS")
  print("MPAI37_ORIGINAL_10_SAMPLES=PASS")
  print("MPAI37_QA_FIELDS="+",".join(sorted(qa_fields)))
  print("MPAI37_ORIGINAL_QA_COUNTS="+",".join(map(str,sample_counts)))
  print("MPAI37_QA_CATEGORIES="+json.dumps(categories,sort_keys=True))
  print("MPAI37_ANSWER_TYPES="+json.dumps(counts,sort_keys=True))
  print("MPAI37_TURN_KEYS="+",".join(sorted(schemas)))
  print("MPAI37_FIRST_SESSION_ITEM_TYPES="+json.dumps(turn_kinds,sort_keys=True))
  print("MPAI37_TURN_TEXT_LENGTH_MEDIAN="+str(sorted(lens)[len(lens)//2] if lens else 0))
  print("MPAI37_NO_GOLD_OR_QUESTIONS_LOGGED=TRUE")
  print("MPAI37_PRODUCTION_MEMORY_WRITES=0")
if __name__=="__main__":
 try:main()
 except Exception as e:
  print("MPAI37_SAFE_ERROR="+(str(e) if re.fullmatch(r"MPAI37_[A-Z0-9_]+",str(e)) else type(e).__name__));sys.exit(2)
