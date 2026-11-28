"""L7 external E2E MR-to-English public developmental scorecards.

String-copy coverage is a narrow literal-copy audit, NOT semantic entailment.
Single-reference token F1 is NOT BLEU or human fluency evaluation. Original
testset_w_refs and protected scientific first-use remain untouched.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sys
import time
import tracemalloc

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from source import FILES,ROLES,COUNTS,load,digest,identity,canonical
from models import PublicLanguageRealizer,contains_value,PLACEHOLDER

ARMS=("REFERENCE_RETRIEVAL","DELEX_TEMPLATE",
      "CONSTRAINED_TEMPLATE","CANONICAL_FACTS")
LITERAL_KEYS=("name","near","food","area","eattype")
TOKEN=re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")


def guard():
    p=json.loads((HERE/"L7_FROZEN_PROTOCOL.json").read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.language.l7.prospective-real-mr-to-language-v1"
    assert p["stage"]=="FROZEN_FIRST_PROTOCOL_COMMIT_BEFORE_SOURCE_LEARNERS_AND_PUBLIC_DEV"
    assert p["external_dataset"]["train"]["git_blob_sha1"]==FILES["trainset.csv"][1]
    assert p["external_dataset"]["dev"]["git_blob_sha1"]==FILES["devset.csv"][1]
    assert p["cohorts"]["role_counts"]==COUNTS
    assert tuple(p["arms"])==ARMS
    assert p["governance"]["mode"]=="ADDITIVE_PUBLIC_DEV_ONLY"
    return p


def token_f1(a,b):
    from collections import Counter
    tokens_a=Counter(TOKEN.findall(a.lower()))
    tokens_b=Counter(TOKEN.findall(b.lower()))
    match=sum((tokens_a&tokens_b).values())
    return 2*match/(sum(tokens_a.values())+sum(tokens_b.values())) if (
        tokens_a or tokens_b) else 1.


def covered(output,mr):
    keys=[k for k in LITERAL_KEYS if k in mr]
    return sum(contains_value(output,mr[k]) for k in keys),len(keys)


def stale_entity_values(output,mr,lexicons):
    # Diagnostic only: these are names/landmarks, not full NLI entailment.
    wrong=0
    for key in ("name","near"):
        for text in lexicons[key]:
            if len(text)<5 or text.casefold()==mr.get(key,"").casefold():
                continue
            if contains_value(output,text):
                wrong+=1
    return wrong


def evaluate(model,batch,known_entity_values):
    from collections import Counter
    outsha=hashlib.sha256()
    literal_hit=literal_total=0
    names_hit=names_total=near_hit=near_total=0
    unresolved=stale=0
    reference_overlap=0.
    word_count=0
    operations=0
    exact_raw_ref=0
    clock=time.perf_counter()
    cpu=time.process_time()
    for row in batch:
        mr=row["mr"]
        candidate,ops=model.generate(mr)
        if not candidate or not isinstance(candidate,str) or ops<0:
            raise ValueError("L7_EMPTY_PUBLIC_LANGUAGE_REALIZATION")
        outsha.update(candidate.encode("utf-8")+b"\n")
        hits,n=covered(candidate,mr)
        literal_hit+=hits
        literal_total+=n
        if "name" in mr:
            names_total+=1
            names_hit+=int(contains_value(candidate,mr["name"]))
        if "near" in mr:
            near_total+=1
            near_hit+=int(contains_value(candidate,mr["near"]))
        unresolved+=int(bool(PLACEHOLDER.search(candidate)))
        stale+=int(stale_entity_values(candidate,mr,known_entity_values)>0)
        reference_overlap+=token_f1(candidate,row["ref"])
        word_count+=len(TOKEN.findall(candidate))
        operations+=ops
        exact_raw_ref+=int(candidate==row["ref"])
    cpu_cost=time.process_time()-cpu
    elapsed=time.perf_counter()-clock
    n=len(batch)
    return {
        "records":n,
        "observed_literal_slots":literal_total,
        "exact_literal_slot_hits":literal_hit,
        "literal_slot_copy_rate":literal_hit/literal_total if literal_total else None,
        "name_literal_recall":names_hit/names_total if names_total else None,
        "near_literal_recall":near_hit/near_total if near_total else None,
        "known_unrequested_name_near_indicator_rate":stale/n,
        "unresolved_placeholder_fraction":unresolved/n,
        "single_reference_token_F1_not_BLEU":reference_overlap/n,
        "generated_mean_token_count":word_count/n,
        "exact_reference_string_fraction":exact_raw_ref/n,
        "generated_output_sha256":outsha.hexdigest(),
        "string_match_operations_proxy_NOT_FLOPs":operations,
        "measured_serial_inference_CPU_s":cpu_cost,
        "measured_serial_wall_us_per_MR":elapsed/n*1e6,
    }


def peak_rss():
    if os.name=="posix":
        import resource
        k=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(k if sys.platform=="darwin" else k*1024)
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        class PROC(ctypes.Structure):
            _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
                ("PeakWorkingSetSize",ctypes.c_size_t),
                ("WorkingSetSize",ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),
                ("QuotaPagedPoolUsage",ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
                ("PagefileUsage",ctypes.c_size_t),
                ("PeakPagefileUsage",ctypes.c_size_t)]
        p=PROC()
        p.cb=ctypes.sizeof(p)
        if ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(p),p.cb):
            return int(p.PeakWorkingSetSize)
    return None


def run(folder):
    guard()
    tracemalloc.start()
    started=time.process_time()
    source_clock=time.process_time()
    original_hash,groups=load(folder)
    source_cpu=time.process_time()-source_clock
    rolesha={role:digest(rows) for role,rows in groups.items()}
    seen=set()
    for role in ROLES:
        if len(groups[role])!=COUNTS[role]:
            raise ValueError("L7_PREDECLARED_SOURCE_ROLE_SHORTAGE")
        for record in groups[role]:
            ident=identity(record["mr"])
            if ident in seen:
                raise ValueError("L7_TRAIN_SELECT_DEV_MR_CONTAMINATION")
            seen.add(ident)
    train=groups["L7_TRAIN"]
    inventory={key:{r["mr"][key] for r in train if key in r["mr"]}
               for key in ("name","near")}
    fitted={}
    costs={}
    for arm in ARMS:
        clock=time.process_time()
        model=PublicLanguageRealizer(arm,train)
        elapsed=time.process_time()-clock
        cp=model.checkpoint()
        costs[arm]={
            "fit_CPU_seconds":elapsed,
            "frozen_checkpoint_sha256":hashlib.sha256(cp).hexdigest(),
            "whole_trained_checkpoint_bytes":len(cp),
            "fit_examples":len(train),
            "learned_delex_patterns":model.fit.patterns if model.fit else 0,
            "is_strong_recurrent_or_transformer_model":False,
            "actually_parallel_hardware":False,
        }
        fitted[arm]=model
    frozen={arm:costs[arm]["frozen_checkpoint_sha256"] for arm in ARMS}
    scores={}
    for role in ROLES:
        scores[role]={}
        for arm in ARMS:
            scores[role][arm]=evaluate(fitted[arm],groups[role],inventory)
            if hashlib.sha256(fitted[arm].checkpoint()).hexdigest()!=frozen[arm]:
                raise ValueError("L7_PUBLIC_DEV_MUTATED_FITTED_REALIZER")
    _,python_peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.language.l7.public-real-mr-text-receipt.v1",
        "governance":"ADDITIVE_PUBLIC_DEV_ONLY",
        "Q21_FSA_HELD_protected_first_use":False,
        "prior_L1_L6_dev_roles_used":0,
        "official_E2E_test_touched":False,
        "independent_blinded_NLI_or_human_language_assessment":False,
        "scientific_Pareto_GO":False,
        "reasoning_coding_math_multilingual_tested":False,
        "fully_trained_resource_matched_neural_controls":False,
        "true_hardware_parallel_generation":False,
        "energy_joules":"NOT_MEASURED",
        "hardware_flops":"NOT_MEASURED",
        "original_git_sha256":original_hash,
        "source_role_sha256":rolesha,
        "role_counts":COUNTS,
        "TRAIN_public_supervised_corpus_bytes":len(canonical(train)),
        "source_generation_CPU_s":source_cpu,
        "fitted_models":costs,
        "public_role_evaluations":scores,
        "total_experiment_CPU_s":time.process_time()-started,
        "peak_python_tracemalloc_bytes":python_peak,
        "peak_process_RSS_bytes":peak_rss(),
        "platform":platform.platform(),
    }


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: runner.py /path/rawE2EtrainAndDev")
    print(json.dumps(run(sys.argv[1]),sort_keys=True,indent=2,allow_nan=False))
