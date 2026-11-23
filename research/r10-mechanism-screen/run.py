"""Actually train C2 gradient surgery and C4 episodic memory on new dev folds.

This program never reads future sealed cohorts, creates first-use claims,
executes production science, or modifies Wingless/Yggdrasil authority.
"""
import argparse,importlib.util,json,math,pathlib,subprocess,sys
from protocol import verify,sha,load,fail
def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],text=True,stderr=subprocess.DEVNULL).strip()
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if not spec or not spec.loader:fail("MODULE_UNAVAILABLE")
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
def run(frozen_raw,review_raw,wingless_root,method_root,forge_root):
    m=verify(frozen_raw,review_raw)
    wingless_root=pathlib.Path(wingless_root)
    method_root=pathlib.Path(method_root)
    forge_root=pathlib.Path(forge_root)
    pin=m["pinned_method"]
    if (git(wingless_root,"rev-parse","HEAD")!=pin["wingless_sha"] or
        git(method_root,"rev-parse","HEAD")!=pin["sha"] or
        git(method_root,"hash-object","research/r36_f3_screen/wingless_methods.py")!=pin["method_blob"] or
        git(method_root,"hash-object","research/r36_f3_screen/wingless_learned.py")!=pin["learned_blob"] or
        git(wingless_root,"status","--porcelain") or
        git(method_root,"status","--porcelain")):fail("UNPINNED_METHOD")
    r34=module(forge_root/"research/r34-wingless/execute.py","r10_parent_r34")
    w52=r34.load_parent(wingless_root/"research/contrib/chatgpt/20261013-w-r52-batch-diversity/execute.py")
    sys.path.insert(0,str(method_root/"research/r36_f3_screen"))
    import wingless_methods
    blocks=m["design"]["development_blocks"]
    reserved=set(m["design"]["future_sealed_heldout_seeds"])
    folds=[]
    for i,block in enumerate(blocks):
        validation=sum((b for j,b in enumerate(blocks) if j!=i),[])
        if len(validation)!=32 or set(validation)&set(block) or reserved.intersection(validation+block):fail("DEVELOPMENT_FOLD_COLLISION")
        family=r34.families(w52,block)
        training=tuple(tuple(a) for a in family.values())
        control=r34.minimax_fit(w52,block)
        arms={"CONTROL":{"weights":list(control["weights"]),"weights_sha256":control["weights_sha256"],"source_counts":control["source_counts"]}}
        metadata={}
        for candidate in m["candidates"]:
            model=wingless_methods.train(candidate["id"],training)
            if (model.get("method")!=candidate["id"] or model.get("epochs")!=32 or
                model.get("source_training_counts")!=(576,576,576) or
                len(model.get("weights",[]))!=16 or
                any(not math.isfinite(a) for a in model["weights"])):fail("METHOD_BUDGET")
            mechanism=model.get("mechanism")
            if candidate["id"]=="W36-C2" and mechanism!={"conflict_projection":"deterministic_pairwise_orthogonal"}:fail("CONFLICT_SOURCE_CHANGED")
            if candidate["id"]=="W36-C4" and mechanism!={"memory_slots_per_source":32,"source_count":3}:fail("EPISODIC_SOURCE_CHANGED")
            arms[candidate["id"]]={"weights":list(model["weights"]),"weights_sha256":model["weights_sha256"],
                "source_counts":dict(zip(w52.GEN,model["source_training_counts"]))}
            metadata[candidate["id"]]=mechanism
        for name,weights in arms.items():
            if name=="CONTROL":weights["source_counts"]=dict(control["source_counts"])
        scores={}
        for name,model in arms.items():
            scores[name]=r34.evaluate(w52,model,validation)
        gains={}
        for ident in ("W36-C2","W36-C4"):
            a,b=scores["CONTROL"],scores[ident]
            delta={g:b["family_accuracy"][g]-a["family_accuracy"][g] for g in a["family_accuracy"]}
            gain=min(b["family_accuracy"].values())-min(a["family_accuracy"].values())
            gains[ident]={"minimum_family_gain":gain,"family_deltas":delta,
                "preregistered_dev_signal":gain>=0.02 and min(delta.values())>=-0.05 and b["accuracy"]>=0.55}
        folds.append({"fold":i,"train_seeds":block,"validation_seeds":validation,"models":arms,
            "source_training_counts":{g:len(v) for g,v in family.items()},
            "mechanisms":metadata,"scores":scores,"gain":gains})
    return {"schema":"forge.r10.two-distinct-learning-mechanisms.public-development.v1",
        "scope":"ACTUAL_NEW_DEV_NOT_F3_SCIENCE","frozen_sha256":sha(frozen_raw),
        "parent_negative_sha256":sha(review_raw),"pinned_method_sha":pin["sha"],
        "pinned_wingless_sha":pin["wingless_sha"],"candidate_ids":["W36-C2","W36-C4"],
        "first_use_claims":0,"new_originals_executed":0,
        "sealed_cohorts_accessed":False,"scientific_accepted":False,
        "folds":folds}
def main():
    p=argparse.ArgumentParser()
    for name in ("frozen","parent_review","wingless_root","method_root","forge_root","out"):
        p.add_argument("--"+name.replace("_","-"),required=True)
    a=p.parse_args()
    x=run(pathlib.Path(a.frozen).read_bytes(),pathlib.Path(a.parent_review).read_bytes(),a.wingless_root,a.method_root,a.forge_root)
    pathlib.Path(a.out).write_text(json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n")
    print("R10_TWO_GENUINE_ALTERNATE_DEVELOPMENT_METHODS=PASS")
    print("R10_FIRST_USE_CLAIMS=ZERO")
if __name__=="__main__":main()
