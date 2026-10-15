"""Run genuine R10 gradient-conflict projection screening on DEVELOPMENT rows only.

No reserved/sealed cohort, no new original, no independent science acceptance.
R36 C2 remains a pinned, draft method whose fidelity must be independently checked.
"""
import argparse,hashlib,importlib.util,json,math,pathlib,subprocess,sys
from next_policy import check_frozen,parse,sha,fail as reject
def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],text=True,stderr=subprocess.DEVNULL).strip()
def dynamic(path,name):
    spec=importlib.util.spec_from_file_location(name,str(path))
    if spec is None or spec.loader is None:reject("SCIENTIFIC_SOURCE_MISSING")
    instance=importlib.util.module_from_spec(spec);spec.loader.exec_module(instance);return instance
def screen(frozen_raw,proposal_raw,wingless_root,method_root,forge_root):
    m=check_frozen(frozen_raw);p=parse(proposal_raw)
    if (p.get("schema")!="forge.r10.negative-informed-next-method-proposal.v1" or
        p.get("frozen_sha256")!=sha(frozen_raw) or
        p.get("next_selected")!="W36-C2" or
        p.get("first_use_claimed") is not False or
        p.get("policy_improvement_proven") is not False or
        p.get("scientific_accepted") is not False):reject("UNQUALIFIED_PROPOSAL")
    wingless_root=pathlib.Path(wingless_root)
    method_root=pathlib.Path(method_root)
    forge_root=pathlib.Path(forge_root)
    source=m["pinned_sources"]
    if (git(wingless_root,"rev-parse","HEAD")!="b1e4972f04142f1f35f76f9483b12491dec4846c" or
        git(method_root,"rev-parse","HEAD")!=source["forge_method_commit"] or
        git(method_root,"hash-object",source["method_path"])!=source["method_blob"] or
        git(wingless_root,"status","--porcelain") or git(method_root,"status","--porcelain")):reject("UNPINNED_METHOD_SOURCE")
    src=wingless_root/"research/contrib/chatgpt/20261013-w-r52-batch-diversity/execute.py"
    r34=dynamic(forge_root/"research/r34-wingless/execute.py","r10_source_pinned_r34")
    w52=r34.load_parent(src)
    method_dir=method_root/"research/r36_f3_screen"
    sys.path.insert(0,str(method_dir))
    import wingless_methods
    m1=m["stages"][0]
    blocks=m1["development_blocks"]
    banned=set(m1["reserved_sealed_heldout_seeds"])
    if len(blocks)!=3:reject("FOLD_COUNT")
    result=[]
    for k,block in enumerate(blocks):
        validation=[s for i,other in enumerate(blocks) if i!=k for s in other]
        if len(block)!=16 or len(validation)!=32 or set(block)&set(validation) or banned.intersection(block+validation):reject("SEALED_OR_FOLD_COLLISION")
        groups=r34.families(w52,block)
        training=tuple(tuple(rows) for rows in groups.values())
        learned=wingless_methods.train("W36-C2",training)
        if (learned.get("method")!="W36-C2" or learned.get("epochs")!=32 or
            learned.get("source_training_counts")!=(576,576,576)):reject("LEARNER_FIDELITY")
        effective=list(learned["weights"])
        if len(effective)!=16 or any(not math.isfinite(x) for x in effective):reject("LEARNER_CAPACITY")
        mechanism=learned["mechanism"]
        if mechanism != {"conflict_projection":"deterministic_pairwise_orthogonal"}:
            reject("NOT_GRADIENT_CONFLICT_SURGERY")
        counts={name:len(rows) for name,rows in groups.items()}
        candidate={"weights":effective,"weights_sha256":learned["weights_sha256"],"source_counts":counts}
        control=r34.minimax_fit(w52,block)
        arms={"control":r34.evaluate(w52,control,validation),
              "gradient_conflict":r34.evaluate(w52,candidate,validation)}
        ca=arms["control"]["family_accuracy"];lb=arms["gradient_conflict"]["family_accuracy"]
        gain=min(lb.values())-min(ca.values())
        harms={key:lb[key]-ca[key] for key in ca}
        rule=m["preregistered_rule"]
        screen_pass=(gain>=rule["min_worst_family_gain"] and
                     min(harms.values())>=-rule["max_allowed_harm"] and
                     arms["gradient_conflict"]["accuracy"]>=rule["min_candidate_accuracy"])
        result.append({"fold":k,"training_seeds":block,
            "development_validation_seeds":validation,
            "training_source_counts":counts,
            "gradient_conflict_mechanism":mechanism,
            "models":{"control":{"weights":control["weights"],"weights_sha256":control["weights_sha256"]},
                      "gradient_conflict":{"weights":effective,"weights_sha256":learned["weights_sha256"]}},
            "score_by_arm":arms,
            "minimum_family_gain":gain,"family_deltas":harms,
            "preregistered_development_signal":screen_pass})
    return {"schema":"forge.r10.gradient-conflict.real-development-screen.v1",
        "status":"PUBLIC_DEVELOPMENT_ONLY_INDEPENDENT_REVIEW_PENDING",
        "candidate_id":"W36-C2","source_wingless_commit":git(wingless_root,"rev-parse","HEAD"),
        "method_forge_commit":git(method_root,"rev-parse","HEAD"),
        "frozen_sha256":sha(frozen_raw),"policy_proposal_sha256":sha(proposal_raw),
        "first_use_claims":0,"new_originals_executed":0,"sealed_cohort_accessed":False,
        "scientific_accepted":False,"paid_api_calls":0,
        "folds":result}
def main():
    p=argparse.ArgumentParser()
    for k in ("frozen","proposal","wingless_root","method_root","forge_root","out"):
        p.add_argument("--"+k.replace("_","-"),required=True)
    a=p.parse_args()
    o=screen(pathlib.Path(a.frozen).read_bytes(),pathlib.Path(a.proposal).read_bytes(),
        a.wingless_root,a.method_root,a.forge_root)
    pathlib.Path(a.out).write_text(json.dumps(o,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n")
    print("R10_GENUINE_GRADIENT_CONFLICT_DEVELOPMENT_EVALUATED=PASS")
    print("R10_SEALED_FIRST_USE=ZERO")
if __name__=="__main__":main()
