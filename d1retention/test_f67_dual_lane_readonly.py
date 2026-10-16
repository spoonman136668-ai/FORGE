"""F67 dual-lane authentic-scope / missing-first-use refusal contracts."""
import base64
from copy import deepcopy
import datetime
import importlib.util
import json
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location(
 "f67_science",Path(__file__).with_name("f67_dual_lane_readonly.py"))
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
NOW="2026-10-16T07:18:05Z"

def enclosed(doc):
 raw=json.dumps(doc).encode()
 return {"type":"file","encoding":"base64",
         "content":base64.b64encode(raw).decode()}

class Fixtures:
 def __init__(self):
  self.calls=[]
  self.data={}
  for program,repo in m.LANES:
   wing=program=="Wingless"
   main_sha=("a" if wing else "d")*40
   active_sha=("b" if wing else "e")*40
   q_sha=("c" if wing else "f")*40
   branch="research/autonomy-"+program.lower()+"-active"
   run_id=38865063917 if wing else 38863421249
   ts="2026-10-16T07:17:57Z" if wing else "2026-10-16T07:40:45Z"
   self.data[(repo,"/branches/main")]={"commit":{"sha":main_sha}}
   config={"schema":"research.autonomy.v2","program":program,
           "enabled":True,"mode":"repo-local-self-chain","authority":"research-only",
           "ckb_plane_role":"governance-only","active_branch":branch,
           "north_star_sha256":"3"*64,"north_star_path":"research/north-star"}
   state={"schema":"research.repo-local-state.v1","program":program,
          "active_branch":branch,"north_star_sha256":"3"*64,
          "north_star_path":"research/north-star","authority":"research-only",
          "ckb_plane_role":"governance-only","experiment":program+"-EXPERIMENT-01",
          "github_run_id":str(run_id),"qualified_head_sha":q_sha,
          "last_completed_utc":ts}
   self.data[(repo,"/contents/.research-autonomy/config.json?ref="+main_sha)]=enclosed(config)
   self.data[(repo,"/branches/"+branch)]={"commit":{"sha":active_sha}}
   self.data[(repo,"/contents/.research-autonomy/state.json?ref="+active_sha)]=enclosed(state)
   self.data[(repo,"/commits/"+q_sha)]={"sha":q_sha}
   self.data[(repo,"/actions/runs/"+str(run_id))]={
     "id":run_id,"head_sha":main_sha,"head_branch":"main",
     "name":program+" research continuation launcher",
     "status":"completed","conclusion":"success",
     "created_at":"2026-10-16T06:00:00Z",
     "updated_at":"2026-10-16T07:45:00Z"}
   self.data[(repo,"/git/trees/"+active_sha+"?recursive=1")]={
     "truncated":False,
     "tree":[
       {"type":"blob","path":".research-autonomy/evidence/E1-38000000001/summary.json"},
       {"type":"blob","path":".research-autonomy/evidence/E1-38000000001/probe.json"},
       {"type":"blob","path":".research-autonomy/evidence/blocked-38000000002.json"},
       {"type":"blob","path":".research-autonomy/state.json"}]}
   self.data[(repo,"/actions/runs?per_page=100&page=1")]={
      "total_count":200,"workflow_runs":[
        {"id":run_id,"status":"completed","conclusion":"success",
         "name":program+" research continuation launcher"},
        {"id":39000000001,"status":"pending","conclusion":None,
         "name":program+" research original"},
        {"id":39000000002,"status":"completed","conclusion":"failure",
         "name":program+" research original"}]}
 def get(self,repo,route):
  self.calls.append((repo,route))
  if (repo,route) not in self.data:raise m.Blocked("F67_MISSING_API_FIXTURE")
  return deepcopy(self.data[(repo,route)])

