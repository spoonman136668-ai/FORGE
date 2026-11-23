"""Independent R10 source-level method-fidelity and genuine development-row witness.

No access to the original scientific evaluator or learned training code.
Reaggregates every reported row against pinned Wingless low-level generator.
"""
import argparse,hashlib,importlib.util,json,math,pathlib,subprocess
from next_policy import check_frozen,parse,sha,fail as reject
def near(a,b):
    return isinstance(a,(int,float)) and not isinstance(a,bool) and math.isfinite(a) and abs(a-b)<1e-8
def verify(frozen_raw,proposal_raw,screen_raw,wingless_root):
    m=check_frozen(frozen_raw);proposal=parse(proposal_raw);report=parse(screen_raw)
    if (report.get("schema")!="forge.r10.gradient-conflict.real-development-screen.v1" or
        report.get("status")!="PUBLIC_DEVELOPMENT_ONLY_INDEPENDENT_REVIEW_PENDING" or
        report.get("candidate_id")!="W36-C2" or
        report.get("frozen_sha256")!=sha(frozen_raw) or
        report.get("policy_proposal_sha256")!=sha(proposal_raw) or
        report.get("source_wingless_commit")!="b1e4972f04142f1f35f76f9483b12491dec4846c" or
        report.get("method_forge_commit")!="7f2f791f98d92ad932e0f530a7d23d0330a15643" or
        proposal.get("next_selected")!="W36-C2" or
        report.get("first_use_claims")!=0 or report.get("new_originals_executed")!=0 or
        report.get("sealed_cohort_accessed") is not False or
        report.get("scientific_accepted") is not False or
        report.get("paid_api_calls")!=0):reject("REAL_METHOD_REVIEW_SOURCE_DRIFT")
    root=pathlib.Path(wingless_root).resolve(strict=True)
    commit=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    if commit!=report["source_wingless_commit"]:reject("REVIEW_SOURCE_COMMIT")
    target=root/"research/contrib/chatgpt/20261013-w-r52-batch-diversity/execute.py"
    spec=importlib.util.spec_from_file_location("r10_independent_low_level",target)
    if not spec or not spec.loader:reject("LOW_LEVEL_UNAVAILABLE")
    source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)
    folds=report.get("folds");stage=m["stages"][0]
    if not isinstance(folds,list) or len(folds)!=3:reject("FOLD_SHAPE")
    status=[]
    sealed=set(stage["reserved_sealed_heldout_seeds"])
    for k,fold in enumerate(folds):
        block=stage["development_blocks"][k]
        validation=sum((stage["development_blocks"][j] for j in range(3) if j!=k),[])
        if fold.get("fold")!=k or fold.get("training_seeds")!=block or fold.get("development_validation_seeds")!=validation:reject("FOLD_DRIFT")
        if sealed.intersection(block+validation):reject("SEALED_TOUCHED")
        scores=fold.get("score_by_arm")
        weights=fold.get("models")
        if not isinstance(scores,dict) or set(scores)!={"control","gradient_conflict"} or not isinstance(weights,dict) or set(weights)!=set(scores):reject("MISSING_CONTROLS")
        summaries={}
        for arm,model in weights.items():
            w=model.get("weights")
            if not isinstance(w,list) or len(w)!=16 or any(type(x) not in (float,int) or not math.isfinite(x) for x in w):reject("BAD_CAPACITY")
            w_hash=hashlib.sha256(json.dumps(w,separators=(",",":"),allow_nan=False).encode()).hexdigest()
            if w_hash!=model.get("weights_sha256"):reject("WEIGHT_FINGERPRINT")
            scorer=scores[arm]
            if scorer.get("weights_sha256")!=w_hash or scorer.get("source_training_example_counts")!=fold.get("training_source_counts"):reject("ROW_SOURCE")
            rows=scorer.get("by_seed")
            if not isinstance(rows,list) or len(rows)!=32:reject("ROW_SHAPE")
            family_scores={g:0 for g in source.GEN}
            overall=0
            for j,seed in enumerate(validation):
                row=rows[j]
                if row.get("seed")!=seed or row.get("total")!=108 or set(row.get("family_correct",{}))!=set(source.GEN):reject("ROW_SEED_OR_FAMILY")
                total=0
                for gen in source.GEN:
                    family_total=0
                    for site in source.SITES:
                        for entity in range(9):
                            base,pos,neg=source.w37.recoded_example(seed,entity,gen,"identity",site,3,False)
                            a=source.w42.feature(base,pos)
                            b=source.w42.feature(base,neg)
                            margin=sum(v*(x-y) for v,x,y in zip(w,a,b))
                            family_total+=source.w45.credit(margin,True)+source.w45.credit(-margin,False)
                    if not near(family_total,row["family_correct"][gen]):reject("CASE_REAGGREGATION")
                    family_scores[gen]+=family_total
                    total+=family_total
                if not near(total,row["correct"]):reject("ROW_TOTAL")
                overall+=total
            mean=overall/(32*108)
            byfam={g:family_scores[g]/(32*36) for g in source.GEN}
            if not near(mean,scorer.get("accuracy")) or set(scorer.get("family_accuracy",{}))!=set(source.GEN):reject("MEAN_OR_GEN_SET")
            for gen in source.GEN:
                if not near(byfam[gen],scorer["family_accuracy"][gen]):reject("GENERATOR_MEAN")
            summaries[arm]={"mean":mean,"min_family":min(byfam.values()),"family":byfam}
        if fold.get("gradient_conflict_mechanism")!={"conflict_projection":"deterministic_pairwise_orthogonal"}:
            reject("GRADIENT_CONFLICT_MECHANISM_DRIFT")
        # Independently reconstruct gradient-conflict updates using only the
        # pinned low-level Wingless generator. Never import training implementation.
        # Each source has 576 signed examples from the fixed 16-seed train block.
        groups=[]
        for group_index,generator in enumerate(source.GEN):
            rows=[]
            for seed in block:
                for entity in range(9):
                    if entity%3!=(group_index+seed)%3:continue
                    for site in source.TRAIN_SITES:
                        for amp in (1,2):
                            base,pos,neg=source.w37.recoded_example(seed,entity,generator,"identity",site,amp,True)
                            a=source.w42.feature(base,pos);b=source.w42.feature(base,neg)
                            delta=tuple(x-y for x,y in zip(a,b))
                            rows.extend(((delta,1),(tuple(-v for v in delta),-1)))
            if len(rows)!=576:reject("REVIEW_TRAINING_SOURCE_BUDGET")
            groups.append(rows)
        w=[0.0]*16
        for epoch in range(32):
            gradients=[]
            for rows in groups:
                grad=[0.0]*16
                for x,y in rows:
                    if y*sum(a*b for a,b in zip(w,x))<=0:
                        for j in range(16):
                            grad[j]+=y*x[j]/len(rows)
                gradients.append(grad)
            corrected=[list(x) for x in gradients]
            for i in range(3):
                for j in range(3):
                    if i==j:continue
                    dot=sum(a*b for a,b in zip(corrected[i],gradients[j]))
                    if dot<0:
                        norm=sum(b*b for b in gradients[j])
                        if norm>0:
                            corrected[i]=[a-dot*b/norm for a,b in zip(corrected[i],gradients[j])]
            step=[sum(g[j] for g in corrected)/3 for j in range(16)]
            w=[w[j]+0.1*step[j] for j in range(16)]
        actual=weights["gradient_conflict"]["weights"]
        if any(abs(a-b)>1e-10 for a,b in zip(w,actual)):
            reject("GRADIENT_SURGERY_FIDELITY_REJECTED")
        control=summaries["control"];candidate=summaries["gradient_conflict"]
        gain=candidate["min_family"]-control["min_family"]
        deltas={gen:candidate["family"][gen]-control["family"][gen] for gen in source.GEN}
        rule=m["preregistered_rule"]
        passed=(gain>=rule["min_worst_family_gain"] and
                min(deltas.values())>=-rule["max_allowed_harm"] and
                candidate["mean"]>=rule["min_candidate_accuracy"])
        if not near(gain,fold.get("minimum_family_gain")) or fold.get("preregistered_development_signal") is not passed:reject("STUDY_CLASSIFICATION")
        if set(fold.get("family_deltas",{}))!=set(source.GEN):reject("FAMILY_DELTA_SET")
        for gen in source.GEN:
            if not near(deltas[gen],fold["family_deltas"][gen]):reject("FAMILY_DELTA")
        status.append({"fold":k,"independent_rows_recomputed":32*2,"minimum_family_gain":gain,"preregistered_dev_signal":passed})
    return {"schema":"forge.r10.independent-gradient-conflict-development-review.v1",
      "method":"gradient-conflict-projection","candidate_id":"W36-C2",
      "method_fidelity_development_verified":True,
      "scientific_improvement_established":False,
      "sealed_f3_first_use_admitted":False,
      "science_production_accepted":False,
      "next_original_authorized":False,
      "reviewed_original_sha256":sha(screen_raw),
      "folds":status,"all_three_folds_passed":all(x["preregistered_dev_signal"] for x in status)}
def main():
    p=argparse.ArgumentParser()
    for k in ("frozen","proposal","screen","wingless_root","out"):p.add_argument("--"+k.replace("_","-"),required=True)
    a=p.parse_args()
    result=verify(pathlib.Path(a.frozen).read_bytes(),pathlib.Path(a.proposal).read_bytes(),
      pathlib.Path(a.screen).read_bytes(),a.wingless_root)
    pathlib.Path(a.out).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("R10_INDEPENDENT_REAL_DEV_METHOD_FIDELITY=PASS")
    print("R10_SEALED_FIRST_USE=ZERO")
if __name__=="__main__":main()
