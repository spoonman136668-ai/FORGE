"""F54: independent read-only review of real first-attempt TRAIN evidence.

Source-free recount of authentic artifacts. Explicitly preserves two failed
two-hop diagnostic uses of the same cohort. No primary original, controller
action, Dream/Theta policy update or accepted scientific reference mutation.
"""
import argparse,hashlib,json,math
from pathlib import Path
class Blocked(ValueError):pass
def need(ok,why):
    if not ok:raise Blocked("F54_"+why)
def sha(b):return hashlib.sha256(b).hexdigest()
def unique(items):
    obj={}
    for k,v in items:
        need(k not in obj,"DUPLICATE_JSON_KEY")
        obj[k]=v
    return obj
def load_json(raw):
    need(0<len(raw)<=5000000,"JSON_SIZE")
    return json.loads(raw,object_pairs_hook=unique)
def artifact(path,spec,lane):
    root=Path(path)
    raw=(root/"result.json").read_bytes()
    need(sha(raw)==spec["report_sha256"],"RESULT_SHA_"+lane)
    audit_name="audit.json" if lane=="Wingless" else "independent-audit.json"
    audit=(root/audit_name).read_bytes()
    need(sha(audit)==spec["audit_sha256"],"AUDIT_SHA_"+lane)
    expected={"result.json":sha(raw),audit_name:sha(audit)}
    actual={}
    for line in (root/"manifest.sha256").read_text().splitlines():
        elements=line.split()
        need(len(elements)==2 and elements[1] not in actual,"BAD_MANIFEST_"+lane)
        actual[elements[1]]=elements[0]
    need(actual==expected,"MANIFEST_DRIFT_"+lane)
    need((root/"SOURCE_SHA").read_text().strip()==spec["source_sha"],
         "SOURCE_DRIFT_"+lane)
    d=load_json(raw);audit_report=load_json(audit)
    need(d.get("schema")==spec["source_schema"]
         and d.get("original_executed") is False
         and d.get("independent_F3") is False
         and d.get("accepted_ref_mutation") is False
         and d.get("paid_api_calls")==0
         and d.get("cases")==spec["total"]
         and len(d.get("rows",[]))==spec["total"],
         "SYNTHETIC_SOURCE_AUTHORITY_"+lane)
    return d,audit_report
def recount(d,spec,lane):
    rows=d["rows"];scores=d["scores"];candidate=spec["candidate"]
    oracle=("private_truth_oracle_unfair" if lane=="Wingless"
            else "private_future_question_oracle_unfair")
    need(candidate in scores and oracle in scores,"ARM_IDENTITY_"+lane)
    n=spec["total"];seen=set()
    counts={a:0 for a in scores}
    family={str(f):{a:0 for a in scores} for f in spec["heldout_families"]}
    for row in rows:
        key=(row["seed"],row["family"],row["length"]) if lane=="Wingless" else (
            row["seed"],row["family"])
        need(key not in seen and row["family"] in spec["heldout_families"],
             "DUPLICATE_OR_FAMILY_"+lane)
        seen.add(key)
        if lane=="Wingless":
            need(581100<=row["seed"]<581116
                 and row["length"] in (8,10)
                 and len(row["chain"])==row["length"]
                 and len(row["public_observations"])==4
                 and len(row["public_calibration"])==4
                 and set(row["answers"])==set(scores)
                 and row["answers"][oracle]==row["truth"],
                 "W_PUBLIC_ROW")
            win=lambda a:int(row["answers"][a]==row["truth"])
            need(set(row["abstract_operations"])==set(scores)-{oracle},
                 "W_WORK_SET")
        else:
            need(591100<=row["seed"]<591116
                 and len(row["public_events"])==72
                 and len(row["public_tags"])==72
                 and sum(row["public_tags"])==36
                 and len(row["question"]["ops"]) in (4,6,8)
                 and set(row["answers"])==set(scores)
                 and set(row["receipts"])==set(scores)-{oracle}
                 and row["answers"][oracle]==1,
                 "Y_PUBLIC_ROW")
            for arm,receipts in row["receipts"].items():
                need(len(receipts)<=12 and
                     all(len(bytes.fromhex(x))==12 for x in receipts),
                     "Y_MEMORY_BYTES")
            win=lambda a:row["answers"][a]
        for arm in scores:
            hit=win(arm)
            need(hit in (0,1),"NONBINARY_RESULT")
            counts[arm]+=hit
            family[str(row["family"])][arm]+=hit
    need(len(seen)==n and family==d["by_family"],"BY_FAMILY_RECOUNT")
    for arm in scores:
        m=scores[arm]
        need(m["correct"]==counts[arm] and m["total"]==n
             and abs(m["accuracy"]-counts[arm]/n)<1e-12,
             "SCORE_RECOUNT")
    fair=[a for a in scores if a not in (candidate,oracle)]
    if lane=="Wingless":
        fair.remove("exact_full_public_bayes")
        work={a:sum(row["abstract_operations"][a] for row in rows)
              for a in d["posterior_abstract_operations"]}
        need(work==d["posterior_abstract_operations"],"W_WORK_RECOUNT")
        ratio=work[candidate]/work["exact_full_public_bayes"]
        need(abs(ratio-spec["expected_work_ratio"])<1e-12
             and abs(ratio-d["posterior_work_ratio_vs_exact"])<1e-12,
             "W_WORK_GATE")
        extra={"abstract_work_ratio_to_exact":ratio}
        need(d["physical_native_576B_unverified"] is True,"PHYSICAL_MEMORY_UNQUALIFIED")
    else:
        extra={"retrieval_ablation_gain":d["retrieval_ablation_gain"],
               "noncompetitive_public_reference_correct":d["bounded_offline_public_reference_correct"]}
        need(abs(d["retrieval_ablation_gain"]-
                 spec["expected_retrieval_ablation_gain"])<1e-12
             and d["bounded_offline_public_reference_correct"]==0
             and d["reference_extra_work_noncompetitive"] is True
             and d["serialized_payload_budget_bytes"]==144
             and d["physically_measured_native_total_576B"] is False,
             "Y_ABLATION_REFERENCE_GATE")
    best=max(counts[a] for a in fair)
    strongest=[a for a in fair if counts[a]==best]
    gain=(counts[candidate]-best)/n
    guard=all(family[str(f)][candidate]>=max(family[str(f)][a] for a in fair)
              for f in spec["heldout_families"])
    verdict=("TRAIN_ONLY_TRANSITION_GENERALIZATION_NEGATIVE"
             if lane=="Wingless" else "TRAIN_ONLY_GLOBAL_MEMORY_NEGATIVE")
    need(counts[candidate]==spec["expected_correct"]
         and best==spec["expected_strongest"]
         and spec["strongest_fair"] in strongest
         and d["per_family_nondegradation"]==guard
         and guard==spec["expected_family_guard"]==False
         and abs(d["candidate_gain"]-gain)<1e-12
         and d["frozen_gate_met"] is False
         and d["verdict"]==verdict,
         "FROZEN_GATE_MISCLASSIFICATION_"+lane)
    return dict(lane=lane,run_id=spec["run_id"],
        first_use_source_sha=spec["source_sha"],report_sha256=spec["report_sha256"],
        total_cases=n,candidate_correct=counts[candidate],strongest_fair_correct=best,
        gain_percentage_points=round(100*gain,6),
        per_family_nondegradation=guard,
        disposition="VALID_TRAIN_ONLY_NEGATIVE_NO_PRIMARY_ORIGINAL",
        next_hypothesis=spec["proposed_F55_hypothesis"],**extra)
