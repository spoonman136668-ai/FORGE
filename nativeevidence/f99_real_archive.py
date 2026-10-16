"""F99: pin exact original archive bytes, independently aggregate historical DEV negatives.

These are observed DEVELOPMENT diagnostics, not independent scientific originals.
No network, executor, CKB, scientific approval, or optimizer training occurs here.
"""
import argparse
import hashlib
import io
import json
import math
import pathlib
import sys
import zipfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
FROZEN=ROOT/"reference/research-intake/f99-authentic-development-negative-history.json"
SCHEMA="forge.autonomy.f99.authentic-development-negative-history.v1"
REPORT="forge.autonomy.f99.row-reaggregated-train-only-shadow.v1"
class Quarantined(ValueError):pass
def need(ok,where):
    if not ok:raise Quarantined("F99_"+where)
def strict_pairs(pairs):
    out={}
    for key,value in pairs:
        need(key not in out,"DUPLICATE_JSON_KEY")
        out[key]=value
    return out
def read_json(raw):
    need(type(raw) is bytes and 0<len(raw)<=640000,"JSON_SIZE")
    try:
        obj=json.loads(raw.decode("utf-8"),object_pairs_hook=strict_pairs,
                      parse_constant=lambda _:need(False,"NONFINITE"))
    except (UnicodeError,json.JSONDecodeError) as exc:
        raise Quarantined("F99_MALFORMED_JSON") from exc
    need(type(obj) is dict,"OBJECT_REQUIRED")
    return obj
def sha(raw):return hashlib.sha256(raw).hexdigest()
def frozen():
    d=read_json(FROZEN.read_bytes())
    need(d.get("schema")==SCHEMA and len(d.get("cohorts",[]))==2 and
         [r.get("lane") for r in d["cohorts"]]==["Wingless","Yggdrasil"],
         "FROZEN_COHORT_DRIFT")
    guard=d.get("assumptions",{})
    for key in ("independent_source_birth_verified","sealed_original_first_use_verified",
                "scientific_results_accepted","genenv_training_activated",
                "optimizer_selection_qualified","policy_promotion_authorized"):
        need(guard.get(key) is False,"UNAUTHORIZED_POLICY_TRAINING")
    for key in ("new_scientific_originals_dispatched","accepted_ref_mutations",
                "codex_calls","paid_api_calls"):
        need(type(guard.get(key)) is int and guard[key]==0,"UNAUTHORIZED_SCIENCE_EXECUTION")
    seen=set()
    for x in d["cohorts"]:
        need(x["repository"]=="spoonman136668-ai/"+x["lane"] and
             x["artifact_id"] not in seen and len(x["zip_sha256"])==64 and
             len(x["payload_sha256"])==64 and len(x["head_sha"])==40 and
             x["training_only"] is True and
             x["classification"]=="HISTORICAL_DEVELOPMENT_NEGATIVE_NOT_ACCEPTED_ORIGINAL" and
             x["pair_count"] in (96,192) and
             x["observed_train_only_vector"]==
             [x["pair_count"]-x["learned_correct_pairs"],x["coded_control_correct_pairs"],x["pair_count"]],
             "HISTORICAL_FROZEN_RECORD_DRIFT")
        seen.add(x["artifact_id"])
    return d
def pair(x):
    return type(x) is list and len(x)==2 and all(type(i) is int for i in x)
