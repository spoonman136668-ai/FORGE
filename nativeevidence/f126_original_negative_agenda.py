"""F126 authentic original-source learning negatives -> autonomous development challenge.

Two exact historic GitHub Actions original-source learned-model results are
independently read and sealed on both runner OSes. The worse pre-registered
model-versus-strongest-control deficit chooses a distinct *development challenge*.
This is never an accepted experiment, scientific first-use, or a learned model.
"""
from __future__ import annotations
import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import f118_autonomy_feedback as f118

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f126-original-negative-autonomy-freeze.json"
BLOB="fb951a16087e2f0a7ac891d40aaed1d50c8e7174"
SCHEMA="forge.autonomy.f126.original-negative-driven-development-agenda.v1"
HEX40=re.compile("^[a-f0-9]{40}$")
HEX64=re.compile("^[a-f0-9]{64}$")
class Blocked(ValueError):pass

def need(ok,code):
    if not ok:raise Blocked("F126_"+code)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def canonical(x):return f118.canonical(x)
def sha(x):return digest(canonical(x))

def freeze():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    need(f118.gitblob(raw)==BLOB,"FROZEN_PROTOCOL_DRIFT")
    spec=json.loads(raw)
    need(spec["schema"]=="forge.autonomy.f126.original-source-negative-to-development-agenda-freeze.v1"
         and spec["parent_f125_head"]=="55ad071015a791bf2146e6f72e14025f0327e06f"
         and len(spec["originals"])==2
         and [x["id"] for x in spec["originals"]]==["F116-O","F117-O"]
         and [x["run_id"] for x in spec["originals"]]==[39026232824,39027222998]
         and all(spec["authority"].values())
         and spec["cohorts"]["paired_train"]==8
         and spec["cohorts"]["paired_confirm"]==32,"FROZEN_PROTOCOL_INCOMPLETE")
    return spec,digest(raw)

def strict(raw):
    need(type(raw) is bytes and 1<len(raw)<1000000,"UNBOUNDED_JSON")
    def pairs(items):
        out={}
        for k,v in items:
            need(k not in out,"DUPLICATE_JSON_KEY")
            out[k]=v
        return out
    try:return json.loads(raw.decode("utf-8"),object_pairs_hook=pairs,
                          parse_constant=lambda _:need(False,"NONFINITE_JSON"))
    except Blocked:raise
    except (ValueError,UnicodeError) as e:raise Blocked("F126_BAD_JSON") from e

def metric(row):
    need(type(row) is dict and row.get("both_classes_present") is True
         and type(row.get("n")) is int and row["n"]>0
         and all(type(row.get(x)) is int and row[x]>=0
                 for x in ("tp","tn","fp","fn","positive","negative"))
         and row["n"]==row["tp"]+row["tn"]+row["fp"]+row["fn"]
         and row["positive"]==row["tp"]+row["fn"]
         and row["negative"]==row["tn"]+row["fp"],"INVALID_MODEL_CONFUSION")
    value=row.get("balanced_accuracy")
    need(type(value) in (int,float) and 0<=value<=1,
         "NOT_A_REAL_BALANCED_ACCURACY")
    from_counts=(Decimal(row["tp"])/Decimal(row["positive"])+
                 Decimal(row["tn"])/Decimal(row["negative"]))/2
    need(abs(from_counts-Decimal(str(value)))<=Decimal("0.000001"),
         "INCONSISTENT_BALANCED_ACCURACY")
    return int((Decimal(str(value))*1000000).to_integral_value())

