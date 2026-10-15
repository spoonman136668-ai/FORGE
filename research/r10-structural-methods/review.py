"""R10 independent scientific development witness: native source rows + training replay.

Does not import the original R10 worker, R34 evaluator, or W36 methods.
Every training source, learned weight, test row and gate is independently
recomputed from frozen low-level Wingless primitives.
"""
import argparse,hashlib,importlib.util,json,math,pathlib,subprocess
from protocol import frozen,parent,sha,fail,obj
ARMS=("hard_minimax","W36-C2","W36-C4")
def near(a,b,tol=1e-8):
    return type(a) in (float,int) and type(b) in (float,int) and math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tol
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def independent_training(native,seeds):
    groups={}
    for idx,g in enumerate(native.GEN):
        rows=[]
        for seed in seeds:
            for entity in range(9):
                if entity%3!=(idx+seed)%3:continue
                for site in native.TRAIN_SITES:
                    for amp in (1,2):
                        base,pos,neg=native.w37.recoded_example(seed,entity,g,"identity",site,amp,True)
                        a=native.w42.feature(base,pos)
                        b=native.w42.feature(base,neg)
                        diff=tuple(x-y for x,y in zip(a,b))
                        rows.extend(((diff,1),(tuple(-z for z in diff),-1)))
        if len(rows)!=576:fail("TRAIN_ROW_BUDGET")
        groups[g]=rows
    if len(groups)!=3:fail("TRAIN_SOURCE_COUNT")
    return groups
def grad(group,w):
    result=[0.0]*16
    for x,y in group:
        if y*dot(w,x)<=0:
            for k in range(16):result[k]+=y*x[k]/len(group)
    return result
def replay_control(groups):
    w=[0.0]*16
    seq=list(groups)
    for _ in range(32):
        losses=[sum(max(0.0,1-y*dot(w,x)) for x,y in groups[g])/576 for g in seq]
        chosen=max(range(len(seq)),key=lambda i:losses[i])
        g=[0.0]*16
        for x,y in groups[seq[chosen]]:
            if y*dot(w,x)<=0:
                for i in range(16):g[i]+=y*x[i]
        w=[w[i]+0.1*g[i]/576 for i in range(16)]
    return w
def replay_c2(groups):
    w=[0.0]*16
    for _ in range(32):
        g=[grad(rows,w) for rows in groups.values()]
        projected=[list(x) for x in g]
        for i in range(3):
            for j in range(3):
                if i==j:continue
                inner=dot(projected[i],g[j])
                if inner<0:
                    norm=dot(g[j],g[j])
                    if norm>0:
                        projected[i]=[a-inner*b/norm for a,b in zip(projected[i],g[j])]
        step=[sum(p[i] for p in projected)/3 for i in range(16)]
        w=[w[i]+0.1*step[i] for i in range(16)]
    return w
def replay_c4(groups):
    w=[0.0]*16
    for _ in range(32):
        memory=[]
        for group in groups.values():
            ranked=sorted(enumerate(group),key=lambda e:(e[1][1]*dot(w,e[1][0]),e[0]))
            memory.append(tuple(item for _i,item in ranked[:32]))
        steps=[grad(m,w) for m in memory]
        delta=[sum(x[i] for x in steps)/3 for i in range(16)]
        w=[w[i]+0.1*delta[i] for i in range(16)]
    return w