def semantic(spec,data):
    lane=spec["lane"]
    wing=lane=="Wingless"
    require_false=("model_retrained","source_birth_independent","sealed_first_use")
    need(data.get("schema")==spec["payload_schema"] and
         data.get("registered_verdict")==spec["verdict"] and
         data.get("stage")=="DEVELOPMENT_ONLY","ORIGINAL_DEV_SCHEMA_OR_VERDICT")
    need(all(data.get(k) is False for k in require_false) and
         type(data.get("external_llm_calls")) is int and data["external_llm_calls"]==0,
         "MODEL_OR_FIRST_USE_UNEXPECTED")
    if wing:
        need(data.get("query_depth_is_present_in_frozen_model_interface") is False and
             data.get("explicit_depth_is_only_control_input") is True and
             data.get("accepted_ref_mutation") is False and
             data.get("graph_states")==96 and
             data.get("paired_questions")==192 and
             data.get("seeds")==[51100,51124],
             "WINGLESS_TASK_OR_SOURCE_DRIFT")
        ids={(seed,depth) for seed in range(51100,51124) for depth in range(4,8)}
        keys={"always_yes_shortcut","coded_depth_aware_oracle",
              "frozen_learned_composition_depth_blind","old_F5_depth_blind"}
    else:
        need(data.get("candidate_state_contains_role_codes") is False and
             data.get("role_swaps_change_only_relation_types") is True and
             data.get("same_untyped_edges_and_query_per_counterfactual") is True and
             data.get("scientific_accepted") is False and
             data.get("graph_pairs")==192 and data.get("question_count")==384 and
             data.get("seeds")==[51400,51448] and
             data.get("families")==[40,41,42,43],
             "YGGDRASIL_TASK_OR_SOURCE_DRIFT")
        ids={(seed,fam) for seed in range(51400,51448) for fam in range(40,44)}
        keys={"always_yes_shortcut","frozen_learned_role_blind",
              "typed_role_aware_oracle","untyped_coded_reachability"}
    rows=data.get("rows")
    need(type(rows) is list and len(rows)==spec["pair_count"],"ROW_COMPLETENESS")
    counts={k:dict(pairs=0,correct=0,negative=0,positive=0,fp=0) for k in keys}
    seen=set()
    for row in rows:
        need(type(row) is dict,"ROW_SCHEMA")
        identity=(row.get("seed"),row.get("path_depth") if wing else row.get("family"))
        need(identity in ids and identity not in seen,"ROW_REPLAY_OR_UNKNOWN_SEED")
        seen.add(identity)
        truth=row.get("truth")
        need(truth==([False,True] if wing else [True,False]) and
             pair(row.get("query") if wing else row.get("question")) and
             type(row.get("edges")) is list and len(row["edges"])==12 and
             all(pair(e) for e in row["edges"]),"ROW_TASK_STRUCTURE")
        preds=row.get("models" if wing else "predictions")
        need(type(preds) is dict and set(preds)==keys,"MISSING_FULL_CONTROL_POPULATION")
        if wing:
            depth=row["path_depth"]
            prob=row.get("frozen_probability")
            need(row.get("requested_depths")==[depth-1,depth] and
                 type(prob) in (int,float) and math.isfinite(prob) and 0<=prob<=1,
                 "DEPTH_PAIR_OR_MODEL_PROBABILITY")
        else:
            roles=row.get("roles_positive")
            swapped=row.get("roles_swapped")
            requested=row.get("requested_role_sequence")
            need(type(roles) is list and type(swapped) is list and
                 type(requested) is list and len(roles)==len(swapped)==12 and
                 len(requested)==4 and
                 all(type(v) is int and 0<=v<=3 for v in roles+swapped+requested) and
                 sum(x!=y for x,y in zip(roles,swapped))==1,
                 "RELATION_ROLE_COUNTERFACTUAL_DRIFT")
        for key,pred in preds.items():
            need(type(pred) is list and len(pred)==2 and
                 all(type(v) is bool for v in pred),"ROW_BOOLEAN_PREDICTION")
            c=counts[key]
            c["pairs"]+=int(pred==truth)
            c["correct"]+=sum(a==b for a,b in zip(pred,truth))
            c["negative"]+=int(pred[0 if wing else 1] is False)
            c["positive"]+=int(pred[1 if wing else 0] is True)
            c["fp"]+=int(pred[0 if wing else 1] is True)
    need(seen==ids,"NONCOMPLETE_FROZEN_COHORT")
    scores=data.get("scores")
    need(type(scores) is dict and set(scores)==keys,"SCORE_CONTROL_COMPLETENESS")
    for key,c in counts.items():
        s=scores[key]
        need(type(s) is dict and type(s.get("paired_correct")) is int and
             s["paired_correct"]==c["pairs"] and
             s.get("paired_accuracy")==c["pairs"]/len(rows) and
             s.get("accuracy")==c["correct"]/(2*len(rows)),
             "SCORE_REAGGREGATION_DRIFT")
        if wing:
            need(s.get("negative_correct")==c["negative"] and
                 s.get("positive_correct")==c["positive"],
                 "WINGLESS_POLARITY_REAGGREGATION")
        else:
            need(s.get("correct")==c["correct"] and
                 s.get("negative_false_positives")==c["fp"],
                 "YGGDRASIL_FALSE_POSITIVES")
    model=counts[spec["learned_model"]]["pairs"]
    coded=counts[spec["coded_control"]]["pairs"]
    need(model==spec["learned_correct_pairs"] and
         coded==spec["coded_control_correct_pairs"] and coded==len(rows) and model==0 and
         [len(rows)-model,coded,len(rows)]==spec["observed_train_only_vector"],
         "FROZEN_HISTORICAL_NEGATIVE_RELABELED")
    return dict(lane=lane,experiment=spec["experiment"],
                source_sha=spec["head_sha"],artifact_id=spec["artifact_id"],
                zip_sha256=spec["zip_sha256"],payload_sha256=spec["payload_sha256"],
                observed_historical_development_pairs=len(rows),
                independently_reaggregated_learned_correct_pairs=model,
                independently_reaggregated_coded_control_pairs=coded,
                historical_development_negative_only=True,
                train_only_observation_vector=[len(rows)-model,coded,len(rows)],
                actual_archive_bytes_rehashed=True,
                contained_json_rows_reaggregated=True,
                independently_accepted_scientific_original=False,
                genenv_training_activated=False)
