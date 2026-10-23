"""L8 development-only attribution and source-literal/format proxy receipts.

The generated 'learned' route is independently determined and asserted
against the BYTE-IDENTICAL prior L7 constrained implementation. The strong
baseline is deterministic literal facts, not a fluent language model.
Literal copy ≠ semantic entailment; known-other-value indicator ≠ an
adjudicated contradiction. All abstentions remain in every denominator.
"""
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import sys
import time
import tracemalloc

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from source import FILES,ROLES,COUNTS,load,identity,digest,canonical
from models import ARMS,AUDIT_KEYS,AttributionRealizer
from l7_models_original import contains_value

TOKEN=re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")


def preregistration_guard():
    p=json.loads((HERE/"L8_FROZEN_PROTOCOL.json").read_text(encoding="utf-8"))
    if (p["schema"]!="forge.optimizer.language.l8.frozen-fallback-attribution-v1" or
        p["status"]!="PROTOCOL_ONLY_COMMITTED_BEFORE_NEW_SOURCE_ROLE_SELECTION_AND_MODEL_AUDIT_CODE" or
        p["original_E2E"]["source_roles"]!=COUNTS or
        tuple(p["methods"])!=ARMS or
        p["governance"]["additive_only"] is not True):
        raise ValueError("L8_FROZEN_EXPOSURE_OR_METHOD_DRIFT")
    for file,(size,sha) in FILES.items():
        documented=p["original_E2E"]["files"][file]
        if documented["bytes"]!=size or documented["git_blob_sha1"]!=sha:
            raise ValueError("L8_UNPINNED_E2E_SOURCE_IDENTITY")
    return p


def token_f1(guessed,gold):
    a,b=Counter(TOKEN.findall(guessed.lower())),Counter(TOKEN.findall(gold.lower()))
    matched=sum((a&b).values())
    return 2*matched/(sum(a.values())+sum(b.values())) if (
        a or b) else 1.


def contains_other_known_values(output,mr,inventory):
    # High-recall *possible* conflicting TRAIN-values only; may include
    # place names in normal prose, never call these adjudicated contradictions.
    count=0
    for key in ("name","near","food","area"):
        supplied=mr.get(key,"").casefold()
        for text in inventory[key]:
            if len(text)<5 or text.casefold()==supplied:
                continue
            if contains_value(output,text):
                count+=1
    return count


