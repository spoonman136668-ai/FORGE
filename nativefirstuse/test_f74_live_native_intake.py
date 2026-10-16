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
   "status":"completed","conclusion":"success","head_sha":main}
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
   ("mode","FORGE-research-owner"),("ckb_plane_role","science-controller"),
   ("program","Yggdrasil"),("schema","untrusted")]:
   def edit(c,s,r,key=key,value=value):
    c[m.LANES[0][1]][key]=value
   with self.subTest(key=key),self.assertRaises(m.Denied):self.work(edit)
 def test_mismatched_repository_run_source_fails_closed(self):
  def edit(c,s,r):
   repo=m.LANES[1][1]
   r[(repo,"/actions/runs/38800000100")]["head_sha"]="f"*40
  with self.assertRaises(m.Denied):self.work(edit)
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
if __name__=="__main__":unittest.main()
