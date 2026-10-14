"""F10 train expected observation information from F9 public-only traces.

No new simulator training probes, labels from a hidden swap, or F9
validation records may enter fitting. The only supervision is whether a
historically observed public scalar deviated from the publicly calibrated
coordinate model. All F9 training episodes and sensor addresses were
previously used F3 development data.
"""
import hashlib
import json
from policy import (SCHEMA,MODEL_STATUS,EPISODES,PROBES,TRAIN,CHECK,PAIRS,
                    public_start,prior_anomaly,anomaly,model_identity)

PARENT_SCHEMA="forge.f9.automatic-public-order-training.v1"
WITNESS_SCHEMA="forge.f9.independent-public-timing-training-review.v1"
F9_SOURCE="5797a257a75fe139313e8486cd1a1ae79c44b148"

def must(value,reason):
    if not value:raise ValueError("F10_TRAIN_"+reason)

def canonical(obj):
    return (json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()

def previous_evidence(parent,witness):
    must(parent.get("schema")==PARENT_SCHEMA and
         parent.get("status")=="F3_PREVIOUSLY_USED_ENGINEERING_ONLY" and
         parent.get("source_commit")==F9_SOURCE and
         parent.get("new_cohort_uses")==0 and
         parent.get("first_use_claims")==0 and
         parent.get("scientific_originals")==0 and
         parent.get("paid_api_calls")==0 and
         parent.get("scientific_dispatch_authorized") is False and
         parent.get("winner_selected") is False,"PARENT_SOURCE_AND_AUTHORITY")
    method=parent.get("model",{})
    must(method.get("schema")=="forge.f9.frozen-public-order-rule.v1" and
         method.get("status")=="TRAINED_F3_USED_SPLIT_ONLY_NO_PROSPECTIVE_AUTHORITY" and
         method.get("training_seeds")==list(TRAIN) and
         method.get("unseen_in_fit_validation_seeds")==list(CHECK) and
         method.get("selected_rule")=="START_GE7_EARLY" and
         method.get("scientific_dispatch_authorized") is False,
         "F9_TRAINING_IDENTITY")
    must(witness.get("schema")==WITNESS_SCHEMA and
         witness.get("status")=="PREVIOUSLY_USED_F3_SPLIT_QUALIFIED_NOT_NEW_SCIENCE" and
         witness.get("selected_rule")==method["selected_rule"] and
         witness.get("replayed_training_arms")==192 and
         witness.get("replayed_validation_arms")==288 and
         witness.get("matched_f8_cases")==96 and
         witness.get("new_originals")==0 and witness.get("first_use_claims")==0 and
         witness.get("scientific_dispatch_authorized") is False,
         "INDEPENDENT_F9_ACCEPTANCE")
    training=parent.get("training")
    validation=parent.get("validation")
    must(type(training) is list and len(training)==192 and
         type(validation) is list and len(validation)==288 and
         all(row.get("seed") in TRAIN and
             row.get("pair") in [list(x) for x in PAIRS] and
             row.get("rule") in ("ALWAYS_EARLY","ALWAYS_SWAP")
             for row in training) and
         all(row.get("seed") in CHECK for row in validation),
         "TRAIN_VALIDATION_LEAK")
    return training

def history_from_row(row):
    sample=row.get("sample_trace",{})
    addresses=sample.get("addresses")
    values=sample.get("public_values")
    must(type(addresses) is list and len(addresses)==5 and
         type(values) is list and len(values)==5,"TRACE")
    result={}
    for t,loc,v in zip(EPISODES,addresses,values):
        must(type(loc) is list and len(loc)==2 and len(set(loc))==2 and
             type(v) is list and len(v)==2,"PUBLIC_PAIR")
        result[t]=dict(zip(loc,v))
        must(len(result[t])==2 and all(type(a) is int and a in range(16)
             and type(b) is int and b in range(16) for a,b in result[t].items()),
             "PUBLIC_OBSERVATIONS")
    return result

def train(parent_bytes,witness_bytes):
    parent=json.loads(parent_bytes)
    witness=json.loads(witness_bytes)
    rows=previous_evidence(parent,witness)
    table=[{"episode":t,"prior_anomaly":flag,"offset":offset,
            "observations":0,"anomalies":0}
           for t in PROBES for flag in (0,1) for offset in range(14)]
    identities=set()
    for row in rows:
        identity=(row["seed"],tuple(row["pair"]),row["regime"],
                  tuple(row["family"]),row["matching_policy"],row["rule"])
        must(identity not in identities,"DUPLICATE_CASE")
        identities.add(identity)
        h=history_from_row(row)
        s=public_start(h)
        for t in PROBES:
            flag=prior_anomaly(h,t)
            for cell,value in h[t].items():
                must(cell in range(2,16),"NONANCHOR_ONLY")
                offset=(cell-2-s)%14
                item=table[PROBES.index(t)*28+flag*14+offset]
                item["observations"]+=1
                item["anomalies"]+=anomaly(h,t,cell,value)
    must(len(identities)==192 and
         sum(item["observations"] for item in table)==1152,
         "TRAIN_LABEL_COUNT")
    model={
       "schema":SCHEMA,
       "status":MODEL_STATUS,
       "hypothesis_id":"Y-FORGE-F10-EXPECTED-PUBLIC-INFORMATION-VALUE-PROPOSAL",
       "source_commit":F9_SOURCE,
       "parent_f9_sha256":hashlib.sha256(parent_bytes).hexdigest(),
       "parent_f9_independent_sha256":hashlib.sha256(witness_bytes).hexdigest(),
       "learned_objective":"posterior_expected_Brier_uncertainty_reduction_p_times_one_minus_p",
       "smoothing_prior":"Beta(1,1)",
       "training_label":"publicly_calibrated_coordinate_residual_nonzero",
       "train_seeds":list(TRAIN),"validation_seeds":list(CHECK),
       "train_public_observations":1152,
       "table":table,
       "public_scalar_reads":10,
       "retained_limit":9,
       "first_use_claims":0,
       "scientific_dispatch_authorized":False
    }
    model_identity(model)
    return model