def sealed_run(evidence,original,source_graph):
    run=evidence["run"];meta=evidence["artifact_metadata"]
    need(type(run) is dict and type(meta) is dict
         and run.get("id")==original["run_id"]
         and run.get("event")==original["event"]=="push"
         and run.get("run_attempt")==1
         and run.get("path")==original["workflow"]
         and run.get("head_branch")==original["branch"]
         and run.get("head_sha")==original["head"]
         and run.get("repository",{}).get("full_name")=="spoonman136668-ai/FORGE"
         and run.get("head_repository",{}).get("full_name")=="spoonman136668-ai/FORGE"
         and run.get("status")=="completed" and run.get("conclusion")=="success",
         "ORIGINAL_RUN_GITHUB_IDENTITY")
    arts=meta.get("artifacts")
    need(type(arts) is list and meta.get("total_count")==len(arts)
         and len(arts)<=100
         and len({x.get("id") for x in arts if type(x) is dict})==len(arts),
         "ARTIFACT_INDEX_NOT_EXHAUSTIVE")
    by_id={x["id"]:x for x in arts if type(x) is dict}
    raws=[]
    for os_name in ("ubuntu","windows"):
        pinned=original[os_name]
        row=by_id.get(pinned["id"])
        need(type(row) is dict and row.get("name")==pinned["name"]
             and row.get("digest")=="sha256:"+pinned["zip"]
             and row.get("expired") is False
             and type(row.get("workflow_run")) is dict
             and row["workflow_run"].get("id")==original["run_id"]
             and row["workflow_run"].get("head_sha")==original["head"],
             "PINNED_ARTIFACT_ZIP_PROVENANCE")
        raw=evidence[os_name+"_state"]
        receipt=evidence[os_name+"_receipt"]
        need(type(raw) is bytes and type(receipt) is bytes
             and 0<len(raw)<500000 and len(receipt)<200
             and receipt.strip() in {
                  (digest(raw)+"  "+original["filename"]).encode(),
                  (digest(raw)+" *"+original["filename"]).encode()}
             and digest(raw)==original["payload"],"CONTAINED_ORIGINAL_PAYLOAD")
        raws.append(raw)
    need(raws[0]==raws[1],"INDEPENDENT_RUNNERS_DISAGREE")
    report=strict(raws[0])
    expected_schema=("forge.optimizer.f116o.public-metaqa-trained-role-composition.v1"
                     if original["id"]=="F116-O" else
                     "forge.optimizer.f117o.public-metaqa-ternary-latent-junction.v1")
    need(report.get("schema")==expected_schema
         and report.get("source_repository")==source_graph["repository"]
         and report.get("source_commit")==source_graph["commit"]
         and report.get("original_graph_git_blob")==source_graph["blob"]
         and report.get("original_graph_sha256")==source_graph["sha256"]
         and report.get("accepted_science") is False
         and report.get("independent_scientific_firstuse") is False
         and report.get("scientific_dispatch") is False
         and report.get("accepted_ref_mutation") is False
         and report.get("dream_pareto_promotion") is False
         and report.get("thetaevolve_accepted_training") is False
         and report.get("model_calls")==0 and report.get("codex_calls")==0,
         "SCIENTIFIC_SOURCE_OR_AUTHORITY_MISREPRESENTED")
    learning=report.get("learning")
    need(type(learning) is dict
         and "GAIN_NOT_DEMONSTRATED" in learning.get("gain_disposition",""),
         "NEGATIVE_NOT_PRESERVED")
    if original["id"]=="F116-O":
        need(learning.get("training_only_gradient_updates") is True
             and learning.get("dev_or_test_in_model_selection") is False
             and learning["model"]["trainable_parameters"]==181,
             "F116_LEARNING_SOURCE")
        m=learning[original["model"]];ctrl=learning[original["comparator"]]
    else:
        need(learning.get("train_only_updates") is True
             and learning.get("dev_test_labels_in_training") is False
             and learning.get("binding_challenge_exact_join_negative")==92
             and learning.get("binding_challenge_n")==256
             and learning.get("pairwise_positive_does_not_guarantee_shared_node") is True
             and report.get("actual_entity_variable_binding_learned") is False,
             "F117_ORIGINAL_VARIABLE_JOIN_NEGATIVE")
        m=learning["terminal_holdout"][original["model"]]
        ctrl=learning["terminal_holdout"][original["comparator"]]
    mm=metric(m); cc=metric(ctrl)
    need(cc>mm and cc-mm==original["observed_gap_scaled_1000000"],
         "FROZEN_STRONGER_CONTROL_GAP_DRIFT")
    return {"experiment":original["id"],"run_id":original["run_id"],
            "source_sha":original["head"],"source_graph_sha256":source_graph["sha256"],
            "payload_sha256":original["payload"],
            "heldout_learned_ba_millionths":mm,
            "heldout_stronger_control_ba_millionths":cc,
            "unrecovered_loss_millionths":cc-mm,
            "has_unconnected_pairwise_witnesses":
                 original["id"]=="F117-O",
            "classification":"Genuine original-source engineering negative, not independent scientific acceptance"}

