"""Perform real, frozen train-only Wingless W36-C2 and W36-C4 development screens.

Two structural candidates vs unchanged hard-minimax, no sealed seeds, no
first-use or independent FSA claims. External model usage prohibited.
"""
import argparse,hashlib,importlib.util,json,math,pathlib,subprocess,sys
from protocol import frozen,parent,sha,fail
def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],text=True,stderr=subprocess.DEVNULL).strip()
def dynamic(path,name):
    spec=importlib.util.spec_from_file_location(name,str(path))
    if not spec or not spec.loader:fail("PINNED_SOURCE_UNAVAILABLE")
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj
def execute(frozen_raw,parent_raw,wingless_root,method_root,forge_root):
    f=frozen(frozen_raw);parent(parent_raw,f)
    wingless_root=pathlib.Path(wingless_root).resolve(strict=True)
    method_root=pathlib.Path(method_root).resolve(strict=True)
    forge_root=pathlib.Path(forge_root).resolve(strict=True)
    if (git(wingless_root,"rev-parse","HEAD")!=f["wingless_source_commit"] or
        git(method_root,"rev-parse","HEAD")!=f["method_source_commit"] or
        git(method_root,"hash-object","research/r36_f3_screen/wingless_methods.py")!=f["methods_git_blob"] or
        git(method_root,"hash-object","research/r36_f3_screen/wingless_learned.py")!=f["learned_git_blob"] or
        git(wingless_root,"status","--porcelain") or git(method_root,"status","--porcelain")):fail("SOURCE_IDENTITY")
    src=wingless_root/"research/contrib/chatgpt/20261013-w-r52-batch-diversity/execute.py"
    r34=dynamic(forge_root/"research/r34-wingless/execute.py","r10_pinned_original_control")
    low=r34.load_parent(src)
    sys.path.insert(0,str(method_root/"research/r36_f3_screen"))
    import wingless_methods
    if (wingless_methods.METHODS!=("W36-C1","W36-C2","W36-C3","W36-C4") or
        wingless_methods.EPOCHS!=32 or wingless_methods.DIM!=16 or
        wingless_methods.ROWS_PER_SOURCE!=576):fail("METHOD_DRIFT")
    blocks=f["new_dev"]["training_blocks"]
    reserved=set(f["new_dev"]["reserved_sealed_heldout"]+f["new_dev"]["future_replication_heldout"]+
        sum(f["new_dev"]["future_replication_training_blocks"],[]))
    folds=[]
    for index,train in enumerate(blocks):
        validation=[v for j,part in enumerate(blocks) if index!=j for v in part]
        if (len(train)!=16 or len(validation)!=32 or
            len(set(train+validation))!=48 or reserved.intersection(train+validation)):fail("BLOCK_CROSSING")
        families=r34.families(low,train)
        training=tuple(tuple(rows) for rows in families.values())
        sources={k:len(v) for k,v in families.items()}
        if len(sources)!=3 or any(v!=576 for v in sources.values()):fail("TRAINING_BUDGET")
        control=r34.minimax_fit(low,train)
        results={"hard_minimax":r34.evaluate(low,control,validation)}
        models={"hard_minimax":{"weights":control["weights"],"weights_sha256":control["weights_sha256"],"mechanism":"hard_train_only_worst_family"}}
        for method in ("W36-C2","W36-C4"):
            trained=wingless_methods.train(method,training)
            if (trained["method"]!=method or trained["epochs"]!=32 or
                trained["source_training_counts"]!=(576,576,576)):fail("TRAINING_SOURCE_CHANGED")
            w=list(trained["weights"])
            if len(w)!=16 or any(not math.isfinite(x) for x in w):fail("TRAINING_PARAMETER_DIM")
            mechanism=trained["mechanism"]
            if method=="W36-C2" and mechanism!={"conflict_projection":"deterministic_pairwise_orthogonal"}:fail("CONFLICT_MECHANISM")
            if method=="W36-C4" and mechanism!={"memory_slots_per_source":32,"source_count":3}:fail("MEMORY_MECHANISM")
            cand={"weights":w,"weights_sha256":trained["weights_sha256"],"source_counts":sources}
            results[method]=r34.evaluate(low,cand,validation)
            models[method]={"weights":w,"weights_sha256":trained["weights_sha256"],"mechanism":mechanism}
        for method in ("W36-C2","W36-C4"):
            baseline=results["hard_minimax"];candidate=results[method]
            baseline_family=baseline["family_accuracy"];cand_family=candidate["family_accuracy"]
            gain=min(cand_family.values())-min(baseline_family.values())
            deltas={g:cand_family[g]-baseline_family[g] for g in baseline_family}
            passing=(gain>=0.02 and min(deltas.values())>=-0.05 and candidate["accuracy"]>=0.55)
            results[method]["preregistered_dev_gain"]=gain
            results[method]["preregistered_dev_pass"]=passing
            results[method]["preregistered_family_deltas"]=deltas
        folds.append({"fold":index,"training_seeds":train,
          "development_validation_seeds":validation,"source_training_counts":sources,
          "models":models,"score_by_arm":results})
    return {"schema":"forge.r10.two-novel-methods.real-development.v1",
      "status":"INDEPENDENT_ROW_AND_TRAINING_FIDELITY_REVIEW_PENDING",
      "parent_review_sha256":sha(parent_raw),"frozen_sha256":sha(frozen_raw),
      "source_wingless_commit":git(wingless_root,"rev-parse","HEAD"),
      "method_forge_commit":git(method_root,"rev-parse","HEAD"),
      "method_ids":["W36-C2","W36-C4"],"folds":folds,
      "sealed_cohort_accessed":False,"first_use_claims":0,
      "scientific_originals_executed":0,"scientific_accepted":False,
      "paid_api_calls":0}
def main():
    a=argparse.ArgumentParser()
    for n in ("frozen","parent","wingless_root","method_root","forge_root","out"):a.add_argument("--"+n.replace("_","-"),required=True)
    x=a.parse_args()
    result=execute(pathlib.Path(x.frozen).read_bytes(),pathlib.Path(x.parent).read_bytes(),x.wingless_root,x.method_root,x.forge_root)
    with pathlib.Path(x.out).open("xb") as f:f.write((json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode())
    print("R10_REAL_STRUCTURAL_METHOD_DEVELOPMENT=PASS")
    print("R10_NEW_ORIGINALS=ZERO")
if __name__=="__main__":main()
