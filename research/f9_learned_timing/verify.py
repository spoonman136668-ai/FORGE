"""Independent F9 source replay and train/validation nonleakage review.

Never import F9 advance.fit/classify_start. Re-derive rule scores from
real pinned Y070 public anchor features and matching outcomes, then replay
every development trial-arm in both disjoint source splits.
"""
import argparse,hashlib,json
from pathlib import Path
from policy import RULES,TRAIN_SEEDS,VALIDATION_SEEDS,PAIRS
from worker import load_source,evaluate,SOURCE_COMMIT

EARLY="ALWAYS_EARLY"
SWAP="ALWAYS_SWAP"

def need(ok,why):
    if not ok:raise ValueError("F9_INDEPENDENT_"+why)

def independent_vote(rule,s):
    # Alternative Boolean formulation; no lookup to F9 producer.
    need(type(s) is int and 0<=s<14,"PUBLIC_START")
    if rule==EARLY:return True
    if rule==SWAP:return False
    if rule=="START_EVEN_EARLY":return (s&1)==0
    if rule=="START_ODD_EARLY":return (s&1)==1
    if rule=="START_LT7_EARLY":return s in range(7)
    if rule=="START_GE7_EARLY":return s in range(7,14)
    if rule=="START_MOD3_ZERO_EARLY":return s in (0,3,6,9,12)
    if rule=="START_MOD3_NONZERO_EARLY":return s not in (0,3,6,9,12)
    raise ValueError("F9_INDEPENDENT_UNKNOWN_RULE")

def controls(rows):
    result={}
    for row in rows:
        key=(row["seed"],tuple(row["pair"]),row["regime"],
             tuple(row["family"]),row["matching_policy"])
        result.setdefault(key,{})
        need(row["rule"] not in result[key],"DUPLICATE_CASE")
        result[key][row["rule"]]=row
    return result