def choose_next(records):
    need(type(records) is list and len(records)==2
         and [x["experiment"] for x in records]==["F116-O","F117-O"]
         and all(type(x["unrecovered_loss_millionths"]) is int
                 and x["unrecovered_loss_millionths"]>0 for x in records),
         "UNBOUND_ORIGINAL_NEGATIVE_POPULATION")
    chosen=sorted(records,key=lambda r:(-r["unrecovered_loss_millionths"],
                                        r["experiment"]))[0]
    focus=("SHARED_NODE_BINDING" if chosen["has_unconnected_pairwise_witnesses"]
           else "ROLE_MARGINAL_SHORTCUT")
    return {"source_experiment":chosen["experiment"],"mechanism_problem":focus,
            "priority_gap_millionths":chosen["unrecovered_loss_millionths"],
            "choice_rule":"largest original-source heldout deficit against strongest precommitted control"}

def build_pair(seed,focus,variant):
    need(type(seed) is int and 130000<=seed<=130131
         and focus in ("SHARED_NODE_BINDING","ROLE_MARGINAL_SHORTCUT")
         and variant in (0,1),"NOT_A_FROZEN_DEVELOPMENT_VARIANT")
    root="s"+str(seed)+"v"+str(variant)
    a,b,c,z,d,e,f,g=[root+x for x in "abczdefg"]
    # The extra distractor variant increases off-path graph size on both arms
    # but cannot add a legitimate alternative a-r0-r1-r2-z chain.
    pos=[(a,"r0",b),(b,"r1",c),(c,"r2",z),
         (d,"r1",e),(f,"r2",g)]
    neg=[(a,"r0",b),(b,"r1",c),(f,"r2",z),
         (d,"r1",e),(e,"r2",g)]
    for j in range(variant):
        off=root+"X"+str(j);targ=root+"Y"+str(j)
        pos.append((off,"offpath",targ))
        neg.append((off,"offpath",targ))
    # Use content-deterministic reversible permutations, preserving all edges.
    rotate=seed%len(pos)
    pos=pos[rotate:]+pos[:rotate];neg=neg[rotate:]+neg[:rotate]
    return {"seed":seed,"focus":focus,"variant":variant,
            "roles":["r0","r1","r2"],"start":a,"target":z,
            "positive":pos,"negative":neg}

def connected(edges,start,target,roles):
    frontier={start}
    for role in roles:
        frontier={dst for src,r,dst in edges
                  if src in frontier and r==role}
    return target in frontier

def adjacent_global(edges,roles):
    for left,right in zip(roles,roles[1:]):
        if not any(end==begin and rl==left and rr==right
                   for start,rl,end in edges
                   for begin,rr,dst in edges):
            return False
    return True

def score_pair(case):
    pos,neg=case["positive"],case["negative"]
    p=connected(pos,case["start"],case["target"],case["roles"])
    n=connected(neg,case["start"],case["target"],case["roles"])
    pair_pos=adjacent_global(pos,case["roles"])
    pair_neg=adjacent_global(neg,case["roles"])
    hist=lambda edges:sorted(r for _,r,_ in edges)
    need(p and not n and pair_pos and pair_neg and hist(pos)==hist(neg)
         and sorted(x for e in pos for x in (e[0],e[2]))!=[],
         "COUNTERFACTUAL_NOT_A_JOINT_WITNESS_FAILURE")
    # Exact graph-role query correct on both examples; pairwise existential
    # shortcut falsely accepts the disconnected counterfactual.
    return {"oracle_paired_correct":1,
            "pairwise_existence_paired_correct":int(pair_pos and not pair_neg),
            "role_only_paired_correct":0,
            "case_sha256":sha(case)}

