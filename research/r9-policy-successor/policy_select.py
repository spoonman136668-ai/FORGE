"""R9 read-only posterior policy updated from actual independently reviewed negative origins.

The policy is learned from prior classifications, NOT proven to improve
research productivity. It proposes different methods; it never dispatches.
"""
import argparse,hashlib,json,pathlib,math
SCHEMA="forge.r9.genuine-negative-trained-research-policy.v1"
ALLOWED_OUTCOMES={"ROBUST_QUARTILE_GAIN","PARTIAL_QUARTILE_GAIN","NO_CONFIRMED_QUARTILE_GAIN"}
CANDIDATES={"W36-C1","W36-C2","W36-C4","RETIRED-R8-QUARTILE"}
REVIEWS=("W-FORGE-R35-TRAIN-QUARTILE-01","W-FORGE-R8-QUARTILE-REPLICATION-01","W-FORGE-R8-QUARTILE-TRANSFER-02")
TARGETS=("W-FORGE-R9-REPRESENTATION-DEVELOPMENT-01","W-FORGE-R9-REPRESENTATION-REPLICATION-02")
def reject(reason):
    raise ValueError("R9_RESEARCH_POLICY_"+reason)
def parse(raw):
    if not 0<len(raw)<64000:reject("INPUT_SIZE")
    def unique(pairs):
        out={}
        for key,value in pairs:
            if key in out:reject("DUPLICATE_JSON_KEY")
            out[key]=value
        return out
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:reject("NONFINITE"))
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def hexid(value,length=64):
    return isinstance(value,str) and len(value)==length and all(ch in "0123456789abcdef" for ch in value)
def check_frozen(raw):
    m=parse(raw)
    if m.get("schema")!=SCHEMA or m.get("lane")!="Wingless" or m.get("scope")!="READ_ONLY_HISTORICAL_OUTCOME_UPDATED_POLICY_NO_FIRST_USE_OR_LIVE_QUALIFICATION":reject("SCOPE")
    if m.get("parent_r8_run_id")!=38660840981 or m.get("prior_source_commit")!="828d8e9fd0eee7099ab2d27f71f0c7cbc103bca7":reject("SOURCE_IDENTITY")
    if not hexid(m.get("parent_r8_terminal_json_sha256")):reject("TERMINAL_PIN")
    h=m.get("history")
    if not isinstance(h,list) or len(h)!=3 or [x.get("experiment_id") for x in h]!=list(REVIEWS):reject("HISTORY_IDENTITY")
    seen=set()
    for x in h:
        if (x.get("family")!="quartile-weighting" or x.get("outcome")!="NO_CONFIRMED_QUARTILE_GAIN"
            or x.get("review_artifact_id") in seen or type(x.get("run_id")) is not int or
            type(x.get("review_artifact_id")) is not int or not hexid(x.get("review_sha256"))):reject("HISTORY_PIN")
        seen.add(x["review_artifact_id"])
    if h[0]["run_id"]!=38538653829 or h[1]["run_id"]!=38660840981 or h[2]["run_id"]!=38660840981:reject("RUN_REUSE_OR_REWRITE")
    p=m.get("selector")
    if (not isinstance(p,dict) or p.get("prior_alpha")!=1 or p.get("prior_beta")!=1 or
        p.get("novelty_weight")!=18 or p.get("max_selected")!=1 or
        p.get("future_cohort_access") is not False or p.get("cost_units")!="PREREG_PLANNING_ESTIMATE_NOT_MEASURED_COMPUTE"):reject("POLICY_PARAMETERS_DRIFT")
    cs=m.get("candidates")
    if not isinstance(cs,list) or len(cs)!=4 or {x.get("id") for x in cs}!=CANDIDATES:reject("CANDIDATE_SET_DRIFT")
    for x in cs:
        if (type(x.get("structural_novelty")) is not int or not 0<=x["structural_novelty"]<=5 or
            type(x.get("estimated_cost_units")) is not int or not 1<=x["estimated_cost_units"]<=100 or
            x.get("source_fidelity_qualified") is not False or not isinstance(x.get("hypothesis"),str)):reject("CANDIDATE_BUDGET")
        if x["id"]=="RETIRED-R8-QUARTILE" and (x.get("family")!="quartile-weighting" or x.get("structural_novelty")!=0):reject("RETIRED_FAMILY")
        if x["id"]!="RETIRED-R8-QUARTILE" and x.get("family")=="quartile-weighting":reject("DISGUISED_OLD_MECHANISM")
    ms=m.get("candidate_method_source")
    if (not isinstance(ms,dict) or ms.get("source_commit")!="7f2f791f98d92ad932e0f530a7d23d0330a15643" or
        ms.get("draft_pr")!=213 or ms.get("method_fidelity_live_qualified") is not False or
        not hexid(ms.get("method_blob"),40) or not hexid(ms.get("learned_blob"),40)):reject("UNQUALIFIED_METHOD")
    constraints=m.get("constraints")
    if (not isinstance(constraints,dict) or constraints.get("paid_model_calls")!=0 or
        constraints.get("first_use_claims")!=0 or constraints.get("new_originals_authorized")!=0 or
        constraints.get("max_eventual_originals")!=2 or
        constraints.get("require_independent_method_fidelity") is not True or
        constraints.get("require_new_owner_authorization") is not True or
        constraints.get("science_accepted") is not False or constraints.get("external_FSA_activated") is not False or
        constraints.get("cloudflare_changed") is not False):reject("AUTHORITY_BOUNDARY")
    stages=m.get("prepared_prospective")
    if not isinstance(stages,list) or len(stages)!=2 or [x.get("experiment_id") for x in stages]!=list(TARGETS):reject("SUCCESSOR_IDS")
    allseeds=set()
    for i,stage in enumerate(stages):
        base,seal=(24000,24200) if i==0 else (25000,25200)
        if (stage.get("parent_experiment_id")!=(REVIEWS[2] if i==0 else TARGETS[0]) or
            stage.get("development_blocks")!=[list(range(base+k,base+k+16)) for k in (0,32,64)] or
            stage.get("reserved_sealed_heldout_seeds")!=list(range(seal,seal+48)) or
            stage.get("max_epochs")!=32 or stage.get("max_parameters")!=16 or
            stage.get("source_count")!=3 or stage.get("training_examples_per_source")!=576 or
            stage.get("stage")!="PREPARE_ONLY_NO_FIRST_USE_CLAIM"):reject("COHORT_OR_CAPACITY_DRIFT")
        allthese=sum(stage["development_blocks"],[])+stage["reserved_sealed_heldout_seeds"]
        if allseeds.intersection(allthese) or len(set(allthese))!=96:reject("COHORT_REUSE")
        allseeds.update(allthese)
    return m