def audit_archive(spec,path):
    raw=pathlib.Path(path).read_bytes()
    need(0<len(raw)<1000000 and sha(raw)==spec["zip_sha256"],"ARCHIVE_ZIP_SHA256_DRIFT")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as f:
            infos=f.infolist()
            need(len(infos)==1 and infos[0].filename==spec["member"] and
                 infos[0].file_size<=500000 and infos[0].compress_size<=500000 and
                 infos[0].file_size<=60*max(1,infos[0].compress_size) and
                 infos[0].compress_type in (zipfile.ZIP_DEFLATED,zipfile.ZIP_STORED) and
                 not infos[0].is_dir(),"ARCHIVE_MEMBER_CONTRACT")
            payload=f.read(infos[0])
    except (zipfile.BadZipFile,RuntimeError,EOFError,ValueError) as exc:
        raise Quarantined("F99_ZIP_MALFORMED") from exc
    need(sha(payload)==spec["payload_sha256"],"CONTAINED_JSON_SHA256_DRIFT")
    return semantic(spec,read_json(payload))
def assess(zip_paths):
    f=frozen()
    need(type(zip_paths) is list and len(zip_paths)==2,"TWO_ARCHIVES_REQUIRED")
    results=[audit_archive(s,p) for s,p in zip(f["cohorts"],zip_paths)]
    return dict(schema=REPORT,
       scope="HISTORICAL_DEV_NEGATIVES_READONLY_NOT_NEW_SCIENCE",
       cohorts=results, archived_negative_development_records=2,
       training_only_observations_observed=2,
       genenv_training_activated=False,
       independent_originals_accepted=0,
       protected_first_use_authorized=False,
       research_results_replayed=False,
       accepted_ref_mutations=0,
       new_originals_dispatched=0,
       model_calls=0,codex_calls=0,paid_api_calls=0)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--wingless-zip",required=True)
    p.add_argument("--yggdrasil-zip",required=True)
    args=p.parse_args()
    print(json.dumps(assess([args.wingless_zip,args.yggdrasil_zip]),
                     sort_keys=True,separators=(",",":")))
if __name__=="__main__":
    try:main()
    except (Quarantined,OSError,KeyError,TypeError) as exc:
        print("FORGE_F99_AUTHENTIC_DEV_ARCHIVE_ROWS=QUARANTINED "+str(exc),file=sys.stderr)
        raise SystemExit(1)
