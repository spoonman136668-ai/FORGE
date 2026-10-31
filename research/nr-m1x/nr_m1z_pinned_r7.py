"""ITD-02 R7 nonlinear, unknown-parent local causal learning from public effects.

No model receives the simulator's hidden parent triples or truth tables.
Given equal public interleaved source experiences, each output bit learns
a three-parent conditional causal circuit. The three-parent structural
hypothesis is explicitly supplied and conventional controls must also get it.
"""
import hashlib,itertools,json
SCHEMA="yggdrasil.itd02.r7.fitted-local-nonlinear-causes.v1"
TRIPLES=tuple(itertools.combinations(range(8),3))

def canon(x):return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def index(state,p):
 return ((state>>p[0])&1)|(((state>>p[1])&1)<<1)|(((state>>p[2])&1)<<2)

class NonlinearLocalLearner:
 def __init__(self):
  self.source={}
  self.models={}
  self.events=0

 def observe(self,world,action,before,after):
  if (type(world)is not str or not world or len(world)>60 or
      type(action)is not int or action not in (0,1,2) or
      type(before)is not int or not 0<=before<256 or
      type(after)is not int or not 0<=after<256):
   raise ValueError("R7_INVALID_PUBLIC_CAUSAL_EFFECT")
  if self.models:raise ValueError("R7_CANNOT_LEARN_AFTER_MODEL_FREEZE")
  d=self.source.setdefault(world,{"0":{},"1":{},"2":{}})[str(action)]
  if str(before) in d:raise ValueError("R7_DUPLICATE_WORLD_ACTION_SOURCE")
  d[str(before)]=after
  self.events+=1

 def fit(self):
  if self.models:raise ValueError("R7_REPEATED_FIT")
  prepared={}
  for world,ops in self.source.items():
   prepared[world]={}
   for op in ("0","1","2"):
    raw=ops[op]
    if len(raw)!=192:raise ValueError("R7_PUBLIC_SOURCE_INCOMPLETE")
    samples=sorted((int(x),y) for x,y in raw.items())
    output=[]
    for outbit in range(8):
     selected=None
     for parents in TRIPLES:
      positives=[0]*8;counts=[0]*8
      for state,after in samples:
       idx=index(state,parents)
       positives[idx]+=(after>>outbit)&1
       counts[idx]+=1
      table=[int(2*positives[i]>=counts[i]) if counts[i]>0 else 0 for i in range(8)]
      # Choose minimum empirical absolute error, then smallest parent tuple.
      error=sum(min(positives[i],counts[i]-positives[i]) for i in range(8))
      if selected is None or error<selected[0]:
       selected=(error,parents,table)
     output.append({"parents":list(selected[1]),"table":selected[2],"fit_errors":selected[0]})
    prepared[world][op]=output
  self.models=prepared
  self.source={} # Retain only condensed fitted cause representation after FIT.
 def step(self,world,action,state):
  if (type(state)is not int or not 0<=state<256 or
      type(action)is not int or action not in (0,1,2)):
   raise ValueError("R7_INVALID_PUBLIC_COMPOSITION")
  fields=self.models[world][str(action)]
  out=0
  for bit,entry in enumerate(fields):
   out|=entry["table"][index(state,entry["parents"])]<<bit
  return out
 def predict(self,world,start,actions):
  if type(actions) not in (tuple,list) or not 1<=len(actions)<=16:
   raise ValueError("R7_INVALID_CAUSAL_CHAIN")
  state=start
  for action in actions:state=self.step(world,action,state)
  return state
 def checkpoint(self):
  if (self.source or not self.models or self.events!=576*len(self.models)):
   raise ValueError("R7_UNQUALIFIED_SOURCE_CUSTODY")
  record={"schema":SCHEMA,"models":self.models,"events":self.events}
  raw=canon(record)
  if len(raw)>150000:raise ValueError("R7_TOO_LARGE")
  return canon({"body":record,"sha256":hashlib.sha256(raw).hexdigest()})
 @classmethod
 def restore(cls,raw):
  if type(raw)is not bytes or not 0<len(raw)<=150000:
   raise ValueError("R7_INVALID_COLD_CHECKPOINT")
  try:
   obj=json.loads(raw)
   if set(obj)!={"body","sha256"} or hashlib.sha256(canon(obj["body"])).hexdigest()!=obj["sha256"]:
    raise ValueError("R7_SOURCE_AUTH_FAIL")
   body=obj["body"]
   if body["schema"]!=SCHEMA or type(body["models"])is not dict:
    raise ValueError("R7_UNTRUSTED_SCHEMA")
   out=cls();out.models=body["models"];out.events=body["events"]
   if not isinstance(out.events,int) or out.events!=576*len(out.models):
    raise ValueError("R7_INCONSISTENT_EXPOSURE")
   for world,ops in out.models.items():
    if not world or len(world)>60 or set(ops)!={"0","1","2"}:
     raise ValueError("R7_CORRUPT_WORLD")
    for bins in ops.values():
     if len(bins)!=8:raise ValueError("R7_INCOMPLETE_OUTPUT")
     for entry in bins:
      pp=entry["parents"];tt=entry["table"]
      if (type(pp)is not list or len(pp)!=3 or tuple(pp)not in TRIPLES or
          type(tt)is not list or len(tt)!=8 or
          any(type(x)is not int or x not in (0,1) for x in tt) or
          type(entry["fit_errors"])is not int or entry["fit_errors"]<0):
       raise ValueError("R7_BAD_CAUSAL_TABLE")
   return out
  except (KeyError,TypeError,ValueError,OverflowError) as e:
   raise ValueError("R7_CHECKPOINT_REJECTED") from e
