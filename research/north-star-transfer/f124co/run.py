#!/usr/bin/env python3
"""F124CO source-law-matched ARTIFICIAL development. No original case birth.

Original E2/F2 mathematical source invoked by this AUDITOR only on prespecified
non-secret artificial (input,param) pairs. Learners receive 40 public FIT rows
ONLY, no oracle/source/module/param, and CHECK/DEV never select a model.
"""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import random
import subprocess
import sys
import time
import tracemalloc

import learn_structure as learner

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=HERE.parent/"f124cj_internal_source.py"
FIXED=HERE.parent/"f124cn"/"learn.py"
FREEZE=HERE/"FROZEN_PROTOCOL.json"
BLOBS={
    "research/north-star-transfer/f124cj_internal_source.py":"4e7bbd8f93dab1c7242a9374c75731302b034f31",
    "research/north-star-transfer/f124cb_dual_link_learner.py":"8a10bf8cec12afc7d8703e3586d8eba91ebfdc7c",
    "research/north-star-transfer/f124cc_trained_two_link_control.py":"29c0c02f54ea539bed0910fe82adcc86d3aff94d",
    "research/north-star-transfer/f124cn/FROZEN_PROTOCOL.json":"6455fe858915cdcd1c95ae0c99791b41eac58fb1"
}

def require(cond, label):
    if not cond:
        raise AssertionError("F124CO_FAIL_CLOSED_"+label)

def hashed_sources():
    out={}
    for path,pin in BLOBS.items():
        actual=subprocess.check_output(["git","hash-object",path],
                                       cwd=ROOT,text=True).strip()
        require(actual==pin,"ORIGINAL_BLOB_DRIFT_"+path.replace("/","_"))
        out[path]=actual
    return out

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

def cold(model,x):
    raw=learner.checkpoint(model)
    code=("import json,sys,learn_structure as L; "
          "m=L.restore(sys.stdin.buffer.read());"
          "print(json.dumps({'prediction':L.result_from_public(m,int(sys.argv[1])),"
          "'checkpoint':L.checkpoint(m).decode()},sort_keys=True))")
    child=subprocess.run([sys.executable,"-B","-c",code,str(x)],
                         cwd=HERE,input=raw,capture_output=True,
                         check=True,timeout=20)
    parsed=json.loads(child.stdout)
    require(parsed["prediction"]==learner.result_from_public(model,x) and
            parsed["checkpoint"]==raw.decode(),"COLD_INDEPENDENT_INTERPRETER_DRIFT")
    return len(raw)

