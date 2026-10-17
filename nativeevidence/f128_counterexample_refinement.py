"""F128: authenticated F127 report -> failure-triggered auxiliary-join synthesis.

Bounded, model-free counterexample-guided program synthesis (CEGIS) in a
developer-authored typed relational operator family. Not open-ended science.
"""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import sys

import f118_autonomy_feedback as f118
import f126_original_negative_agenda as f126
import f127_program_synthesis as f127

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f128-counterexample-expansion-freeze.json"
BLOB="0c2c5e6351e60faefdb228438a6fe0ad436751e9"
SCHEMA="forge.autonomy.f128.counterexample-expanded-mechanism-development.v1"
HEX40=re.compile(r"^[0-9a-f]{40}$")
HEX64=re.compile(r"^[0-9a-f]{64}$")
class Blocked(ValueError):pass

def need(ok,reason):
    if not ok:raise Blocked("F128_"+reason)
def canonical(x):return f118.canonical(x)
def sha(x):return hashlib.sha256(canonical(x)).hexdigest()

def freeze():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    need(f118.gitblob(raw)==BLOB,"FROZEN_CONTRACT_DRIFT")
    p=json.loads(raw)
    need(p["schema"]=="forge.autonomy.f128.frozen-counterexample-directed-operator-expansion.v1"
         and p["parent_f127_head"]=="f02d288735f2caa9b9cba7faa81aad40f3cda3ce"
         and p["prior"]["run_id"]==39043407682
         and p["prior"]["payload_sha256"]=="74c74d66db98e5119c1d2db3f25e7f228966ba7464bd2ab5d698bf167307ff5e"
         and p["cohorts"]["train_pairs"]==16
         and p["cohorts"]["heldout_a_pairs"]==40
         and p["cohorts"]["heldout_b_pairs"]==40
         and p["expansion"]["max_synthesized_candidates"]==128
         and all(p["boundaries"].values()),"PRECOMMITTED_METHOD_OR_AUTHORITY_CHANGED")
    return p,hashlib.sha256(raw).hexdigest()