def evaluate(learner,rows,inventory):
    count=len(rows)
    route_counts=Counter()
    learned_num=learned_literal_num=learned_literal_den=0
    fallback_num=fallback_literal_num=fallback_literal_den=0
    abstain_num=0
    audited_total=audited_hits=0
    all_total=all_hits=0
    all_complete=0
    name_total=name_hits=near_total=near_hits=0
    ref_f1=0.
    learned_ref_f1=0.
    possible_wrong=0
    unresolved=0
    sentence_terminal=0
    semicolon=0
    work_total=0
    prediction_identity=hashlib.sha256()
    start_cpu=time.process_time()
    start_wall=time.perf_counter()
    for row in rows:
        mr=row["mr"]
        output,trace=learner.predict(mr)
        route=trace["route"]
        route_counts[route]+=1
        work_total+=trace["operations"]
        if output is not None:
            prediction_identity.update(output.encode("utf-8")+b"\n")
        else:
            prediction_identity.update(b"<L8_AUDITED_ABSTAIN>\n")
            abstain_num+=1
        five=[key for key in AUDIT_KEYS if key in mr]
        observed=sum(contains_value(output,mr[key]) for key in five) if output else 0
        audited_total+=len(five)
        audited_hits+=observed
        # Literal matching for non-five keys is especially NOT a reliable
        # semantic coverage measure e.g. yes/no paraphrases.
        across=sum(contains_value(output,mr[key]) for key in mr) if output else 0
        all_total+=len(mr)
        all_hits+=across
        all_complete+=int(output is not None and across==len(mr))
        if "name" in mr:
            name_total+=1
            name_hits+=int(bool(output) and contains_value(output,mr["name"]))
        if "near" in mr:
            near_total+=1
            near_hits+=int(bool(output) and contains_value(output,mr["near"]))
        if output:
            f1=token_f1(output,row["ref"])
            ref_f1+=f1
            possible_wrong+=int(contains_other_known_values(output,mr,inventory)>0)
            unresolved+=int("{{" in output or "}}" in output)
            sentence_terminal+=int(output.strip().endswith((".","!","?")))
            semicolon+=int(";" in output)
        else:
            f1=0.
        if route=="learned_pattern":
            learned_num+=1
            learned_literal_num+=observed
            learned_literal_den+=len(five)
            learned_ref_f1+=f1
        elif route=="canonical_fallback":
            fallback_num+=1
            fallback_literal_num+=observed
            fallback_literal_den+=len(five)
    cpu_elapsed=time.process_time()-start_cpu
    wall_elapsed=time.perf_counter()-start_wall
    if sum(route_counts.values())!=count:
        raise ValueError("L8_UNACCOUNTED_LEARNED_OR_FALLBACK_GENERATION")
    return {
        "records":count,
        "route_counts":dict(sorted(route_counts.items())),
        "learned_only_output_count":learned_num,
        "canonical_fallback_count":fallback_num,
        "abstention_count":abstain_num,
        "learned_route_fraction":learned_num/count,
        "canonical_fallback_fraction":fallback_num/count,
        "abstention_fraction":abstain_num/count,
        "observed_five_literal_slots":audited_total,
        "five_literal_exact_copy_hits":audited_hits,
        "five_literal_copy_rate_with_abstention_zero":(
            audited_hits/audited_total if audited_total else None),
        "learned_route_literal_hits":learned_literal_num,
        "learned_route_literal_slots":learned_literal_den,
        "learned_route_literal_copy_rate_conditional":(
            learned_literal_num/learned_literal_den if learned_literal_den else None),
        "fallback_route_literal_hits":fallback_literal_num,
        "fallback_route_literal_slots":fallback_literal_den,
        "fallback_route_literal_copy_rate_conditional":(
            fallback_literal_num/fallback_literal_den if fallback_literal_den else None),
        "all_MR_keys_raw_literal_slots":all_total,
        "all_MR_keys_raw_literal_hits":all_hits,
        "all_MR_keys_raw_literal_copy_proxy":all_hits/all_total,
        "all_keys_raw_literal_complete_rate":all_complete/count,
        "name_literal_recall":name_hits/name_total if name_total else None,
        "near_literal_recall":near_hits/near_total if near_total else None,
        "possible_conflicting_TRAIN_value_rate_NOT_NLI":possible_wrong/count,
        "unresolved_brace_marker_rate":unresolved/count,
        "reference_token_F1_one_human_ref_NOT_fluency":ref_f1/count,
        "learned_route_reference_F1_conditional":(
            learned_ref_f1/learned_num if learned_num else None),
        "sentence_terminal_punctuation_proxy":sentence_terminal/count,
        "semicolon_factlist_indicator":semicolon/count,
        "generated_outputs_sha256":prediction_identity.hexdigest(),
        "string_comparison_operation_proxy_NOT_FLOPs":work_total,
        "measured_serial_CPU_seconds":cpu_elapsed,
        "measured_serial_wall_us_per_MR":wall_elapsed/count*1e6,
    }


def process_high_water_RSS():
    if os.name=="posix":
        import resource
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(peak if sys.platform=="darwin" else peak*1024)
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        class STAT(ctypes.Structure):
            _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
                ("PeakWorkingSetSize",ctypes.c_size_t),("WorkingSetSize",ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),
                ("QuotaPagedPoolUsage",ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
                ("PagefileUsage",ctypes.c_size_t),("PeakPagefileUsage",ctypes.c_size_t)]
        v=STAT();v.cb=ctypes.sizeof(v)
        if ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(v),v.cb):
            return int(v.PeakWorkingSetSize)
    return None


