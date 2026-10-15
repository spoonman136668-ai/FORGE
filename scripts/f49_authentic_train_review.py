"""F49 independent replay of new public-rank and causal-null TRAIN studies.

Frozen validation logic precedes F49 outcomes. Never dispatch or treat train
as independent F3 first use, Dream-RSI gain, or owner scientific acceptance.
"""
import argparse,hashlib,json,math
from pathlib import Path

class Blocked(ValueError):pass
def require(ok,reason):
    if not ok:raise Blocked("F49_"+reason)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def unique(pairs):
    d={}
    for k,v in pairs:
        require(k not in d,"DUPLICATE_JSON_KEY")
        d[k]=v
    return d
def parse(raw):
    require(type(raw)==bytes and 0<len(raw)<=4000000,"JSON_SIZE")
    return json.loads(raw,object_pairs_hook=unique)

def load(root,lane,source):
    spec=source[lane]
    root=Path(root)
    raw=(root/"result.json").read_bytes()
    require(sha(raw)==spec["report_sha256"],"REPORT_HASH")
    manifest=(root/"result.sha256").read_text().split()
    require(len(manifest)==2 and manifest[0]==sha(raw) and
        Path(manifest[1]).name=="result.json","REPORT_CHECKSUM")
    require((root/"SOURCE_SHA").read_text().strip()==spec["head"],"HEAD")
    data=parse(raw)
    require(data.get("paid_api_calls")==0 and
        data.get("accepted_ref_mutation") is False and
        data.get("independent_F3_custody") is False and
        data.get("primary_original_not_executed") is True,
        "FALSE_SCIENCE_OR_ORIGINAL")
    return data

def recount(lane,doc):
    w=lane=="Wingless"
    n=64 if w else 128
    lo,hi=([431100,431108] if w else [441100,441108])
    fam={640,641,642,643} if w else {660,661,662,663}
    schema=("wingless.f49.public-rank-information.trainonly.v1"
            if w else "yggdrasil.f49.conditional-pair-causal-null.trainonly.v1")
    stage=("NEW_PUBLIC_RANK_DIAGNOSTIC_NOT_PRIMARY_ORIGINAL"
           if w else "NEW_CAUSAL_NULL_TRAIN_DIAGNOSTIC_NO_ORIGINAL")
    reserved=[432000,432016] if w else [442000,442016]
    require(doc.get("schema")==schema and doc.get("stage")==stage and
            doc.get("diagnostic_seeds")==[lo,hi] and
            doc.get("proposed_originals_not_consumed")==reserved and
            set(doc.get("families",[]))==fam and
            doc.get("questions")==n and len(doc.get("rows",[]))==n,
            "SCHEMA_OR_COHORT")
    key="answers" if w else "predictions"
    rows=doc["rows"]; scores=doc["scores"];seen=set()
    for row in rows:
        require(type(row.get("seed")) is int and lo<=row["seed"]<hi and
                row.get("family") in fam, "RESERVED_OR_SOURCE")
        if w:
            ident=(row["seed"],row["family"],row["length"])
            require(row["length"] in (3,5) and
                    type(row.get("first_purchase_public_rank_agreement")) is bool and
                    len(row.get("public_partition_gains",[]))==2,
                    "W_STRUCTURE")
        else:
            ident=(row["seed"],row["family"],row["mechanism"],row["condition"])
            require(row["condition"] in ("coupled","decoupled") and
                    row["mechanism"] in ("nonlinear_hysteresis","cross_channel_flip") and
                    row.get("public_pairs")==12 and
                    row.get("public_flat_anchors")==24,"Y_STRUCTURE")
        require(ident not in seen and set(row[key])==set(scores),"DUPLICATE_ROW")
        seen.add(ident)
        for arm, trace in row["receipts"].items():
            if w:
                require(len(trace)<=2 and len({tuple(r[:2]) for r in trace})==len(trace),
                        "W_MAPPING_BUDGET")
            else:
                require(len(trace)==3 and all(len(t)==2 and t[0]==0 and
                        t[1] in (1,2,3) for t in trace),"Y_SENSOR_BUDGET")
    counted={}
    for arm,score in scores.items():
        c=sum(r[key][arm]==r["truth"] for r in rows)
        require(score["correct"]==c and score["total"]==n and
            abs(score["accuracy"]-c/n)<1e-12,"ACCURACY_RECOUNT")
        counted[arm]=c
        if not w:
            fp=sum(bool(r[key][arm]) and not r["truth"] for r in rows)
            fn=sum(not bool(r[key][arm]) and r["truth"] for r in rows)
            p=[r["probabilities"][arm] for r in rows]
            require(all(type(z) in (int,float) and 0<z<1 for z in p),
                    "PROBABILITY_INVALID")
            brier=sum((r["probabilities"][arm]-r["truth"])**2 for r in rows)/n
            loss=-sum(math.log(r["probabilities"][arm] if r["truth"] else
                              1-r["probabilities"][arm]) for r in rows)/n
            require(fp==score["fp"] and fn==score["fn"] and
                    abs(brier-score["Brier"])<1e-10 and
                    abs(loss-score["logloss"])<1e-10,"PROBABILITY_METRICS")
    return rows,counted

