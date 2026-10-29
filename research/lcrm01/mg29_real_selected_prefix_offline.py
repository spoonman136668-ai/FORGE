#!/usr/bin/env python3
"""MG29: true original MG24 historical selected public prefixes -> candidate actions.

Never executes an environment or asks an oracle about an unselected action.
Counterfactual *proposal* outcomes remain unknown. The strong MG28 prior
(action-only beats context+action for next-visible-change prediction) remains.
"""
from __future__ import annotations
import argparse,base64,collections,hashlib,json,math,resource,time
from pathlib import Path

from mg25_original_policy_activation_audit import get_source,inspect,ROLES,SEEDS,FAMILIES,digest
from mg18_native_mission_boundary_audit import WingBridge

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg29_native_original_prefix_prereg.json"
MG24_SHA="e2dda4721d6d96ffd083faac5960013380b29c3325f560defa989c4eef0852a9"
NATIVE=("wingless_MG23","yggdrasil_MG23")
ACTORS=NATIVE+("conventional_full",)
STATUS_W="MG28_NATIVE_OWN_SELECTED_REAL_NEXT_PUBLIC_CHANGE"
STATUS_Y="MG28_LOCAL_OWN_SELECTED_REAL_NEXT_PUBLIC_CHANGE"

def frozen():
    p=json.loads(PREREG.read_text(encoding="utf-8"))
    if (p["schema"]!="itd02.mg29.authentic-original-prefix-native-override-falsification.v1"
        or p["phase"]!="RETROSPECTIVE_EXPOSED_SOURCE_PROSPECTIVE_TO_ANALYTIC_CODE_ONLY"
        or p["historic_archive"]["source_sha256"]!=MG24_SHA
        or p["historic_archive"]["source_selected_actions"]!=9186
        or p["design"]["roles"]!=list(ACTORS)
        or p["parents"]["WINGLESS_MG28"]!="0a7dde659045719763dfadf656fea1be2818d7ab"
        or p["parents"]["YGGDRASIL_MG28"]!="e6f20efd875642421ef8c34ae87c8b1a1e4618a5"):
        raise ValueError("MG29_FROZEN_SOURCE_CONTRACT_CHANGED")
    for forbidden in ("no_new_original_world_reset_or_step","no_source_seed_release",
                      "no_model_parent_update","no_accepted_main_merge",
                      "no_forge_or_ckb_plane_controller_mutation",
                      "no_G29_waiver","no_paid_api","no_heldout_first_use"):
        if p["bounds"][forbidden] is not True:
            raise ValueError("MG29_SOURCE_BOUNDARY_DISABLED:"+forbidden)
    if (p["design"]["signal_threshold"]!={
          "min_count":3,"laplace_changed_probability":0.75,
          "minimum_advantage_over_parent":0.10}
        or p["historic_archive"]["exposed_dev_seeds"]!=[948101,948103,948201,948203,
                                                          948301,948303,948401,948403]):
        raise ValueError("MG29_FROZEN_SIGNAL_CRITERIA_DRIFT")
    return p

def context(before,blind=False,action_only=False):
    if action_only:return "GLOBAL_PER_SELECTED_ACTION"
    front=before["image"][3][5]
    value={"direction":before["direction"],"front":[front[0],front[1],front[2]]}
    if not blind:value["mission"]=before["mission"]
    return digest(value)

class IndependentConventional:
    def __init__(self,mode):
        if mode not in ("full","mission_blind","action_scrambled","outcome_inverted","action_only"):
            raise ValueError("MG29_UNKNOWN_NON_NATIVE_CONTROL")
        self.mode=mode
        self.counts={}
        self.updates=0
    def key(self,b):
        return context(b,self.mode=="mission_blind",self.mode=="action_only")
    def choose(self,b,base):
        row=self.counts.get(self.key(b),[[0,0] for _ in range(7)])
        old=row[base]
        prior=10000*(old[1]+1)//(old[0]+2)
        best=None;high=0
        for action,stat in enumerate(row):
            if stat[0]<3:continue
            value=10000*(stat[1]+1)//(stat[0]+2)
            if value>=7500 and value>=prior+1000 and value>high:
                best=action;high=value
        return base if best is None else best
    def observe(self,b,selected,after):
        if type(selected)is not int or selected not in range(7):
            raise ValueError("MG29_NOT_ORIGINAL_SELECTED_ACTION")
        action=(selected+1)%7 if self.mode=="action_scrambled" else selected
        changed=digest(b)!=digest(after)
        if self.mode=="outcome_inverted":changed=not changed
        key=self.key(b)
        row=self.counts.setdefault(key,[[0,0] for _ in range(7)])
        row[action][0]+=1
        row[action][1]+=int(changed)
        self.updates+=1