def verify_review(raw,meta):
    if sha(raw)!=meta["review_sha256"]:reject("REVIEW_BYTES")
    j=parse(raw)
    if (j.get("experiment_id")!=meta["experiment_id"] or j.get("outcome")!=meta["outcome"] or
        j.get("independently_validated") is not True or
        j.get("original_replay_allowed") is not False or
        j.get("science_production_accepted") is not False):reject("REVIEW_AUTHORITY_DRIFT")
    want="forge.r35.independent-original-review.v1" if meta["experiment_id"]==REVIEWS[0] else "forge.r8.independent-development-review.v1"
    if j.get("schema")!=want or not hexid(j.get("original_sha256")):reject("ORIGINAL_DIGEST")
    if j["experiment_id"]==REVIEWS[1] and j.get("parent_experiment_id")!=REVIEWS[0]:reject("PARENT_ONE")
    if j["experiment_id"]==REVIEWS[2] and j.get("parent_experiment_id")!=REVIEWS[1]:reject("PARENT_TWO")
def select(frozen_raw,review_raws,terminal_raw):
    m=check_frozen(frozen_raw)
    if not isinstance(review_raws,list) or len(review_raws)!=3:reject("HISTORY_COUNT")
    for raw,meta in zip(review_raws,m["history"]):verify_review(raw,meta)
    if sha(terminal_raw)!=m["parent_r8_terminal_json_sha256"]:reject("TERMINAL_BYTES")
    terminal=parse(terminal_raw)
    if (terminal.get("schema")!="forge.r8.actual-two-new-development-originals.v1" or
        terminal.get("new_development_originals_executed")!=2 or terminal.get("sequential_auto_progression") is not True or
        terminal.get("independent_row_reviews")!=2 or terminal.get("first_use_consumed")!=2 or
        terminal.get("historical_originals_replayed")!=0 or
        terminal.get("scientific_results_accepted") is not False or
        terminal.get("original_one_outcome")!="NO_CONFIRMED_QUARTILE_GAIN" or
        terminal.get("original_two_outcome")!="NO_CONFIRMED_QUARTILE_GAIN"):reject("R8_COMPLETENESS")
    family_counts={}
    for row in m["history"]:
        successes,trials=family_counts.get(row["family"],(0,0))
        successes+=int(row["outcome"] in ("ROBUST_QUARTILE_GAIN","PARTIAL_QUARTILE_GAIN"))
        family_counts[row["family"]]=(successes,trials+1)
    ranked=[]
    for c in m["candidates"]:
        wins,trials=family_counts.get(c["family"],(0,0))
        alpha=m["selector"]["prior_alpha"]+wins
        beta=m["selector"]["prior_beta"]+trials-wins
        posterior_basis_points=(10000*alpha)//(alpha+beta)
        novelty_component=100*m["selector"]["novelty_weight"]*c["structural_novelty"]
        score_numerator=posterior_basis_points+novelty_component
        planning_priority=score_numerator//c["estimated_cost_units"]
        eligible=c["family"]!="quartile-weighting" and c["structural_novelty"]>0
        ranked.append({"id":c["id"],"family":c["family"],"posterior_alpha":alpha,
          "posterior_beta":beta,"posterior_mean_basis_points":posterior_basis_points,
          "preregistered_novelty":c["structural_novelty"],
          "estimated_cost_units":c["estimated_cost_units"],
          "planning_priority":planning_priority,"eligible_for_development_proposal":eligible})
    ranked.sort(key=lambda x:(not x["eligible_for_development_proposal"],-x["planning_priority"],x["estimated_cost_units"],x["id"]))
    candidates=[x for x in ranked if x["eligible_for_development_proposal"]]
    if not candidates:reject("NO_STRUCTURALLY_NEW_METHOD")
    top=candidates[0]
    if top["id"]!="W36-C1" or top["family"]!="learned-invariant-projection":reject("FROZEN_SOURCE_MISMATCH")
    return {"schema":"forge.r9.train-updated-prospective-hypothesis.v1",
      "mode":"READ_ONLY_REVIEWED_NEGATIVE_POSTERIOR_NOT_PROVEN_POLICY_IMPROVEMENT",
      "history_sha256":[sha(x) for x in review_raws],
      "parent_terminal_sha256":sha(terminal_raw),
      "frozen_sha256":sha(frozen_raw),
      "ranked_candidates":ranked,
      "selected_candidate_id":top["id"],"selected_family":top["family"],
      "selected_hypothesis":next(c["hypothesis"] for c in m["candidates"] if c["id"]==top["id"]),
      "parent_negative_count":3,
      "new_method_qualifies_for_development_screen":True,
      "selected_method_fidelity_qualified":False,
      "fresh_successor_prepared":[{"experiment_id":s["experiment_id"],
        "parent_experiment_id":s["parent_experiment_id"],
        "method_candidate":top["id"],"development_seeds":[z for block in s["development_blocks"] for z in block],
        "sealed_heldout_seed_count":len(s["reserved_sealed_heldout_seeds"]),
        "future_sealed_access":False} for s in m["prepared_prospective"]],
      "execution_chain_reference":"forge-r8-real-autochain",
      "existing_once_only_executor_compatible_in_principle":True,
      "first_use_authorized":False,"originals_executed":0,"scientific_accepted":False,
      "independent_fsa_qualified":False,"policy_improvement_demonstrated":False,
      "policy_training_has_other_family_outcomes":False,
      "model_api_calls":0,"ckb_authority_mutated":False}
def main():
    p=argparse.ArgumentParser()
    for option in ("frozen","r35","r8_one","r8_two","r8_terminal","out"):
        p.add_argument("--"+option.replace("_","-"),required=True)
    a=p.parse_args()
    x=select(pathlib.Path(a.frozen).read_bytes(),
      [pathlib.Path(getattr(a,k)).read_bytes() for k in ("r35","r8_one","r8_two")],
      pathlib.Path(a.r8_terminal).read_bytes())
    pathlib.Path(a.out).write_text(json.dumps(x,sort_keys=True,indent=2)+"\n")
    print("R9_AUTHENTIC_NEGATIVE_UPDATED_NOVEL_METHOD=PASS")
    print("R9_SELECTED="+x["selected_candidate_id"])
    print("R9_POLICY_IMPROVEMENT_DEMONSTRATED=false")
if __name__=="__main__":main()