def evaluate(focus,variant,phase):
    seeds=range(130000,130008) if phase=="TRAIN" else range(130100,130132)
    rows=[score_pair(build_pair(s,focus,variant)) for s in seeds]
    return {"cases":len(rows),"source_sha256":sha(rows),
            "exact_oracle_paired_correct":sum(x["oracle_paired_correct"] for x in rows),
            "pairwise_shortcut_paired_correct":
                sum(x["pairwise_existence_paired_correct"] for x in rows),
            "role_only_paired_correct":
                sum(x["role_only_paired_correct"] for x in rows)}

def execute(source,run_id,event,inputs):
    spec,freeze_sha=freeze()
    need(type(source) is str and HEX40.fullmatch(source)
         and type(run_id) is int and run_id>39027222998
         and event in ("pull_request","push","schedule","workflow_dispatch")
         and (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source)
         and type(inputs) is dict and set(inputs)=={"F116-O","F117-O"},
         "CURRENT_SOURCE_NOT_BOUND")
    records=[sealed_run(inputs[o["id"]],o,spec["source_graph"])
             for o in spec["originals"]]
    direction=choose_next(records)
    focus=direction["mechanism_problem"]
    train=[{"variant":i,"result":evaluate(focus,i,"TRAIN")} for i in (0,1)]
    # Diversity tie-break frozen by variant index; never inspect holdout.
    selected=sorted(train,key=lambda x:(
      -(x["result"]["exact_oracle_paired_correct"]-
        x["result"]["pairwise_shortcut_paired_correct"]),x["variant"]))[0]["variant"]
    held=evaluate(focus,selected,"CONFIRM")
    need(held["cases"]==32 and held["exact_oracle_paired_correct"]==32,
         "FROZEN_NEW_CHALLENGE_UNQUALIFIED")
    return {"schema":SCHEMA,"source_sha":source,"run_id":run_id,"event":event,
            "freeze_sha256":freeze_sha,"original_source_records":records,
            "original_source_negative_findings_preserved":2,
            "source_driven_autonomous_selection":direction,
            "source_only_synthetic_development_controls":train,
            "train_only_selected_variant":selected,
            "heldout_development_probe":held,
            "new_accepted_scientific_originals":0,
            "real_scientific_first_use":False,
            "new_learned_mechanism_implemented":False,
            "independent_scientific_generalization_proven":False,
            "optimizer_promotions":0,"accepted_ref_mutations":0,
            "Codex_calls":0,"paid_model_calls":0,
            "new_scheduler":False,"ckb_plane_contact":False,
            "cloudflare_writes":0,"mind_palace_writes":0}

def main():
    p=argparse.ArgumentParser()
    for name in ("source-ref","event","output"):p.add_argument("--"+name,required=True)
    p.add_argument("--run-id",required=True,type=int)
    for label in ("f116","f117"):
        for name in ("run-json","artifacts-json","ubuntu-state","ubuntu-receipt",
                     "windows-state","windows-receipt"):
            p.add_argument("--"+label+"-"+name,required=True)
    a=p.parse_args()
    inp={}
    for id,label in (("F116-O","f116"),("F117-O","f117")):
        props={}
        for key,suff in (("run","run_json"),("artifact_metadata","artifacts_json"),
                         ("ubuntu_state","ubuntu_state"),("ubuntu_receipt","ubuntu_receipt"),
                         ("windows_state","windows_state"),("windows_receipt","windows_receipt")):
            path=Path(getattr(a,label+"_"+suff))
            raw=path.read_bytes()
            props[key]=strict(raw) if key in ("run","artifact_metadata") else raw
        inp[id]=props
    report=execute(a.source_ref,a.run_id,a.event,inp)
    out=Path(a.output)
    need(out.parent.is_dir() and not out.exists(),"NOT_A_NEW_OUTPUT")
    with out.open("xb") as fp:fp.write(canonical(report))

if __name__=="__main__":
    try:main()
    except (Blocked,f118.Quarantined,OSError,ValueError,KeyError,TypeError) as e:
        print("F126_AUTHENTIC_ORIGINAL_NEGATIVE_QUARANTINED "+str(e),file=sys.stderr)
        raise SystemExit(1)