def compare_rows(source,rows,seeds,rules):
    expected_len=2*2*4*len(seeds)*3*len(rules)
    need(type(rows) is list and len(rows)==expected_len,"BOUND")
    i=0
    totals={rule:{"cases":0,"total_mismatches":0,"first_detection_cases":0,
                  "steady_errors":0,"early_decisions":0} for rule in rules}
    for pair in PAIRS:
        for regime in ("steady","onset1"):
            for family in source.FAMILIES:
                for seed in seeds:
                    for match in source.POLICIES:
                        checks=[]
                        for rule in rules:
                            row=rows[i];i+=1
                            need(row.get("seed")==seed and
                                 row.get("pair")==list(pair) and
                                 row.get("regime")==regime and
                                 row.get("family")==list(family) and
                                 row.get("matching_policy")==match and
                                 row.get("rule")==rule,
                                 "SEED_FAMILY_PAIR_IDENTITY")
                            expected=evaluate(source,seed,pair,regime,family,match,rule)
                            need(row==expected,"PINNED_REAL_SOURCE_OR_TRACE")
                            facts=row["sample_trace"]["decision"]
                            need(facts["rule"]==rule and facts["reads"]==10 and
                                 facts["distinct_nonanchor_cells"]==6 and
                                 len(facts["physical_nonanchor_set"])==6,
                                 "NONORACLE_PUBLIC_BUDGET")
                            stats=totals[rule]
                            stats["cases"]+=1
                            stats["total_mismatches"]+=row["pre_mismatch"]+row["post_mismatch"]
                            stats["first_detection_cases"]+=int(row["first_detection"] is not None)
                            stats["early_decisions"]+=int(facts["decision"]=="EARLY")
                            if regime=="steady":
                                stats["steady_errors"]+=row["pre_mismatch"]+row["post_mismatch"]
                            checks.append(facts)
                        need(all(x["physical_nonanchor_set"]==
                                 checks[0]["physical_nonanchor_set"] for x in checks),
                             "SOURCE_SENSOR_SET_IDENTITY")
    need(all(v["cases"]==expected_len//len(rules) for v in totals.values()),
         "UNBALANCED")
    return totals

def verify(result,parent_raw,review_raw,root):
    model=result.get("model",{})
    need(result.get("schema")=="forge.f9.automatic-public-order-training.v1"
         and result.get("status")=="F3_PREVIOUSLY_USED_ENGINEERING_ONLY"
         and result.get("parent_f8_sha256")==hashlib.sha256(parent_raw).hexdigest()
         and result.get("parent_f8_witness_sha256")==hashlib.sha256(review_raw).hexdigest()
         and result.get("parent_trigger")=="F8_PUBLIC_TIME_ORDER_MATTERS_MATCHED_SENSOR_SET"
         and result.get("source_commit")==SOURCE_COMMIT,"F8_SUCCESSION")
    parent=json.loads(parent_raw);review=json.loads(review_raw)
    need(parent.get("source_commit")==SOURCE_COMMIT
         and parent.get("schema")=="forge.f8.automatic-f7-matched-timing-engineering.v1"
         and parent.get("status")=="PREVIOUSLY_USED_F3_ONLY_NOT_FROZEN_SCIENCE"
         and parent.get("used_development_seeds")==list(VALIDATION_SEEDS)
         and parent.get("matched_physical_sensor_sets") is True
         and parent.get("new_first_use_claims")==0
         and parent.get("scientific_dispatch_authorized") is False
         and review.get("schema")=="forge.f8.independent-matched-sensor-timing-review.v1"
         and review.get("status")=="USED_F3_REAL_SOURCE_REPLAY_ONLY_NO_SCIENCE"
         and review.get("totals")==parent.get("groups")
         and review.get("replayed_trial_arms")==192
         and review.get("matched_set_comparisons")==96,
         "PARENT_ATTESTATION")
    need(model.get("schema")=="forge.f9.frozen-public-order-rule.v1"
         and model.get("status")=="TRAINED_F3_USED_SPLIT_ONLY_NO_PROSPECTIVE_AUTHORITY"
         and model.get("hypothesis_id")==
             "Y-FORGE-F9-LEARNED-PUBLIC-OBSERVATION-ORDER-PROPOSAL"
         and model.get("source_commit")==SOURCE_COMMIT
         and model.get("training_seeds")==list(TRAIN_SEEDS)
         and model.get("unseen_in_fit_validation_seeds")==list(VALIDATION_SEEDS)
         and model.get("training_case_pairs")==96
         and model.get("rule_bank")==list(RULES)
         and model.get("budget_public_reads")==10 and model.get("max_retained")==9
         and model.get("new_cohort_uses")==0
         and model.get("new_first_use_claims")==0
         and model.get("scientific_originals")==0
         and model.get("scientific_dispatch_authorized") is False,
         "FROZEN_TRAIN_IDENTITY")
    source=load_source(root)
    train=result.get("training")
    validation=result.get("validation")
    train_totals=compare_rows(source,train,TRAIN_SEEDS,(EARLY,SWAP))
    training=controls(train)
    need(len(training)==96 and all(set(v)=={EARLY,SWAP}
         for v in training.values()),"MISSING_COUNTERFACTUAL")
    scores=[]
    for rule in RULES:
        score=0;early_n=0
        for key,arms in sorted(training.items()):
            early,swap=arms[EARLY],arms[SWAP]
            e=early["sample_trace"]["decision"]
            w=swap["sample_trace"]["decision"]
            need(e["public_start"]==w["public_start"] and
                 e["physical_nonanchor_set"]==w["physical_nonanchor_set"],
                 "TRAIN_SENSOR_SET_DRIFT")
            vote=independent_vote(rule,e["public_start"])
            early_n+=int(vote)
            case=early if vote else swap
            score+=case["pre_mismatch"]+case["post_mismatch"]
        scores.append({"rule":rule,"training_mismatch_total":score,
                       "training_early_cases":early_n})
    best=min(scores,key=lambda x:(x["training_mismatch_total"],
                                 RULES.index(x["rule"])))
    need(model.get("scores")==scores and
         model.get("selected_rule")==best["rule"] and
         model.get("selected_training_loss")==best["training_mismatch_total"],
         "TRAIN_ONLY_SELECTION_DRIFT")
    validation_rules=tuple(dict.fromkeys((EARLY,SWAP,best["rule"])))
    need(result.get("validation_rules")==list(validation_rules),
         "VALIDATION_SOURCE_SELECTOR")
    validation_totals=compare_rows(source,validation,VALIDATION_SEEDS,validation_rules)
    need(result.get("training_case_arms")==len(train)==192 and
         result.get("validation_case_arms")==len(validation) and
         len(validation) in (192,288),"CANDIDATE_COUNTS")
    # Compare F9's constant controls to F8's *already independently*
    # source-qualified validation records on the exact same used seeds.
    old={}
    for row in parent["records"]:
        key=(row["seed"],tuple(row["pair"]),row["regime"],
             tuple(row["family"]),row["matching_policy"]))
        old.setdefault(key,{})[row["arm"]]=row
    new=controls(validation)
    need(len(old)==len(new)==96,"PARENT_COMPARISON_N")
    for key,arms in new.items():
        need(key in old,"PARENT_CASE_DRIFT")
        for rule,old_name in ((EARLY,"F8-F7-EARLY-CONTROL"),
                              (SWAP,"F8-SAME-SET-3-5-SWAP")):
            current=arms[rule]
            previous=old[key][old_name]
            need(current["pre_mismatch"]==previous["pre_mismatch"]
                 and current["post_mismatch"]==previous["post_mismatch"]
                 and current["first_detection"]==previous["first_detection"]
                 and current["sample_trace"]["addresses"]==
                     previous["sample_trace"]["addresses"]
                 and current["sample_trace"]["public_values"]==
                     previous["sample_trace"]["public_values"],
                 "F8_F9_SOURCE_CONTROL_MISMATCH")
    need(result.get("winner_selected") is False and
         result.get("scientific_dispatch_authorized") is False and
         all(result.get(k)==0 for k in (
             "new_cohort_uses","first_use_claims",
             "scientific_originals","paid_api_calls")),"ORIGINAL_AUTHORITY")
    return {"schema":"forge.f9.independent-public-timing-training-review.v1",
            "status":"PREVIOUSLY_USED_F3_SPLIT_QUALIFIED_NOT_NEW_SCIENCE",
            "selected_rule":best["rule"],"rule_is_adaptive":best["rule"] not in (EARLY,SWAP),
            "replayed_training_arms":len(train),
            "replayed_validation_arms":len(validation),
            "training_controls":train_totals,
            "validation_controls":validation_totals,
            "matched_f8_cases":len(old),
            "new_originals":0,"first_use_claims":0,
            "scientific_dispatch_authorized":False}

def main():
    p=argparse.ArgumentParser()
    for key in ("record","parent","witness","source-root","out"):
        p.add_argument("--"+key,required=True)
    a=p.parse_args()
    report=verify(json.loads(Path(a.record).read_bytes()),
                  Path(a.parent).read_bytes(),Path(a.witness).read_bytes(),
                  a.source_root)
    raw=(json.dumps(report,sort_keys=True,separators=(",",":"))+"\n").encode()
    with Path(a.out).open("xb") as fd:fd.write(raw)
    print("F9_INDEPENDENT_PUBLIC_TRAIN_AND_VALIDATION=PASS")
    print("F9_FROZEN_RULE="+report["selected_rule"])
    print("F9_TRUE_ADAPTIVE_RULE="+str(report["rule_is_adaptive"]).lower())
    print("F9_DEVELOPMENT_SPLIT_RESULTS="+json.dumps(report["validation_controls"],sort_keys=True))
    print("F9_REVIEW_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F9_NO_PROSPECTIVE_FIRST_USE=PASS")
if __name__=="__main__":main()