def original_events(source):
    s=source["source"]
    rows=s["full_original_selected_source_72_episodes"]
    data={(e["family"],e["dev_seed_exposed"],e["role"]):e for e in rows}
    for fam,seedpair in zip(FAMILIES,SEEDS):
        for role in ACTORS:
            for seed in seedpair:
                if (fam,seed,role) not in data:
                    raise ValueError("MG29_ROLE_OR_COHORT_MISSING")
    return data

def ygg_native():
    from research.native.itd02.mg28.selected_change_cells import SelectedChangeCells
    from research.native.itd02.mg19.original_mission_cells import OriginalMissionAdapter
    return SelectedChangeCells,OriginalMissionAdapter

def native_session(role,first,second,binary,p):
    if role==NATIVE[0]:
        model=WingBridge(binary)
        parent=None
        try:
            yield from replay_first_second(role,first,second,model,None,None,p)
        finally:
            model.close()
    elif role==NATIVE[1]:
        Model,Adapter=ygg_native()
        model=Model(enabled=True)
        yield from replay_first_second(role,first,second,None,model,Adapter,p)
    else:
        raise ValueError("MG29_WRONG_NATIVE_ROLE")

def replay_first_second(role,first,second,go,ygg,Adapter,p):
    controls={name:IndependentConventional(name) for name in
              ("full","mission_blind","action_scrambled","outcome_inverted","action_only")}
    count=0
    for index,row in enumerate((first,second)):
        if go is not None:
            ack=go.request("begin_episode")
            if ack.get("updates")!=count:raise ValueError("MG29_GO_BEGIN_SELECTED_COUNT_DRIFT")
        else:
            adapter=Adapter()
            adapter.reset_public(row["selected_source_events"][0]["before"])
            ygg.start_session(adapter,
                "mg29-authentic-prefix-"+str(row["family"])+"-"+str(row["dev_seed_exposed"]),
                live=True)
        episode={"family":row["family"],"seed_exposed":row["dev_seed_exposed"],"role":role,
                 "original_source_selected_steps":len(row["selected_source_events"]),
                 "native_real_selected_proposal_divergences":0,
                 "native_against_recorded_original_proposals":0,
                 "native_parent_against_recorded_original_proposals":0,
                 "native_supported_override_contexts":0,
                 "independent_matched_control_divergences":collections.Counter(),
                 "authentic_prefix_feedback_events":0}
        for event in row["selected_source_events"]:
            b,n=event["before"],event["after"]
            selected=event["action"]
            if go is not None:
                reply=go.request("choose",before=b)
                candidate=reply.get("action")
                base=reply.get("parent_action")
                status=reply.get("status")
                if not reply.get("ok") or not status:raise ValueError("MG29_GO_ORIGINAL_PROPOSAL_ERROR")
            else:
                parent=ygg.parent.choose(b)
                proposal=ygg.choose(b)
                candidate=proposal.get("action")
                base=parent.get("action")
                status=proposal.get("status")
                if parent.get("external_fallback") or proposal.get("external_fallback"):
                    raise ValueError("MG29_NATIVE_SOURCE_EXTERNAL_ACTION")
            if (type(candidate)is not int or candidate not in range(7)
                or type(base)is not int or base not in range(7)):
                raise ValueError("MG29_NOT_NATIVE_PUBLIC_PROPOSAL")
            override=candidate!=base
            if override and status!=(STATUS_W if go is not None else STATUS_Y):
                raise ValueError("MG29_OVERRIDE_WITHOUT_ACTUAL_NATIVE_SOURCE_SIGNAL")
            episode["native_real_selected_proposal_divergences"]+=int(override)
            episode["native_against_recorded_original_proposals"]+=int(candidate!=selected)
            episode["native_parent_against_recorded_original_proposals"]+=int(base!=selected)
            if override:episode["native_supported_override_contexts"]+=1
            for name,ctrl in controls.items():
                predicted=ctrl.choose(b,base)
                episode["independent_matched_control_divergences"][name]+=int(predicted!=base)
            # Historical selected action is used strictly as training target: never
            # apply reward/consequence of an alternate hypothetical proposal.
            if go is not None:
                go.request("commit",before=b,action=selected)
                receipt=go.request("feedback",before=b,action=selected,after=n,
                    reward=event["reward"],terminal=bool(event["terminated"] or event["truncated"]))
                updated=receipt.get("updates")
            else:
                adapter.submit(selected)
                adapter.complete(n,float(event["reward"]),bool(event["terminated"]),bool(event["truncated"]))
                ygg.learn_selected(adapter,b,n)
                updated=ygg.samples
            count+=1
            if updated!=count:raise ValueError("MG29_NATIVE_ORIGINAL_FEEDBACK_SAMPLE_GAP")
            for ctrl in controls.values():ctrl.observe(b,selected,n)
            if any(c.updates!=count for c in controls.values()):
                raise ValueError("MG29_CONVENTIONAL_EQUAL_PUBLIC_SOURCE_COUNT")
            episode["authentic_prefix_feedback_events"]+=1
        if go is not None:
            snapshot=go.snapshot()
            cold=WingBridge(binary)
            try:
                state=base64.b64encode(snapshot).decode()
                ack=cold.request("load",state=state)
                if ack.get("updates")!=count or cold.snapshot()!=snapshot:
                    raise ValueError("MG29_GO_COLD_ORIGINAL_MEMORY_UNSTABLE")
            finally:cold.close()
            # Do not restart the original continuous source ledger; the same
            # model remains in memory for the subsequent original DEV episode.
        else:
            blob=ygg.checkpoint()
            cold=type(ygg).restore(blob)
            if cold.samples!=count or cold.checkpoint()!=blob:
                raise ValueError("MG29_YGG_COLD_ORIGINAL_MEMORY_UNSTABLE")
        episode["checkpoint_sha256"]=hashlib.sha256(snapshot if go is not None else blob).hexdigest()
        episode["independent_matched_control_divergences"]=dict(episode["independent_matched_control_divergences"])
        yield episode

