"""F128-R public FIT-only bit-order and untouched TRAIN_CHECK original evidence.

The science thresholds are reported, not tuned and not used to filter cases.
Native indexed exact is a mandatory eligible comparator. No CONFIRM.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,sys
from pathlib import Path
import f118_autonomy_feedback as f118
import f120_generated_environment as f120
import f128r_freeze_admission as freeze
import f128r_train_environment as env
import f128r_bit_order_model as model

SCHEMA="forge.research.f128r.fit-train-check-indexed-exact.v1"
def need(x,tag):env.need(bool(x),"ADMISSION_"+tag)
def sha(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def evaluate(name,vectors,candidate_hashes):
    fit=env.cohort_rows(name,vectors,"FIT")
    check=env.cohort_rows(name,vectors,"TRAIN_CHECK")
    need(len(fit)==64 and len(check)==64 and
         not(set(env.digest(g) for g,y in fit)&
             set(env.digest(g) for g,y in check)),"SOURCE_SPLIT_DISJOINT")
    # Learner consumes ONLY FIT public graphs, not graph labels.
    learned,training=model.fit([g for g,y in fit])
    need(training["labels_accessed"] is False and
         training["complete_passes"]==1 and
         len(learned)==16,"FIT_ONLY_LABEL_BLIND")
    scores,bit_ratio=model.compare(check,learned)
    timing=model.benchmark([g for g,y in check],learned)
    baseline=scores["CTRL_OPTIMIZED_INDEXED_EXACT_VECTOR_EQUALITY"]
    need(baseline["paired_correct"]==32 and
         all(x["paired_correct"]==32 for x in scores.values()),
         "UNEXPECTED_INEXACTNESS")
    bit_ok=bit_ratio<=.75
    time_ok=timing["passes_walltime_target"]
    return {"lane":name,"candidate_sha256":candidate_hashes,
       "fit_public_graphs":64,"train_check_public_graphs":64,
       "fit_pairs":32,"train_check_pairs":32,
       "FIT_sha256":env.digest(fit),"TRAIN_CHECK_sha256":env.digest(check),
       "learned_bit_order":list(learned),
       "fit_training_receipt":training,
       "all_frozen_control_scores":scores,
       "bit_access_ratio_to_native_full16":round(bit_ratio,8),
       "passes_bit_work_target":bit_ok,
       "same_host_timing":timing,
       "passes_median_walltime_target":time_ok,
       "development_cost_criterion_passed":bool(bit_ok and time_ok),
       "no_source_reselection":True,
       "independent_scientific_acceptance":False,
       "protected_CONFIRM_read":False}
def run(advisory,sha_commit):
    cfg,freeze_sha=freeze.frozen()
    need(type(sha_commit) is str and re.fullmatch("[0-9a-f]{40}",sha_commit)
       and (not os.getenv("GITHUB_SHA") or os.environ["GITHUB_SHA"]==sha_commit),
       "EXACT_COMMIT")
    candidates=f120.validate(advisory,sha_commit)
    need(set(candidates)=={"Wingless","Yggdrasil"},"SOURCES_TWO_LANES")
    lanes=[]
    for name in ("Wingless","Yggdrasil"):
        c=candidates[name]
        need(len(c)==2 and [e["candidate_index"] for e in c]==[2,3] and
             c[0]["vector"]!=c[1]["vector"],"FROZEN_SOURCE_VECTORS")
        lanes.append(evaluate(name,[e["vector"] for e in c],
                   [e["source_candidate_sha256"] for e in c]))
    passed=all(x["development_cost_criterion_passed"] for x in lanes)
    return {"schema":SCHEMA,"source_sha":sha_commit,
      "frozen_git_blob":freeze.SOURCE_BLOB,
      "freeze_sha256":freeze_sha,"advisory_sha256":sha(advisory),
      "phase":"PUBLIC_SYNTHETIC_FIT_THEN_UNTOUCHED_TRAIN_CHECK",
      "lanes":lanes,
      "both_lanes_meet_development_accuracy_and_cost":passed,
      "scientific_first_use":False,"scientific_acceptance":False,
      "optimizer_promotion":False,"protected_CONFIRM_read":False,
      "accepted_ref_mutation":False,"originals_dispatched":0,
      "paid_api_calls":0,"codex_calls":0,"new_scheduler":False}
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--advisory",required=True)
    a.add_argument("--source-sha",required=True)
    a.add_argument("--output",required=True)
    args=a.parse_args()
    doc=run(f118.load_report(args.advisory),args.source_sha)
    out=Path(args.output)
    need(out.parent.is_dir() and not out.exists(),"DENY_OVERWRITE")
    raw=(json.dumps(doc,sort_keys=True,separators=(",",":"))+"\n").encode()
    out.open("xb").write(raw)
    print("F128R_TRAIN_CUSTODY_SHA256="+hashlib.sha256(raw).hexdigest())
    for x in doc["lanes"]:
        print("F128R_"+x["lane"].upper()+"_BIT_RATIO="+str(x["bit_access_ratio_to_native_full16"]))
        print("F128R_"+x["lane"].upper()+"_WALL_RATIO="+str(x["same_host_timing"]["median_walltime_ratio"]))
        print("F128R_"+x["lane"].upper()+"_PAIRED="+str(x["all_frozen_control_scores"]["F128R_FIT_ONLY_LEARNED_EARLY_REJECT"]["paired_correct"])+"/32")
    print("F128R_PROTECTED_CONFIRM=false")
    print("F128R_SCIENTIFIC_ACCEPTANCE=false")
if __name__=="__main__":
    try:main()
    except (env.Invalid,freeze.Invalid,f118.Quarantined,f120.Invalid,
            OSError,ValueError,TypeError,KeyError,IndexError) as ex:
        print("F128R_SOURCE_QUARANTINED="+str(ex),file=sys.stderr)
        raise SystemExit(1)
