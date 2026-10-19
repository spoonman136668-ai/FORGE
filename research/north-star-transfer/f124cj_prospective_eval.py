"""F124-CJ one-time internal prospective unfamiliar E/F development.

Source birth is a separate prior GitHub job; this evaluator NEVER imports
the source generator or private symbolic oracle. Each child receives ONLY
one public FIT/CHECK+graph JSON, with source family, private generator
parameters and original birth seed omitted. All 24 cases, seven frozen
arms, five fresh full OS processes per arm (840) and 168 preflights kept.
Scientific negatives, abstentions and every mismatched native task count.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCE_PUBLIC_ENV="F124CJ_PUBLIC_CASE_DIRECTORY"
ARMS=("AZ","BQ","BX","BZ","CA","CB","CC")
CASES=tuple(range(930000,930012))+tuple(range(931000,931012))
REPS=5
BASE=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
DELTA=[0.,0.]


def need(ok,msg):
    if not ok:raise RuntimeError("F124CJ_PROVIDER_ORIGINAL_"+msg)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    need(spec is not None and spec.loader is not None,"MODULE_NOT_PRESENT")
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m


def digest(value):
    return hashlib.sha256(
        json.dumps(value,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()


def positive_decisions(graphs,word,decoder):
    decisions=[]
    for g in graphs:
        current=g["start"]
        carry=None
        matched=True
        for role in g["roles"]:
            edges=[e for e in g["edges"]
                   if e["from"]==current and e["role"]==role]
            if len(edges)!=1:
                matched=False
                break
            edge=edges[0]
            y=sum(bit<<i for i,bit in enumerate(edge["src_bits"]))
            x=decoder.inverse(y,word)
            if carry is not None and carry!=x:
                matched=False
                break
            carry=sum(bit<<i for i,bit in enumerate(edge["dst_bits"]))
            current=edge["to"]
        decisions.append(bool(matched and current==g["target"]))
    return decisions


def one(case,arm,capture):
    need(sys.platform=="linux" and case in CASES and arm in ARMS,
         "ONLY_EXACT_LINUX_NATIVE_SOURCE_NEUTRAL")
    original_public_dir=os.environ.get(SOURCE_PUBLIC_ENV)
    need(type(original_public_dir) is str and bool(original_public_dir),
         "BIRTH_JOB_SANITIZED_PUBLIC_CASE_DIRECTORY_REQUIRED")
    original_json=Path(original_public_dir)/("case-"+str(case)+".json")
    witness=json.loads(original_json.read_text())
    need(witness["schema"]=="mass.f124cj.public-model-only-case.v1"
         and witness["task_id"]==case
         and witness["no_oracle_or_seed_passed_to_model"] is True,
         "SOURCE_BIRTH_PUBLIC_CASE_NOT_BOUNDED")
    task=witness["public_task"]
    need(set(task)=={"task_id","FIT","CHECK","positive","hard_negative"}
         and task["task_id"]==case and len(task["FIT"])==40
         and len(task["CHECK"])==8
         and witness["public_task_sha256"]==digest(task),
         "NO_ORACLE_SOURCE_OR_PRIVATE_METADATA_IN_MODEL_INPUT")
    graphs=(task["positive"],task["hard_negative"])
    graph_sha=digest({"FIT":task["FIT"],"CHECK":task["CHECK"],"graphs":graphs})
    original=digest(graphs)
    sys.path.insert(0,str(ROOT/"nativeevidence"))
    import f124ag_transition_models as native
    observed=[]
    original_code=native.ygg_transition.__code__
    def trace(frame,event,arg):
        if frame.f_code is original_code:
            if event=="call":
                observed.append({"graph":copy.deepcopy(frame.f_locals["g"])})
            elif event=="return":
                need(observed and "result" not in observed[-1],
                     "NATIVE_ACTUAL_CALL_ORDER")
                observed[-1]["result"]=arg
    if capture:sys.setprofile(trace)
    route="abstain"
    calls=0
    decisions=[False,False]
    receipts={}
    try:
        if arm=="AZ":
            import f124az_joint_public_inverse as az
            demo=[{"input_bits":[(x>>i)&1 for i in range(16)],
                   "output_bits":[(y>>i)&1 for i in range(16)]}
                  for x,y in task["FIT"]+task["CHECK"]]
            trained=az.train(demo,"SOURCE_BLIND_INTERNAL_EF",0)
            route=trained["choice"]
            outcomes=[az.score(g,list(BASE),list(DELTA),trained,demo)
                      for g in graphs]
            calls=sum(x[1] is not None for x in outcomes)
            decisions=[bool(x[0]>=0) for x in outcomes]
            receipts={"forced_AZ_native_route":False,
                      "actual_original_AZ_route":route}
        else:
            BQ=load("CA_original_BQ_frozen",HERE/"f124bq_program_learner.py")
            view=load("CA_original_native_view",HERE/"f124br_native_view.py")
            import types
            if arm=="BQ":
                prog,r,plausible=BQ.learn(task["FIT"],task["CHECK"])
                route="BQ" if prog is not None else "abstain"
                adapter=BQ
                if prog is not None:
                    decisions=[BQ.causal_consensus(g,prog,plausible)[0]
                               for g in graphs]
                receipts={"trained_40_FIT":True,"CHECK_veto_only":True,
                          "state_bits":32,"receipt":r}
            elif arm=="BX":
                BX=load("CA_frozen_BX",HERE/"f124bx_learned_flag.py")
                prog,r,plausible=BX.learn(task["FIT"],task["CHECK"],BQ)
                route="BX" if prog is not None else "abstain"
                adapter=types.SimpleNamespace(
                    inverse=lambda y,p:BX.inverse(y,p,BQ))
                if prog is not None:
                    decisions=[BX.causal_consensus(g,prog,plausible,BQ)[0]
                               for g in graphs]
                receipts={"trained_40_FIT":True,"CHECK_veto_only":True,
                          "state_bits":32,"receipt":r}
            elif arm=="BZ":
                BZ=load("CA_frozen_BZ",HERE/"f124bz_binding_candidate.py")
                prog,r=BZ.learn(task["FIT"],task["CHECK"])
                route="BZ" if prog is not None else "abstain"
                adapter=BZ
                if prog is not None:
                    decisions=positive_decisions(graphs,prog,adapter)
                receipts={"trained_40_FIT":True,"CHECK_veto_only":True,
                          "state_bits":32,"receipt":r}
            elif arm=="CA":
                CA=load("CB_frozen_trained_control",HERE/"f124ca_trained_symbol_control.py")
                prog,r=CA.train(task["FIT"],task["CHECK"])
                route="CA" if prog is not None else "abstain"
                adapter=CA
                if prog is not None:
                    decisions=positive_decisions(graphs,prog,adapter)
                receipts={"trained_40_FIT":True,"CHECK_veto_only":True,
                          "state_bits":32,"receipt":r}
            elif arm=="CB":
                CB=load("CC_unchanged_original_CB",HERE/"f124cb_dual_link_learner.py")
                prog,r=CB.learn(task["FIT"],task["CHECK"])
                route="CB" if prog is not None else "abstain"
                adapter=CB
                if prog is not None:
                    decisions=positive_decisions(graphs,prog,adapter)
                receipts={"trained_40_FIT":True,"CHECK_veto_only":True,
                          "state_bits":32,"receipt":r}
            else:
                CC=load("CC_independently_trained_two_link",HERE/"f124cc_trained_two_link_control.py")
                prog,r=CC.train(task["FIT"],task["CHECK"])
                route="CC" if prog is not None else "abstain"
                adapter=CC
                if prog is not None:
                    decisions=positive_decisions(graphs,prog,adapter)
                receipts={"trained_40_FIT":True,"CHECK_veto_only":True,
                          "state_bits":32,"receipt":r}
            if prog is not None:
                scored=view.score_exact_native_pair(
                    graphs,adapter,prog,native,BASE,DELTA)
                calls=len(scored)
        need(digest(graphs)==original,"SCIENTIFIC_GRAPH_INPUT_MUTATED")
    finally:
        if capture:sys.setprofile(None)
    if capture:need(calls==len(observed),"UNFORCED_NATIVE_PROFILER_ACCOUNTING")
    receipt={
        "schema":"mass.f124cj.original-prospective-internal-EF-native-v1",
        "case":case,"arm":arm,"source_task_sha256":graph_sha,
        "natural_route":route,"actual_native_calls":calls,
        "positive_accepted":bool(decisions[0]),
        "hard_false_positive":bool(decisions[1]),
        "source_family_label_used_by_learner":False,
        "private_oracle_passed_to_model":False,
        "original_internal_prospective_development":True,
        "old_BV_CE_original_source_reused":False,
        "protected_128_cohorts_opened":False,
        "training":receipts
    }
    if capture:
        receipt["original_native_input_hashes"]=[
            digest(x["graph"]) for x in observed]
        receipt["original_native_full_output_hashes"]=[
            digest(x["result"]) for x in observed]
    return receipt


def measure_process(case,arm,capture=False):
    import resource
    args=[sys.executable,"-B",str(Path(__file__).resolve()),
          "--child","--case",str(case),"--arm",arm]
    if capture:args.append("--capture")
    env=dict(os.environ)
    if arm in ("BZ","CA","BX","CB","CC"):
        env["PYTHONMALLOC"]="malloc"
    else:
        env.pop("PYTHONMALLOC",None)
    # Temporary files prevent output buffering deadlock; wait4 captures
    # genuinely whole process (Python boot+imports+training+native scorer).
    with tempfile.TemporaryFile(mode="w+t") as stdout, tempfile.TemporaryFile(mode="w+t") as stderr:
        child=subprocess.Popen(args,cwd=ROOT,env=env,
                               stdout=stdout,stderr=stderr,text=True)
        pid,status,usage=os.wait4(child.pid,0)
        need(pid==child.pid,"ORIGINAL_CHILD_PID")
        child.returncode=os.waitstatus_to_exitcode(status)
        stdout.seek(0);stderr.seek(0)
        text=stdout.read();err=stderr.read()
        need(child.returncode==0,"REAL_PROCESS_"+str(case)+"_"+arm+":"+err[-2200:])
    obj=json.loads(text)
    need(obj["case"]==case and obj["arm"]==arm
         and not obj["old_BV_CE_original_source_reused"]
         and not obj["protected_128_cohorts_opened"],
         "SOURCE_IDENTITY")
    obj["complete_process_cpu_ns"]=round(
        (usage.ru_utime+usage.ru_stime)*1e9)
    obj["complete_OS_peak_RSS_bytes"]=usage.ru_maxrss*1024
    obj["complete_process_cpu_covers_boot_imports_training_and_native"]=True
    obj["allocator"]=env.get("PYTHONMALLOC","default")
    need(obj["complete_process_cpu_ns"]>0 and
         obj["complete_OS_peak_RSS_bytes"]>0,"VALID_FULL_PROCESS_COST")
    journal=os.environ.get("F124CJ_ORIGINAL_APPEND_JOURNAL")
    need(type(journal) is str and bool(journal),
         "REQUIRED_DURABLE_ORIGINAL_RESULT_JOURNAL")
    with open(journal,"a",encoding="utf8") as handle:
        handle.write(json.dumps({
            "schema":"mass.f124cj.original-append-only-process-receipt.v1",
            "is_original_native_preflight":bool(capture),
            "original_complete_process_measurement":obj
        },sort_keys=True)+"\n")
        handle.flush()
        os.fsync(handle.fileno())
    return obj


def overview(pre,samples):
    need(len(pre)==24*7 and len(samples)==24*7*REPS,
         "ALL_168_NATIVE_PREFLIGHTS_AND_840_REAL_OS_PROCESSES_REQUIRED")
    original={(x["case"],x["arm"]):x for x in pre}
    need(len(original)==168,"ALL_FROZEN_CASE_ARM_PREFLIGHTS_UNIQUE")
    cases={}
    failures={
      "CB_hard_false_positives":[],
      "loss_of_trained_or_AZ_accepted_positive":[],
      "CB_CC_unmatched_actual_native_work":[],
      "no_fully_trained_eligible_equal_native_control":[],
      "full_CPU_or_peak_RSS_regression":[],
      "some_original_controls_abstained":[]}
    for case in CASES:
        observed={arm:original[case,arm] for arm in ARMS}
        need(len({obs["source_task_sha256"] for obs in observed.values()})==1,
             "ALL_MODELS_ACTUAL_SAME_PUBLIC_TASK")
        cb=observed["CB"]
        cc=observed["CC"]
        equals=lambda arm:bool(
            observed[arm]["actual_native_calls"]==2
            and cb["actual_native_calls"]==2
            and observed[arm].get("original_native_input_hashes")==
                cb.get("original_native_input_hashes")
            and observed[arm].get("original_native_full_output_hashes")==
                cb.get("original_native_full_output_hashes"))
        eligible=[arm for arm in ("BQ","BX","BZ","CA","CC") if equals(arm)]
        CB_CC_same=("CC" in eligible)
        if cb["hard_false_positive"]:
            failures["CB_hard_false_positives"].append(case)
        if any(observed[arm]["positive_accepted"]
               and not cb["positive_accepted"] for arm in ARMS if arm!="CB"):
            failures["loss_of_trained_or_AZ_accepted_positive"].append(case)
        if not CB_CC_same:
            failures["CB_CC_unmatched_actual_native_work"].append(case)
        if not eligible:
            failures["no_fully_trained_eligible_equal_native_control"].append(case)
        if any(obs["natural_route"]=="abstain" for obs in observed.values()):
            failures["some_original_controls_abstained"].append(case)
        cost={}
        for arm in ARMS:
            rows=[row for row in samples if row["case"]==case and row["arm"]==arm]
            need(len(rows)==REPS,"FIVE_ORIGINAL_PROCESS_SAMPLES_PER_ARM_CASE")
            baseline=observed[arm]
            expected_alloc="malloc" if arm in ("BZ","CA","BX","CB","CC") else "default"
            need(all(row["source_task_sha256"]==baseline["source_task_sha256"]
                     and row["natural_route"]==baseline["natural_route"]
                     and row["actual_native_calls"]==baseline["actual_native_calls"]
                     and row["positive_accepted"]==baseline["positive_accepted"]
                     and row["hard_false_positive"]==baseline["hard_false_positive"]
                     and row["allocator"]==expected_alloc
                     and row["complete_process_cpu_covers_boot_imports_training_and_native"]
                     for row in rows),
                 "FROZEN_SCORER_OR_COMPLETE_OS_PROCESS_DRIFT")
            cpu=[row["complete_process_cpu_ns"] for row in rows]
            rss=[row["complete_OS_peak_RSS_bytes"] for row in rows]
            cost[arm]={
                "complete_CPU_samples_ns":cpu,
                "complete_OS_peak_RSS_samples_bytes":rss,
                "median_complete_CPU_ns":statistics.median(cpu),
                "median_peak_RSS_bytes":statistics.median(rss),
                "max_peak_RSS_bytes":max(rss),
                "natural_route":baseline["natural_route"],
                "positive_accepted":baseline["positive_accepted"],
                "hard_false_positive":baseline["hard_false_positive"],
                "actual_native_calls":baseline["actual_native_calls"],
                "real_native_input_SHA256":baseline.get("original_native_input_hashes",[]),
                "real_native_return_SHA256":baseline.get("original_native_full_output_hashes",[])
            }
        cand=cost["CB"]
        budget=bool(CB_CC_same and all(
              cand["median_complete_CPU_ns"]<=cost[arm]["median_complete_CPU_ns"]
              and cand["median_peak_RSS_bytes"]<=cost[arm]["median_peak_RSS_bytes"]
              and cand["max_peak_RSS_bytes"]<=cost[arm]["max_peak_RSS_bytes"]
              for arm in eligible))
        if eligible and not budget:
            failures["full_CPU_or_peak_RSS_regression"].append(case)
        cases[case]={
          "E2_or_F2_from_reserved_case_identity_only":"E2" if case<931000 else "F2",
          "all_original_source_sha256":cb["source_task_sha256"],
          "actual_CB_CC_native_work_identical":CB_CC_same,
          "all_fully_trained_same_native_controls":eligible,
          "CB_complete_CPU_RSS_nonregressing":budget,
          "all_trained_arm_original_metrics":cost}
    family_summary={}
    for family,lo in (("E2",930000),("F2",931000)):
        selected=list(range(lo,lo+12))
        def correct(arm):
            return sum(original[case,arm]["positive_accepted"]
                       and not original[case,arm]["hard_false_positive"]
                       for case in selected)
        trained={arm:correct(arm) for arm in ("BQ","BX","BZ","CA","CC")}
        candidate=correct("CB")
        best=max(trained.values())
        family_summary[family]={
           "original_case_ids":selected,
           "CB_correct_paired_cases":candidate,
           "original_fully_trained_control_correct_pairs":trained,
           "strongest_trained_control_correct_pairs":best,
           "CB_net_correct_pairs_over_strongest_trained_control":candidate-best,
           "required_net_gain":2,
           "zero_CB_hard_false_positives":all(
                not original[case,"CB"]["hard_false_positive"] for case in selected),
           "zero_accepted_positive_losses":all(
                case not in failures["loss_of_trained_or_AZ_accepted_positive"]
                for case in selected),
           "all_CB_CC_actual_native_work_matched":all(
                cases[case]["actual_CB_CC_native_work_identical"]
                for case in selected),
           "all_complete_CPU_RSS_nonregressing":all(
                cases[case]["CB_complete_CPU_RSS_nonregressing"]
                for case in selected)}
    scientifically_eligible=bool(
       all(v["CB_net_correct_pairs_over_strongest_trained_control"]>=2
           and v["zero_CB_hard_false_positives"]
           and v["zero_accepted_positive_losses"]
           and v["all_CB_CC_actual_native_work_matched"]
           and v["all_complete_CPU_RSS_nonregressing"]
           for v in family_summary.values()))
    return {
        "schema":"mass.f124cj.original-internal-prospective-EF-840-OS-process.v1",
        "original_168_native_preflights":pre,
        "original_840_full_OS_process_measurements":samples,
        "all_24_prospective_case_outcomes":cases,
        "E2_F2_full_family_summaries":family_summary,
        "all_original_failures_including_unmatched_and_abstained":failures,
        "frozen_scientific_development_gate_passed":scientifically_eligible,
        "source_origin_internally_authored_not_external":True,
        "independent_research_group_replication_claimed":False,
        "old_BV_924_925_and_CE_926_927_firstuse":False,
        "new_E_F_128x2_protected_cohorts_opened":False,
        "optimizer_or_production_promoted":False,
        "science_accepted":False}

def validate_born_packet(path):
    born=json.loads(path.read_text())
    need(born["schema"]=="mass.f124cj.original-sealed-internal-EF-birth.v1"
         and len(born["original_all_24_firstuse_cases"])==24
         and born["original_source_identity"]=="INTERNALLY_AUTHORED_NOT_EXTERNAL"
         and born["case_birth_before_evaluation"] is True
         and born["model_or_native_scoring_executed"] is False
         and not born["new_EF_replication_cohorts_created"]
         and born["BV_924_925_unchanged"] and born["CE_926_927_unchanged"],
         "SOURCE_JOB_ORIGINAL_BIRTH_BEFORE_EVAL_REQUIRED")
    hashed=digest(born["original_all_24_firstuse_cases"])
    need(hashed==born["original_all_case_packet_sha256"],
         "IMMUTABLE_EF_BIRTH_CASE_HASH")
    ids=[case["task_identity"] for case in born["original_all_24_firstuse_cases"]]
    need(ids==list(CASES) and len(set(ids))==24,
         "ALL_24_FROZEN_SOURCE_IDS_REQUIRED")
    for case in born["original_all_24_firstuse_cases"]:
        need(case["internally_authored_not_external"]
             and not case["replication_cohort_opened"]
             and not case["prior_924_925_926_927_source_reused"]
             and case["symbolic_ground_truth"]==
                 {"positive":True,"hard_negative":False}
             and case["public_task_sha256"]==digest(case["public_task"]),
             "PRIVATE_ORACLE_SOURCE_FIRSTBIRTH_DIGEST_DRIFT")
    return born


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--child",action="store_true")
    ap.add_argument("--case",type=int,choices=CASES)
    ap.add_argument("--arm",choices=ARMS)
    ap.add_argument("--capture",action="store_true")
    ap.add_argument("--birth",type=Path)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if args.child:
        need(args.case is not None and args.arm is not None,"CHILD_ARGS")
        print(json.dumps(one(args.case,args.arm,args.capture),sort_keys=True))
        return
    need(args.birth is not None and args.out is not None,
         "REQUIRE_UNCONSUMED_EF_BIRTH_ARTIFACT")
    born=validate_born_packet(args.birth)
    with tempfile.TemporaryDirectory(prefix="f124cj-public-no-oracle-") as directory:
        public_dir=Path(directory)
        for case in born["original_all_24_firstuse_cases"]:
            public={
                "schema":"mass.f124cj.public-model-only-case.v1",
                "task_id":case["task_identity"],
                "public_task":case["public_task"],
                "public_task_sha256":case["public_task_sha256"],
                "no_oracle_or_seed_passed_to_model":True}
            (public_dir/("case-"+str(case["task_identity"])+".json")).write_text(
                json.dumps(public,sort_keys=True))
        os.environ[SOURCE_PUBLIC_ENV]=str(public_dir)
        pre=[measure_process(case,arm,True)
             for case in CASES for arm in ARMS]
        samples=[]
        for iteration in range(REPS):
            for case in CASES:
                for arm in (ARMS if iteration%2==0 else ARMS[::-1]):
                    samples.append(measure_process(case,arm,False))
        result=overview(pre,samples)
    result["original_birth_Git_head"]=born["original_source_git_head"]
    result["original_birth_source_blob"]=born["original_source_blob_sha"]
    result["original_birth_manifest_SHA256"]=born["original_all_case_packet_sha256"]
    result["original_birth_verified_before_scorer"]=True
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open("x",encoding="utf8") as out:
        json.dump(result,out,sort_keys=True,indent=2)
        out.write("\n")
    for family,value in result["E2_F2_full_family_summaries"].items():
        print("F124CJ_"+family+"_CB_CORRECT_PAIRS="+str(value["CB_correct_paired_cases"]))
        print("F124CJ_"+family+"_BEST_TRAINED_CORRECT_PAIRS="+str(value["strongest_trained_control_correct_pairs"]))
        print("F124CJ_"+family+"_NET_TRANSFER_PAIRS="+str(value["CB_net_correct_pairs_over_strongest_trained_control"]))
        print("F124CJ_"+family+"_ALL_CB_CC_SAME_NATIVE="+str(value["all_CB_CC_actual_native_work_matched"]))
        print("F124CJ_"+family+"_RESOURCE_NONREGRESSION="+str(value["all_complete_CPU_RSS_nonregressing"]))
    for key,failed in result["all_original_failures_including_unmatched_and_abstained"].items():
        print("F124CJ_"+key.upper()+"="+str(len(failed)))
    print("F124CJ_ORIGINAL_NATIVE_PREFLIGHTS=168")
    print("F124CJ_FRESH_COMPLETE_OS_PROCESSES=840")
    print("F124CJ_PROSPECTIVE_DEVELOPMENT_SCIENCE_GATE="+str(result["frozen_scientific_development_gate_passed"]))
    print("F124CJ_EXTERNALLY_INDEPENDENT_SOURCE_AUTHORSHIP=false")
    print("F124CJ_PROTECTED_FIRSTUSE=0")

if __name__=="__main__":
    main()
