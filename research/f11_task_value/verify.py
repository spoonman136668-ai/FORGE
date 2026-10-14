"""Independent F11 expected-task-value witness; replay and refit.

No import of producer advance.fit/initial_model/run. All 576 original
source-used training arm records and 672 validation arm records are
replayed from the frozen Y070 simulator; context/action task-loss stats,
shrinkage metadata, active/retained limits, source identity and first-use
zero assertions are checked independently.
"""
import argparse,hashlib,json
from pathlib import Path
from policy import (SCHEMA,STATUS,ORDERS,PSEUDO,MIN_CONTEXT_SUPPORT,
                    TRAIN_SEEDS,TEST_SEEDS,PAIRS)
from worker import load_source,evaluate,SOURCE_COMMIT

def need(ok,why):
    if not ok:raise ValueError("F11_INDEPENDENT_"+why)

def verify(record,inputs,root):
    docs=[json.loads(raw) for raw in inputs]
    f10,f10w,proposal,prior=docs
    need(record.get("schema")=="forge.f11.automatic-task-aligned-information-value-engineering.v1"
         and record.get("status")=="REUSED_F3_TRAIN_AND_VALIDATION_ONLY"
         and record.get("source_commit")==SOURCE_COMMIT
         and record.get("parent_sha256")=={
             "f10":hashlib.sha256(inputs[0]).hexdigest(),
             "f10_witness":hashlib.sha256(inputs[1]).hexdigest(),
             "f11_hypothesis":hashlib.sha256(inputs[2]).hexdigest(),
             "f11_hypothesis_witness":hashlib.sha256(inputs[3]).hexdigest()},
         "PROVENANCE")
    need(f10.get("status")=="F3_USED_ONLY_NO_SCIENTIFIC_AUTHORITY"
         and f10.get("model",{}).get("train_seeds")==list(TRAIN_SEEDS)
         and f10.get("new_first_use_claims")==0
         and f10w.get("status")=="F3_USED_SOURCE_REPLAY_QUALIFIED_NOT_SCIENCE"
         and f10w.get("f10_historical_mismatches")==112
         and proposal.get("selected_proposal_id")==
            "Y-FORGE-F11-TASK-ALIGNED-OBSERVATION-VALUE-PROPOSAL"
         and proposal.get("original_f10_model_frozen_no_retuning") is True
         and proposal.get("scientific_dispatch_authorized") is False
         and prior.get("status")=="F11_DESIGN_PREPARED_NO_PROSPECTIVE_FIRST_USE"
         and prior.get("selected_id")==proposal["selected_proposal_id"],
         "ACCEPTED_PARENT_NEGATIVE")
    model=record.get("model",{})
    need(model.get("schema")==SCHEMA and model.get("status")==STATUS
         and model.get("source_commit")==SOURCE_COMMIT
         and model.get("train_seeds")==list(TRAIN_SEEDS)
         and model.get("validation_seeds")==list(TEST_SEEDS)
         and model.get("orders")==[list(x) for x in ORDERS]
         and model.get("pseudo_observations")==PSEUDO
         and model.get("minimum_context_support")==MIN_CONTEXT_SUPPORT
         and model.get("training_cases_per_order")==96
         and model.get("public_scalar_reads")==10
         and model.get("retained_limit")==9
         and model.get("new_first_use_claims")==0
         and model.get("scientific_dispatch_authorized") is False,
         "MODEL_SOURCE_FROZEN")
    source=load_source(root)
    def replay(rows,seeds,actions):
        need(type(rows) is list and
             len(rows)==96*len(actions),"CASE_COVERAGE")
        totals={str(x):{"cases":0,"pre":0,"post":0,"detections":0,
                         "steady_errors":0,"earliest_detection":None}
                for x in actions}
        observed=[];index=0
        for pair in PAIRS:
            for regime in ("steady","onset1"):
                for family in source.FAMILIES:
                    for seed in seeds:
                        for policy in source.POLICIES:
                            decisions=[]
                            for action in actions:
                                item=rows[index];index+=1
                                need(item.get("seed")==seed
                                     and item.get("pair")==list(pair)
                                     and item.get("regime")==regime
                                     and item.get("family")==list(family)
                                     and item.get("matching_policy")==policy
                                     and item.get("arm")==action,
                                     "CASE_IDENTITY")
                                new=evaluate(source,model,seed,pair,regime,
                                             family,policy,action)
                                need(new==item,"SOURCE_OR_PUBLIC_TRACE_TAMPER")
                                read=item["sample_trace"]["decision"]
                                need(read["reads"]==10
                                     and read["distinct_nonanchors"]==6
                                     and len(read["physical_cells"])==6,
                                     "SENSING_LIMIT")
                                decisions.append(read)
                                t=totals[str(action)]
                                t["cases"]+=1
                                t["pre"]+=item["pre_mismatch"]
                                t["post"]+=item["post_mismatch"]
                                t["detections"]+=int(item["first_detection"] is not None)
                                if regime=="steady":
                                    t["steady_errors"]+=item["pre_mismatch"]+item["post_mismatch"]
                                first=item["first_detection"]
                                if first is not None:
                                    t["earliest_detection"]=(first if t["earliest_detection"] is None
                                        else min(t["earliest_detection"],first))
                                observed.append(item)
                            need(all(x["physical_cells"]==decisions[0]["physical_cells"]
                                     for x in decisions),"PHYSICAL_SENSOR_SET_DRIFT")
        need(index==len(rows) and all(t["cases"]==96 for t in totals.values()),
             "CASE_BALANCE")
        return totals
    training=record.get("training")
    validation=record.get("validation")
    train_totals=replay(training,TRAIN_SEEDS,tuple(range(6)))
    counts=[[[0,0] for _ in range(6)] for _ in range(14)]
    globalsums=[0 for _ in range(6)]
    for row in training:
        s=row["sample_trace"]["decision"]["public_start"]
        action=row["arm"]
        cost=row["pre_mismatch"]+row["post_mismatch"]
        need(type(s) is int and 0<=s<14 and
             type(action) is int and action in range(6)
             and type(cost) is int and 0<=cost<=8,
             "TRAINING_INPUT")
        counts[s][action][0]+=1
        counts[s][action][1]+=cost
        globalsums[action]+=cost
    expected=[{"public_start":s,"action_index":action,
               "cases":counts[s][action][0],
               "total_task_loss":counts[s][action][1],
               "global_loss":globalsums[action]}
              for s in range(14) for action in range(6)]
    need(model.get("value_table")==expected
         and all(len(set(counts[s][a][0] for a in range(6)))==1
                 for s in range(14)),
         "FROZEN_TASK_LOSS_TABLE")
    checks=replay(validation,TEST_SEEDS,tuple(range(6))+("LEARNED",))
    need(checks==record.get("validation_summary"),"SUMMARY")
    need(checks["0"]["pre"]+checks["0"]["post"]==74 and
         checks["2"]["pre"]+checks["2"]["post"]==66,
         "PREVIOUSLY_QUALIFIED_F8_COMPARATORS")
    need(all(x["steady_errors"]==0 for x in checks.values())
         and record.get("scientific_winner_selected") is False
         and record.get("scientific_dispatch_authorized") is False
         and all(record.get(x)==0 for x in (
             "new_first_use_claims","new_originals",
             "new_cohort_accesses","paid_api_calls")),
         "FALSE_SCIENTIFIC_AUTHORITY")
    return {
      "schema":"forge.f11.independent-task-aligned-value-review.v1",
      "status":"PREVIOUS_F3_SOURCE_REPLAY_ONLY_NO_NEW_SCIENCE",
      "training_real_source_case_arms":576,
      "validation_real_source_case_arms":672,
      "reviewed_model_table_values":84,
      "validation_totals":checks,
      "best_constant_historical_mismatch":min(
          v["pre"]+v["post"] for k,v in checks.items() if k!="LEARNED"),
      "learned_historical_mismatch":checks["LEARNED"]["pre"]+checks["LEARNED"]["post"],
      "new_first_use_claims":0,
      "scientific_dispatch_authorized":False
    }

def main():
    p=argparse.ArgumentParser()
    for key in ("record","f10","f10-witness","f11","f11-witness","source-root","out"):
        p.add_argument("--"+key,required=True)
    a=p.parse_args()
    inputs=[Path(getattr(a,key.replace("-","_"))).read_bytes() for key in
            ("f10","f10-witness","f11","f11-witness")]
    x=verify(json.loads(Path(a.record).read_bytes()),inputs,a.source_root)
    raw=(json.dumps(x,sort_keys=True,separators=(",",":"))+"\n").encode()
    with Path(a.out).open("xb") as out:out.write(raw)
    print("F11_INDEPENDENT_TASK_VALUE_FIT_AND_SOURCE_REPLAY=PASS")
    print("F11_BEST_FIXED_HISTORICAL_TOTAL="+str(x["best_constant_historical_mismatch"]))
    print("F11_LEARNED_HISTORICAL_TOTAL="+str(x["learned_historical_mismatch"]))
    print("F11_AUDIT_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F11_ORIGINAL_FIRST_USE=ZERO")
if __name__=="__main__":main()