def evaluate_rows(native,weights,seeds,reported):
    rows=reported.get("by_seed")
    if not isinstance(rows,list) or len(rows)!=len(seeds):fail("SOURCE_ROW_COUNT")
    families={g:0.0 for g in native.GEN}
    total=0
    for index,seed in enumerate(seeds):
        row=rows[index]
        if row.get("seed")!=seed or row.get("total")!=108 or set(row.get("family_correct",{}))!=set(native.GEN):fail("SOURCE_ROW_SEED")
        n=0
        for g in native.GEN:
            correct=0
            for site in native.SITES:
                for entity in range(9):
                    base,pos,neg=native.w37.recoded_example(seed,entity,g,"identity",site,3,False)
                    a=native.w42.feature(base,pos);b=native.w42.feature(base,neg)
                    margin=dot(weights,[x-y for x,y in zip(a,b)])
                    correct+=native.w45.credit(margin,True)+native.w45.credit(-margin,False)
            if not near(correct,row["family_correct"][g]):fail("RECOMPUTED_GENERATOR_ROW")
            families[g]+=correct;n+=correct
        if not near(n,row.get("correct")):fail("RECOMPUTED_ROW_TOTAL")
        total+=n
    mean=total/(len(seeds)*108)
    fam={g:families[g]/(len(seeds)*36) for g in native.GEN}
    if not near(mean,reported.get("accuracy")) or set(reported.get("family_accuracy",{}))!=set(fam):fail("SOURCE_ACCURACY")
    for g in fam:
        if not near(fam[g],reported["family_accuracy"][g]):fail("SOURCE_FAMILY_ACCURACY")
    return {"accuracy":mean,"family_accuracy":fam,"worst_family":min(fam.values())}