def run(directory):
    preregistration_guard()
    tracemalloc.start()
    total_start=time.process_time()
    load_start=time.process_time()
    originals,source_roles,old_l7=load(directory)
    source_cpu=time.process_time()-load_start
    if len(old_l7["L7_SELECT"])!=80 or len(old_l7["L7_DEV"])!=100:
        raise ValueError("L8_RECONSTRUCTED_EXPOSED_L7_TEST_ROLE_DRIFT")
    old_spent={identity(r["mr"]) for r in (
        old_l7["L7_SELECT"]+old_l7["L7_DEV"])}
    old_train={identity(r["mr"]) for r in old_l7["L7_TRAIN"]}
    identities={}
    hashes={}
    for role in ROLES:
        rows=source_roles[role]
        if len(rows)!=COUNTS[role]:
            raise ValueError("L8_EXPECTED_EXPERIENCE_ROLE_CARDINALITY_DRIFT")
        current={identity(r["mr"]) for r in rows}
        if len(current)!=len(rows) or (
            role!="L8_TRAIN" and
            (current&old_spent or current&old_train)):
            raise ValueError("L8_EXPOSED_L7_DEV_OR_MODEL_TRAIN_LEAKAGE")
        identities[role]=current
        hashes[role]=digest(rows)
    if (identities["L8_AUDIT_SELECT"]&
        identities["L8_AUDIT_DEV"]):
        raise ValueError("L8_NEW_AUDIT_SELECT_DEV_OVERLAP")
    train=source_roles["L8_TRAIN"]
    inventory={key:{r["mr"][key] for r in train if key in r["mr"]}
               for key in ("name","near","food","area")}
    models={}
    costs={}
    for arm in ARMS:
        start=time.process_time()
        if arm=="NO_FALLBACK_CONSTRAINED":
            model=AttributionRealizer(
                arm,train,shared_constrained=models["CONSTRAINED_TEMPLATE"].model)
        else:
            model=AttributionRealizer(arm,train)
        trained_cpu=time.process_time()-start
        cp=model.checkpoint()
        costs[arm]={
            "fit_CPU_seconds":trained_cpu,
            "original_l7_trained_examples":len(train),
            "checkpoint_bytes":len(cp),
            "checkpoint_sha256":hashlib.sha256(cp).hexdigest(),
            "trained_pattern_count":model.model.fit.patterns if model.model.fit else 0,
            "shares_model_and_training_with":(
                "CONSTRAINED_TEMPLATE" if arm=="NO_FALLBACK_CONSTRAINED" else None),
            "incremental_trained_checkpoint_bytes":(
                0 if arm=="NO_FALLBACK_CONSTRAINED" else len(cp)),
            "hardware_parallel_inference":False,
        }
        models[arm]=model
    receipts={}
    frozen={k:val["checkpoint_sha256"] for k,val in costs.items()}
    for role in ROLES:
        receipts[role]={}
        for arm in ARMS:
            receipts[role][arm]=evaluate(models[arm],source_roles[role],inventory)
            if hashlib.sha256(models[arm].checkpoint()).hexdigest()!=frozen[arm]:
                raise ValueError("L8_AUDIT_OR_DEV_FITTED_L7_MODEL_MUTATION")
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.language.l8.public-fallback-attribution-native.v1",
        "research_scope":"ADDITIVE_PUBLIC_DEVELOPMENT_ONLY",
        "prior_L7_180_public_dev_used_for_fit_or_eval":0,
        "E2E_official_TEST_consumed":False,
        "Q21_FSA_HELD_first_use":False,
        "NCI_ITD_BIO_Optimizer_FORGE_unchanged":True,
        "externally_blinded_semantics_or_human_fluency":False,
        "fully_trained_neural_comparator_and_matched_compute":False,
        "scientific_pareto_go":False,
        "hardware_parallel_generation":False,
        "measured_FLOPs":"NOT_MEASURED",
        "energy_joules":"NOT_MEASURED",
        "original_files_sha256":originals,
        "source_role_sha256":hashes,
        "counts":COUNTS,
        "old_l7_dev_mr_identity_sha256":hashlib.sha256(
            canonical(sorted(old_spent))).hexdigest(),
        "train_supervision_bytes":len(canonical(train)),
        "models":costs,
        "evaluations":receipts,
        "source_generation_CPU_s":source_cpu,
        "total_CPU_s":time.process_time()-total_start,
        "peak_python_tracemalloc_bytes":peak,
        "peak_process_RSS_bytes":process_high_water_RSS(),
        "platform":platform.platform(),
    }


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: runner.py /absolute/pinned/E2E/files")
    print(json.dumps(run(sys.argv[1]),indent=2,sort_keys=True,allow_nan=False))