def conventional_session(first,second):
    controls={name:IndependentConventional(name) for name in
              ("full","mission_blind","action_scrambled","outcome_inverted","action_only")}
    total=0
    for row in (first,second):
        counts=collections.Counter()
        for event in row["selected_source_events"]:
            b,n=event["before"],event["after"]
            base=event["action"] # actual historical conventional action, not invented parent
            for name,control in controls.items():
                counts[name]+=int(control.choose(b,base)!=base)
                control.observe(b,base,n)
            total+=1
        if any(c.updates!=total for c in controls.values()):
            raise ValueError("MG29_CONVENTIONAL_HISTORICAL_SOURCE_DRIFT")
        yield {"family":row["family"],"seed_exposed":row["dev_seed_exposed"],
               "role":"conventional_full",
               "authentic_prefix_feedback_events":len(row["selected_source_events"]),
               "original_source_selected_steps":len(row["selected_source_events"]),
               "independent_matched_control_divergences":dict(counts),
               "observational_baseline_source_action_not_replayed_native":True}

def evaluate(source,binary,p):
    indexed=original_events(source)
    reports=[]
    for fam,seeds in zip(FAMILIES,SEEDS):
        for role in ACTORS:
            pair=indexed[(fam,seeds[0],role)],indexed[(fam,seeds[1],role)]
            if role in NATIVE:
                reports.extend(native_session(role,*pair,binary,p))
            else:
                reports.extend(conventional_session(*pair))
    if len(reports)!=24:
        raise ValueError("MG29_MISSING_NATIVE_CONVENTIONAL_EIGHT_FAMILY_COHORTS")
    summary={}
    for role in NATIVE:
        r=[x for x in reports if x["role"]==role]
        summary[role]={
            "episodes":len(r),
            "original_selected_feedback_events":sum(x["authentic_prefix_feedback_events"] for x in r),
            "enabled_vs_disabled_actual_offline_native_proposal_changes":sum(x["native_real_selected_proposal_divergences"] for x in r),
            "no_signal_parent_vs_actual_historical_source_policy_mismatch":sum(x["native_parent_against_recorded_original_proposals"] for x in r),
            "enabled_vs_actual_historical_source_policy_mismatch":sum(x["native_against_recorded_original_proposals"] for x in r),
            "conventional_ablation_proposals_vs_same_parent":{
                name:sum(x["independent_matched_control_divergences"][name] for x in r)
                for name in ("full","mission_blind","action_scrambled","outcome_inverted","action_only")}
        }
    overall=sum(summary[r]["enabled_vs_disabled_actual_offline_native_proposal_changes"] for r in NATIVE)
    classification=("MG29_AUTHENTIC_SOURCE_OFFLINE_NATIVE_OVERRIDE_OBSERVED__NO_CAUSAL_SCIENCE"
                    if overall else
                    "MG29_AUTHENTIC_SOURCE_NATIVE_MG28_DID_NOT_OVERRIDE_ANY_OFFLINE_ACTION__NO_SCIENCE")
    return {"schema":"itd02.mg29.original-source-prefix-native-action-falsification.v1",
            "classification":classification,
            "native_original_model_heads":{"wingless":"0a7dde659045719763dfadf656fea1be2818d7ab",
                                           "yggdrasil":"e6f20efd875642421ef8c34ae87c8b1a1e4618a5"},
            "original_source_selected_72_full_episodes_verified":72,
            "original_source_selected_actions_verified":9186,
            "original_selected_replay_rows":reports,
            "per_native_actual_source_prefix_summary":summary,
            "original_world_actions_executed":0,
            "hypothetical_action_outcomes_known":False,
            "scientific_first_use":False,
            "native_models_promoted":False,
            "forge_controller_or_main_edited":False}