def verify(frozen_raw,parent_raw,screen_raw,wingless_root):
    f=frozen(frozen_raw);parent(parent_raw,f)
    if len(screen_raw)>1000000:fail("SCREEN_BYTES")
    m=obj(screen_raw)
    if (m.get("schema")!="forge.r10.two-novel-methods.real-development.v1" or
        m.get("status")!="INDEPENDENT_ROW_AND_TRAINING_FIDELITY_REVIEW_PENDING" or
        m.get("frozen_sha256")!=sha(frozen_raw) or
        m.get("parent_review_sha256")!=sha(parent_raw) or
        m.get("source_wingless_commit")!=f["wingless_source_commit"] or
        m.get("method_forge_commit")!=f["method_source_commit"] or
        m.get("method_ids")!=["W36-C2","W36-C4"] or
        m.get("sealed_cohort_accessed") is not False or
        m.get("first_use_claims")!=0 or m.get("scientific_originals_executed")!=0 or
        m.get("scientific_accepted") is not False or m.get("paid_api_calls")!=0):fail("MEASUREMENT_IDENTITY")
    root=pathlib.Path(wingless_root).resolve(strict=True)
    if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()!=f["wingless_source_commit"]:fail("WING_SOURCE")
    target=root/"research/contrib/chatgpt/20261013-w-r52-batch-diversity/execute.py"
    spec=importlib.util.spec_from_file_location("r10_independent_wingless_native",target)
    if not spec or not spec.loader:fail("NATIVE_SOURCE_MISSING")
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    folds=m.get("folds")
    if not isinstance(folds,list) or len(folds)!=3:fail("FOLD_COUNT")
    aggregate={method:[] for method in ("W36-C2","W36-C4")}
    testimony=[]
    for i,fold in enumerate(folds):
        train=f["new_dev"]["training_blocks"][i]
        validate=sum((f["new_dev"]["training_blocks"][j] for j in range(3) if j!=i),[])
        if (fold.get("fold")!=i or fold.get("training_seeds")!=train or
            fold.get("development_validation_seeds")!=validate):fail("CROSS_DEV_SPLIT")
        groups=independent_training(native,train)
        if fold.get("source_training_counts")!={g:len(rows) for g,rows in groups.items()}:fail("SOURCE_TRAINING_COUNT")
        models=fold.get("models",{});scores=fold.get("score_by_arm",{})
        if set(models)!=set(ARMS) or set(scores)!=set(ARMS):fail("EXACT_ARM_SET")
        expected={"hard_minimax":replay_control(groups),"W36-C2":replay_c2(groups),"W36-C4":replay_c4(groups)}
        verified={}
        for arm in ARMS:
            record=models[arm]
            weights=record.get("weights")
            if not isinstance(weights,list) or len(weights)!=16 or any(type(z) not in (float,int) or not math.isfinite(z) for z in weights):fail("PARAMETER_BUDGET")
            if any(not near(v,ref,1e-9) for v,ref in zip(weights,expected[arm])):fail("INDEPENDENT_TRAIN_REPLAY")
            digest=hashlib.sha256(json.dumps(weights,separators=(",",":"),allow_nan=False).encode()).hexdigest()
            if record.get("weights_sha256")!=digest or scores[arm].get("weights_sha256")!=digest:fail("WEIGHT_DIGEST")
            if scores[arm].get("source_training_example_counts")!=fold["source_training_counts"]:fail("METRIC_SOURCE_COUNT")
            mech=record.get("mechanism")
            if arm=="hard_minimax" and mech!="hard_train_only_worst_family":fail("BASELINE_METHOD")
            if arm=="W36-C2" and mech!={"conflict_projection":"deterministic_pairwise_orthogonal"}:fail("PROJECTION_FIDELITY")
            if arm=="W36-C4" and mech!={"memory_slots_per_source":32,"source_count":3}:fail("MEMORY_FIDELITY")
            verified[arm]=evaluate_rows(native,weights,validate,scores[arm])
        outcome={}
        for arm in ("W36-C2","W36-C4"):
            control=verified["hard_minimax"];candidate=verified[arm]
            gain=candidate["worst_family"]-control["worst_family"]
            delta={g:candidate["family_accuracy"][g]-control["family_accuracy"][g] for g in control["family_accuracy"]}
            passed=gain>=0.02 and min(delta.values())>=-0.05 and candidate["accuracy"]>=0.55
            if (not near(scores[arm].get("preregistered_dev_gain"),gain) or
                scores[arm].get("preregistered_dev_pass") is not passed or
                set(scores[arm].get("preregistered_family_deltas",{}))!=set(delta)):fail("RESULT_CLASSIFICATION")
            for g in delta:
                if not near(scores[arm]["preregistered_family_deltas"][g],delta[g]):fail("GENERATOR_DELTA")
            outcome[arm]={"gain":gain,"pass":passed}
            aggregate[arm].append(outcome[arm])
        testimony.append({"fold":i,"source_training_rows":1728,
            "independently_recomputed_seed_arm_rows":96,"candidate_results":outcome})
    ranks=[]
    for method in ("W36-C2","W36-C4"):
        results=aggregate[method];passed=sum(x["pass"] for x in results)
        average_gain=sum(x["gain"] for x in results)/3
        ranks.append({"method":method,"passed_folds":passed,"mean_worst_family_gain":average_gain,
          "eligible_for_fresh_original":passed==3})
    ranks.sort(key=lambda x:(-x["passed_folds"],-x["mean_worst_family_gain"],x["method"]))
    eligible=[x for x in ranks if x["eligible_for_fresh_original"]]
    chosen=eligible[0]["method"] if eligible else None
    return {"schema":"forge.r10.independent-structural-development-verification.v1",
      "frozen_sha256":sha(frozen_raw),"parent_r9_negative_sha256":sha(parent_raw),
      "measurement_sha256":sha(screen_raw),"method_fidelity_independently_recomputed":True,
      "development_row_verification":True,"folds":testimony,"ranked_methods":ranks,
      "selected_candidate_id":chosen,"three_fold_development_gate_passed":chosen is not None,
      "development_negatives_preserved":True,
      "scientific_originals_executed":0,"first_use_claims_created":0,
      "sealed_holdouts_accessed":False,"scientific_improvement_qualified":False,
      "scientific_accepted":False,"independent_fsa_qualified":False,
      "new_science_dispatch_authorized":False,"paid_api_calls":0}
def main():
    p=argparse.ArgumentParser()
    for x in ("frozen","parent","measurement","wingless_root","out"):p.add_argument("--"+x.replace("_","-"),required=True)
    args=p.parse_args()
    report=verify(pathlib.Path(args.frozen).read_bytes(),pathlib.Path(args.parent).read_bytes(),
      pathlib.Path(args.measurement).read_bytes(),args.wingless_root)
    with pathlib.Path(args.out).open("xb") as o:o.write((json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n").encode())
    print("R10_INDEPENDENT_TRAINING_AND_ROW_REAGGREGATION=PASS")
    print("R10_DEVELOPMENT_ELIGIBLE="+str(report["three_fold_development_gate_passed"]).lower())
    print("R10_SCIENTIFIC_FIRST_USE=ZERO")
if __name__=="__main__":main()
