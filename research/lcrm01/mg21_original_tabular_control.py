"""MG21 independent original-public seven-action count and reward baseline."""
import hashlib,json
from mg17_original_family_source_qual import canonical,digest
def empty():return [{"count":0,"positive":0} for _ in range(7)]
class Tabular:
 def __init__(self):self.states={};self.samples=0
 def learn(self,before,action,after,reward,terminal):
  if (self.samples>=4096 or type(action)is not int or action not in range(7)
      or before["mission"]!=after["mission"]):raise ValueError("MG21_TABULAR_INVALID_SOURCE")
  k=digest(before)
  if k not in self.states and len(self.states)>=4096:raise ValueError("MG21_TABULAR_CONTEXT_CAP")
  stat=self.states.setdefault(k,empty())[action]
  stat["count"]+=1
  if reward>0 and terminal and k!=digest(after):stat["positive"]+=1
  self.samples+=1
 def choose(self,before):
  k=digest(before);row=self.states.get(k,empty())
  scores=[4096*v["positive"]//(v["count"]+64) for v in row]
  if max(scores):
   return min(a for a,v in enumerate(scores) if v==max(scores)),"CONVENTIONAL_EXACT_STATE_REWARD"
  low=min(v["count"] for v in row);start=int(k[:2],16)%7
  for n in range(7):
   a=(start+n)%7
   if row[a]["count"]==low:return a,"CONVENTIONAL_LEAST_OBSERVED_ACTION"
  raise ValueError("MG21_TABULAR_NO_ACTION")
 def checkpoint(self):
  state={"schema":"mg21.independent.original.public.tabular.v1","samples":self.samples,"states":self.states}
  return canonical({"state":state,"sha256":hashlib.sha256(canonical(state)).hexdigest()})
 @classmethod
 def restore(cls,raw):
  try:
   wire=json.loads(raw);s=wire["state"]
   if (s["schema"]!="mg21.independent.original.public.tabular.v1"
       or hashlib.sha256(canonical(s)).hexdigest()!=wire["sha256"]
       or type(s["samples"]) is not int or s["samples"]>4096
       or len(s["states"])>4096
       or sum(v["count"] for row in s["states"].values() for v in row)!=s["samples"]):
    raise ValueError("MG21_TABULAR_CHECKPOINT_INVALID")
   x=cls();x.samples=s["samples"];x.states=s["states"]
   if x.checkpoint()!=raw:raise ValueError("MG21_TABULAR_NONCANONICAL")
   return x
  except (KeyError,ValueError,TypeError) as e:raise ValueError("MG21_TABULAR_UNTRUSTED") from e