def main():
    args=argparse.ArgumentParser()
    for flag in ("first","second","go_binary","output"):
        args.add_argument("--"+flag,type=Path,required=True)
    o=args.parse_args()
    p=frozen()
    # Authenticate all 72 source-original trajectories FIRST. Source has already
    # been exposed; this is NOT a sealed evaluation or new environment run.
    first=get_source(o.first)
    second=get_source(o.second)
    if first["source"]!=second["source"]:
        raise ValueError("MG29_INDEPENDENT_ORIGINAL_PROCESSES_SOURCE_TRACE_MISMATCH")
    verify=inspect(first)
    if verify is None:
        raise ValueError("MG29_COMPLETE_MG25_AUTHENTICATION_UNAVAILABLE")
    result=evaluate(first,o.go_binary,p)
    out={"schema":"itd02.mg29.authentic-source-prefix-comparison-receipt.v1",
         "original_source_sha256":MG24_SHA,
         "result":result,
         "cold_source_input_preregistered":True,
         "original_source_first_use":False}
    out["canonical_reproducible_receipt_sha256"]=digest(out)
    o.output.parent.mkdir(parents=True,exist_ok=True)
    o.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("MG29_ORIGINAL_PREFIX_NATIVE_SOURCE_RESULT",result["classification"])
    print("MG29_ORIGINAL_PREFIX_NATIVE_SOURCE_SUMMARY",json.dumps(result["per_native_actual_source_prefix_summary"],sort_keys=True))
    print("MG29_CANONICAL_TWO_PROCESS_ORIGINAL_SOURCE_DIGEST",out["canonical_reproducible_receipt_sha256"])
if __name__=="__main__":
    main()
