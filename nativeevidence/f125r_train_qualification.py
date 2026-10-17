"""F125-R public TRAIN-only learning using authenticated frozen headroom receipts.

Fail-closed exact source identity and immutable F125-R proposal, no original
science or protected confirmation. Retains every positive and negative TRAIN
case even if model fails. No hyperparameter selection on reserved inputs.
"""
from __future__ import annotations
import argparse,hashlib,json,math,os,re,sys
from pathlib import Path
import f118_autonomy_feedback as f118
import f120_generated_environment as f120
import f125r_freeze_admission as freeze
import f125r_train_environment as env
import f125r_train_headroom as headroom
import f125r_path_model as model

SCHEMA="forge.autonomy.f125r.path-preserving-public-train-custody.v1"

def need(ok,why):env.need(bool(ok),"TRAIN_ADMISSION_"+why)
def sealed(path):
    p=Path(path)
    raw=p.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    seal=p.with_suffix(p.suffix+".sha256")
    need(seal.exists() and seal.read_text(encoding="utf-8").strip()==
         digest+"  "+p.name,"ORIGINAL_SHA256_RECEIPT")
    return json.loads(raw.decode("utf-8-sig")),digest

def git_blob(p):
    content=Path(p).read_bytes().replace(b"\r\n",b"\n")
    return hashlib.sha1(b"blob "+str(len(content)).encode()+b"\0"+content).hexdigest()