class F67Tests(unittest.TestCase):
 def test_two_independent_lanes_and_all_uncertain_runs_remain_no_release(self):
  api=Fixtures()
  d=m.audit(api)
  self.assertEqual(len(d["lanes"]),2)
  self.assertNotEqual(d["lanes"][0]["repository"],d["lanes"][1]["repository"])
  for row in d["lanes"]:
   self.assertTrue(row["last_completed_run_github_confirmed"])
   self.assertEqual(row["research_authority"],"research-only")
   self.assertEqual(row["evidence_inventory"]["versioned_evidence_dossiers_observed"],1)
   self.assertEqual(row["evidence_inventory"]["standalone_blocker_or_exception_evidence_files"],1)
   self.assertFalse(row["all_historical_run_pages_exhausted"])
   self.assertFalse(row["original_science_firstuse_lease_history_complete"])
   self.assertFalse(row["uncertain_scientific_original_attempts_all_resolved"])
   self.assertEqual(row["last_100_github_actions_status_counts"],{
     "completed_failure":1,"completed_success":1,"unresolved_pending":1})
  for key in ("current_owner_epoch_and_research_firstuse_independently_proven",
              "all_active_consumed_uncertain_original_seed_leases_reconciled",
              "cloudflare_atomic_firstuse_deployed","worker_execution_permit_issued",
              "controller_cutover_authorized"):
   self.assertFalse(d[key])
  self.assertEqual(d["new_scientific_originals_dispatched"],0)
  self.assertEqual(len(api.calls),18)

 def test_fake_self_reported_completion_without_actual_github_run_is_denied(self):
  for name,value in (("status","in_progress"),("conclusion","failure"),
                     ("head_sha","f"*40),("head_branch","research/fake"),
                     ("name","someone else"),("id",30000000001)):
   api=Fixtures()
   repo=m.LANES[0][1]
   item=api.data[(repo,"/actions/runs/38865063917")]
   item[name]=value
   with self.subTest(name=name),self.assertRaises(m.Blocked):
    m.audit(api)

 def test_foreign_science_scope_and_forged_source_are_denied(self):
  variants=[
   ("config","authority","all-missions"),
   ("config","enabled",False),
   ("config","ckb_plane_role","new-controller"),
   ("state","active_branch","research/attacker"),
   ("state","qualified_head_sha","wrong"),
   ("state","north_star_sha256","0"*64),
   ("state","last_completed_utc","2035-01-01T00:00:00Z")
  ]
  repo=m.LANES[0][1];a="a"*40;b="b"*40
  for target,key,value in variants:
   api=Fixtures()
   route=("/contents/.research-autonomy/config.json?ref="+a if target=="config"
         else "/contents/.research-autonomy/state.json?ref="+b)
   doc=json.loads(base64.b64decode(api.data[(repo,route)]["content"]))
   doc[key]=value
   api.data[(repo,route)]=enclosed(doc)
   with self.subTest(target=target,key=key),self.assertRaises(m.Blocked):
    m.audit(api)

 def test_live_branch_drift_or_truncated_archive_is_not_accepted(self):
  api=Fixtures();repo=m.LANES[0][1]
  api.data[(repo,"/git/trees/"+("b"*40)+"?recursive=1")]["truncated"]=True
  with self.assertRaises(m.Blocked):m.audit(api)
  api=Fixtures()
  branch=api.data[(repo,"/branches/research/autonomy-wingless-active")]
  # Control-plane HEAD should never change within one census.
  count=[0]
  initial=api.get
  def changing(name,route):
   x=initial(name,route)
   if name==repo and route=="/branches/research/autonomy-wingless-active":
    count[0]+=1
    if count[0]>1:x["commit"]["sha"]="9"*40
   return x
  api.get=changing
  with self.assertRaises(m.Blocked):m.audit(api)

 def test_unknown_actions_status_and_no_evidence_fail_closed(self):
  api=Fixtures();repo=m.LANES[1][1]
  api.data[(repo,"/actions/runs?per_page=100&page=1")]["workflow_runs"][1]["status"]="weird"
  with self.assertRaises(m.Blocked):m.audit(api)
  api=Fixtures();repo=m.LANES[1][1]
  api.data[(repo,"/git/trees/"+("e"*40)+"?recursive=1")]["tree"]=[]
  with self.assertRaises(m.Blocked):m.audit(api)

 def test_blocked_route_cannot_scan_arbitrary_repository(self):
  api=m.GitHubReadonly()
  with self.assertRaises(m.Blocked):api.get("bad-user/repo","/actions/runs")
  with self.assertRaises(m.Blocked):api.get(m.LANES[0][1],"/../../secrets")
  self.assertEqual(api.calls,0)

if __name__=="__main__":
 unittest.main()