def read_previous(run,artifacts,linux,linux_receipt,windows,windows_receipt,
                  current_run_id,event,protocol=None):
    p=protocol if protocol is not None else freeze()[0]
    prior=p["prior"]
    need(type(run) is dict and type(artifacts) is dict
         and type(current_run_id) is int and current_run_id>0
         and event in ("pull_request","schedule","push","workflow_dispatch"),
         "GITHUB_PRIOR_ENVELOPE_INVALID")
    old=run.get("id")
    need(type(old) is int and 0<old<current_run_id
         and run.get("status")=="completed" and run.get("conclusion")=="success"
         and run.get("run_attempt")==prior["attempt"]
         and run.get("path")==prior["workflow"]
         and run.get("repository",{}).get("full_name")==prior["repo"]
         and run.get("head_repository",{}).get("full_name")==prior["repo"]
         and type(run.get("head_sha")) is str and HEX40.fullmatch(run["head_sha"]),
         "PREVIOUS_RUN_NOT_GENUINE")
    scheduled=event=="schedule"
    if scheduled:
        need(run.get("event")=="schedule" and run.get("head_branch")=="main",
             "PR_FIXTURE_CANNOT_STAND_FOR_SCHEDULED_RUN")
    else:
        need(old==prior["run_id"] and run.get("event")==prior["event"]
             and run.get("head_sha")==prior["head"]
             and run.get("head_branch")=="research/f127-evidence-driven-program-synthesis"
             and type(run.get("pull_requests")) is list
             and any(z.get("number")==prior["pr"] and
                     z.get("head",{}).get("sha")==prior["head"]
                     for z in run["pull_requests"]),
             "F127_UNAUTHENTIC_PR_LINEAGE")
    rows=artifacts.get("artifacts")
    need(type(rows) is list and type(artifacts.get("total_count")) is int
         and len(rows)==artifacts["total_count"] and len(rows)<=100
         and len({x.get("id") for x in rows if type(x) is dict})==len(rows),
         "TRUNCATED_GITHUB_ARTIFACT_INDEX")
    for os_name in ("ubuntu","windows"):
        pin=prior["artifacts"][os_name]
        matches=[row for row in rows if type(row) is dict
                 and row.get("name")==pin["name"]]
        need(len(matches)==1,"DUAL_OS_F127_NOT_PRESENT")
        entry=matches[0]
        need(entry.get("expired") is False
             and type(entry.get("size_in_bytes")) is int
             and entry["size_in_bytes"]>0
             and type(entry.get("workflow_run")) is dict
             and entry["workflow_run"].get("id")==old
             and entry["workflow_run"].get("head_sha")==run["head_sha"],
             "GITHUB_ARTIFACT_WRONG_SOURCE")
        if not scheduled:
            need(entry.get("id")==pin["id"]
                 and entry.get("digest")=="sha256:"+pin["sha256"],
                 "PINNED_F127_ZIP_DIGEST_DRIFT")
    for data,receipt in ((linux,linux_receipt),(windows,windows_receipt)):
        need(type(data) is bytes and 0<len(data)<500000 and
             type(receipt) is bytes and len(receipt)<200
             and receipt.strip()==(hashlib.sha256(data).hexdigest()+
                "  f127-program-synthesis.json").encode(),
             "EXTRACTED_F127_REPORT_OR_RECEIPT_INVALID")
    need(linux==windows,"CROSS_PLATFORM_PRIOR_OUTCOMES_DISAGREE")
    prior_hash=hashlib.sha256(linux).hexdigest()
    if not scheduled:need(prior_hash==prior["payload_sha256"],"F127_RECORD_DRIFT")
    report=f126.strict(linux)
    source=run["head_sha"] if scheduled else prior["checkout"]
    need(report.get("schema")==f127.SCHEMA
         and report.get("source_sha")==source
         and report.get("run_id")==old and report.get("event")==run["event"]
         and report.get("program_count")==8
         and report.get("source_only_heldout",{}).get("paired_correct")==64
         and report.get("exact_symbolic_ceiling",{}).get("paired_correct")==64
         and report.get("selection_from_training_only") is True
         and report.get("frozen_heldout_mechanism_criterion_passed") is True
         and report.get("scientific_originals_dispatched")==0
         and report.get("scientific_first_use_authorized") is False
         and report.get("accepted_ref_mutations")==0
         and report.get("optimizer_promotions")==0
         and report.get("Codex_calls")==0 and report.get("paid_model_calls")==0,
         "PRIOR_F127_AUTHORITY_OR_SOURCE_DRIFT")
    ast=report.get("selected_ast")
    identity=report.get("selected_ast_sha256")
    need(type(ast) is dict
         and ast=={"grammar":"typed-3-hop-join-v1","start_anchor":True,
                   "bind_intermediate_nodes":True,"target_anchor":True}
         and identity==sha(ast),"F127_BASELINE_NOT_A_FULL_CONNECTED_PATH")
    if not scheduled:need(identity==prior["expected_f127_selected_ast"],
                          "FROZEN_BASELINE_SHA_DRIFT")
    selection=report.get("synthesized_problem")
    need(type(selection) is dict
         and selection.get("source_experiment")=="F117-O"
         and selection.get("mechanism_problem")=="SHARED_NODE_BINDING",
         "PREVIOUS_ORIGINAL_NEGATIVE_NOT_ADMITTED")
    return {"prior_run_id":old,"prior_sha256":prior_hash,"prior_ast":ast,
            "prior_ast_sha256":identity,"prior_problem":selection,
            "scheduled_lineage":scheduled,"development_only":True}

def base_nodes(case,edges):
    # An executable 3-hop relational matcher: never exposes target labels.
    paths=[(case["start"],)]
    for role in case["path_roles"]:
        nxt=[]
        for path in paths:
            for a,r,b in edges:
                if a==path[-1] and r==role:
                    nxt.append(path+(b,))
        need(len(nxt)<=128,"LINEAR_PATH_SEARCH_BUDGET")
        paths=nxt
    return [p for p in paths if p[-1]==case["target"]]

