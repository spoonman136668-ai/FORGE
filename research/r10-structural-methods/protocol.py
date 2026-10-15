"""Fail-closed R10 study plan: actual R9 negative and two structurally different learners."""
import hashlib,json,math
SCHEMA="forge.r10.two-native-structural-methods.development.v1"
R9_REVIEW_SHA="6600be273b38afbba2333938dc8e35da39b5c7e2c0e3b4256994c55816edf60e"
SOURCE_WING="b1e4972f04142f1f35f76f9483b12491dec4846c"
SOURCE_METHOD="7f2f791f98d92ad932e0f530a7d23d0330a15643"
METHOD_BLOB="d75f36f25aca35e30a90bd50e31c8e0d90cedc28"
LEARNED_BLOB="4a4d53bf992dd3e651b3f0add54f780c37f8a9a8"
IDS=("W36-C2","W36-C4")
def fail(why):raise ValueError("R10_SOURCE_GATE_"+why)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def obj(raw):
    if not isinstance(raw,bytes) or not 0<len(raw)<=65536:fail("JSON_SIZE")
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:fail("DUPLICATE_KEY")
            d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:fail("NONFINITE"))
def frozen(raw):
    f=obj(raw)
    if (f.get("schema")!=SCHEMA or f.get("lane")!="Wingless" or
        f.get("scope")!="PUBLIC_NEW_DEVELOPMENT_ONLY_NOT_SEALED_OR_ACCEPTED_SCIENCE" or
        f.get("wingless_source_commit")!=SOURCE_WING or
        f.get("method_source_commit")!=SOURCE_METHOD or
        f.get("methods_git_blob")!=METHOD_BLOB or f.get("learned_git_blob")!=LEARNED_BLOB):fail("FROZEN_SOURCE")
    p=f.get("parent",{})
    if (p.get("id")!="W-FORGE-R9-REPRESENTATION-DEVELOPMENT-01" or
        p.get("classification")!="DEVELOPMENT_NEGATIVE" or
        p.get("run_id")!=38662331650 or p.get("independent_review_artifact_id")!=11939945692 or
        p.get("independent_review_sha256")!=R9_REVIEW_SHA or
        len(p.get("minimum_family_gains",[]))!=3 or
        any(type(x) is not float or x>=-0.20 or x< -1 for x in p["minimum_family_gains"])):fail("PARENT_NEGATIVE_SOURCE")
    if [x.get("id") for x in f.get("methods",[])]!=list(IDS) or [x.get("family") for x in f["methods"]]!=["gradient-conflict-projection","bounded-episodic-memory"]:fail("METHOD_IDENTITIES")
    if any(x.get("unqualified_scientific_first_use") is not True for x in f["methods"]):fail("FALSE_METHOD_CUSTODY")
    s=f.get("selection",{})
    if (s.get("controls")!=["hard_minimax","W36-C2","W36-C4"] or
        s.get("criterion")!="training-separated_three_fold_worst_source_gain" or
        s.get("minimum_gain_every_fold")!=0.02 or s.get("max_source_harm")!=0.05 or
        s.get("minimum_overall_accuracy")!=0.55 or s.get("ranking")!="number_passed_folds_desc_then_mean_worst_family_gain_desc_then_candidate_id_asc" or
        s.get("single_candidate_max")!=1 or s.get("on_no_candidate")!="VALID_NEGATIVE_DO_NOT_LAUNCH_SCIENCE" or
        s.get("r9_C1_negative_family_posterior")!=[1,2] or
        s.get("unobserved_C2_C4_prior")!=[1,1] or
        s.get("holdout_tuning") is not False or s.get("no_sealed_data_for_selection") is not True):fail("PREDEFINED_SELECTION")
    d=f.get("new_dev",{})
    def blocks(base):return [list(range(base+v,base+v+16)) for v in (0,32,64)]
    if (d.get("training_blocks")!=blocks(26000) or d.get("future_replication_training_blocks")!=blocks(27000) or
        d.get("reserved_sealed_heldout")!=list(range(26400,26448)) or
        d.get("future_replication_heldout")!=list(range(27400,27448)) or
        d.get("feature_dim")!=16 or d.get("train_epochs")!=32 or
        d.get("training_sources")!=3 or d.get("examples_per_source")!=576 or
        d.get("new_originals_executed")!=0 or d.get("first_use_claims")!=0 or
        d.get("paid_api_calls")!=0):fail("NEW_FROZEN_DEVELOPMENT")
    if (f.get("no_external_FSA") is not True or f.get("cloudflare_changed") is not False or
        f.get("scientific_accepted") is not False or f.get("authenticated_sealed_first_use") is not False):fail("AUTHORITY")
    return f
def parent(raw,manifest):
    if sha(raw)!=manifest["parent"]["independent_review_sha256"]:fail("PARENT_BYTES")
    x=obj(raw)
    if (x.get("schema")!="forge.r9.independent-learned-method-development-review.v1" or
        x.get("candidate_id")!="W36-C1" or x.get("all_three_folds_passed") is not False or
        x.get("method_fidelity_development_verified") is not True or
        x.get("next_original_authorized") is not False or
        x.get("science_production_accepted") is not False or
        x.get("scientific_improvement_established") is not False or
        x.get("sealed_f3_first_use_admitted") is not False or
        len(x.get("folds",[]))!=3):fail("PARENT_OUTCOME")
    for idx,row in enumerate(x["folds"]):
        if (row.get("fold")!=idx or row.get("preregistered_dev_signal") is not False or
            abs(row.get("minimum_family_gain",999)-manifest["parent"]["minimum_family_gains"][idx])>1e-9):fail("PARENT_RESULTS")
    return x