def wingless(doc,rows,counts):
    trial="public_stability_gate"
    fair=("one_step_value","exact_entropy","query_frontier","budget_matched_rank")
    strongest=max(counts[a] for a in fair)
    gain=(counts[trial]-strongest)/len(rows)
    totals={a:sum(r["work"][a] for r in rows) for a in doc["posterior_world_work"]}
    require(totals==doc["posterior_world_work"] and
        doc["strongest_fair_control"] in fair,"WORK_RECOUNT")
    ratio=totals[trial]/max(1,totals[doc["strongest_fair_control"]])
    families={str(f):{a:sum(r["answers"][a]==r["truth"] for r in rows
                           if r["family"]==f) for a in counts}
                for f in (640,641,642,643)}
    require(families==doc["by_family"],"FAMILY_RECOUNT")
    guard=all(families[str(f)][trial]>=max(families[str(f)][a] for a in fair)
              for f in (640,641,642,643))
    stable=[r for r in rows if r["first_purchase_public_rank_agreement"]]
    unstable=[r for r in rows if not r["first_purchase_public_rank_agreement"]]
    def uplift(items):
        return sum(int(r["answers"][trial]==r["truth"])-
                   int(r["answers"]["no_purchase"]==r["truth"])
                   for r in items)/len(items) if items else 0.
    s,u=uplift(stable),uplift(unstable)
    rate=len(stable)/len(rows)
    passed=(len(stable)>=4 and len(unstable)>=4 and rate>=.6 and
             s-u>=.05 and gain>=.03 and ratio<=3 and guard)
    require(abs(gain-doc["candidate_gain"])<1e-12 and
         abs(ratio-doc["work_ratio"])<1e-12 and
         guard==doc["family_nondegradation"] and
         len(stable)==doc["stable_cases"] and len(unstable)==doc["unstable_cases"] and
         abs(rate-doc["public_rank_agreement_rate"])<1e-12 and
         abs(s-doc["stable_ex_post_purchase_uplift"])<1e-12 and
         abs(u-doc["unstable_ex_post_purchase_uplift"])<1e-12 and
         passed==doc["frozen_criterion_met"] and
         doc["verdict"]==("TRAIN_ONLY_SUPPORTED_NOT_F3" if passed else "TRAIN_ONLY_NEGATIVE"),
         "FROZEN_THRESHOLD")
    require(doc["evaluator_private_truth_not_selector_input"] is True and
            doc["prereg_fit_seeds_held_not_consumed"]==[431000,431004],
            "FIT_LEAK")
    return dict(lane="Wingless",correct=counts[trial],fair=strongest,total=len(rows),
      gain_pp=round(gain*100,6),work_ratio=round(ratio,6),
      rank_agreement_rate=round(rate,6),stable_cases=len(stable),
      unstable_cases=len(unstable),stable_uplift=round(s,6),
      unstable_uplift=round(u,6),family_nondegradation=guard,
      disposition="TRAIN_ONLY_SUPPORTED_NOT_F3" if passed else "TRAIN_ONLY_NEGATIVE",
      next_hypothesis=("MEASURE_WHICH_PUBLIC_OBSERVATIONS_HAVE_IDENTIFIABLE_INFORMATION_GAIN_BEFORE_RELEARNING_ACTION_RANKS"
          if not passed else "REPLICATE_PUBLIC_RANK_STABILITY_ON_DISJOINT_TRAIN_FAMILIES"))