def variant_a(seed,phase):
    need((phase=="TRAIN" and 160000<=seed<=160015) or
         (phase=="A" and 160100<=seed<=160139),"A_SOURCE_SEED_RANGE")
    n=lambda s:"F128-A/"+str(seed)+"/"+s
    path=[n(x) for x in ("s","b","c","t")]
    p,b,c,t=path
    pos=[(p,"main-0",b),(b,"main-1",c),(c,"main-2",t)]
    neg=list(pos)
    a1,a2=n("branch-x"),n("branch-y")
    q,q2=n("other-src"),n("other-target")
    pos += [(b,"aux-first",a1),(a1,"aux-last",t),
            (q,"aux-first",a2),(a2,"aux-last",q2)]
    neg += [(b,"aux-first",a1),(a1,"aux-last",q2),
            (q,"aux-first",a2),(a2,"aux-last",t)]
    # Correlated decoys satisfy individual anchored and unanchored clauses.
    shared=[(b,"aux-first",n("b-false-mid")),
            (n("b-false-mid"),"aux-last",n("b-false-end")),
            (n("q-src"),"aux-first",n("q-mid")),
            (n("q-mid"),"aux-last",t)]
    for j in range(seed%4):
        shared.append((n("noise-"+str(j)),"irrelevant-"+str(j),n("noise-end-"+str(j))))
    pos.extend(shared);neg.extend(shared)
    rotate=seed%len(pos)
    pos=pos[rotate:]+pos[:rotate]
    neg=neg[rotate:]+neg[:rotate]
    return {"seed":seed,"family":phase,"start":p,"target":t,
            "path_roles":["main-0","main-1","main-2"],
            "positive":pos,"negative":neg}

def variant_b(seed):
    """Separately built schema-keyed adjacency construction, unseen motifs."""
    need(161100<=seed<=161139,"B_SOURCE_SEED_RANGE")
    import itertools
    stem="B/%s/"%seed
    token=lambda k:stem+str(k*97+seed%37)
    query=[token(k) for k in range(4)]
    a,b,c,z=query
    links={
      "main":[(a,"main-0",b),(b,"main-1",c),(c,"main-2",z)],
      "right":[(b,"aux-first",token(5)),(token(5),"aux-last",z)],
      "other":[(token(6),"aux-first",token(7)),(token(7),"aux-last",token(8))],
      "root-decoy":[(b,"aux-first",token(9)),(token(9),"aux-last",token(8))],
      "end-decoy":[(token(10),"aux-first",token(11)),(token(11),"aux-last",z)],
      "cycles":[(token(14),"new-cycle",token(15)),
                (token(15),"new-cycle",token(14)),
                (token(16),"off-branch",token(17))]}
    for idx in range(seed%5):
        links["cycles"].append((token(20+idx),"dangling-"+str(idx),token(30+idx)))
    flatten=lambda m:[edge for key in sorted(m) for edge in m[key]]
    pos=flatten(links)
    modified={k:list(v) for k,v in links.items()}
    modified["right"][1]=(token(5),"aux-last",token(8))
    modified["other"][1]=(token(7),"aux-last",z)
    neg=flatten(modified)
    # Independent deterministic reordering, not A's list rotation.
    tag=lambda e:int.from_bytes(hashlib.sha256(
        (repr(e)+"#"+str(seed)).encode()).digest()[:8],"big")
    return {"seed":seed,"family":"B","start":a,"target":z,
            "path_roles":["main-0","main-1","main-2"],
            "positive":sorted(pos,key=tag),"negative":sorted(neg,key=tag)}

def challenge(seed,phase):
    case=variant_b(seed) if phase=="B" else variant_a(seed,phase)
    pos,neg=case["positive"],case["negative"]
    nodes=lambda edges:(sorted(x[0] for x in edges),sorted(x[2] for x in edges))
    roles=lambda edges:sorted(x[1] for x in edges)
    need(nodes(pos)==nodes(neg) and roles(pos)==roles(neg),
         "PAIR_GRAPH_MARGINALS_CHANGED")
    old={"grammar":"typed-3-hop-join-v1","start_anchor":True,
         "bind_intermediate_nodes":True,"target_anchor":True}
    # The original F127 full linear mechanism is insufficient on both arms.
    need(f127.execute_ast(old,{"roles":case["path_roles"],
          "start":case["start"],"target":case["target"]},pos)
         and f127.execute_ast(old,{"roles":case["path_roles"],
          "start":case["start"],"target":case["target"]},neg),
         "F127_MUST_FAIL_ON_BOTH_LABELED_GRAPHS")
    return case

