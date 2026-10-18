"""F124-BB exact frozen FIT selection with conditional unseen SCREEN.

Evaluate unchanged affine/joint and new public graph-consensus verifier against
the same 48 public responses, same paired cases and original donor weights.
No parent scientific outcome is supplied to model or model election.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,sys,time,tracemalloc
from pathlib import Path
import f124bb_train_source as source
import f124bb_public_consensus as model
import f124az_joint_public_inverse as original
import f124av_informative_inverse as affine
import f124q_independent_binding as q

SCHEMA="forge.research.f124bb.one-original-fresh-public-consensus.v1"
SPECS=(("affine_balanced48","balanced_basis48","affine",None),
       ("affine_random48","random48","affine",None),
       ("joint_balanced48","balanced_basis48","joint",None),
       ("joint_random48","random48","joint",None),
       ("consensus_balanced_eta0","balanced_basis48","consensus",0.),
       ("consensus_balanced_eta02","balanced_basis48","consensus",.2),
       ("consensus_random_eta0","random48","consensus",0.),
       ("consensus_random_eta02","random48","consensus",.2))
CONTROLS=SPECS[:4]
NEW=SPECS[4:]
def need(ok,name):source.need(ok,"PROSPECTIVE_"+name)

def measured(fn):
    gc.collect();tracemalloc.start()
    cpu=time.process_time_ns();wall=time.perf_counter_ns()
    result=fn()
    peak=tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return result,{"CPU_ns":time.process_time_ns()-cpu,
                   "wall_ns":time.perf_counter_ns()-wall,
                   "peak_Python_bytes":peak}

def fresh():
    return {"pairs":0,"paired":0,"FP":0,"FN":0,
      "accepted_positive_case_ids":[],"case_outcomes":[],
      "by_operator":{"affine":{"pairs":0,"paired":0,"FP":0,"FN":0},
                     "feistel":{"pairs":0,"paired":0,"FP":0,"FN":0}},
      "by_family":{f:{"pairs":0,"paired":0,"FP":0,"FN":0} for f in source.FAMILIES},
      "public_response_calls":0,"original_extra_queries":0,
      "query_CPU_ns":0,"model_CPU_ns":0,"model_wall_ns":0,
      "peak_Python_bytes":0,"max_extra_task_model_bits_lower":0,
      "verification_graphs":0,"verification_vetoes":0,
      "extra_verifier_scans":0,"extra_verifier_bit_ops":0,
      "max_verifier_active":0,"max_verifier_retained":0,
      "max_verifier_graph_state_bits_lower":0,
      "max_active":0,"max_retained":0}

def evaluate(rows,base,delta,spec):
    name,query,mode,eta=spec
    need(spec in SPECS,"FROZEN_ONLY_ARMS")
    out=fresh()
    for seed,vec,family,op,nonce,pos,neg in rows:
        demos,qcost=measured(lambda:source.public48(seed,vec,op,query,pos["demos"]))
        need(pos["demos"]==neg["demos"],"LABEL_BLIND_PUBLIC_SUPPORT")
        def apply():
            if mode=="affine":
                coeff,info=affine.fit(demos,nonce)
                checked=affine.check(demos,coeff)
                a,wa,_=affine.score(pos,base,delta,coeff,info,checked,12,96)
                b,wb,_=affine.score(neg,base,delta,coeff,info,checked,12,96)
                bits=info["transient_task_coefficient_bits"]
                diags=({}, {})
            else:
                fitted=original.train(demos,nonce,0)
                if mode=="joint":
                    a,wa,_=original.score(pos,base,delta,fitted,demos)
                    b,wb,_=original.score(neg,base,delta,fitted,demos)
                    diags=({}, {})
                else:
                    a,wa,da=model.score(pos,base,delta,fitted,demos,eta)
                    b,wb,db=model.score(neg,base,delta,fitted,demos,eta)
                    diags=(da,db)
                bits=fitted["extra_task_model_bits_lower"]
            return a,b,wa,wb,bits,diags
        (a,b,wa,wb,bits,diags),cost=measured(apply)
        p=a>=0;n=b>=0
        key=q.digest([seed,list(vec),family])
        typ="affine" if op.startswith("affine_") else "feistel"
        for bucket in (out,out["by_operator"][typ],out["by_family"][family]):
            bucket["pairs"]+=1
            bucket["paired"]+=int(p and not n)
            bucket["FP"]+=int(n)
            bucket["FN"]+=int(not p)
        if p:out["accepted_positive_case_ids"].append(key)
        for diag in diags:
            out["verification_graphs"]+=int(diag.get("second_pass_performed",False))
            out["verification_vetoes"]+=int(diag.get("veto",False))
            out["extra_verifier_scans"]+=diag.get("extra_verifier_public_edge_scans",0)
            out["extra_verifier_bit_ops"]+=diag.get("extra_verifier_bit_ops",0)
            out["max_verifier_active"]=max(out["max_verifier_active"],diag.get("max_verifier_active",0))
            out["max_verifier_retained"]=max(out["max_verifier_retained"],diag.get("max_verifier_retained",0))
            out["max_verifier_graph_state_bits_lower"]=max(out["max_verifier_graph_state_bits_lower"],diag.get("extra_public_graph_state_bits_lower",0))
        out["case_outcomes"].append({"case_id":key,"operator_family":typ,
            "graph_family":family,"positive_accepted":p,"negative_accepted":n,
            "verification_veto_positive":diags[0].get("veto",False),
            "verification_veto_negative":diags[1].get("veto",False)})
        out["public_response_calls"]+=48
        out["original_extra_queries"]+=24
        out["query_CPU_ns"]+=qcost["CPU_ns"]
        out["model_CPU_ns"]+=cost["CPU_ns"]
        out["model_wall_ns"]+=cost["wall_ns"]
        out["peak_Python_bytes"]=max(out["peak_Python_bytes"],qcost["peak_Python_bytes"],cost["peak_Python_bytes"])
        out["max_extra_task_model_bits_lower"]=max(out["max_extra_task_model_bits_lower"],bits)
        for work in (wa,wb):
            if work:
                out["max_active"]=max(out["max_active"],work["max_active"])
                out["max_retained"]=max(out["max_retained"],work["max_retained"])
    need(out["pairs"]==24 and out["public_response_calls"]==1152
         and out["original_extra_queries"]==576
         and all(x["pairs"]==12 for x in out["by_operator"].values())
         and all(x["pairs"]==6 for x in out["by_family"].values())
         and out["max_active"]<=7 and out["max_retained"]<=9
         and out["max_verifier_active"]<=7 and out["max_verifier_retained"]<=9,
         "EQUAL_INFO_SEQUENTIAL_7_PLUS_9")
    return out

def matched_joint(name):
    return "joint_balanced48" if "balanced" in name else "joint_random48"

def eligibility(cards,name):
    r=cards[name];parent=cards[matched_joint(name)]
    retained=set(parent["accepted_positive_case_ids"])
    accepted=set(r["accepted_positive_case_ids"])
    # A pure veto can only shrink original joint acceptances. A strict FP
    # improvement is necessary to claim reduction, even if old joint is FP0.
    improved=parent["FP"]>r["FP"]
    preserved=retained.issubset(accepted)
    ok=(improved and preserved and
        r["FP"]==0 and r["paired"]==parent["paired"] and
        r["by_operator"]["feistel"]["paired"]==parent["by_operator"]["feistel"]["paired"] and
        r["by_operator"]["feistel"]["paired"]>=1)
    return ok,{"eligible":ok,"joint_FP":parent["FP"],"candidate_FP":r["FP"],
        "joint_paired":parent["paired"],"candidate_paired":r["paired"],
        "joint_Feistel":parent["by_operator"]["feistel"]["paired"],
        "candidate_Feistel":r["by_operator"]["feistel"]["paired"],
        "joint_accepted_positive_ids":len(retained),
        "preserved_joint_accepted_positive_ids":len(accepted&retained),
        "all_joint_accepted_positive_ids_retained":preserved,
        "strictly_reduced_joint_false_positives":improved}

def run(base,delta):
    source.frozen()
    need(type(base) is list and len(base)==7 and type(delta) is list and len(delta)==2
         and all(type(x) in (float,int) and math.isfinite(x) for x in base+delta),
         "AUTHENTIC_HISTORIC_WEIGHTS_NOT_SCIENCE_RESULTS")
    fitcases=source.rows("FIT")
    fit={spec[0]:evaluate(fitcases,base,delta,spec) for spec in SPECS}
    admissible={spec[0]:eligibility(fit,spec[0])[1] for spec in NEW}
    qualifying=[name for name,r in admissible.items() if r["eligible"]]
    elected=min(qualifying,key=lambda name:(
        -fit[name]["paired"],fit[name]["model_CPU_ns"],name)) if qualifying else None
    receipt={"schema":SCHEMA,"frozen_blob":source.FREEZE_BLOB,
      "frozen_commit":source.FIRST_COMMIT,"qualified_parent_head":source.PARENT,
      "FIT_paired_cases":24,"FIT_models":fit,"FIT_candidate_eligibility":admissible,
      "FIT_selected":elected,"SCREEN_paired_cases":0,"SCREEN_models":None,
      "SCREEN_elected_eligibility":None,"SCREEN_strict_acceptance":False,
      "sourceblind_graph_consensus_not_evaluator_oracle":True,
      "same_48_public_observations_all_models":True,
      "extra_model_compute_and_public_verifier_memory_separately_counted":True,
      "exact_original_cognition_7_active_9_retained":True,
      "prior_BA_AZ_consumed_cases_as_training_input":False,
      "Ygg_DEV_constructed":0,"Wingless_DEV_constructed":0,
      "science_protected_acceptance":False,"optimizer_promotion":False,
      "production_activation":False,"accepted_ref_mutation":False}
    if elected is None:
        receipt["SCREEN_unconstructed_due_to_no_FIT_eligible"]=True
        return receipt
    # Construct independent SCREEN only after the FIT-selected arm is frozen.
    held=source.rows("SCREEN")
    selected=next(s for s in NEW if s[0]==elected)
    relevant=(next(s for s in CONTROLS if s[0]==matched_joint(elected)),selected)
    screened={spec[0]:evaluate(held,base,delta,spec) for spec in relevant}
    ok,detail=eligibility(screened,elected)
    receipt.update({"SCREEN_paired_cases":24,"SCREEN_models":screened,
        "SCREEN_elected_eligibility":detail,"SCREEN_strict_acceptance":ok,
        "SCREEN_unconstructed_due_to_no_FIT_eligible":False})
    return receipt

def main():
    p=argparse.ArgumentParser()
    for key in ("base","delta","output"):p.add_argument("--"+key,required=True)
    args=p.parse_args()
    path=Path(args.output)
    need(path.parent.is_dir() and not path.exists(),"NEW_IMMUTABLE_FIRST_RESULT")
    result=run(json.loads(Path(args.base).read_text()),json.loads(Path(args.delta).read_text()))
    data=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
    with path.open("xb") as f:f.write(data)
    print("F124BB_ONE_ORIGINAL_FIT_JSON_SHA256="+hashlib.sha256(data).hexdigest())
    print("F124BB_FIT_SELECTED="+str(result["FIT_selected"]))
    for name,c in result["FIT_models"].items():
        print("F124BB_FIT_"+name+"="+json.dumps({
            k:c[k] for k in ("paired","FP","FN","verification_vetoes")},sort_keys=True))
    print("F124BB_HELD_SCREEN_CONSTRUCTED="+str(result["SCREEN_paired_cases"]>0).lower())
    print("F124BB_PROTECTED_DEV_UNCONSTRUCTED=true")
if __name__=="__main__":
    try:main()
    except (ValueError,TypeError,KeyError,OSError,ArithmeticError,AssertionError) as e:
        print("F124BB_FAIL_CLOSED:"+str(e),file=sys.stderr);sys.exit(1)
