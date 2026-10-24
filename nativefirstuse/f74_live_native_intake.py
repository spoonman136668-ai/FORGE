"""F74: non-authorizing live source readback from both existing research lanes.

No first-use claims, Cloudflare writes, owner migration or dispatch. Public
repo-local continuation reports cannot independently attest all original
first-use seed leases or a protected scientific-owner release.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import base64

SCHEMA="forge.f74.real-two-lane-native-intake.readonly.v1"
API="https://api.github.com/repos/"
LANES=(("Wingless","spoonman136668-ai/Wingless"),("Yggdrasil","spoonman136668-ai/Yggdrasil"))
HEX40=re.compile("^[0-9a-f]{40}$")
class Denied(ValueError):pass

def need(ok,msg):
 if not ok:raise Denied("F74_"+msg)
def get(repo,path):
 need(repo in [r for _,r in LANES] and path.startswith("/") and ".." not in path,
      "ROUTE_UNSAFE")
 url=API+repo+path
 headers={"Accept":"application/vnd.github+json","User-Agent":"FORGE-F74-NATIVE-SCIENCE-SOURCE-READONLY"}
 token=os.environ.get("GH_TOKEN","")
 if token:headers["Authorization"]="Bearer "+token
 req=urllib.request.Request(url,headers=headers,method="GET")
 with urllib.request.urlopen(req,timeout=18) as r:
  need(r.status==200 and r.url==url,"GITHUB_HTTP_UNTRUSTED")
  raw=r.read(131073)
 need(0<len(raw)<=131072,"GITHUB_RESPONSE_TOO_LARGE")
 return json.loads(raw)
def doc(repo,sha,path):
 need(bool(HEX40.fullmatch(sha)),"SOURCE_SHA_INVALID")
 item=get(repo,"/contents/"+path+"?ref="+sha)
 need(item.get("type")=="file" and item.get("encoding")=="base64" and
      isinstance(item.get("content"),str),"SOURCE_FILE_INVALID")
 raw=base64.b64decode(item["content"],validate=False)
 need(0<len(raw)<=65536,"SOURCE_DOC_UNBOUNDED")
 obj=json.loads(raw)
 need(isinstance(obj,dict),"SOURCE_DOC_INVALID")
 return obj
def run_head_is_ancestor(repo,main_sha,run_sha):
 """Only a real prior main-line ancestor can authenticate a historical run."""
 need(bool(HEX40.fullmatch(run_sha)),"RUN_HEAD_SHA_INVALID")
 pending=[main_sha]
 seen=set()
 while pending:
  need(len(seen)<64,"RUN_ANCESTRY_BOUND_EXCEEDED")
  sha=pending.pop()
  if sha==run_sha:return True
  if sha in seen:continue
  seen.add(sha)
  commit=get(repo,"/git/commits/"+sha)
  parents=commit.get("parents")
  need(commit.get("sha")==sha and isinstance(parents,list) and
       len(parents)<=2 and all(isinstance(p,dict) and
       isinstance(p.get("sha"),str) and HEX40.fullmatch(p["sha"]) for p in parents),
       "RUN_ANCESTRY_UNTRUSTED")
  pending.extend(p["sha"] for p in reversed(parents) if p["sha"] not in seen)
 raise Denied("F74_RUN_HEAD_NOT_ANCESTOR_OF_CURRENT_MAIN")

def audit():
 summary=[]
 for name,repo in LANES:
  m=get(repo,"/branches/main")
  sha=m.get("commit",{}).get("sha")
  need(isinstance(sha,str) and HEX40.fullmatch(sha),"MAIN_SHA_INVALID")
  cfg=doc(repo,sha,".research-autonomy/config.json")
  need(cfg.get("schema")=="research.autonomy.v2" and
       cfg.get("program")==name and cfg.get("enabled") is True and
       cfg.get("mode")=="repo-local-self-chain" and
       cfg.get("authority")=="research-only" and
       cfg.get("ckb_plane_role")=="governance-only","RESEARCH_AUTHORITY_DRIFT")
  active=cfg.get("active_branch")
  need(isinstance(active,str) and active.startswith("research/autonomy-")
       and len(active)<140 and re.fullmatch("[a-z0-9/_-]+",active),
       "ACTIVE_BRANCH_INVALID")
  b=get(repo,"/branches/"+urllib.parse.quote(active,safe="/"))
  active_sha=b.get("commit",{}).get("sha")
  need(isinstance(active_sha,str) and HEX40.fullmatch(active_sha),"ACTIVE_SHA_INVALID")
  state=doc(repo,active_sha,".research-autonomy/state.json")
  need(state.get("schema")=="research.repo-local-state.v1" and
       state.get("program")==name and state.get("active_branch")==active and
       state.get("north_star_sha256")==cfg.get("north_star_sha256") and
       state.get("authority")=="research-only" and
       state.get("ckb_plane_role")=="governance-only" and
       isinstance(state.get("experiment"),str) and
       len(state["experiment"])<=200,
       "RESEARCH_STATE_NOT_PINNED")
  last_id=int(state.get("github_run_id",0))
  need(last_id>0,"LAST_RUN_NOT_IDENTIFIED")
  run=get(repo,"/actions/runs/"+str(last_id))
  need(run.get("id")==last_id and run.get("name")==name+" research continuation launcher" and
       run.get("status")=="completed" and run.get("conclusion")=="success" and
       run.get("head_branch")=="main" and
       isinstance(run.get("head_sha"),str) and
       HEX40.fullmatch(run["head_sha"]),"RESEARCH_RUN_SOURCE_UNCONFIRMED")
  run_head_is_ancestor(repo,sha,run["head_sha"])
  again=get(repo,"/branches/"+urllib.parse.quote(active,safe="/"))
  need(again.get("commit",{}).get("sha")==active_sha,"SOURCE_MOVED_DURING_READ")
  summary.append({
   "lane":name,"repository":repo,"main_sha":sha,"active_research_head":active_sha,
   "reported_last_completed_experiment":state["experiment"],
   "last_continuation_run_confirmed":last_id,
   "last_continuation_source_sha":run["head_sha"],
   "last_run_head_ancestor_of_current_main":True,
   "repo_local_research_workflow_confirmed":True,
   "full_original_seed_lease_ledger_independently_observed":False,
   "current_scientific_owner_independently_authorized":False,
   "prospective_original_firstuse_available":False,
  })
 return {
  "schema":SCHEMA,"lanes":summary,
  "private_rbackup_restoration_qualified":False,
  "cloudflare_time_travel_only_is_independent_backup":False,
  "atomic_live_original_firstuse_claim_qualified":False,
  "native_worker_execution_permit_issued":False,
  "new_protected_originals_dispatched":0,
  "disposition":"LIVE_BOTH_LANES_READONLY_CONFIRMED_NO_AUTHORITATIVE_ORIGINAL_START",
 }
if __name__=="__main__":
 try:
  print(json.dumps(audit(),separators=(",",":"),sort_keys=True))
  print("F74_FORGE_NATIVE_PROTECTED_ORIGINAL=DENIED")
 except (Denied,ValueError,KeyError,TypeError,OSError) as exc:
  print("F74_LIVE_SOURCE_READBACK=BLOCKED",file=sys.stderr)
  raise SystemExit(1)
