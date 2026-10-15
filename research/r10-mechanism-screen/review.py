"""Independent source-pinned row witness and fixed development-only decision.

Never imports the original worker, training implementation, or R34 evaluator.
"""
import argparse,hashlib,importlib.util,json,math,pathlib,subprocess
from protocol import verify,load,sha,fail
def close(a,b):return type(a) in (int,float) and math.isfinite(a) and abs(a-b)<=1e-8
def review(frozen_raw,parent_raw,record_raw,wingless_root):
    m=verify(frozen_raw,parent_raw);rec=load(record_raw)
    pin=m["pinned_method"]
    if (rec.get("schema")!="forge.r10.two-distinct-learning-mechanisms.public-development.v1" or
        rec.get("scope")!="ACTUAL_NEW_DEV_NOT_F3_SCIENCE" or
        rec.get("frozen_sha256")!=sha(frozen_raw) or
        rec.get("parent_negative_sha256")!=sha(parent_raw) or
        rec.get("pinned_method_sha")!=pin["sha"] or
        rec.get("pinned_wingless_sha")!=pin["wingless_sha"] or
        rec.get("candidate_ids")!=["W36-C2","W36-C4"] or
        rec.get("first_use_claims")!=0 or rec.get("new_originals_executed")!=0 or
        rec.get("sealed_cohorts_accessed") is not False or
        rec.get("scientific_accepted") is not False):fail("RECORD_IDENTITY")
    source_root=pathlib.Path(wingless_root)
    if subprocess.check_output(["git","-C",str(source_root),"rev-parse","HEAD"],text=True).strip()!=pin["wingless_sha"]:fail("WINGLESS_SOURCE")
    spec=importlib.util.spec_from_file_location("r10_independent_row_generator",
        source_root/"research/contrib/chatgpt/20261013-w-r52-batch-diversity/execute.py")
    if not spec or not spec.loader:fail("INDEPENDENT_SOURCE_LOAD")
    source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)
    records=rec.get("folds")
    if not isinstance(records,list) or len(records)!=3:fail("FOLD_COUNT")
    bymethod={"W36-C2":[],"W36-C4":[]}
    allrows=0
    for fold_index,fold in enumerate(records):
        block=m["design"]["development_blocks"][fold_index]
        validation=sum((b for i,b in enumerate(m["design"]["development_blocks"]) if i!=fold_index),[])
        if (fold.get("fold")!=fold_index or fold.get("train_seeds")!=block or fold.get("validation_seeds")!=validation or
            fold.get("source_training_counts")!={g:576 for g in source.GEN}):fail("TRAINING_AND_VALIDATION_IDENTITY")
        scores=fold.get("scores",{});models=fold.get("models",{});mechanisms=fold.get("mechanisms",{})
        arms={"CONTROL","W36-C2","W36-C4"}
        if set(scores)!=arms or set(models)!=arms or set(mechanisms)!={"W36-C2","W36-C4"}:fail("ARM_SHAPE")
        if (mechanisms["W36-C2"]!={"conflict_projection":"deterministic_pairwise_orthogonal"} or
            mechanisms["W36-C4"]!={"memory_slots_per_source":32,"source_count":3}):fail("METHOD_FIDELITY")
        summaries={}
        for arm in sorted(arms):
            model=models[arm];w=model.get("weights")
            if not isinstance(w,list) or len(w)!=16 or any(type(v) not in (int,float) or not math.isfinite(v) for v in w):fail("PARAMETER_CAPACITY")
            h=hashlib.sha256(json.dumps(w,separators=(",",":"),allow_nan=False).encode()).hexdigest()
            if model.get("weights_sha256")!=h or model.get("source_counts")!={g:576 for g in source.GEN}:fail("WEIGHTS_OR_BUDGET")
            scored=scores[arm];rows=scored.get("by_seed")
            if (scored.get("weights_sha256")!=h or scored.get("source_training_example_counts")!={g:576 for g in source.GEN} or
                not isinstance(rows,list) or len(rows)!=32):fail("ROW_HEADERS")
            per_family={g:0 for g in source.GEN};total_correct=0
            for i,seed in enumerate(validation):
                row=rows[i]
                if (row.get("seed")!=seed or row.get("total")!=108 or
                    set(row.get("family_correct",{}))!=set(source.GEN)):fail("ROW_ORDER")
                subtotal=0
                for family in source.GEN:
                    amount=0
                    for site in source.SITES:
                        for entity in range(9):
                            base,pos,neg=source.w37.recoded_example(seed,entity,family,"identity",site,3,False)
                            a=source.w42.feature(base,pos)
                            b=source.w42.feature(base,neg)
                            margin=sum(c*(v-u) for c,v,u in zip(w,a,b))
                            amount+=source.w45.credit(margin,True)+source.w45.credit(-margin,False)
                    if not close(amount,row["family_correct"][family]):fail("ROW_FAMILY_TAMPER")
                    per_family[family]+=amount;subtotal+=amount
                if not close(subtotal,row["correct"]):fail("ROW_TOTAL_TAMPER")
                total_correct+=subtotal
                allrows+=1
            mean=total_correct/(32*108)
            family_accuracy={g:per_family[g]/(32*36) for g in source.GEN}
            if not close(mean,scored.get("accuracy")) or set(scored.get("family_accuracy",{}))!=set(source.GEN):fail("AGGREGATE")
            for g in source.GEN:
                if not close(family_accuracy[g],scored["family_accuracy"][g]):fail("FAMILY_AGGREGATE")
            summaries[arm]=(mean,family_accuracy)
        gains=fold.get("gain",{})
        if set(gains)!={"W36-C2","W36-C4"}:fail("GAIN_SET")
        for ident in ("W36-C2","W36-C4"):
            control=summaries["CONTROL"];candidate=summaries[ident]
            delta={g:candidate[1][g]-control[1][g] for g in source.GEN}
            gain=min(candidate[1].values())-min(control[1].values())
            signal=gain>=0.02 and min(delta.values())>=-0.05 and candidate[0]>=0.55
            reported=gains[ident]
            if (not close(gain,reported.get("minimum_family_gain")) or
                reported.get("preregistered_dev_signal") is not signal or
                set(reported.get("family_deltas",{}))!=set(source.GEN)):fail("FALSE_POSITIVE")
            for g in source.GEN:
                if not close(delta[g],reported["family_deltas"][g]):fail("DELTA_TAMPER")
            bymethod[ident].append((gain,min(delta.values()),signal))
    scored=[]
    for ident,items in bymethod.items():
        mean_gain=sum(x[0] for x in items)/3
        worst_harm=min(x[1] for x in items)
        eligible=all(x[2] for x in items)
        scored.append({"id":ident,"mean_min_family_gain":mean_gain,
                       "minimum_source_delta":worst_harm,"development_gate_passed":eligible})
    scored.sort(key=lambda x:(-x["mean_min_family_gain"],-x["minimum_source_delta"],x["id"]))
    return {"schema":"forge.r10.independent-two-method-real-development-review.v1",
        "source_original_sha256":sha(record_raw),"parent_r9_review_sha256":sha(parent_raw),
        "independent_row_reaggregations":allrows,
        "independent_method_identities_checked":True,
        "ranked_heldout_blind_development_candidates":scored,
        "prospective_method_proposal":scored[0]["id"] if scored[0]["development_gate_passed"] else None,
        "method_superiority_established":False,
        "new_scientific_first_use_authorized":False,
        "sealed_cohort_accessed":False,
        "scientific_accepted":False,
        "originals_executed":0}
def main():
    p=argparse.ArgumentParser()
    for k in ("frozen","parent_review","record","wingless_root","out"):p.add_argument("--"+k.replace("_","-"),required=True)
    a=p.parse_args()
    result=review(pathlib.Path(a.frozen).read_bytes(),pathlib.Path(a.parent_review).read_bytes(),
        pathlib.Path(a.record).read_bytes(),a.wingless_root)
    pathlib.Path(a.out).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("R10_INDEPENDENT_NEW_GRADIENT_VS_EPISODIC_SCREEN=PASS")
    print("R10_NO_SEALED_ORIGINALS=PASS")
if __name__=="__main__":main()
