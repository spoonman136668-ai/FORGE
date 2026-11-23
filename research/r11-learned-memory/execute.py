"""Real R11 development-only learning. No first use and no sealed access."""
import argparse,importlib.util,json,math,pathlib,subprocess,sys
from protocol import freeze,verify_parent,sha,stop
import controller
def git(root,*args):return subprocess.check_output(["git","-C",str(root),*args],text=True,stderr=subprocess.DEVNULL).strip()
def importfile(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if not spec or not spec.loader:stop("MISSING_PINNED_NATIVE")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def run(frozen_raw,parent_raw,wingless_root,forge_root,method_root):
    m=freeze(frozen_raw);verify_parent(parent_raw,m)
    wingless_root=pathlib.Path(wingless_root).resolve(strict=True)
    forge_root=pathlib.Path(forge_root).resolve(strict=True)
    method_root=pathlib.Path(method_root).resolve(strict=True)
    p=m["pinned"]
    if (git(wingless_root,"rev-parse","HEAD")!=p["wingless_sha"] or
        git(method_root,"rev-parse","HEAD")!=p["r36_sha"] or
        git(method_root,"hash-object","research/r36_f3_screen/wingless_methods.py")!=p["r36_blob"] or
        git(forge_root,"hash-object","research/r34-wingless/execute.py")!=p["r34_blob"] or
        git(wingless_root,"status","--porcelain") or
        git(method_root,"status","--porcelain")):stop("PINNED_METHOD_DRIFT")
    r34=importfile(forge_root/"research/r34-wingless/execute.py","r11_verified_baseline")
    source=r34.load_parent(wingless_root/"research/contrib/chatgpt/20261013-w-r52-batch-diversity/execute.py")
    sys.path.insert(0,str(method_root/"research/r36_f3_screen"))
    import wingless_methods
    if wingless_methods.METHODS!=("W36-C1","W36-C2","W36-C3","W36-C4"):stop("FIXED_MEMORY_SOURCE")
    folds=[]
    blocks=m["development"]["train_blocks"]
    reserved=set(m["development"]["reserved_future_sealed_seeds"]+
        m["development"]["reserved_future_replication_sealed"]+
        sum(m["development"]["reserved_future_replication_training"],[]))
    for i,train_seeds in enumerate(blocks):
        valid=[x for j,block in enumerate(blocks) if j!=i for x in block]
        if len(set(valid+train_seeds))!=48 or len(valid)!=32 or reserved.intersection(valid+train_seeds):stop("COHORT_LEAK")
        per_family=r34.families(source,train_seeds)
        training=tuple(tuple(v) for v in per_family.values())
        model=controller.train(training)
        fixed=wingless_methods.train("W36-C4",training)
        baseline=r34.minimax_fit(source,train_seeds)
        model["source_counts"]=dict(zip(source.GEN,[576]*3))
        fixedm={"weights":list(fixed["weights"]),"weights_sha256":fixed["weights_sha256"],"source_counts":dict(zip(source.GEN,[576]*3))}
        families={"hard_minimax":baseline,"fixed_C4_memory":fixedm,"learned_retention":model}
        scores={name:r34.evaluate(source,record,valid) for name,record in families.items()}
        c=scores["hard_minimax"];b=scores["learned_retention"]
        gains={g:b["family_accuracy"][g]-c["family_accuracy"][g] for g in source.GEN}
        gain=min(b["family_accuracy"].values())-min(c["family_accuracy"].values())
        passed=gain>=0.02 and min(gains.values())>=-0.05 and b["accuracy"]>=0.55
        folds.append({"fold":i,"train_seeds":train_seeds,"validation_seeds":valid,
            "models":{name:{"weights":record["weights"],"weights_sha256":record["weights_sha256"],
                            "source_counts":record["source_counts"]} for name,record in families.items()},
            "retention_trace":model["gate_trace"],"trained_gate_logits":model["gate_logits"],
            "retained_slots":model["persistent_memory_slots"],
            "controller_trainable_scalar_count":model["learned_controller_parameters"],
            "score_by_arm":scores,
            "preregistered_worst_family_gain":gain,
            "preregistered_family_deltas":gains,
            "preregistered_development_positive":passed})
    return {"schema":"forge.r11.real-learned-memory.development.v1",
      "scope":"ACTUAL_TRAIN_ONLY_PROXY_LEARNER_ON_NEW_PUBLIC_DEVELOPMENT",
      "frozen_sha256":sha(frozen_raw),"parent_r10_review_sha256":sha(parent_raw),
      "wingless_commit":p["wingless_sha"],"method_commit":p["r36_sha"],
      "classifier_parameters":16,"additional_learned_gate_parameters":3,
      "fixed_memory_slots":96,"training_epochs":32,
      "development_folds":folds,
      "sealed_cohorts_accessed":False,"new_originals_executed":0,
      "first_use_claims_created":0,"scientific_accepted":False,"paid_api_calls":0}
def main():
    parser=argparse.ArgumentParser()
    for x in ("frozen","parent","wingless_root","method_root","forge_root","out"):parser.add_argument("--"+x.replace("_","-"),required=True)
    a=parser.parse_args()
    report=run(pathlib.Path(a.frozen).read_bytes(),pathlib.Path(a.parent).read_bytes(),a.wingless_root,a.forge_root,a.method_root)
    with pathlib.Path(a.out).open("xb") as f:f.write((json.dumps(report,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode())
    print("R11_REAL_LEARNED_MEMORY_DEV=PASS")
    print("R11_AUTHENTIC_ORIGINAL_EXECUTION=ZERO")
if __name__=="__main__":main()
