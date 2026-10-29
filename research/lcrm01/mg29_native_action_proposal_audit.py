#!/usr/bin/env python3
"""MG29 read-only authentic-prefix falsification: no off-policy action outcome."""
from __future__ import annotations
import argparse,collections,json
from pathlib import Path

from mg25_original_policy_activation_audit import (
 get_source,inspect as authenticate,FAMILIES,SEEDS,digest
)
from mg29_policy_proposal_proxy import Prefix

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg29_native_policy_proposal_prereg.json"
SOURCE="e2dda4721d6d96ffd083faac5960013380b29c3325f560defa989c4eef0852a9"
PARENT="5927496d5f6e02c2cbff1974912f03aa2b2a245c"
ROLES=("wingless_MG23","yggdrasil_MG23","conventional_full")


def preflight():
 p=json.loads(FROZEN.read_text(encoding="utf-8"))
 x=p["immutable_original"];m=p["diagnostic"];f=p["fences"]
 if (p["schema"]!="itd02.mg29.retrospective-native-mg28-public-change-policy-proposal-v1" or
     p["phase"]!="FROZEN_BEFORE_EXECUTABLE_RETROSPECTIVE_ONLY_EXPOSED_DEV_NOT_FIRST_USE" or
     x["MG24_original_selected_action_sha256"]!=SOURCE or
     x["selected_actions"]!=9186 or x["episodes"]!=72 or
     x["MG24_origin_run"]!=40874118161 or
     x["roles"]!=list(ROLES) or
     p["frozen_parent"]["MG28_strong_falsification"]!=PARENT or
     p["frozen_parent"]["Wingless_original_MG28_blob"]!="751f95e1ef29cee2870cbaf5e78b8170867f8af2" or
     p["frozen_parent"]["Yggdrasil_original_MG28_blob"]!="2c30ca4da6f6603ecc5ec36b1f460a246b120d89" or
     m["candidate_rule"]["same_context_action_min_prior"]!=3 or
     m["candidate_rule"]["laplace_score_min_basis_points"]!=7500 or
     m["candidate_rule"]["margin_vs_original_selected_action_basis_points"]!=1000 or
     m["matched_action_only"]["same_min_prior"]!=3 or
     m["matched_action_only"]["same_laplace_threshold"]!=7500 or
     m["matched_action_only"]["same_margin_against_actual_original_action"]!=1000 or
     not m["context_aware_action_control_required"] or
     not all(f.values())):
  raise ValueError("MG29_FROZEN_PROSPECTIVE_TO_RETROSPECTIVE_METHOD_DRIFT")
 return p


def event_validation(row,event,expected_index,previous):
 if (event["index"]!=expected_index or
     event["before"]["mission"]!=row["original_mission"] or
     event["after"]["mission"]!=row["original_mission"] or
     event["before_sha256"]!=digest(event["before"]) or
     event["after_sha256"]!=digest(event["after"]) or
     previous is not None and event["before_sha256"]!=previous or
     type(event["public_mission_target_pickup"])is not bool or
     type(event["public_locked_door_open"])is not bool):
  raise ValueError("MG29_SELECTED_ORIGINAL_PUBLIC_EVENT_TAMPER")
 return event["before_sha256"]!=event["after_sha256"]


