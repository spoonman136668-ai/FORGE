"""Actually execute the pinned original CKB R196 plan_lane and compare FORGE."""
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

ckb=Path(os.environ["CKB_SOURCE"])
sys.path.insert(0,str(ckb))
r196=importlib.import_module("portfolio_progression_r196")
portfolio=importlib.import_module("portfolio")
assert r196.SCIENTIFIC_TERMINAL==frozenset(("supported","mixed","negative"))
EXE=os.environ["FORGE_R196_EXE"]
SHA="a"*64
GO={
 "supported":"SUPPORTED","mixed":"MIXED","negative":"NEGATIVE","invalid":"INVALID"
}
cases=[
 ["PLANNED"],
 ["BLOCKED"],
 ["RUNNING"],
 ["QUALIFIED"],
 ["CLASSIFIED:supported","PLANNED"],
 ["CLASSIFIED:mixed","BLOCKED"],
 ["CLASSIFIED:negative","RUNNING"],
 ["CLASSIFIED:invalid","PLANNED"],
 ["CLASSIFIED:supported","CLASSIFIED:mixed","CLASSIFIED:negative"]
]
for seq in cases:
 ids=[f"candidate_{i}" for i in range(len(seq))]
 states={}
 go_rows=[]
 for cid,value in zip(ids,seq):
  state,_,cls=value.partition(":")
  go_rows.append({"Status":state,"Classification":GO.get(cls,"")})
  states[cid]={"candidate_id":cid,"status":state,"classification":cls or None}
 advisory={"program":"Wingless","advisory_sha256":SHA,"shortlist":{"selected":[{"candidate_id":cid} for cid in ids]}}
 gate={"schema":"ckb.r196-science-gate-advisory.v1","lane":"Wingless",
  "state":"SCIENTIFIC_QUALIFICATION_PENDING","official_receipt_sha256":SHA,
  "independent_source_admitted":False,"full_preregistration_frozen":False,
  "sealed_source_set_sha256":None,"cross_lane_exclusion_receipt_sha256":None,
  "sealed_outcomes_accessed":False,"accepted_ref_mutation":False}
 gate_pin=portfolio.digest(gate)
 original_rows=[{"candidate_id":cid} for cid in ids]
 original_reconcile=r196.reconcile
 original_candidate_rows=r196.candidate_rows
 try:
  r196.reconcile=lambda a,j:{"last_receipt_sha256":None,"candidates":list(states.values())}
  r196.candidate_rows=lambda a:original_rows
  actual=r196.plan_lane(advisory,[],gate,independently_pinned_advisory_sha256=SHA,
    independently_pinned_last_event_sha256=None,independently_pinned_gate_sha256=gate_pin)
 finally:
  r196.reconcile=original_reconcile
  r196.candidate_rows=original_candidate_rows
 proc=subprocess.run([EXE],input=json.dumps(go_rows),text=True,capture_output=True,timeout=10)
 assert proc.returncode==0,(seq,proc.stderr)
 assert actual["disposition"]==proc.stdout.strip(),(seq,actual["disposition"],proc.stdout)
 assert actual["dispatch_authority"] is False
 print("CKB_R196_EXECUTABLE_PARITY=PASS",seq)
print("R19C_SOURCE_PINNED_CROSS_REPOSITORY_EXECUTION=PASS")
