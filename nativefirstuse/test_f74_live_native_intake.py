"""Adversarial F74 native two-lane live science-source test fixtures."""
import importlib.util
from pathlib import Path
from unittest.mock import patch
import unittest
p=Path(__file__).with_name("f74_live_native_intake.py")
spec=importlib.util.spec_from_file_location("f74_native_intake",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def fixed():
 configs={}; states={}; data={}
 for lane,repo in m.LANES:
  main=("a" if lane=="Wingless" else "c")*40
  live=("b" if lane=="Wingless" else "d")*40
  branch="research/autonomy-"+lane.lower()+"-active"
  configs[repo]={"schema":"research.autonomy.v2","program":lane,
   "enabled":True,"mode":"repo-local-self-chain",
   "authority":"research-only","ckb_plane_role":"governance-only",
   "active_branch":branch,"north_star_sha256":"1"*64}
  states[repo]={"schema":"research.repo-local-state.v1",
   "program":lane,"active_branch":branch,"north_star_sha256":"1"*64,
   "authority":"research-only","ckb_plane_role":"governance-only",
   "experiment":"R-VALID-01","github_run_id":"38800000100"}
  data[(repo,"/branches/main")]={"commit":{"sha":main}}
  data[(repo,"/branches/"+branch)]={"commit":{"sha":live}}
  data[(repo,"/actions/runs/38800000100")]={
   "id":38800000100,"name":lane+" research continuation launcher",
   "status":"completed","conclusion":"success","head_sha":main,
   "head_branch":"main","run_attempt":1}
 def gh(repo,path):
  return data[(repo,path)]
 def d(repo,sha,path):
  return configs[repo] if path.endswith("config.json") else states[repo]
 return configs,states,data,gh,d

class F74(unittest.TestCase):
 def work(self,edit=lambda c,s,r:None):
  cfg,states,api,get,doc=fixed();edit(cfg,states,api)
  with patch.object(m,"get",side_effect=get),patch.object(m,"doc",side_effect=doc):
   return m.audit()
 def test_synthetic_correspondence_still_denies_science(self):
  d=self.work()
  self.assertEqual(len(d["lanes"]),2)
  self.assertEqual({x["lane"] for x in d["lanes"]},{"Wingless","Yggdrasil"})
  self.assertTrue(all(x["repo_local_research_workflow_confirmed"] for x in d["lanes"]))
  for row in d["lanes"]:
   self.assertFalse(row["full_original_seed_lease_ledger_independently_observed"])
   self.assertFalse(row["current_scientific_owner_independently_authorized"])
   self.assertFalse(row["prospective_original_firstuse_available"])
  self.assertFalse(d["private_rbackup_restoration_qualified"])
  self.assertFalse(d["native_worker_execution_permit_issued"])
  self.assertEqual(d["new_protected_originals_dispatched"],0)
 def test_forged_current_owner_or_wrong_research_scope_is_denied(self):
  for key,value in [
   ("enabled",False),("authority","cloudflare-firstuse-authority"),
   ("mode","FORGE-research-owner"),
   ("program","Yggdrasil"),("schema","untrusted")]:
   def edit(c,s,r,key=key,value=value):
    c[m.LANES[0][1]][key]=value
   with self.subTest(key=key),self.assertRaises(m.Denied):self.work(edit)
 def test_mismatched_repository_run_source_fails_closed(self):
  def edit(c,s,r):
   repo=m.LANES[1][1]
   r[(repo,"/actions/runs/38800000100")]["head_sha"]="f"*40
  with self.assertRaises(KeyError):self.work(edit)
 def test_ancestor_is_history_without_granting_current_continuity(self):
  def edit(c,s,r):
   repo=m.LANES[1][1];old="e"*40;current="c"*40
   r[(repo,"/actions/runs/38800000100")]["head_sha"]=old
   s[repo]["classification"]="preregistered-blocked"
   r[(repo,"/compare/"+old+"..."+current)]={"status":"ahead",
    "base_commit":{"sha":old},"merge_base_commit":{"sha":old},
    "ahead_by":21,"behind_by":0}
  result=self.work(edit);row=result["lanes"][1]
  self.assertEqual(row["last_continuation_source_sha"],"e"*40)
  self.assertFalse(row["historical_run_is_current_main"])
  self.assertEqual(row["reported_classification"],"preregistered-blocked")
  self.assertFalse(row["current_research_continuity_verified"])
  self.assertFalse(result["current_research_continuity_verified"])
 def test_diverged_missing_or_forged_ancestry_is_rejected(self):
  for field,value in [("status","diverged"),("ahead_by",0),
     ("ahead_by",True),("behind_by",1),("base_commit",{"sha":"a"*40}),
     ("merge_base_commit",{"sha":"a"*40})]:
   def edit(c,s,r,field=field,value=value):
    repo=m.LANES[1][1];old="e"*40
    r[(repo,"/actions/runs/38800000100")]["head_sha"]=old
    proof={"status":"ahead","base_commit":{"sha":old},
      "merge_base_commit":{"sha":old},"ahead_by":21,"behind_by":0}
    proof[field]=value;r[(repo,"/compare/"+old+"..."+"c"*40)]=proof
   with self.subTest(field=field),self.assertRaises(m.Denied):self.work(edit)
 def test_rerun_foreign_branch_or_unsuccessful_history_is_rejected(self):
  for field,value in [("run_attempt",2),("head_branch","other"),
      ("conclusion","failure"),("status","in_progress"),("head_sha","bad")]:
   def edit(c,s,r,field=field,value=value):
    r[(m.LANES[0][1],"/actions/runs/38800000100")][field]=value
   with self.subTest(field=field),self.assertRaises(m.Denied):self.work(edit)
 def test_legacy_role_is_not_execution_authority(self):
  def edit(c,s,r):
   for repo in c:
    c[repo].pop("ckb_plane_role");s[repo].pop("ckb_plane_role")
  self.assertFalse(self.work(edit)["native_worker_execution_permit_issued"])
 def test_main_or_active_branch_moving_during_read_is_rejected(self):
  for branch in ("/branches/main","/branches/research/autonomy-wingless-active"):
   c,s,r,get,doc=fixed();counts={}
   def moving(repo,path):
    counts[(repo,path)]=counts.get((repo,path),0)+1
    if repo==m.LANES[0][1] and path==branch and counts[(repo,path)]==2:
     return {"commit":{"sha":"f"*40}}
    return get(repo,path)
   with self.subTest(branch=branch),patch.object(m,"get",side_effect=moving),patch.object(m,"doc",side_effect=doc),self.assertRaises(m.Denied):m.audit()
 def test_state_claim_cannot_skip_owner_or_history(self):
  for field,value in [("authority","owner-signed"),
                      ("north_star_sha256","f"*64),
                      ("active_branch","research/fake"),
                      ("program","Wingless")]:
   def edit(c,s,r,field=field,value=value):
    s[m.LANES[1][1]][field]=value
   with self.subTest(field=field),self.assertRaises(m.Denied):self.work(edit)
 def test_unrecognized_egress_route_denied(self):
  with self.assertRaises(m.Denied):m.get("attacker/foreign","/branches/main")
  with self.assertRaises(m.Denied):m.get(m.LANES[0][1],"/../secret")
  for route in ("/compare/"+"a"*40+"...evil", "//foreign/path", "/branches/main#bad"):
   with self.assertRaises(m.Denied):m.get(m.LANES[0][1],route)
 def test_compare_metadata_has_finite_route_specific_response_budget(self):
  repo=m.LANES[0][1];route="/compare/"+"a"*40+"..."+"b"*40
  class Response:
   status=200
   def __init__(self,path,size):self.url=m.API+repo+path;self.size=size
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self,limit):return (b'{"padding":"'+b'x'*self.size+b'"}')[:limit]
  with patch.object(m.urllib.request,"urlopen",return_value=Response(route,200000)):
   self.assertEqual(len(m.get(repo,route)["padding"]),200000)
  for path,size in [(route,600001),("/branches/main",200000)]:
   with self.subTest(path=path),patch.object(m.urllib.request,"urlopen",return_value=Response(path,size)),self.assertRaises(m.Denied):m.get(repo,path)
if __name__=="__main__":unittest.main()
