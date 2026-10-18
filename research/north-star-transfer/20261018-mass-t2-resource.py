"""Mass T2 source-neutral same-public-observation training cost comparator.

Qualifies engineering fit feasibility on two negative-numbered fixtures only.
Strong original F124-AZ fitted against same 48 public pairs; the new 32-bit
shear is compared without introducing extra observations. Source families
are different and OOD, full amortized meta-training and scoring are NOT
qualified. Results are diagnostics, never science acceptance.
"""
from __future__ import annotations
import importlib.util,json,subprocess,sys,time,tracemalloc
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NATIVE=ROOT/"nativeevidence"
SOURCE=HERE/"20261018-mass-t2-source.py"
KERNEL=HERE/"20261018-mass-learned-kernel.py"
MODEL=NATIVE/"f124az_joint_public_inverse.py"
def need(v,tag):
    if not v:raise ValueError("MASS_T2_RESOURCE_"+tag)
def blob(p):
    return subprocess.run(["git","hash-object",str(p)],cwd=ROOT,check=True,
            text=True,capture_output=True).stdout.strip()
def import_file(name,p):
    spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m)
    return m
def measure(f):
    tracemalloc.start()
    start=time.process_time_ns()
    result=f()
    cpu=time.process_time_ns()-start
    peak=tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return result,{"CPU_ns":cpu,"Python_peak_bytes":peak}
def attest():
    need(blob(MODEL)=="0122190aa3a0972ffb4a709bc1bdd8179c8ba6c7"
         and blob(KERNEL)=="bf81ed56cc0daa2c413ad7d9c698969f92befe3d",
         "EXACT_OLD_AZ_VS_NEW_T1")
    sys.path.insert(0,str(NATIVE))
    src=import_file("t2_mass_src",SOURCE)
    learn=import_file("t2_mass_kernel",KERNEL)
    import f124az_joint_public_inverse as old
    p,private=src.fixture(-931)
    same=p["observations"]
    need(len(same)==48 and same[:40]==p["FIT"] and same[40:]==p["CHECK"],
         "UNMODIFIED_40_FIT_8_CHECK")
    fitpairs=[(row["input_bits"],row["output_bits"]) for row in p["FIT"]]
    chk=[(row["input_bits"],row["output_bits"]) for row in p["CHECK"]]
    (new,learn_meta),newcost=measure(lambda:learn.fit_public(fitpairs,chk))
    (control),oldcost=measure(lambda:old.train(same,"T2-MASS-NEGATIVE-FIXTURE",0))
    need(len(new)==4 and control["trained_both_from_same_40_FIT"]
         and control["model_receives_operator_token"] is False,
         "MATCHED_NO_ORACLE_FIT_ONLY")
    return {"schema":"mass.t2.same-public-pairs-training-cost.v1",
        "original_public_responses":48,
        "new_source_family":"INDEPENDENT_TWO_SHEAR_TEST_FIXTURE_ONLY",
        "candidate_fit_CPU_ns":newcost["CPU_ns"],
        "original_AZ_fit_CPU_ns":oldcost["CPU_ns"],
        "candidate_task_Python_peak_bytes":newcost["Python_peak_bytes"],
        "original_AZ_Python_peak_bytes":oldcost["Python_peak_bytes"],
        "candidate_model_parameters_bits":32,
        "original_AZ_model_parameter_bits_lower":
             control["extra_task_model_bits_lower"],
        "candidate_fit_bit_errors":learn_meta["public_FIT_bit_errors"],
        "candidate_check_bit_errors":learn_meta["public_CHECK_bit_errors"],
        "original_selected_public_route":control["choice"],
        "real_metatraining_amortized_cost_measured":False,
        "complete_graph_scoring_cost_measured":False,
        "same_source_operator_family_as_original_AZ":False,
        "eligible_equal_full_compute_memory":False,
        "unseen_source_constructed":0,
        "scientific_transfer_ready":False}
if __name__=="__main__":print(json.dumps(attest(),sort_keys=True))