def verify_headroom(advisory,eligibility,source):
    protocol,_=freeze.frozen()
    need(type(source) is str and re.fullmatch(r"[0-9a-f]{40}",source)
         and (not os.getenv("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source)
         and eligibility.get("schema")==headroom.SCHEMA
         and eligibility.get("source_sha")==source
         and eligibility.get("freeze_git_blob")==freeze.FROZEN_BLOB
         and eligibility.get("advisory_sha256")==env.digest(advisory)
         and eligibility.get("phase")=="PUBLIC_SYNTHETIC_TRAIN_ELIGIBILITY_ONLY"
         and eligibility.get("disposition")=="TRAIN_HEADROOM_ELIGIBLE"
         and eligibility.get("all_lanes_headroom_eligible") is True
         and eligibility.get("trained_weights_created") is False
         and eligibility.get("reserved_confirm_generated") is False
         and eligibility.get("scientific_first_use") is False
         and eligibility.get("no_seed_or_threshold_retuning") is True,
         "INELIGIBLE_HEADROOM_OR_IDENTITY")
    source_entries=f120.validate(advisory,source)
    need(type(eligibility.get("lanes")) is list and
         len(eligibility["lanes"])==2
         and [x.get("lane") for x in eligibility["lanes"]]==
             ["Wingless","Yggdrasil"],"SPLIT_OR_LANE_ORDER")
    for x in eligibility["lanes"]:
        lane=x["lane"]
        entries=source_entries[lane]
        vectors=[e["vector"] for e in entries]
        need(x.get("source_candidate_shas")==
             [e["source_candidate_sha256"] for e in entries]
             and x.get("vectors_sha256")==env.digest(vectors)
             and x.get("train_pairs")==64
             and x.get("minimum_frozen_headroom")==0.08
             and x.get("exact_public_symbolic_ceiling",{}).get("paired_correct")==64
             and x.get("headroom_eligible") is True
             and x.get("train_ceiling_minus_best_fixed_fraction",0)>=0.08,
             "HEADROOM_BEFORE_TRAIN")
        rows=env.train_rows(lane,vectors)
        need(x.get("full_train_rows_sha256")==env.digest(rows),
             "GRAPH_SOURCE_TAMPERING")
    return source_entries

def train(advisory,eligibility,source):
    candidates=verify_headroom(advisory,eligibility,source)
    _,freeze_sha=freeze.frozen()
    lanes=[]
    for lane in ("Wingless","Yggdrasil"):
        vectors=[e["vector"] for e in candidates[lane]]
        rows=env.train_rows(lane,vectors)
        trained,movement=model.fit(rows)
        score=model.score(rows,trained)
        total={}
        max_states=0
        for obs,label in rows:
            prediction,gradient,trace=model.forward(obs,trained,True)
            max_states=max(max_states,trace["work"]["state_limit_peak"])
            for key,count in trace["work"].items():
                total[key]=total.get(key,0)+count
        need(score["pairs"]==64 and len(trained)==20 and
             movement>.0001 and max_states<=256,
             "MODEL_FINAL_SCORE_OR_BUDGET")
        lanes.append({
           "lane":lane,
           "source_candidate_shas":[e["source_candidate_sha256"]
                                    for e in candidates[lane]],
           "source_vectors_sha256":env.digest(vectors),
           "train_rows_sha256":env.digest(rows),
           "trained_weights":trained,
           "weights_sha256":model.sha(trained),
           "weight_movement_l2":round(movement,12),
           "learned_parameter_count":20,
           "frozen_optimizer_epochs":100,
           "train_score":score,
           "train_graphs_instrumented":128,
           "public_max_state_keys":max_states,
           "work_accounting":total,
           "pruned_states_by_design":0,
           "matched_compute_ratio_to_f123_dense_established":False,
           "protected_confirmation_samples":0,
           "scientific_accepted":False})
    return {"schema":SCHEMA,
       "source_sha":source,
       "frozen_git_blob":freeze.FROZEN_BLOB,
       "freeze_sha256":freeze_sha,
       "model_git_blob":git_blob(model.__file__),
       "train_graph_git_blob":git_blob(env.__file__),
       "headroom_source_git_blob":git_blob(headroom.__file__),
       "advisory_sha256":env.digest(advisory),
       "headroom_report_sha256":env.digest(eligibility),
       "phase":"AUTHENTIC_SOURCE_PUBLIC_TRAIN_ONLY_NOT_SCIENCE",
       "lanes":lanes,
       "protected_confirmation_read":False,
       "scientific_first_use":False,
       "scientific_acceptance":False,
       "optimizer_promotion":False,
       "accepted_ref_mutation":False,
       "originals_dispatched":0,
       "paid_model_calls":0,
       "codex_calls":0,
       "new_scheduler":False}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--advisory",required=True)
    parser.add_argument("--headroom",required=True)
    parser.add_argument("--source-sha",required=True)
    parser.add_argument("--output",required=True)
    a=parser.parse_args()
    raw_advisory=f118.load_report(a.advisory)
    eligible,_=sealed(a.headroom)
    # Verify input advisory unchanged and content-received from same run.
    advisory_sha=hashlib.sha256(Path(a.advisory).read_bytes()).hexdigest()
    advisory_seal=Path(a.advisory).with_suffix(".json.sha256")
    need(advisory_seal.exists() and
         advisory_seal.read_text(encoding="utf-8").strip()==
         advisory_sha+"  "+Path(a.advisory).name,
         "ADVISORY_SHA256_RECEIPT")
    result=train(raw_advisory,eligible,a.source_sha)
    dest=Path(a.output)
    need(dest.parent.is_dir() and not dest.exists(),"RECEIPT_OVERWRITE")
    raw=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    dest.open("xb").write(raw)
    print("F125R_TRAIN_REPORT_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in result["lanes"]:
        print("F125R_"+lane["lane"].upper()+"_PAIRED="+
              str(lane["train_score"]["paired_correct"])+"/64")
    print("F125R_SCIENCE_ACCEPTANCE=false")
    print("F125R_CONFIRM_EXECUTED=false")

if __name__=="__main__":
    try:main()
    except (env.Invalid,freeze.Invalid,f118.Quarantined,f120.Invalid,
            ValueError,KeyError,TypeError,IndexError,OSError) as exc:
        print("F125R_TRAIN_QUARANTINED="+str(exc),file=sys.stderr)
        raise SystemExit(1)
