#!/usr/bin/env python3
"""K4W retrospective causal-information attribution; FIT-only, no simulator."""
import argparse,collections,hashlib,importlib,json,math,sys,tempfile
from pathlib import Path
import zipfile
from k4v_fit_replay import source_bytes
HERE=Path(__file__).resolve().parent
P=HERE/"k4w_frozen_credit_attribution.json"
def digest(x):return hashlib.sha256(x).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def check(cond,why):
    if not cond:raise RuntimeError("K4W_"+why)
def load(archive,protocol):
    raw=archive.read_bytes()
    pin=protocol["historic_source"]
    check(digest(raw)==pin["zip_sha256"],"ZIP_SHA_DRIFT")
    with zipfile.ZipFile(archive) as z:
        check(set(pin["member_sha256"]).issubset(z.namelist()),"MISSING_ARCHIVE_MEMBER")
        evidence={}
        for name,sha in pin["member_sha256"].items():
            member=z.read(name)
            check(digest(member)==sha,"MEMBER_DRIFT_"+name)
            evidence[name]=json.loads(member)
    check(evidence["comparison.json"]["science_identical"] is True and
          evidence["comparison.json"]["result"]=="NO_REPEATABLE_NATIVE_MINIGRID_TRANSFER_ADVANCEMENT",
          "ORIGINAL_NEGATIVE_NOT_PRESERVED")
    a,b=evidence["process-a.json"],evidence["process-b.json"]
    for x in (a,b):
        check(x["gate"]=="LCRM01-K4U" and x["scientific_accepted"] is False
              and x["scientific_first_use"] is False
              and x["FIT_episodes"]==48 and x["FIT_public_experience_count"]==6114
              and x["source_commit"]=="7f5853792ea7f04f75614661006d87fcf949f26d"
              and x["native_Yggdrasil_commit"]==protocol["native_ygg"]["commit"]
              and x["native_FIT_checks"]["yggdrasil_checkpoint_sha256"]==protocol["native_ygg"]["expected_original_FIT_checkpoint_sha256"],
              "ORIGINAL_IDENTITY_OR_SCIENCE_DRIFT")
    check(canon(a["FIT_public_experiences"])==canon(b["FIT_public_experiences"]),
          "TWO_ORIGINAL_FIT_STREAMS_DIVERGE")
    return a["FIT_public_experiences"],a["native_FIT_checks"]

def discrete_counts(rows):
    stats={}
    for family in ("empty","fourrooms"):
        entries=[x for x in rows if x["family"]==family]
        per_action={}
        for act in (0,1,2):
            select=[x for x in entries if x["action"]==act]
            def distance(o):return abs(o["GoalX"]-o["X"])+abs(o["GoalY"]-o["Y"])
            delta=[distance(x["before"])-distance(x["after"]) for x in select]
            per_action[str(act)]={"events":len(select),
              "positive_original_reward":sum(x["reward"]>0 for x in select),
              "zero_original_reward":sum(x["reward"]==0 for x in select),
              "negative_original_reward":sum(x["reward"]<0 for x in select),
              "positive_manhattan_delta":sum(v>0 for v in delta),
              "zero_manhattan_delta":sum(v==0 for v in delta),
              "negative_manhattan_delta":sum(v<0 for v in delta),
              "signed_manhattan_delta_sum":sum(delta),
              "original_reward_sum":sum(x["reward"] for x in select)}
        stats[family]={"FIT_events":len(entries),"terminal_flags":sum(x["terminal"] for x in entries),
          "positive_original_reward":sum(x["reward"]>0 for x in entries),
          "actions":per_action}
    check(sum(x["FIT_events"] for x in stats.values())==6114,"FIT_ROWS_NOT_EXHAUSTIVE")
    check(all(stats[f]["actions"][str(a)]["events"]>0 for f in stats for a in (0,1,2)),
          "MISSING_ACTION_SUPPORT")
    check(all(stats[f]["actions"][str(a)]["zero_manhattan_delta"]==stats[f]["actions"][str(a)]["events"] for f in stats for a in (0,1)),
          "TURN_POSITION_CHANGED")
    return stats

def read_native(protocol):
    spec=protocol["native_ygg"]
    exact={"name":"Yggdrasil","repo":spec["repository"],"commit":spec["commit"],
           "file":spec["path"],"git_blob":spec["git_blob"]}
    return source_bytes(exact)

