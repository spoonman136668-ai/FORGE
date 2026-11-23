"""F80: scientific result admission never conflates authentic FIT data with accepted originals."""
import json,sys
PINS={
 "Wingless":dict(run=38830952488,artifact=12017177693,digest="sha256:19496ccd797dce059bff909a69c5f1f8a3190bd913db7d348ecce1fb7fe8ccaa",source="57555a26f95591f81c996d5ea456ad8b00d485aa"),
 "Yggdrasil":dict(run=38831091860,artifact=12016759624,digest="sha256:adc3dbcbedadbcf1566c132b36b211a92f6c5ce11cb0bcd664583642542a3fd2")
}
def evaluate(lane, run, items):
 if lane not in PINS or not isinstance(items,list):raise ValueError("INVALID_EVIDENCE")
 pin=PINS[lane]
 found=[x for x in items if x.get("id")==pin["artifact"] and x.get("digest")==pin["digest"] and x.get("expired") is False and x.get("workflow_run",{}).get("id")==run==pin["run"]]
 if len(found)!=1:raise ValueError("IDENTITY_OR_DIGEST_DRIFT")
 return {"lane":lane,"run_id":run,"archive_digest_verified":True,"accepted_original":False,"prospective_policy_gain_qualified":False,"optimizer_training_eligible":False}
if __name__=="__main__":
 if len(sys.argv)!=3:sys.exit(2)
 for lane,path in zip(("Wingless","Yggdrasil"),sys.argv[1:]):
  with open(path) as f:obj=json.load(f)
  print(json.dumps(evaluate(lane,PINS[lane]["run"],obj["artifacts"]),sort_keys=True))
 print("F80_AUTHENTIC_FIT_ARCHIVES=PASS")
 print("F80_ACCEPTED_SCIENTIFIC_ORIGINALS=ZERO")
 print("F80_DREAM_PARETO_POLICY_PROMOTION=DENIED")
