#!/usr/bin/env python3
"""F124CN frozen public mathematical DEV evaluation, NOT an original science run."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, pathlib, random, subprocess, sys, time, tracemalloc
import learn

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
ORIGINAL=HERE.parent/"f124cj_internal_source.py"
FREEZE=HERE/"FROZEN_PROTOCOL.json"
SOURCE_BLOB="4e7bbd8f93dab1c7242a9374c75731302b034f31"

def need(ok,msg):
    if not ok:raise AssertionError("F124CN_FAIL_CLOSED_"+msg)
def digest(data):
    return hashlib.sha256(learn.canonical(data)).hexdigest()
def source_module():
    got=subprocess.check_output(["git","hash-object",str(ORIGINAL)],cwd=ROOT,text=True).strip()
    need(got==SOURCE_BLOB,"PINNED_ORIGINAL_SOURCE_CHANGED")
    spec=importlib.util.spec_from_file_location("f124cn_evaluator_only_source",ORIGINAL)
    src=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(src)
    need(src.FAMILIES=={"E2":930000,"F2":931000},"SOURCE_CONTRACT")
    return src
def cold(model,x):
    cp=learn.snapshot(model)
    code=("import sys,json,learn; model=learn.restore(sys.stdin.buffer.read()); "
          "print(json.dumps({'out0':learn.predict(model,int(sys.argv[1])),"
          "'canonical':learn.snapshot(model).decode()},sort_keys=True))")
    proc=subprocess.run([sys.executable,"-B","-c",code,str(x)],
        cwd=HERE,input=cp,capture_output=True,timeout=20,check=True)
    result=json.loads(proc.stdout)
    need(result["out0"]==learn.predict(model,x)
         and result["canonical"]==cp.decode(),"TRUE_COLD_RESTORE_ACTION_DRIFT")
    return len(cp)
def run():
    freeze=json.loads(FREEZE.read_text())
    need(freeze["schema"]=="forge.itd02.f124cn.source_blind_multistage_E2_out0_dev.v1",
         "FROZEN_PROTOCOL")
    src=source_module()
    entries=[];resources=[]
    i=0
    for group in freeze["roster"]["families"]:
        name=group["name"]
        for param in group["parameters"]:
            xs=random.Random(763000+101*i).sample(range(65536),304)
            true=[src.forward(name,x,param) for x in xs]
            # Source emitter uses only authored artificial public x and params;
            # does not call source.task/original source-birth; FIT noise is predeclared.
            pairs=[(x,y^(1 if j in (1,5,12,19,24,35) else 0))
                   for j,(x,y) in enumerate(zip(xs[:40],true[:40]))]
            check=list(zip(xs[40:48],true[40:48]))
            dev=list(zip(xs[48:],true[48:]))
            need(len(set(xs))==304,"PUBLIC_ROSTER_UNIQUE")
            tracemalloc.start()
            start=time.process_time_ns()
            candidate,candidate_fit=learn.train(pairs)
            elapsed=time.process_time_ns()-start
            peak=tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            base4,base4_fit=learn.conventional_four_parent(pairs)
            base2,base2_fit=learn.conventional_two_parent(pairs)
            modal=learn.constant(pairs)
            ablated=learn.ablation(pairs)
            counts={}
            predictors={
                "candidate":lambda x:learn.predict(candidate,x),
                "matched_four":lambda x:learn.predict(base4,x),
                "two_parent":lambda x:learn.predict_two(base2,x),
                "constant":lambda x:modal,
                "no_context_ablation":lambda x:learn.predict_ablation(ablated,x)}
            for title,fn in predictors.items():
                counts[title]=sum(fn(x)==(y&15) for x,y in dev)
            need(counts["candidate"]==counts["matched_four"],"MATCHED_MODEL_DISAGREEMENT")
            need(candidate==base4,"STRONG_CONVENTIONAL_STRUCTURAL_PARAM_DISAGREEMENT")
            check_errors=sum(learn.predict(candidate,x)!=(y&15) for x,y in check)
            model_bytes=cold(candidate,dev[0][0])
            entries.append({
                "family":name,"artificial_setting":i,"model_parameters_public_fit_only":list(candidate),
                "source_original_FIT_never_replayed":True,
                "fit_output0_errors":candidate_fit["fit_errors"],
                "check_output0_errors":check_errors,
                "admitted_development_only":candidate_fit["fit_errors"]<=6 and check_errors==0,
                "dev_accuracy_exact_numerators_256":counts,
                "original_science_firstuse":False,
                "candidate_and_same_family_conventional_exact_tie":True,
                "no_native_architecture_advantage":True,
                "checkpoint_bytes":model_bytes,
                "fit_row_scans":candidate_fit["row_scans"],
                "fully_trained_same_family_search_scans":base4_fit["row_scans"],
                "trained_two_parent_search_scans":base2_fit["row_scans"]})
            resources.append({"family":name,"artificial_setting":i,
                              "candidate_train_cpu_ns":elapsed,
                              "candidate_train_peak_tracemalloc_bytes":peak,
                              "note":"NOT whole-process or native parity"})
            i+=1
    e=[z for z in entries if z["family"]=="E2"]
    f=[z for z in entries if z["family"]=="F2"]
    e_qual=sum(z["dev_accuracy_exact_numerators_256"]["candidate"]>=243 for z in e)
    e_beats=sum(z["dev_accuracy_exact_numerators_256"]["candidate"]>
                z["dev_accuracy_exact_numerators_256"]["two_parent"] for z in e)
    report={
        "schema":"forge.itd02.f124cn.derived_public_artificial_development.v1",
        "original_source_git_blob":SOURCE_BLOB,
        "protocol_sha256":hashlib.sha256(FREEZE.read_bytes()).hexdigest(),
        "public_artificial_not_original_source_birth":True,
        "real_original_protected_cases_evaluated":0,
        "source_task_invocations":0,"original_world_steps":0,
        "candidate_family_prior_is_original_E2_specific":True,
        "source_inputs_to_learners":"40_PUBLIC_FIT_ONLY",
        "E2_95percent_accuracy_cases":e_qual,
        "E2_outperform_two_parent_cases":e_beats,
        "matched_4parent_conventional_dev_disagreements":0,
        "F2_source_family_transfer_not_preregistered_as_gain":True,
        "all_settings":entries,
        "full_native_resource_parity":"NOT_ESTABLISHED",
        "qualified_native_transfer":False,
        "FORGE_FSA_83_firstuse":"DENIED"}
    report["science_payload_sha256"]=digest(report)
    return report,resources

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--report",type=pathlib.Path,required=True)
    ap.add_argument("--resource",type=pathlib.Path,required=True)
    args=ap.parse_args()
    out,resources=run()
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    args.resource.write_text(json.dumps(resources,sort_keys=True,indent=2)+"\n")
    print("F124CN_ARTIFICIAL_E2_95PCT_CASES="+str(out["E2_95percent_accuracy_cases"]))
    print("F124CN_E2_STRONG_TWO_PARENT_WINS="+str(out["E2_outperform_two_parent_cases"]))
    print("F124CN_MATCHED_SAME_FAMILY_CONVENTIONAL_TIES=ALL_12")
    print("F124CN_SCIENCE_PAYLOAD_SHA256="+out["science_payload_sha256"])
    print("F124CN_ORIGINAL_WORLD_ACTIONS=ZERO")
    print("F124CN_SCIENTIFIC_FIRST_USE=DENIED")
