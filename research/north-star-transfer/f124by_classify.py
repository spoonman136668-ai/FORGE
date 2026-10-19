"""F124-BY classifier: all 12 cases, no selective admission or tuning.

Three fixed arms: unchanged original AZ natural router, unchanged BQ public
learner, frozen BX third-shear learner. The generator private truth never
enters either learner. Captured native input/return belongs ONLY to this
eligibility diagnostic, NOT to CPU/RSS timing.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/"nativeevidence"))
import f124ag_transition_models as native

SOURCE=HERE/"f124by_panel.py"
BQ=HERE/"f124bq_program_learner.py"
BX=HERE/"f124bx_learned_flag.py"
VIEW=HERE/"f124br_native_view.py"
ARMS=("AZ","BQ","BX")
BASE=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
DELTA=[0.,0.]


def need(ok,msg):
    if not ok:raise RuntimeError("F124BY_CLASSIFIER_"+msg)


def load(name,path):
    sp=importlib.util.spec_from_file_location(name,path)
    o=importlib.util.module_from_spec(sp)
    sys.modules[name]=o
    sp.loader.exec_module(o)
    return o


def sha(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def bitvec(x):
    return [(x>>i)&1 for i in range(16)]


def classify_one(case,arm,capture=True):
    src=load("BY_source_neutral_panel",SOURCE)
    entry,_=src.profile(case)
    need(arm in ARMS,"FROZEN_ARMS")
    task,private=src.make(case)
    original=copy.deepcopy((task["positive"],task["hard_negative"]))
    graphs=(task["positive"],task["hard_negative"])
    graph_sha=sha({"fit":task["FIT"],"check":task["CHECK"],"graphs":graphs})
    observer=[]
    def trace(frame,event,arg):
        if frame.f_code is native.ygg_transition.__code__:
            if event=="call":
                observer.append({"graph":copy.deepcopy(frame.f_locals["g"])})
            elif event=="return":
                need(len(observer)>0 and "result" not in observer[-1],
                     "ORIGINAL_NATIVE_TRACE_ORDER")
                observer[-1]["result"]=copy.deepcopy(arg)
    if capture:sys.setprofile(trace)
    native_calls=0
    positive=False
    hard=False
    route="abstain"
    receipt={}
    try:
        if arm=="AZ":
            import f124az_joint_public_inverse as az
            demos=[{"input_bits":bitvec(x),"output_bits":bitvec(y)}
                   for x,y in task["FIT"]+task["CHECK"]]
            trained=az.train(demos,"BY_NONREGISTERED_ENGINEERING",0)
            route=trained["choice"]
            scores=[]
            for graph in graphs:
                value,work,diag=az.score(graph,list(BASE),list(DELTA),trained,demos)
                scores.append((value,work,diag))
            native_calls=sum(work is not None for _,work,_ in scores)
            positive=scores[0][0]>=0
            hard=scores[1][0]>=0
            receipt={"AZ_original_natural_route":route,
                     "AZ_forced_diagnostic":False}
        else:
            old=load("BY_frozen_original_BQ",BQ)
            view=load("BY_exact_BX_native_view",VIEW)
            if arm=="BQ":
                learned,rec,possibles=old.learn(task["FIT"],task["CHECK"])
                route="original_BQ" if learned is not None else "abstain"
                decoder=old
                confidence=rec["confidence"]
            else:
                candidate=load("BY_frozen_BX_model",BX)
                learned,rec,possibles=candidate.learn(
                    task["FIT"],task["CHECK"],old)
                route="frozen_BX_structural" if learned is not None else "abstain"
                import types
                decoder=types.SimpleNamespace(
                    inverse=lambda y,p:candidate.inverse(y,p,old))
                confidence=rec["confidence"]
            receipt={
              "FIT_SHA256":rec.get("FIT_sha256",rec.get("public_original_FIT_sha256")),
              "FIT_error_bits":rec.get("FIT_error_bits",rec.get("original_BQ_FIT_error_bits")),
              "CHECK_error_bits":rec.get("CHECK_error_bits",rec.get("original_BQ_CHECK_error_bits")),
              "stored_bits":rec.get("state_bits",rec.get("actual_packed_state_bits")),
              "sourceblind_FIT":True,"CHECK_veto_only":True,
              "confidence":confidence,
              "structural_flag":rec.get("learned_structural_flag"),
              "source_labels_used":False}
            if learned is not None:
                if arm=="BQ":
                    decisions=[old.causal_consensus(g,learned,possibles)[0]
                               for g in graphs]
                else:
                    decisions=[candidate.causal_consensus(g,learned,possibles,old)[0]
                               for g in graphs]
                positive,hard=decisions
                result=view.score_exact_native_pair(
                    graphs,decoder,learned,native,BASE,DELTA)
                native_calls=len(result)
    finally:
        if capture:sys.setprofile(None)
    need(original==graphs,"ACTUAL_GRAPH_MUTATION")
    if capture:need(len(observer)==native_calls,"Genuine_NATIVE_CALLS")
    need(private["no_registered_science_firstuse"] is True,
         "ORIGINAL_SCIENCE_LEAK")
    return {
       "schema":"mass.f124by.original-nonregistered-graph-arm.v1",
       "case":case,"arm":arm,
       "grammar_label_used_by_model":False,
       "source_case_id_used_by_model":False,
       "graph_source_sha256":graph_sha,
       "route":route,"native_calls":native_calls,
       "positive_accepted":bool(positive),"hard_false_positive":bool(hard),
       "native_graph_input_sha256":[sha(t["graph"]) for t in observer],
       "native_full_return_sha256":[sha(t["result"]) for t in observer],
       "source_private_truth_to_model":False,
       "fit_receipt":receipt,
       "original_registered_case_firstuse":False,
       "protected_cohorts_used":False
    }


def all_cases():
    src=load("BY_frozen_case_registry",SOURCE)
    return tuple(x["id"] for x in json.loads(src.FROZEN.read_text())["cases"])


def aggregate(rows):
    ids=all_cases()
    need(len(ids)==12 and len(set(ids))==12
         and len(rows)==len(ids)*len(ARMS),"EXACT_ALL_REGISTERED_ENGINEERING_CASES")
    by={(r["case"],r["arm"]):r for r in rows}
    need(len(by)==len(rows),"DUPLICATED_OR_MISSING_SCIENTIFIC_EVIDENCE")
    result={}
    totals={"hard_false_positives":[],"lost_BQ_baseline_positives":[],
            "new_correct_pairs":[],"AZ_not_naturally_eligible":[],
            "native_mismatch":[],"BX_abstentions":[]}
    for case in ids:
        az=by[case,"AZ"];old=by[case,"BQ"];new=by[case,"BX"]
        need(len({a["graph_source_sha256"] for a in (az,old,new)})==1,
             "ORIGINAL_SOURCE_SHA_DRIFT")
        need(all(not a["source_private_truth_to_model"]
                 and not a["original_registered_case_firstuse"]
                 and not a["protected_cohorts_used"] for a in (az,old,new)),
             "PROTECTED_SOURCE_OR_ORACLE_LEAK")
        native_ok=(az["route"] in ("affine","feistel")
                   and az["native_calls"]==2
                   and new["native_calls"]==2
                   and az["native_graph_input_sha256"]==new["native_graph_input_sha256"]
                   and az["native_full_return_sha256"]==new["native_full_return_sha256"])
        if new["hard_false_positive"]:
            totals["hard_false_positives"].append(case)
        if old["positive_accepted"] and not new["positive_accepted"]:
            totals["lost_BQ_baseline_positives"].append(case)
        if new["positive_accepted"] and not new["hard_false_positive"] and not (old["positive_accepted"] and not old["hard_false_positive"]):
            totals["new_correct_pairs"].append(case)
        if az["route"] not in ("affine","feistel") or az["native_calls"]!=2:
            totals["AZ_not_naturally_eligible"].append(case)
        if not native_ok:
            totals["native_mismatch"].append(case)
        if new["route"]=="abstain":
            totals["BX_abstentions"].append(case)
        result[case]={
           "AZ_route":az["route"],"BQ_route":old["route"],"BX_route":new["route"],
           "BX_structural_flag":new["fit_receipt"].get("structural_flag"),
           "AZ_positive":az["positive_accepted"],
           "BQ_positive":old["positive_accepted"],
           "BX_positive":new["positive_accepted"],
           "AZ_hard_FP":az["hard_false_positive"],
           "BQ_hard_FP":old["hard_false_positive"],
           "BX_hard_FP":new["hard_false_positive"],
           "same_actual_native_work_eligible":native_ok,
           "same_public_input_sha256":az["graph_source_sha256"],
           "source_grammar_truth_not_input":True
        }
    src=load("BY_original_frozen_panel",SOURCE)
    grammars={src.profile(case)[0]["grammar"] for case in totals["new_correct_pairs"]}
    win=(not totals["hard_false_positives"] and
         not totals["lost_BQ_baseline_positives"] and
         len(totals["new_correct_pairs"])>=3 and len(grammars)>=2)
    return {"schema":"mass.f124by.all-12-compositions-admission.v1",
            "cases":result,"original_all_36_arm_results":rows,
            "counts":{k:len(v) for k,v in totals.items()},
            "failures_or_gains":totals,
            "distinct_new_correct_grammars":len(grammars),
            "no_hard_FP_and_no_baseline_positive_loss_and_gain_gate":win,
            "matched_native_all_cases":len(totals["native_mismatch"])==0,
            "12_source_neutral_firstuses_only":True,
            "independent_scientific_origination":False,
            "original_development_924xxx_925xxx_consumed":False,
            "protected_128x2_used":False,
            "scientific_transfer_accepted":False,
            "optimizer_policy_promoted":False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--child",action="store_true")
    p.add_argument("--case",choices=all_cases())
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.child:
        need(a.case and a.arm,"EXACT_FROZEN_SOURCE_AND_ARM")
        print(json.dumps(classify_one(a.case,a.arm),sort_keys=True))
        return
    need(a.out is not None,"RECEIPT_PATH")
    rows=[]
    for case in all_cases():
        for arm in ARMS:
            run=subprocess.run(
                [sys.executable,"-B",str(Path(__file__).resolve()),
                 "--child","--case",case,"--arm",arm],
                cwd=ROOT,capture_output=True,text=True,timeout=120)
            need(run.returncode==0,"ORIGINAL_CASE_EXECUTION_"+case+arm+":"+run.stderr[-2000:])
            rows.append(json.loads(run.stdout))
    report=aggregate(rows)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2,sort_keys=True)
        f.write("\n")
    for case,item in report["cases"].items():
        print("BY_CASE="+case+" BQ_POS="+str(item["BQ_positive"])+
              " BX_POS="+str(item["BX_positive"])+
              " BX_HARD_FP="+str(item["BX_hard_FP"])+
              " AZ_ROUTE="+str(item["AZ_route"])+
              " MATCHED_NATIVE="+str(item["same_actual_native_work_eligible"]))
    for k,v in report["counts"].items():
        print("F124BY_"+k.upper()+"="+str(v))
    print("F124BY_UNSEEN_INDEPENDENT_SCIENCE_ACCEPTED=false")


if __name__=="__main__":
    main()
