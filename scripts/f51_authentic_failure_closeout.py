"""F51 exact-source science qualification failure intake. No experiment dispatch.

This read-only audit uses source-control manifests and the *failed* first-attempt
GitHub Actions runs; it never changes preregistration, promotes science, replays
the consumed TRAIN cohort, or invokes a research optimizer.
"""
import argparse,ast,hashlib,json,pathlib
EXPECTED={
 "Wingless":{"head":"38aa2b6a6bb879a76301bf290d576b81e18b8236",
   "run":38812785715,"pr":259,"prereg_commit":"6d28b6e6850aa5120d2f24f023be69326b261a3a",
   "source_path":"research/foundational/20261015-w-f51/source_pilot.py",
   "prereg_path":"research/foundational/20261015-w-f51/prereg.json",
   "registered_oracle":"private_sign_oracle_UNFAIR",
   "executed_oracle":"private_operator_oracle_unfair"},
 "Yggdrasil":{"head":"49a604b410982391f8f48f1a1c56906eee7d322b",
   "run":38812939418,"pr":253,"prereg_commit":"ab72c07892241b3d9d30a098bd6027452150807d",
   "source_path":"research/foundational/20261015-y-f51/source_pilot.py",
   "prereg_path":"research/foundational/20261015-y-f51/prereg.json",
   "audit_path":"research/foundational/20261015-y-f51/audit_result.py",
   "registered_oracle":"private_future_query_oracle_UNFAIR",
   "executed_oracle":"private_future_query_oracle_unfair"}}
class Blocked(ValueError):pass
def need(v,msg):
 if not v:raise Blocked("F51_"+msg)
def unique(pairs):
 d={}
 for k,v in pairs:
  need(k not in d,"DUPLICATE_JSON_KEY");d[k]=v
 return d
def read_json(path):
 raw=pathlib.Path(path).read_bytes()
 need(0<len(raw)<120000,"SOURCE_SIZE")
 return json.loads(raw,object_pairs_hook=unique)
def read_arms(source):
 tree=ast.parse(pathlib.Path(source).read_text())
 assignment=next((node for node in tree.body if isinstance(node,ast.Assign)
   and any(isinstance(t,ast.Name) and t.id=="ARMS" for t in node.targets)),None)
 need(assignment is not None,"ARMS_DECLARATION")
 arms=list(ast.literal_eval(assignment.value))
 need(len(arms)==len(set(arms)),"DUPLICATE_ARMS")
 return arms
def review(root):
 root=pathlib.Path(root)
 decisions=[]
 for lane,ids in EXPECTED.items():
  sub=root/lane
  run=read_json(sub/"run.json")
  need(run.get("id")==ids["run"] and run.get("head_sha")==ids["head"]
      and run.get("run_attempt")==1 and run.get("status")=="completed"
      and run.get("conclusion")=="failure","ACTUAL_FAILED_RUN_"+lane)
  p=read_json(sub/"prereg.json")
  arms=read_arms(sub/"source_pilot.py")
  key="frozen_controls" if lane=="Wingless" else "controls"
  frozen=p[key]
  need(type(frozen) is list and len(frozen)==len(set(frozen)),"PREREG_CONTROLS_"+lane)
  need(ids["registered_oracle"] in frozen
       and ids["executed_oracle"] in arms
       and ids["registered_oracle"] not in arms
       and ids["executed_oracle"] not in frozen,"ORACLE_CONTROL_DRIFT_"+lane)
  need(set(frozen)-{ids["registered_oracle"]} ==
       set(arms)-{ids["executed_oracle"]},
       "OTHER_CONTROL_DRIFT_"+lane)
  need(set(frozen)!=set(arms),"FROZEN_ARM_SET_MATCH_UNEXPECTED_"+lane)
  prereg_sha=hashlib.sha256((sub/"prereg.json").read_bytes()).hexdigest()
  audit_syntax_bad=False
  if lane=="Yggdrasil":
   src=(sub/"audit_result.py").read_text()
   try: compile(src,"frozen_y_f51_audit_result.py","exec")
   except SyntaxError: audit_syntax_bad=True
   need(audit_syntax_bad and
      "assert set(d['scores'])==set(arms)\\n" in src,
      "ORIGINAL_Y_AUDIT_SYNTAX_WITNESS")
  decisions.append({"lane":lane,"source_commit":ids["head"],"pr_number":ids["pr"],
    "failed_run":ids["run"],"original_run_conclusion":"failure",
    "prereg_source_sha256":prereg_sha,"frozen_controls":frozen,
    "implemented_controls":arms,"control_identity_exact_match":False,
    "original_audit_syntax_bad":audit_syntax_bad,
    "scientific_source_qualified":False,
    "reason":"FROZEN_CONTROL_IDENTITY_MISMATCH"+
       ("_AND_AUDIT_SYNTAX_ERROR" if audit_syntax_bad else ""),
    "next_step":"NEW_FRESH_PRECODE_AND_DISJOINT_COHORT_NOT_REPLAY"})
 return {"schema":"forge.f51.frozen-first-use-failure-closeout.v1",
   "decisions":decisions,"prior_failed_research_runs_preserved":True,
   "new_experiments_executed":0,"primary_original_executed":False,
   "scientific_accepted_ref_mutation":False,
   "optimizer_training_or_promotion_authorized":False,
   "automatic_science_dispatch_authorized":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",required=True);p.add_argument("--out",required=True)
 a=p.parse_args()
 pathlib.Path(a.out).write_text(json.dumps(review(a.root),sort_keys=True,separators=(",",":"))+"\n")
if __name__=="__main__":main()