def observed_role_pairs(training):
    signatures=set()
    for case in training:
        for edges in (case["positive"],case["negative"]):
            outgoing={}
            for u,role,v in edges:outgoing.setdefault(u,[]).append((role,v))
            for u,role,v in edges:
                if role in case["path_roles"]:continue
                for role2,w in outgoing.get(v,[]):
                    if role2 in case["path_roles"]:continue
                    signatures.add((role,role2))
    need(0<len(signatures)<=8,"ROLE_PAIR_GRAMMAR_NOT_BOUNDED")
    return sorted(signatures)

def programs(train_cases):
    role_pairs=observed_role_pairs(train_cases)
    out=[]
    for left,right in role_pairs:
        for src_idx,dst_idx in itertools.product(range(4),repeat=2):
            ast={"grammar":"f128-two-hop-branch-refinement-v1",
                 "prior_base":"typed-3-hop-join-v1",
                 "left_role":left,"right_role":right,
                 "branch_start_path_index":src_idx,
                 "branch_end_path_index":dst_idx}
            out.append({"ast":ast,"sha256":sha(ast),
                        "structural_complexity":2+
                         abs(src_idx-dst_idx)})
    need(0<len(out)<=128 and len({r["sha256"] for r in out})==len(out),
         "TOO_MANY_GENERATED_OPERATORS")
    return out

def execute_ast(ast,case,edges):
    need(type(ast) is dict and
         set(ast)=={"grammar","prior_base","left_role","right_role",
                    "branch_start_path_index","branch_end_path_index"} and
         ast["grammar"]=="f128-two-hop-branch-refinement-v1"
         and ast["prior_base"]=="typed-3-hop-join-v1"
         and type(ast["left_role"]) is str and type(ast["right_role"]) is str
         and all(type(ast[k]) is int and 0<=ast[k]<4 for k in
             ("branch_start_path_index","branch_end_path_index")),
         "UNQUALIFIED_SYNTHESIZED_BRANCH_AST")
    adjacency={}
    for s,role,t in edges:adjacency.setdefault((s,role),[]).append(t)
    for nodes in base_nodes(case,edges):
        src=nodes[ast["branch_start_path_index"]]
        dest=nodes[ast["branch_end_path_index"]]
        if any(dest in adjacency.get((mid,ast["right_role"]),[])
               for mid in adjacency.get((src,ast["left_role"]),[])):
            return True
    return False

def evaluate(candidate,cohort):
    cases=cohort
    rows=[]
    for case in cases:
        pos=execute_ast(candidate["ast"],case,case["positive"])
        neg=execute_ast(candidate["ast"],case,case["negative"])
        rows.append((int(pos),int(not neg),int(pos and not neg)))
    return {"pairs":len(rows),"positive_correct":sum(r[0] for r in rows),
            "negative_correct":sum(r[1] for r in rows),
            "paired_correct":sum(r[2] for r in rows),
            "graphs_sha256":sha([sha(c) for c in cases])}

def strong_control(case,edges):
    # Independent adjacency-index construction, not candidate interpreter.
    adj={}
    for s,r,t in edges:adj.setdefault((s,r),set()).add(t)
    for first in adj.get((case["start"],case["path_roles"][0]),()):
        for second in adj.get((first,case["path_roles"][1]),()):
            if case["target"] not in adj.get((second,case["path_roles"][2]),()):
                continue
            for midpoint in adj.get((first,"aux-first"),()):
                if case["target"] in adj.get((midpoint,"aux-last"),()):
                    return True
    return False

def source_only_oracle(cases):
    correct=0
    for c in cases:
        need(strong_control(c,c["positive"]) and
             not strong_control(c,c["negative"]),"HOLDOUT_ORACLE_BROKEN")
        correct+=1
    return correct

