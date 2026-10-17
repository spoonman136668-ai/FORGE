"""F127-R FIT-only source and untouched TRAIN_CHECK comparison."""
import argparse,hashlib,json,os,re,sys
from pathlib import Path
import f118_autonomy_feedback as f118
import f120_generated_environment as f120
import f127r_freeze_admission as freeze
import f127r_train_environment as env
import f127r_calibrated_model as model
import f126r_contrastive_model as f126
import f125r_path_model as f125
import f123_controls as fixed
import f126r_train_qualification as base
import f123_learned_routing as dense

def need(v,k):env.need(bool(v),"AUDIT_"+k)
def eval_lane(lane,vectors):
    fit=env.cohort_rows(lane,vectors,"FIT")
    check=env.cohort_rows(lane,vectors,"TRAIN_CHECK")
    need(len(fit)==len(check)==64,"SPLIT")
    need(not ({env.digest(g) for g,y in fit}&{env.digest(g) for g,y in check}),
         "SOURCE_COLLISION")
    weights,motion=model.fit(fit)
    # Original frozen comparison fit routines use 128 rows. Duplicate
    # FIT only; do not read/check scores to train or change native sources.
    doubled=fit+fit
    w126,_=f126.fit(doubled)
    w125,_=f125.fit(doubled)
    w123=base.trained_dense(doubled)
    wquery=base.trained_query(doubled)
    funcs={
      "F127R_LEARNED":lambda g:model.forward(g,weights)[0],
      "CTRL_EXACT_PUBLIC_SYMBOLIC_ELIGIBLE":lambda g:float(env.graph_paths(g,True)>0),
      "CTRL_F126R_ORIGINAL_ARCH_FRESH_FIT":lambda g:f126.forward(g,w126)[0],
      "CTRL_F125R_PATH_PRESERVING_FRESH_FIT":lambda g:f125.forward(g,w125)[0],
      "CTRL_F123_DENSE_B_FRESH_FIT":lambda g:dense.predict_b(g,w123)[0],
      "CTRL_FIXED_SOFT_12_OF_16":lambda g:float(fixed.fixed_soft_path(g)),
      "CTRL_ROLE_ONLY":lambda g:float(env.graph_paths(g)>0),
      "CTRL_QUERY_ONLY_FRESH_FIT":lambda g:model.sigmoid(
          sum(a*b for a,b in zip(wquery,fixed.topology_features(g)))),
      "CTRL_F127R_NO_DEPTH_AND_PATH_RESIDUAL_ABLATION":
           lambda g:model.forward(g,weights,ablation="NO_RESIDUAL")[0],
      "CTRL_F127R_GRAPH_NULL_SUBTRACTION_ABLATION":
           lambda g:model.forward(g,weights,ablation="GRAPH_NULL_SUBTRACTION")[0]}
    scores={name:model.score(check,predict) for name,predict in funcs.items()}
    need(scores["CTRL_EXACT_PUBLIC_SYMBOLIC_ELIGIBLE"]["paired_correct"]==32,
         "EXACT_ELIGIBLE")
    blocked=sum(len(g["roles"])>4 for g,y in check)
    need(blocked>0,"NATIVE_SPARSE_INTERFACE")
    scores["CTRL_F124R_SPARSE2_FROZEN_INTERFACE_BLOCKED_AT_DEPTH5"]={
       "status":"BLOCKED_FROZEN_INTERFACE_DEPTH_5",
       "incompatible_graphs":blocked,"native_source_unmodified":True}
    return {"lane":lane,"FIT_sha256":env.digest(fit),
        "TRAIN_CHECK_sha256":env.digest(check),
        "FIT_pairs":32,"TRAIN_CHECK_pairs":32,
        "weights":weights,"motion_l2":motion,
        "weights_sha256":env.digest(weights),
        "fit_score_diagnostic":model.score(fit,funcs["F127R_LEARNED"]),
        "TRAIN_CHECK_scores":scores,
        "exact_symbolic_is_eligible":True,
        "cost_superiority_proven":False,
        "scientific_accepted":False}
def run(advisory,sha):
    freeze.frozen()
    need(type(sha) is str and re.fullmatch(r"[0-9a-f]{40}",sha)
        and (not os.getenv("GITHUB_SHA") or os.environ["GITHUB_SHA"]==sha),
        "SOURCE_SHA")
    cand=f120.validate(advisory,sha)
    lanes=[]
    for name in ("Wingless","Yggdrasil"):
        e=cand[name]
        need(len(e)==2 and [x["candidate_index"] for x in e]==[2,3]
             and e[0]["vector"]!=e[1]["vector"],"SOURCE_CANDIDATES")
        result=eval_lane(name,[x["vector"] for x in e])
        result["candidate_sha256"]=[x["source_candidate_sha256"] for x in e]
        lanes.append(result)
    return {"schema":"forge.research.f127r.fit-train-check-controls.v1",
        "source_sha":sha,"frozen_blob":freeze.FREEZE_BLOB,
        "phase":"PUBLIC_FIT_AND_DISJOINT_TRAIN_CHECK",
        "lanes":lanes,"protected_CONFIRM_read":False,
        "originals_dispatched":0,"scientific_first_use":False,
        "scientific_acceptance":False,"optimizer_promotion":False,
        "accepted_ref_mutations":0,"codex_calls":0,"paid_calls":0}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--advisory",required=True)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",required=True)
    x=p.parse_args()
    report=run(f118.load_report(x.advisory),x.source_sha)
    target=Path(x.output)
    need(target.parent.is_dir() and not target.exists(),"OVERWRITE")
    raw=(json.dumps(report,sort_keys=True,separators=(",",":"))+"\n").encode()
    target.open("xb").write(raw)
    print("F127R_TRAIN_SHA256="+hashlib.sha256(raw).hexdigest())
    for r in report["lanes"]:
        s=r["TRAIN_CHECK_scores"]["F127R_LEARNED"]
        print("F127R_"+r["lane"].upper()+"_PAIRED="+str(s["paired_correct"])+"/32")
        print("F127R_"+r["lane"].upper()+"_RANK="+str(s["rank_correct"])+"/32")
if __name__=="__main__":
    try:main()
    except (env.Invalid,freeze.Quarantined,f118.Quarantined,
            KeyError,ValueError,TypeError,OSError) as error:
        print("F127R_FAIL_CLOSED="+str(error),file=sys.stderr)
        raise SystemExit(1)