def native_audit(rows,src,original_checks):
    with tempfile.TemporaryDirectory(prefix="k4w-native-original-") as tmp:
        Path(tmp,"native_policy.py").write_bytes(src)
        sys.path.insert(0,tmp)
        try:
            native=importlib.import_module("native_policy")
            learner=native.GridColony()
            groups={family:{"native_choices_before_update":[0,0,0],"right_score_margin_negative":0,
                             "right_score_margin_zero":0,"right_score_margin_positive":0,
                             "right_margin_sum":0.0,"events":0} for family in ("empty","fourrooms")}
            before_states=[]
            for i,item in enumerate(rows):
                def grid(q):
                    return native.PublicGrid(q["X"],q["Y"],q["GoalX"],q["GoalY"],
                                             q["Direction"],q["FrontBlocked"])
                b=grid(item["before"]);after=grid(item["after"])
                scores=[learner.score(b,k) for k in (0,1,2)]
                action=learner.choose(b)
                check(action==max(range(3),key=lambda k:(scores[k],-k)),"NATIVE_CHOOSE_MISMATCH")
                check(all(math.isfinite(s) for s in scores),"NONFINITE_ACTION_SCORE")
                group=groups[item["family"]];group["events"]+=1
                group["native_choices_before_update"][action]+=1
                margin=scores[1]-max(scores[0],scores[2])
                group["right_margin_sum"]+=margin
                key="right_score_margin_positive" if margin>1e-12 else (
                    "right_score_margin_negative" if margin< -1e-12 else "right_score_margin_zero")
                group[key]+=1
                before_states.append(b)
                learner.observe(b,item["action"],after,float(item["reward"]),item["terminal"])
            exact_bytes=learner.save()
            check(learner.feedback_updates==6114,"ORIGINAL_NATIVE_UPDATE_COUNT")
            check(digest(exact_bytes)==original_checks["yggdrasil_checkpoint_sha256"],
                  "ORIGINAL_YGG_CHECKPOINT_MISMATCH")
            # POST-FIT diagnostic score projections; no state mutation or fitting.
            final={"full":[0,0,0],"without_ring":[0,0,0],"fast_only":[0,0,0],
                   "slow_only":[0,0,0]}
            for b in before_states:
                phi=native.features(b)
                scores=[learner.score(b,k) for k in (0,1,2)]
                raw=[[cell.output(f) for cell,f in zip(learner.cells[str(k)],phi)]
                     for k in (0,1,2)]
                without=[sum(vals) for vals in raw]
                fast=[sum(cell.fast*f for cell,f in zip(learner.cells[str(k)],phi))
                      for k in (0,1,2)]
                slow=[sum(cell.slow*f for cell,f in zip(learner.cells[str(k)],phi))
                      for k in (0,1,2)]
                for name,vals in (("full",scores),("without_ring",without),
                                  ("fast_only",fast),("slow_only",slow)):
                    chosen=max(range(3),key=lambda k:(vals[k],-k))
                    final[name][chosen]+=1
            check(all(sum(v)==6114 for v in final.values()),"ABLATION_ACCOUNTING")
            groups_out={}
            for f,x in groups.items():
                groups_out[f]={**x,"mean_right_score_margin_before_update":
                                      x["right_margin_sum"]/x["events"]}
            return {"source_git_blob":"3aa22b1e418a7f8cd9619c476f02b8c614917b16",
                    "original_ygg_checkpoint_sha256":digest(exact_bytes),
                    "original_ygg_checkpoint_bytes":len(exact_bytes),
                    "original_native_selected_action_evidence":groups_out,
                    "posthoc_final_state_score_views":final,
                    "posthoc_not_retrained_and_not_policy_outcomes":True}
        finally:
            sys.modules.pop("native_policy",None)
            sys.path.pop(0)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    check(not a.output.exists(),"RECEIPT_EXISTS")
    frozen=json.loads(P.read_text())
    check(frozen["schema"]=="mass.lcrm01.k4w.frozen-native-credit-failure-attribution-v1",
          "FROZEN_CONTRACT")
    rows,original=load(a.original,frozen)
    native=read_native(frozen)
    stats=discrete_counts(rows)
    policy=native_audit(rows,native,original)
    out={"schema":"mass.lcrm01.k4w.fit-only-original-credit-attribution.v1",
         "gate":"K4W","verdict":"ORIGINAL_FIT_INFORMATION_AND_NATIVE_POLICY_DIAGNOSTIC_ONLY",
         "archive_sha256":frozen["historic_source"]["zip_sha256"],
         "native_sha256":digest(native),
         "fit_stream_sha256":digest(canon(rows)),
         "original_process_count":2,"FIT_only":True,
         "source_original_episodes_executed":0,
         "CHECK_DEV_original_scores_not_read":True,
         "scientific_first_use":False,"scientific_accepted":False,
         "FIT_signal":stats,"Yggdrasil_original_native_fit":policy}
    a.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("K4W_ORIGINAL_FIT_ONLY_SHA_CUSTODY=PASS")
    print("K4W_FIT_INFORMATION="+json.dumps(stats,sort_keys=True))
    print("K4W_YGG_NATIVE_ACTION_RANK="+json.dumps(policy["original_native_selected_action_evidence"],sort_keys=True))
    print("K4W_POSTHOC_SCORE_PROJECTIONS="+json.dumps(policy["posthoc_final_state_score_views"],sort_keys=True))
    print("K4W_EXACT_ORIGINAL_YGG_FIT_CHECKPOINT=PASS")
    print("K4W_NEW_ORIGINAL_EPISODES=0_NOT_SCIENTIFIC_ADVANCEMENT")
if __name__=="__main__":main()