def synthesize(prior,source,run_id,event):
    spec,freeze_sha=freeze()
    need(type(prior) is dict and prior.get("development_only") is True
         and type(prior.get("prior_run_id")) is int
         and prior["prior_run_id"]<run_id and
         prior.get("prior_ast_sha256")==sha(prior["prior_ast"])
         and prior.get("prior_problem",{}).get("mechanism_problem")=="SHARED_NODE_BINDING"
         and type(source) is str and HEX40.fullmatch(source)
         and type(run_id) is int and run_id>0
         and event in ("pull_request","push","schedule","workflow_dispatch")
         and (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source),
         "CURRENT_AUTHORITY_OR_SOURCE_UNTRUSTED")
    need(prior.get("scheduled_lineage") is (event=="schedule"),
         "SCHEDULED_RUN_LINEAGE_SPOOFED")
    training=[challenge(i,"TRAIN") for i in range(160000,160016)]
    baseline_failure=sum(int(
        f127.execute_ast(prior["prior_ast"],
            {"roles":c["path_roles"],"start":c["start"],"target":c["target"]},
            c["positive"]) and not f127.execute_ast(prior["prior_ast"],
            {"roles":c["path_roles"],"start":c["start"],"target":c["target"]},
            c["negative"])) for c in training)
    need(baseline_failure==0,"PREVIOUS_MECHANISM_NOT_FALSIFIED")
    proposals=programs(training)
    scored=[{**p,"training":evaluate(p,training)} for p in proposals]
    selected=sorted(scored,key=lambda r:(-r["training"]["paired_correct"],
                    r["structural_complexity"],r["sha256"]))[0]
    a=[challenge(i,"A") for i in range(160100,160140)]
    b=[challenge(i,"B") for i in range(161100,161140)]
    a_result=evaluate(selected,a);b_result=evaluate(selected,b)
    oracle={"A":source_only_oracle(a),"B":source_only_oracle(b)}
    return {"schema":SCHEMA,"source_sha":source,"run_id":run_id,"event":event,
        "freeze_sha256":freeze_sha,
        "prior_real_f127_run_id":prior["prior_run_id"],
        "prior_report_sha256":prior["prior_sha256"],
        "problem_selected_by_original_negatives":prior["prior_problem"],
        "counterexamples_required_before_expansion":True,
        "prior_linear_program_train_paired_correct":baseline_failure,
        "inferred_role_signatures":observed_role_pairs(training),
        "candidate_count":len(scored),
        "candidate_evaluations":scored,
        "train_only_selected_ast":selected["ast"],
        "selected_ast_sha256":selected["sha256"],
        "selected_train":selected["training"],
        "heldout_generator_a":a_result,"heldout_generator_b":b_result,
        "exact_conjunctive_oracle":oracle,
        "original_strong_baseline_heldout_correct":0,
        "development_refinement_passed":
            selected["training"]["paired_correct"]==16 and
            a_result["paired_correct"]==40 and b_result["paired_correct"]==40,
        "unbounded_scientific_invention_proven":False,
        "independent_scientific_validation_proven":False,
        "two_genuine_unattended_scheduled_cycles_proven":False,
        "scientific_originals_dispatched":0,"scientific_first_use_authorized":False,
        "accepted_ref_mutations":0,"optimizer_promotions":0,
        "Codex_calls":0,"paid_model_calls":0,"new_schedulers":0,
        "ckb_plane_contact":False,"cloudflare_writes":0,"mind_palace_writes":0}

def main():
    p=argparse.ArgumentParser()
    for key in ("run-json","artifacts-json","ubuntu-report","ubuntu-receipt",
                "windows-report","windows-receipt","source-ref","event","output"):
        p.add_argument("--"+key,required=True)
    p.add_argument("--run-id",required=True,type=int)
    a=p.parse_args()
    raw=lambda x:Path(x).read_bytes()
    source_spec,_=freeze()
    prior=read_previous(f126.strict(raw(a.run_json)),f126.strict(raw(a.artifacts_json)),
        raw(a.ubuntu_report),raw(a.ubuntu_receipt),
        raw(a.windows_report),raw(a.windows_receipt),
        a.run_id,a.event,source_spec)
    result=synthesize(prior,a.source_ref,a.run_id,a.event)
    target=Path(a.output)
    need(target.parent.is_dir() and not target.exists(),"UNSAFE_OUTPUT_PATH")
    with target.open("xb") as f:f.write(canonical(result))

if __name__=="__main__":
    try:main()
    except (Blocked,f126.Blocked,f127.Blocked,f118.Quarantined,
            ValueError,TypeError,KeyError,OSError) as e:
        print("F128_COUNTEREXAMPLE_OPERATOR_SYNTHESIS_QUARANTINED "+str(e),file=sys.stderr)
        raise SystemExit(1)