def yggdrasil(doc,rows,counts):
    trial="learned_intervention_invariant"
    shuffled="count_matched_shuffled_intervention_pairs"
    unpaired="learned_unpaired_ablation"
    fair=("fitted_Gaussian_latent","empirical_conditional_Brier","Gaussian_kernel",
      "public_global_static","source_variance",unpaired,shuffled)
    partitions={c:[r for r in rows if r["condition"]==c] for c in ("coupled","decoupled")}
    require(len(partitions["coupled"])==len(partitions["decoupled"])==64,
        "CONDITION_BALANCE")
    d={}
    for condition,rr in partitions.items():
        d[condition]={a:sum(r["predictions"][a]==r["truth"] for r in rr)
                      for a in counts}
    require(d==doc["condition_correct"],"CONDITION_RECOUNT")
    coupled=d["coupled"];null=d["decoupled"]
    gain=(coupled[trial]-max(coupled[a] for a in fair))/64
    shuffled_gain=(coupled[trial]-coupled[shuffled])/64
    unpaired_gain=(coupled[trial]-coupled[unpaired])/64
    null_gain=(null[trial]-null[shuffled])/64
    mechanisms={m:{a:sum(r["predictions"][a]==r["truth"] for r in rows
                   if r["mechanism"]==m) for a in counts}
        for m in ("nonlinear_hysteresis","cross_channel_flip")}
    require(mechanisms==doc["heldout_mechanism_correct"],
           "MECHANISM_RECOUNT")
    guard=all(mechanisms[m][trial]>=max(mechanisms[m][a] for a in fair)
              for m in mechanisms)
    passed=(gain>=.02 and shuffled_gain>0 and unpaired_gain>0 and
        abs(null_gain)<=.01 and shuffled_gain-null_gain>=.02 and guard)
    for v,k in ((gain,"coupled_gain_over_strongest_fair"),
                (shuffled_gain,"coupled_paired_vs_shuffled_gain"),
                (unpaired_gain,"coupled_paired_vs_unpaired_gain"),
                (null_gain,"decoupled_null_paired_vs_shuffled_gain"),
                (shuffled_gain-null_gain,"coupled_minus_null_ablation_difference")):
        require(abs(v-doc[k])<1e-12,"CONDITION_METRIC_"+k)
    require(guard==doc["heldout_mechanism_nondegradation"] and
        passed==doc["frozen_criterion_met"] and
        doc["fit_seeds"]==[441000,441008] and
        doc["evaluator_truth_never_selector_input"] is True and
        doc["verdict"]==("TRAIN_ONLY_SUPPORTED_NOT_F3" if passed else "TRAIN_ONLY_NEGATIVE"),
        "FROZEN_CAUSAL_THRESHOLD")
    return dict(lane="Yggdrasil",correct=counts[trial],
       fair=max(counts[a] for a in fair),total=len(rows),
       coupled_gain_pp=round(gain*100,6),
       paired_vs_shuffled_coupled_pp=round(shuffled_gain*100,6),
       paired_vs_unpaired_coupled_pp=round(unpaired_gain*100,6),
       paired_vs_shuffled_decoupled_null_pp=round(null_gain*100,6),
       heldout_mechanism_nondegradation=guard,
       disposition="TRAIN_ONLY_SUPPORTED_NOT_F3" if passed else "TRAIN_ONLY_NEGATIVE",
       next_hypothesis=("ISOLATE_DIRECT_CAUSAL_PAIR_INFORMATION_WITH_MATCHED_NULL_AND_UNPAIRED_CONTROLS"
           if not passed else "REPLICATE_IDENTIFIABLE_PAIRED_CAUSAL_GAIN_WITH_DISJOINT_TRAIN_MECHANISMS"))

def review(wroot,yroot,identities):
    require(identities.get("schema")=="forge.f49.source-manifest.v1" and
        set(identities.get("lanes",{}))=={"Wingless","Yggdrasil"},"IDENTITY_MANIFEST")
    d={}
    for lane,path in (("Wingless",wroot),("Yggdrasil",yroot)):
        spec=identities["lanes"][lane]
        require(type(spec["head"]) is str and len(spec["head"])==40 and
            type(spec["report_sha256"]) is str and len(spec["report_sha256"])==64 and
            type(spec["run_id"]) is int and type(spec["artifact_id"]) is int,
            "INVALID_SOURCE_ID")
        d[lane]=load(path,lane,identities["lanes"])
    wr,wc=recount("Wingless",d["Wingless"])
    yr,yc=recount("Yggdrasil",d["Yggdrasil"])
    return dict(schema="forge.f49.two-genuine-train-negatives.v1",
        sources=identities["lanes"],
        outcomes=[wingless(d["Wingless"],wr,wc),yggdrasil(d["Yggdrasil"],yr,yc)],
        new_train_diagnostics_recounted=2,
        prospective_primary_originals_executed=0,
        owner_admission_or_accepted_science=False,
        dream_rsi_prospective_improvement_proven=False,
        theta_evolve_learning_eligible=False,
        live_controller_or_worker_dispatch_authorized=False,
        f50_hypotheses_advisory_only=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--wingless",required=True)
    p.add_argument("--yggdrasil",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    manifest=parse(Path(a.manifest).read_bytes())
    Path(a.out).write_text(json.dumps(review(a.wingless,a.yggdrasil,manifest),
        sort_keys=True,separators=(",",":"))+"\n")
if __name__=="__main__":main()
