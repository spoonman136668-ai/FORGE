"""F127: authenticated F126 negative -> autonomous bounded executable AST synthesis.

All proposed programs execute in a tiny deterministic source-only graph-query
interpreter. This is finite grammar PROGRAM SYNTHESIS (not an LLM, new source
patch, neural learner, original scientific run, or deployment authority).
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

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f127-autonomous-program-synthesis-freeze.json"
FREEZE_BLOB="79dd6b6db2c45576bf6bb7bc71256e6ed55e98ac"
SCHEMA="forge.autonomy.f127.evidence-driven-program-synthesis-development.v1"
HEX40=re.compile(r"^[a-f0-9]{40}$")
HEX64=re.compile(r"^[a-f0-9]{64}$")
class Blocked(ValueError): pass

def need(ok,code):
    if not ok:raise Blocked("F127_"+code)
def canonical(x):return f118.canonical(x)
def sha(x):return hashlib.sha256(canonical(x)).hexdigest()

def frozen():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    need(f118.gitblob(raw)==FREEZE_BLOB,"PREREGISTRATION_CHANGED")
    p=json.loads(raw)
    need(p["schema"]=="forge.autonomy.f127.frozen-evidence-conditioned-program-synthesis.v1"
         and p["parent_f126_head"]=="82f9641734df9940c1498d59b0c98bef0205b991"
         and p["source"]["prior_run_id"]==39041234945
         and p["source"]["prior_json_sha256"]=="034c8f016918c8bdcd9a64cd8564a0b3ce4070f477a48343ec88391b2fa77d62"
         and p["evaluation"]["train_pairs"]==16
         and p["evaluation"]["confirm_pairs"]==64
         and p["grammar"]["max_candidate_programs"]==8
         and all(p["limits"].values()),
         "METHOD_OR_AUTHORITY_DRIFT")
    return p,hashlib.sha256(raw).hexdigest()

def read_previous(run,artifacts,linux,linux_receipt,windows,windows_receipt,
                  current_run_id,event,protocol=None):
    p=protocol if protocol is not None else frozen()[0]
    s=p["source"]
    need(type(run) is dict and type(artifacts) is dict
         and type(current_run_id) is int and current_run_id>0
         and event in ("pull_request","schedule","push","workflow_dispatch"),
         "PRIOR_ENVELOPE_INVALID")
    old=run.get("id")
    need(type(old) is int and 0<old<current_run_id
         and run.get("path")==s["prior_workflow"]
         and run.get("status")=="completed" and run.get("conclusion")=="success"
         and run.get("run_attempt")==1
         and run.get("repository",{}).get("full_name")==s["repository"]
         and run.get("head_repository",{}).get("full_name")==s["repository"]
         and type(run.get("head_sha")) is str
         and HEX40.fullmatch(run["head_sha"]), "UNAUTHENTIC_GITHUB_RUN")
    scheduled=event=="schedule"
    if scheduled:
        need(run.get("event")=="schedule" and run.get("head_branch")=="main",
             "PR_DEVELOPMENT_CANNOT_PROVE_UNATTENDED_SCHEDULE")
    else:
        need(old==s["prior_run_id"]
             and run.get("event")=="pull_request"
             and run.get("head_sha")==s["prior_head"]
             and run.get("head_branch")=="research/f126-original-negative-to-agenda"
             and type(run.get("pull_requests")) is list
             and any(x.get("number")==437 and
                     x.get("head",{}).get("sha")==s["prior_head"]
                     for x in run["pull_requests"]),
             "PINNED_F126_PR_SOURCE_MISMATCH")
    rows=artifacts.get("artifacts")
    need(type(rows) is list and type(artifacts.get("total_count")) is int
         and artifacts["total_count"]==len(rows) and len(rows)<=100
         and len({a.get("id") for a in rows if type(a) is dict})==len(rows),
         "INCOMPLETE_ARTIFACT_INDEX")
    for platform in ("ubuntu","windows"):
        f=s["prior_"+platform]
        matches=[a for a in rows if a.get("name")==f["name"]]
        need(len(matches)==1,"MISSING_PRIOR_OS_ARTIFACT")
        item=matches[0]
        need(item.get("expired") is False
             and type(item.get("size_in_bytes")) is int
             and item["size_in_bytes"]>0
             and item.get("workflow_run",{}).get("id")==old
             and item["workflow_run"].get("head_sha")==run["head_sha"]
             and type(item.get("digest")) is str
             and HEX64.fullmatch(item["digest"].removeprefix("sha256:")),
             "PRIOR_ARTIFACT_WRONG_RUN")
        if not scheduled:
            need(item.get("id")==f["id"]
                 and item.get("digest")=="sha256:"+f["zip_digest"],
                 "FROZEN_ARCHIVE_IDENTITY_DRIFT")
    for blob,receipt in ((linux,linux_receipt),(windows,windows_receipt)):
        need(type(blob) is bytes and len(blob)>0 and len(blob)<500000
             and type(receipt) is bytes and len(receipt)<200
             and receipt.strip()==(hashlib.sha256(blob).hexdigest()+
              "  f126-original-negative-selected-agenda.json").encode(),
             "EXTRACTED_F126_RECEIPT_MISMATCH")
    need(linux==windows,"INDEPENDENT_OS_REPORT_DRIFT")
    measured=hashlib.sha256(linux).hexdigest()
    if not scheduled:need(measured==s["prior_json_sha256"],"ORIGINAL_RECEIPT_DRIFT")
    report=f126.strict(linux)
    source=run["head_sha"] if scheduled else s["prior_checkout_merge"]
    need(report.get("schema")==f126.SCHEMA
         and report.get("run_id")==old
         and report.get("event")==run["event"]
         and report.get("source_sha")==source
         and report.get("original_source_negative_findings_preserved")==2
         and report.get("new_accepted_scientific_originals")==0
         and report.get("real_scientific_first_use") is False
         and report.get("new_learned_mechanism_implemented") is False
         and report.get("optimizer_promotions")==0
         and report.get("accepted_ref_mutations")==0
         and report.get("new_scheduler") is False
         and report.get("Codex_calls")==0
         and report.get("paid_model_calls")==0, "PRIOR_SOURCE_AUTHORITY_VIOLATION")
    selection=report.get("source_driven_autonomous_selection")
    rec=report.get("original_source_records")
    need(type(selection) is dict and type(rec) is list and len(rec)==2
         and [x.get("experiment") for x in rec]==["F116-O","F117-O"]
         and all(type(x.get("unrecovered_loss_millionths")) is int and
                 x["unrecovered_loss_millionths"]>0 for x in rec)
         and f126.choose_next(rec)==selection,
         "F126_OUTCOME_DECISION_NOT_RECOMPUTABLE")
    if not scheduled:
        need(selection.get("source_experiment")==s["expected_selected_source_original"]
             and selection.get("mechanism_problem")==s["expected_development_problem"]
             and selection.get("priority_gap_millionths")==s["expected_loss_millionths"],
             "PINNED_RESEARCH_PROBLEM_DRIFT")
    need(selection.get("mechanism_problem")=="SHARED_NODE_BINDING",
         "GRAMMAR_NOT_FROZEN_FOR_UNEXPECTED_PROBLEM")
    c=report.get("heldout_development_probe")
    need(type(c) is dict and c.get("cases")==32
         and c.get("exact_oracle_paired_correct")==32
         and c.get("pairwise_shortcut_paired_correct")==0,
         "PREVIOUS_CHALLENGE_NOT_REPRODUCIBLE")
    return {"verified_prior_run":old,"verified_artifact_sha256":measured,
            "selected_development_problem":selection,
            "source_original_losses":rec,
            "development_only":True,
            "scheduled_cross_run_real":scheduled}

def generated_programs():
    # Mechanism search is executable AST synthesis from frozen combinator grammar,
    # not handing the evaluator a privileged equality bit or answer.
    programs=[]
    for start,join,end in itertools.product((False,True),repeat=3):
        ast={"grammar":"typed-3-hop-join-v1",
             "start_anchor":start,"bind_intermediate_nodes":join,
             "target_anchor":end}
        programs.append({"ast":ast,"ast_sha256":sha(ast),
                         "complexity":int(start)+int(join)+int(end)})
    need(len(programs)==8 and len({p["ast_sha256"] for p in programs})==8,
         "SYNTHESIS_GRAMMAR_COLLAPSED")
    return programs

def execute_ast(ast,case,edges):
    need(type(ast) is dict and ast.get("grammar")=="typed-3-hop-join-v1"
         and all(type(ast.get(k)) is bool for k in
                 ("start_anchor","bind_intermediate_nodes","target_anchor")),
         "UNQUALIFIED_GENERATED_PROGRAM")
    # Exhaustive bounded relational algebra. The compiled mechanism sees only
    # source graph edges, role sequence and the public query endpoints.
    matches=[e for e in edges if e[1]==case["roles"][0] and
             (not ast["start_anchor"] or e[0]==case["start"])]
    for role in case["roles"][1:]:
        new=[(path+(e,)) for path in matches for e in edges
             if e[1]==role and
             (not ast["bind_intermediate_nodes"] or path[-1][2]==e[0])]
        need(len(new)<=4096,"EXECUTABLE_GRAMMAR_BUDGET")
        matches=new
    return any((not ast["target_anchor"] or path[-1][2]==case["target"])
               for path in matches)

def stable_rank(seed,label):
    return int.from_bytes(hashlib.sha256((str(seed)+"/"+label).encode()).digest()[:8],"big")

def challenge(seed,phase):
    need(phase in ("TRAIN","CONFIRM")
         and ((phase=="TRAIN" and 140000<=seed<=140015)
              or (phase=="CONFIRM" and 140100<=seed<=140163)),
         "TRAIN_HOLDOUT_PROVENANCE")
    root="f127/"+phase+"/"+str(seed)+"/"
    n=lambda name:root+name
    start,end=n("query-src"),n("query-dst")
    # Paired positive/negative differ only in the target's 3rd edge assignment.
    # The global role histogram AND all graph node in/out degrees are preserved
    # by a two-edge terminal swap; offpath paths are identically present.
    positive=[
        (start,"r0",n("junction-1")),(n("junction-1"),"r1",n("junction-2")),
        (n("junction-2"),"r2",end),(n("unlinked-subject"),"r2",n("false-target")),
        # Real full chain from correct start to an INCORRECT terminal.
        (start,"r0",n("wrong-end-a")),(n("wrong-end-a"),"r1",n("wrong-end-b")),
        (n("wrong-end-b"),"r2",n("wrong-end")),
        # Real full chain from an INCORRECT start to correct target.
        (n("wrong-start"),"r0",n("wrong-start-a")),
        (n("wrong-start-a"),"r1",n("wrong-start-b")),
        (n("wrong-start-b"),"r2",end),
        # Unanchored valid chain: global evidence not enough.
        (n("elsewhere-a"),"r0",n("elsewhere-b")),
        (n("elsewhere-b"),"r1",n("elsewhere-c")),
        (n("elsewhere-c"),"r2",n("elsewhere-d"))]
    negative=[(a,b,(n("false-target") if a==n("junction-2") and b=="r2" else
                      end if a==n("unlinked-subject") and b=="r2" else c))
              for a,b,c in positive]
    # Seeded both-arm offpath variation; no path from start to query target.
    for j in range(seed%3):
        extra=(n("noise-"+str(j)),"unused-role-"+str(j),n("noise-end-"+str(j)))
        positive.append(extra);negative.append(extra)
    order=lambda es:sorted(es,key=lambda e:stable_rank(seed,"/".join(e)))
    case={"seed":seed,"phase":phase,"start":start,"target":end,
          "roles":["r0","r1","r2"],"positive":order(positive),
          "negative":order(negative)}
    degree=lambda es:sorted([e[0] for e in es])+sorted([e[2] for e in es])
    need(sorted(e[1] for e in case["positive"])==
         sorted(e[1] for e in case["negative"])
         and degree(case["positive"])==degree(case["negative"]),
         "CONTROLLED_GRAPH_MARGINAL_DRIFT")
    upper={"grammar":"typed-3-hop-join-v1","start_anchor":True,
           "bind_intermediate_nodes":True,"target_anchor":True}
    need(execute_ast(upper,case,case["positive"])
         and not execute_ast(upper,case,case["negative"]),
         "ORIGINAL_SHARED_NODE_FALSIFICATION_MISSING")
    return case

def evaluate(program,phase):
    seeds=range(140000,140016) if phase=="TRAIN" else range(140100,140164)
    scored=[]
    for seed in seeds:
        case=challenge(seed,phase)
        yes=execute_ast(program["ast"],case,case["positive"])
        no=execute_ast(program["ast"],case,case["negative"])
        scored.append({"seed":seed,"graph_sha256":sha(case),
                       "positive_correct":bool(yes),
                       "negative_correct":not no,
                       "paired_correct":bool(yes and not no)})
    return {"count":len(scored),"graph_sha256":sha([r["graph_sha256"] for r in scored]),
            "positive_correct":sum(x["positive_correct"] for x in scored),
            "negative_correct":sum(x["negative_correct"] for x in scored),
            "paired_correct":sum(x["paired_correct"] for x in scored)}

def synthesize(previous,source,run_id,event):
    protocol,freeze_sha=frozen()
    need(type(previous) is dict
         and previous.get("development_only") is True
         and previous.get("verified_prior_run")<run_id
         and previous.get("selected_development_problem",{}).get("mechanism_problem")==
         "SHARED_NODE_BINDING"
         and type(source) is str and HEX40.fullmatch(source)
         and type(run_id) is int and run_id>0
         and event in ("pull_request","schedule","push","workflow_dispatch")
         and (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source),
         "CURRENT_SOURCE_OR_PRIOR_RECORD_INVALID")
    if event=="schedule":
        need(previous.get("scheduled_cross_run_real") is True,
             "PR_RUN_CANNOT_CLAIM_REAL_UNATTENDED_CONTINUITY")
    else:
        need(previous.get("scheduled_cross_run_real") is False,
             "SCHEDULED_STATE_CANNOT_BE_PR_FIXTURE")
    programs=generated_programs()
    train=[{**program,"training":evaluate(program,"TRAIN")} for program in programs]
    best=sorted(train,key=lambda p:(-p["training"]["paired_correct"],
                                    p["complexity"],p["ast_sha256"]))[0]
    heldout=evaluate(best,"CONFIRM")
    oracle=next(p for p in programs if p["complexity"]==3)
    ceiling=evaluate(oracle,"CONFIRM")
    require_64=heldout["paired_correct"]==64
    return {"schema":SCHEMA,"source_sha":source,"run_id":run_id,"event":event,
            "freeze_sha256":freeze_sha,
            "prior_f126_run_id":previous["verified_prior_run"],
            "prior_f126_report_sha256":previous["verified_artifact_sha256"],
            "synthesized_problem":previous["selected_development_problem"],
            "generated_executable_programs":train,
            "program_count":8,"selection_from_training_only":True,
            "selected_ast":best["ast"],"selected_ast_sha256":best["ast_sha256"],
            "selected_complexity":best["complexity"],
            "source_only_heldout":heldout,"exact_symbolic_ceiling":ceiling,
            "frozen_heldout_mechanism_criterion_passed":require_64,
            "independent_scientific_mechanism_invented":False,
            "general_algorithmic_invention_proven":False,
            "genuine_two_scheduled_run_continuity_proven":False,
            "scientific_originals_dispatched":0,
            "scientific_first_use_authorized":False,
            "accepted_ref_mutations":0,"optimizer_promotions":0,
            "Codex_calls":0,"paid_model_calls":0,"new_schedulers":0,
            "ckb_plane_contact":False,"cloudflare_writes":0,
            "mind_palace_writes":0}

def main():
    parser=argparse.ArgumentParser()
    for key in ("run-json","artifacts-json","ubuntu-report","ubuntu-receipt",
                "windows-report","windows-receipt","source-ref","event","output"):
        parser.add_argument("--"+key,required=True)
    parser.add_argument("--run-id",required=True,type=int)
    args=parser.parse_args()
    read=lambda path:Path(path).read_bytes()
    protocol,_=frozen()
    previous=read_previous(f126.strict(read(args.run_json)),
        f126.strict(read(args.artifacts_json)),
        read(args.ubuntu_report),read(args.ubuntu_receipt),
        read(args.windows_report),read(args.windows_receipt),
        args.run_id,args.event,protocol)
    output=synthesize(previous,args.source_ref,args.run_id,args.event)
    file=Path(args.output)
    need(file.parent.is_dir() and not file.exists(),"OUTPUT_NOT_IMMUTABLE")
    with file.open("xb") as f:f.write(canonical(output))

if __name__=="__main__":
    try:main()
    except (Blocked,f126.Blocked,f118.Quarantined,ValueError,OSError,TypeError,KeyError) as e:
        print("F127_EVIDENCE_DRIVEN_PROGRAM_SYNTHESIS_QUARANTINED "+str(e),file=sys.stderr)
        raise SystemExit(1)
