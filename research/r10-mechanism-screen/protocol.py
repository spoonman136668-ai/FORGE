"""Minimal immutable R10 source and negative R9 lineage verifier."""
import hashlib,json
class Blocked(ValueError):pass
def fail(s):raise Blocked("R10_"+s)
def load(b):
    def unique(pairs):
        x={}
        for k,v in pairs:
            if k in x:fail("DUPLICATE_KEY")
            x[k]=v
        return x
    return json.loads(b,object_pairs_hook=unique,parse_constant=lambda z:fail("NONFINITE"))
def sha(b):return hashlib.sha256(b).hexdigest()
def verify(manifest_raw,r9_review_raw):
    if not 0<len(manifest_raw)<20000 or not 0<len(r9_review_raw)<50000:fail("OVERSIZE")
    x=load(manifest_raw);r=load(r9_review_raw)
    if (x.get("schema")!="forge.r10.frozen-gradient-memory-dev-portfolio.v1" or
        x.get("mode")!="TWO_ALTERNATE_MECHANISMS_NO_SEALED_ORIGINAL"):fail("FROZEN_IDENTITY")
    p=x.get("parent",{})
    if (p.get("experiment_id")!="W-FORGE-R9-REPRESENTATION-DEVELOPMENT-01" or
        p.get("source_review_artifact_id")!=11939945692 or
        p.get("source_review_sha256")!=sha(r9_review_raw) or
        p.get("source_review_sha256")!="6600be273b38afbba2333938dc8e35da39b5c7e2c0e3b4256994c55816edf60e" or
        p.get("source_commit")!="06776e21d8d507ffbd383a4508f0154c4d7e1db5"):fail("R9_SOURCE")
    if (r.get("schema")!="forge.r9.independent-learned-method-development-review.v1" or
        r.get("candidate_id")!="W36-C1" or
        r.get("method_fidelity_development_verified") is not True or
        r.get("all_three_folds_passed") is not False or
        r.get("science_production_accepted") is not False or
        r.get("sealed_f3_first_use_admitted") is not False):fail("R9_PARENT_OUTCOME")
    folds=r.get("folds")
    if (not isinstance(folds,list) or len(folds)!=3 or
        [v.get("fold") for v in folds]!=[0,1,2] or
        any(type(v.get("minimum_family_gain")) not in (int,float) or
            v.get("minimum_family_gain")>=0 or
            v.get("preregistered_dev_signal") is not False for v in folds)):fail("R9_FAKE_NEGATIVE")
    src=x.get("pinned_method",{})
    if (src.get("sha")!="7f2f791f98d92ad932e0f530a7d23d0330a15643" or
        src.get("method_blob")!="d75f36f25aca35e30a90bd50e31c8e0d90cedc28" or
        src.get("learned_blob")!="4a4d53bf992dd3e651b3f0add54f780c37f8a9a8" or
        src.get("wingless_sha")!="b1e4972f04142f1f35f76f9483b12491dec4846c"):fail("METHOD_SOURCE")
    cs=x.get("candidates",[])
    if not isinstance(cs,list) or [c.get("id") for c in cs]!=["W36-C2","W36-C4"] or cs[0].get("family")!="gradient-conflict-projection" or cs[1].get("family")!="bounded-episodic-memory":fail("CANDIDATES")
    d=x.get("design",{})
    expected=[list(range(26000+k,26016+k)) for k in (0,32,64)]
    if (d.get("development_blocks")!=expected or
        d.get("future_sealed_heldout_seeds")!=list(range(26200,26248)) or
        d.get("control")!="hard_minimax_train_only" or
        d.get("epochs")!=32 or d.get("dimension")!=16 or
        d.get("sources")!=3 or d.get("training_examples_per_source")!=576):fail("COHORT_OR_CAPACITY")
    future=x.get("next_prospective",{})
    if (future.get("id")!="W-FORGE-R10-MECHANISM-TRANSFER-01" or
        future.get("dev_blocks")!=[list(range(27000+k,27016+k)) for k in (0,32,64)] or
        future.get("sealed_future")!=list(range(27200,27248)) or
        future.get("first_use_claimed") is not False):fail("FUTURE_PREPARATION")
    allids=sum(expected,[])+d["future_sealed_heldout_seeds"]+sum(future["dev_blocks"],[])+future["sealed_future"]
    if len(set(allids))!=len(allids):fail("PRIOR_OR_FUTURE_REUSE")
    bounds=x.get("limits",{})
    if (bounds.get("max_dev_candidates")!=2 or
        any(bounds.get(k)!=0 for k in ("new_first_use_claims","originals_executed","paid_api_calls")) or
        any(bounds.get(k) is not False for k in ("science_accepted","new_controller","external_fsa_activated","ckb_authority_changed"))):fail("AUTHORITY_MUTATION")
    return x