def execute(first,second):
 preflight()
 a=get_source(first);b=get_source(second)
 if a["canonical_source_sha256"]!=SOURCE or b["canonical_source_sha256"]!=SOURCE or a["source"]!=b["source"]:
  raise ValueError("MG29_IMMUTABLE_TWO_SOURCE_PROCESS_DIFFER")
 authenticate(a);authenticate(b)
 rows=a["source"]["full_original_selected_source_72_episodes"]
 indexed={(r["family"],r["dev_seed_exposed"],r["role"]):r for r in rows}
 if len(rows)!=72 or len(indexed)!=72:
  raise ValueError("MG29_NOT_ORIGINAL_COMPLETE_EPISODE_MATRIX")
 reports={}
 total=collections.Counter()
 first_evidence=[]
 for role in ROLES:
  for family,seeds in zip(FAMILIES,SEEDS):
   memory=Prefix();result=collections.Counter();per_seed=[]
   for seed in seeds:
    source=indexed[(family,seed,role)]
    last=None
    for i,e in enumerate(source["selected_source_events"],1):
     changed=event_validation(source,e,i,last)
     before=e["before"];actual=e["action"]
     # Score using strictly EARLIER actor+family original source events.
     proposal=memory.before(before,actual)
     target=e["public_mission_target_pickup"]
     door=e["public_locked_door_open"]
     result["selected_steps"]+=1
     result["original_public_changed"]+=int(changed)
     result["real_target_public_effects"]+=int(target)
     result["real_locked_door_open_effects"]+=int(door)
     result["real_terminal_positive"]+=int(e["terminated"] and e["reward"]>0)
     action_only=proposal["action_only_proposal"]
     full=proposal["full_proposal"]
     if full is not None:
      result["full_proxy_eligible_divergence"]+=1
      result["full_proxy_prior_task_relevant_effects"]+=int(proposal["full_prior_task_effects"]>0)
      result["full_proxy_no_prior_task_effects"]+=int(proposal["full_prior_task_effects"]==0)
      result["full_only_disagreement_vs_action_only"]+=int(action_only is None or action_only!=full)
      result["both_same_proposed_action"]+=int(action_only==full)
      if len(first_evidence)<12:
       first_evidence.append({"role":role,"family":family,"seed_already_exposed":seed,
        "source_decision_index":i,"original_action":actual,"proxy_full_alternate":full,
        "proxy_action_only_alternate":action_only,"prior_full_source_count":proposal["full_support"],
        "prior_task_relevant_original_selected_events":proposal["full_prior_task_effects"],
        "before_original_source_sha256":e["before_sha256"]})
     if action_only is not None:
      result["action_only_proxy_eligible_divergence"]+=1
     memory.after(before,actual,changed,target,door)
     last=e["after_sha256"]
    per_seed.append({"seed_already_exposed":seed,"actual_original_source_steps":i})
   if memory.events!=result["selected_steps"] or memory.events>4096:
    raise ValueError("MG29_SOURCE_PREFIX_EVENT_CONSERVATION")
   result["source_history_relevant_effects"]=memory.task_relevant_events
   reports[family+"|"+role]={"counts":dict(sorted(result.items())),"episodes":per_seed}
   total.update(result)
 if (sum(v["counts"]["selected_steps"] for v in reports.values())>9186 or len(reports)!=12):
  raise ValueError("MG29_AUTHENTIC_SELECTED_SOURCE_ROLE_COHORT_MISSING")
 # Negative previously precommitted: full-context next-change Brier worse than
 # same-event action-only. This analysis may measure coverage, not override it.
 result={"schema":"itd02.mg29.authentic-historical-native-policy-proposal-coverage.v1",
  "classification":"RETROSPECTIVE_PROXY_ONLY_NO_NATIVE_ACTION_EXECUTION_NO_SCIENCE",
  "original_source_sha256":SOURCE,
  "source_episodes_authenticated":72,"source_actions_authenticated":9186,
  "analyzed_actor_family_sequences":12,"analyzed_actor_episodes":24,
  "original_two_process_source_identical":True,
  "mg28_previous_full_context_action_brier":"0.1023041387",
  "mg28_previous_action_only_brier":"0.0711625756",
  "mg28_stronger_control_negative":True,
  "MG28_optin_authorized_for_new_source_world":False,
  "totals":dict(sorted(total.items())),
  "by_original_role_family":reports,
  "example_proxy_decisions_not_executed":first_evidence,
  "caveat":"Proposed alternates are offline one-step counterfactual PROPOSALS only. Actual original source consequences belong solely to actually selected MG23 actions. NO source goal improvement or model causal credit can be inferred.",
  "new_original_source_actions":0,"new_native_model_or_controller_changes":0,
  "scientific_first_use":False}
 result["sha256"]=digest(result)
 return result


def compare(first,second):
 a=json.loads(Path(first).read_text(encoding="utf-8"))
 b=json.loads(Path(second).read_text(encoding="utf-8"))
 if (a!=b or a["sha256"]!=digest({k:v for k,v in a.items() if k!="sha256"}) or
     a["source_actions_authenticated"]!=9186 or a["new_original_source_actions"]!=0 or
     a["MG28_optin_authorized_for_new_source_world"]is not False):
  raise ValueError("MG29_INDEPENDENT_CROSS_HOST_AUTHENTIC_SOURCE_FALSIFICATION_DRIFT")
 print("MG29_CROSS_HOST_READ_ONLY_NATIVE_PROPOSAL_COVERAGE_PASS_NOT_SCIENCE "+a["sha256"])


def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--first",type=Path)
 parser.add_argument("--second",type=Path)
 parser.add_argument("--output",type=Path)
 parser.add_argument("--compare",nargs=2,type=Path)
 args=parser.parse_args()
 if args.compare:
  compare(*args.compare);return
 if not (args.first and args.second and args.output):
  parser.error("require authentic --first --second --output")
 result=execute(args.first,args.second)
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
 print("MG29_AUTHENTIC_ACTOR_SOURCE_PREFIX_EXAMINED_NO_OFFPOLICY_REWARD "+result["sha256"])
 print("MG29_STRONG_ACTION_ONLY_CONTROL_AND_PROXY_COVERAGE "+json.dumps(result["totals"],sort_keys=True))
if __name__=="__main__":main()