def run():
    protocol=json.loads(FREEZE.read_text())
    require(protocol["schema"]==
      "forge.itd02.f124co.general_wiring_fit_only_development.v1", "PROTOCOL_SCHEMA")
    blobs=hashed_sources()
    source=load("f124co_auditor_pinned_original_math",SOURCE)
    fixed=load("f124co_independent_F124CN_baseline",FIXED)
    require(source.FAMILIES=={"E2":930000,"F2":931000},"ORIGINAL_MATH_FAMILIES")
    cases=[]
    performance=[]
    settings=protocol["roster"]["artificial_settings"]
    require(len(settings)==12,"FROZEN_SETTINGS")
    for ordinal,(family,param) in enumerate(settings):
        xs=random.Random(882000+149*ordinal).sample(range(65536),304)
        true=[source.forward(family,x,param) for x in xs]
        fit=[(x,y^(1 if j in (1,5,12,19,24,35) else 0))
             for j,(x,y) in enumerate(zip(xs[:40],true[:40]))]
        check=list(zip(xs[40:48],true[40:48]))
        dev=list(zip(xs[48:],true[48:]))
        require(len(set(xs))==304 and len(fit)==40 and len(check)==8 and len(dev)==256,
                "ARTIFICIAL_PUBLIC_SPLITS")

        tracemalloc.start()
        start=time.process_time_ns()
        model,fit_receipt=learner.train(fit)
        fit_cpu=time.process_time_ns()-start
        fit_peak=tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()

        start=time.process_time_ns()
        equal_model,control_receipt=learner.conventional_enumeration(fit)
        equal_cpu=time.process_time_ns()-start
        fixed_model,fixed_receipt=fixed.train(fit)
        two_model,two_receipt=fixed.conventional_two_parent(fit)
        simple=fixed.constant(fit)
        ablation=fixed.ablation(fit)

        require(model==equal_model,"STRONG_MATCHED_CONVENTIONAL_DISAGREES")
        require(fit_receipt["FIT_nibble_mismatches"]==
                control_receipt["FIT_nibble_mismatches"],
                "MATCHED_CONVENTIONAL_FIT_MISMATCH")
        scores={
            "discovered_wiring":sum(learner.result_from_public(model,x)==(y&15)
                                    for x,y in dev),
            "fitted_conventional_same_class":sum(learner.result_from_public(equal_model,x)==(y&15)
                                                  for x,y in dev),
            "trained_source_informed_fixed_wire":sum(fixed.predict(fixed_model,x)==(y&15)
                                                      for x,y in dev),
            "trained_full_two_parent":sum(fixed.predict_two_parent(two_model,x)==(y&15)
                                          for x,y in dev),
            "trained_modal_constant":sum(simple==(y&15) for x,y in dev),
            "no_gate_ablation":sum(fixed.predict_ablation(ablation,x)==(y&15)
                                    for x,y in dev)
        }
        require(scores["discovered_wiring"]==
                scores["fitted_conventional_same_class"],"HOLDOUT_CONTROL_TIE")
        check_err=sum(learner.result_from_public(model,x)!=(y&15) for x,y in check)
        model_bytes=cold(model,dev[0][0])
        cases.append({
          "role":"artificial_development_not_original_case",
          "ordinal":ordinal,"family_label_auditor_only":family,
          "learned_carrier_pair":list(model[:2]),
          "learned_gate_feature":model[2],"learned_gate_direction":model[3],
          "learned_other_input_coefficients":list(model[4:6]),
          "learned_residual_bias":model[6],
          "FIT_nibble_mismatches":fit_receipt["FIT_nibble_mismatches"],
          "CHECK_veto_errors":check_err,
          "DEV_out0_correct_numerators_256":scores,
          "estimated_checkpoint_bytes":model_bytes,
          "enumerated_wiring_candidates":fit_receipt["layout_candidates"],
          "conventional_exhaustive_model_candidates":
                    control_receipt["full_candidate_words"],
          "NO_original_task_or_source_birth":True
        })
        performance.append({
          "setting":ordinal,"candidate_train_cpu_ns":fit_cpu,
          "candidate_train_tracemalloc_peak_bytes":fit_peak,
          "conventional_train_cpu_ns":equal_cpu,
          "note":"sequential Python source-only algorithm measurements; not full native CPU/RSS parity"
        })
    e=[case for case in cases if case["family_label_auditor_only"]=="E2"]
    report={
      "schema":"forge.itd02.f124co.discovered_wiring_development_result.v1",
      "frozen_contract_sha256":hashlib.sha256(FREEZE.read_bytes()).hexdigest(),
      "original_source_blobs":blobs,
      "result_roles":"artificial_public_math_DEV_only_unblinded_source_law",
      "source_independent_native_model_built":False,
      "source_law_specific_grammar_bias":True,
      "learner_did_not_receive_source_params":True,
      "learner_did_not_receive_original_source_module":True,
      "CHECK_and_DEV_not_used_to_fit":True,
      "E2_cases_95_percent":sum(c["DEV_out0_correct_numerators_256"]["discovered_wiring"]>=243 for c in e),
      "E2_cases_beating_two_parent":sum(c["DEV_out0_correct_numerators_256"]["discovered_wiring"]>
                      c["DEV_out0_correct_numerators_256"]["trained_full_two_parent"] for c in e),
      "matched_strong_same_class_conventional_ties":len(cases),
      "target_mathematical_suboutput_only":"LOW_NIBBLE",
      "real_original_E2F2_cases_reused":0,
      "original_source_task_born":0,
      "protected_holdouts_opened":0,
      "new_world_actions":0,
      "off_family_scientific_transfer":"NOT_DEMONSTRATED",
      "native_architectural_advantage":"NOT_DEMONSTRATED",
      "scientific_FSA_firstuse":"DENIED",
      "cases":cases
    }
    report["canonical_result_sha256"]=hashlib.sha256(learner.canonical(report)).hexdigest()
    return report,performance

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--json",type=pathlib.Path,required=True)
    ap.add_argument("--resources",type=pathlib.Path,required=True)
    options=ap.parse_args()
    result,resources=run()
    options.json.parent.mkdir(parents=True,exist_ok=True)
    options.json.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    options.resources.write_text(json.dumps(resources,sort_keys=True,indent=2)+"\n")
    print("F124CO_E2_95PCT_CASES="+str(result["E2_cases_95_percent"]))
    print("F124CO_E2_BEAT_FULL_TWO_PARENT_CASES="+str(result["E2_cases_beating_two_parent"]))
    print("F124CO_IDENTICAL_FIT_FULL_CONVENTIONAL_TIES="+str(result["matched_strong_same_class_conventional_ties"]))
    print("F124CO_CANONICAL_RESULT_SHA256="+result["canonical_result_sha256"])
    print("F124CO_REAL_ORIGINAL_FIRSTUSE=ZERO")
    print("F124CO_NATIVE_INTELLIGENCE_ADVANCE=NOT_DEMONSTRATED")
