"""R10: inherit existing frozen portfolio rank, quarantine independently reviewed R9 negative.

Read-only historical policy adaptation; never upgrades development evidence to a
scientific original, independently qualified FSA, or first-use authority.
"""
import argparse,hashlib,json,pathlib
def fail(label):raise ValueError("R10_"+label)
def parse(raw):
    if not 0<len(raw)<65536:fail("INPUT_SIZE")
    def unique(pairs):
        out={}
        for key,value in pairs:
            if key in out:fail("DUPLICATE_KEY")
            out[key]=value
        return out
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:fail("NONFINITE_JSON"))
def sha(raw):return hashlib.sha256(raw).hexdigest()
def hexid(s,n=64):
    return isinstance(s,str) and len(s)==n and all(c in "0123456789abcdef" for c in s)
def check_frozen(raw):
    m=parse(raw)
    if (m.get("schema")!="forge.r10.reviewed-negative-next-frozen-policy.v1" or
        m.get("scope")!="DEVELOPMENT_ONLY_UNCONSUMED_PREDEFINED_ALTERNATIVE_ZERO_AUTHORITY" or
        m.get("source_main_sha")!="93974bae44793386a52b7d2a485bca49565cc07b" or
        m.get("prior_r9_run_id")!=38662331650 or
        m.get("prior_r9_proposal_artifact_id")!=11939262978 or
        m.get("prior_r9_review_artifact_id")!=11939945692 or
        not all(hexid(m.get(k)) for k in ("prior_r9_proposal_sha256","prior_r9_review_sha256","prior_r9_original_measurement_sha256"))):
        fail("HISTORICAL_PIN")
    if (m.get("candidate_preregistered_order")!=["W36-C1","W36-C2","W36-C4"] or
        m.get("retired_development_negative")!="W36-C1" or
        m.get("next_candidate")!="W36-C2" or
        m.get("candidate_family")!="gradient-conflict-projection" or
        m.get("method")!="trainable_gradient_conflict_projection"):fail("FROZEN_METHOD")
    sources=m.get("pinned_sources",{})
    if (sources.get("forge_method_commit")!="7f2f791f98d92ad932e0f530a7d23d0330a15643" or
        sources.get("method_blob")!="d75f36f25aca35e30a90bd50e31c8e0d90cedc28" or
        sources.get("wingless_commit")!="b1e4972f04142f1f35f76f9483b12491dec4846c"):fail("METHOD_SOURCE_DRIFT")
    rule=m.get("preregistered_rule",{})
    if (rule.get("min_worst_family_gain")!=0.02 or rule.get("max_allowed_harm")!=0.05 or
        rule.get("min_candidate_accuracy")!=0.55 or rule.get("all_three_folds_required") is not True):fail("THRESHOLD_REWRITE")
    stages=m.get("stages")
    if not isinstance(stages,list) or len(stages)!=2:fail("COHORT_COUNT")
    used=set()
    for i,x in enumerate(stages):
        base,seal=(26000,26200) if i==0 else (27000,27200)
        if (x.get("experiment_id")!=("W-FORGE-R10-GRADIENT-CONFLICT-DEVELOPMENT-01" if i==0 else "W-FORGE-R10-GRADIENT-CONFLICT-REPLICATION-02") or
            x.get("parent_experiment_id")!=("W-FORGE-R9-REPRESENTATION-DEVELOPMENT-01" if i==0 else stages[0]["experiment_id"]) or
            x.get("development_blocks")!=[list(range(base+k,base+k+16)) for k in (0,32,64)] or
            x.get("reserved_sealed_heldout_seeds")!=list(range(seal,seal+48)) or
            x.get("max_epochs")!=32 or x.get("train_sources")!=3 or
            x.get("training_examples_per_source")!=576 or x.get("feature_dimension")!=16 or
            x.get("status")!="PREPARED_NOT_FIRSTUSE"):fail("COHORT_OR_BUDGET_DRIFT")
        values=sum(x["development_blocks"],[])+x["reserved_sealed_heldout_seeds"]
        if len(set(values))!=96 or used.intersection(values):fail("SEED_REUSE")
        used.update(values)
    constraints=m.get("constraints",{})
    if (constraints.get("paid_api_calls")!=0 or constraints.get("first_use_claims")!=0 or
        constraints.get("new_scientific_originals_authorized")!=0 or
        constraints.get("no_external_fsa") is not True or
        constraints.get("no_new_controller") is not True or
        constraints.get("no_sealed_cohort_access") is not True or
        constraints.get("cloudflare_unchanged") is not True):fail("AUTHORITY_ESCAPE")
    return m