def review(root,manifest):
    need(manifest.get("schema")=="forge.f54.authentic-firstuse-train-feedback.v1"
         and set(manifest.get("qualified_diagnostic_negatives",{}))==
             {"Wingless","Yggdrasil"},"MANIFEST_SCHEMAS")
    d=manifest["constraints"]
    need(d["f3_authority"] is False
         and d["primary_originals_executed"]==0
         and d["accepted_ref_mutation"] is False
         and d["dream_rsi_prospective_policy_gain_proven"] is False
         and d["thetaevolve_live_weight_update_authorized"] is False
         and d["no_science_dispatch_or_new_controller"] is True,
         "NO_FALSE_PROMOTION")
    failed=manifest["separately_failed_once_only_diagnostics"]
    need(len(failed)==2 and failed[0]["run_id"]==38819249753
         and failed[1]["run_id"]==38819267489
         and failed[0]["reason"]=="DATA_GENERATED_THEN_AUDIT_PROVENANCE_ASSERTION_FAILURE"
         and failed[1]["reason"]=="SAME_COHORT_REGENERATED_THEN_AUDIT_PROVENANCE_ASSERTION_FAILURE"
         and d["both_failed_queries_remain_unqualified"] is True
         and d["source_only_repair_cannot_promote_old_results"] is True,
         "FAILING_Y_DIAGNOSTICS_RECLASSIFIED")
    valid=[]
    for lane in ("Wingless","Yggdrasil"):
        spec=manifest["qualified_diagnostic_negatives"][lane]
        result,audit=artifact(Path(root)/lane,spec,lane)
        decision=recount(result,spec,lane)
        if lane=="Wingless":
            need(audit.get("candidate_correct")==decision["candidate_correct"]
                 and audit.get("strongest_correct")==decision["strongest_fair_correct"]
                 and audit.get("source_frozen_train_gate") is False,
                 "W_OWNER_AUDIT_IDENTITY")
        else:
            need(audit.get("candidate_correct")==decision["candidate_correct"]
                 and audit.get("strongest_fair_correct")==decision["strongest_fair_correct"]
                 and audit.get("result")=="TRAIN_ONLY_GLOBAL_MEMORY_NEGATIVE"
                 and audit.get("accepted_original") is False,
                 "Y_OWNER_AUDIT_IDENTITY")
        valid.append(decision)
    return dict(schema="forge.f54.authentic-feedback-f55-advisory.v1",
        qualified_original_train_negatives=valid,
        separately_failed_consumed_y_diagnostics=failed,
        source_only_repair_pr=d["source_only_repair_pr"],
        accepted_scientific_originals=0,
        live_dream_rsi_prospective_policy_improvement_proven=False,
        theta_evolve_live_training_eligible=False,
        bounded_F55_hypotheses_advisory_only=True,
        new_experiment_dispatched=False)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    m=load_json(Path(a.manifest).read_bytes())
    Path(a.out).write_text(json.dumps(review(a.root,m),
        sort_keys=True,separators=(",",":"))+"\n")