def successor(frozen,prior_proposal,prior_review):
    m=check_frozen(frozen)
    if sha(prior_proposal)!=m["prior_r9_proposal_sha256"] or sha(prior_review)!=m["prior_r9_review_sha256"]:fail("EVIDENCE_REPLACEMENT")
    p=parse(prior_proposal);review=parse(prior_review)
    if (p.get("schema")!="forge.r9.train-updated-prospective-hypothesis.v1" or
        p.get("selected_candidate_id")!="W36-C1" or
        p.get("parent_negative_count")!=3 or
        p.get("first_use_authorized") is not False or
        p.get("originals_executed")!=0 or
        p.get("policy_improvement_demonstrated") is not False):fail("PREDECESSOR_POLICY_DRIFT")
    if (review.get("schema")!="forge.r9.independent-learned-method-development-review.v1" or
        review.get("candidate_id")!="W36-C1" or
        review.get("method_fidelity_development_verified") is not True or
        review.get("reviewed_original_sha256")!=m["prior_r9_original_measurement_sha256"] or
        review.get("all_three_folds_passed") is not False or
        review.get("science_production_accepted") is not False or
        review.get("sealed_f3_first_use_admitted") is not False or
        review.get("next_original_authorized") is not False or
        len(review.get("folds",[]))!=3 or
        any(row.get("preregistered_dev_signal") is not False or
            row.get("minimum_family_gain",1)>=0 or
            row.get("independent_rows_recomputed")!=64 for row in review["folds"])):
        fail("DEVELOPMENT_NEGATIVE_UNVERIFIED")
    ranked=p.get("ranked_candidates")
    if not isinstance(ranked,list) or len(ranked)!=4:fail("PRIOR_RANKING")
    selected=[x["id"] for x in ranked if x.get("eligible_for_development_proposal") is True]
    if selected!=["W36-C1","W36-C2","W36-C4"]:fail("PREREG_RANK_DRIFT")
    remaining=[ident for ident in selected if ident!=review["candidate_id"]]
    if not remaining or remaining[0]!=m["next_candidate"]:fail("NEXT_SELECTION_NOT_PREDEFINED")
    return {"schema":"forge.r10.negative-informed-next-method-proposal.v1",
       "mode":"FROZEN_R9_RANK_PLUS_INDEPENDENT_DEVELOPMENT_NEGATIVE",
       "prior_policy_sha256":sha(prior_proposal),
       "prior_development_review_sha256":sha(prior_review),
       "frozen_sha256":sha(frozen),
       "retired_for_development":["RETIRED-R8-QUARTILE","W36-C1"],
       "next_selected":remaining[0],"remaining_preordered":remaining,
       "substantively_different":True,
       "policy_improvement_proven":False,
       "first_use_claimed":False,"new_originals_executed":0,
       "scientific_accepted":False,"external_fsa_qualified":False,
       "new_development_folds":m["stages"][0]["development_blocks"],
       "reserved_sealed_heldout_accessed":False,
       "later_replication_reserved":m["stages"][1]["experiment_id"]}
def main():
    ap=argparse.ArgumentParser()
    for k in ("frozen","proposal","review","out"):ap.add_argument("--"+k,required=True)
    a=ap.parse_args()
    result=successor(pathlib.Path(a.frozen).read_bytes(),pathlib.Path(a.proposal).read_bytes(),pathlib.Path(a.review).read_bytes())
    pathlib.Path(a.out).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("R10_INDEPENDENT_NEGATIVE_TO_FROZEN_DIFFERENT_METHOD=PASS")
    print("R10_FIRST_USE_CLAIMS=ZERO")
if __name__=="__main__":main()
