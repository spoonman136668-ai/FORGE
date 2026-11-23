"""Read-only, no-first-use scientific hypothesis admission for R36 and F3."""
import argparse,hashlib,json,pathlib,subprocess,sys

FROZEN_BLOB="4140cf897c05d27dd6dac01cea796f383fa2ef44"
EXPECTED={
"wingless":{"id":"W-FORGE-R35-TRAIN-QUARTILE-01","outcome":"NO_CONFIRMED_QUARTILE_GAIN",
            "schema":"forge.r35.independent-original-review.v1",
            "prereg":"8228c9006777394376549ddca418ecd7efc5b49f",
            "run":38538653829,"run_conclusion":"failure",
            "original_job":"wingless-original","review_job":"wingless-review",
            "original_artifact":11881570490,"review_artifact":11880764124,
            "review_artifact_name":"forge-r35-independent-review"},
"yggdrasil":{"id":"Y-FORGE-F2-LEGAL-PAIR-TRANSFER-01","outcome":"LATENCY_TRANSFER_GAIN",
            "schema":"forge.yggdrasil.f2-independent-review.v1",
            "prereg":"04bc2ab3cb6c6e0385a9e6cc3e3132f7f254f588",
            "run":38539898614,"run_conclusion":"success",
            "original_job":"yggdrasil-original","review_job":"yggdrasil-review",
            "original_artifact":11882085778,"review_artifact":11881667209,
            "review_artifact_name":"forge-f2-independent-review"}
}
def fail(code):raise ValueError("R36_F3_ADMISSION_"+code)
def load(raw):
    def no_dupes(pairs):
        d={}
        for k,v in pairs:
            if k in d:fail("DUPLICATE_KEY")
            d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=no_dupes,parse_constant=lambda _:fail("NONFINITE"))
def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
def verify_portfolio(raw):
    if git_blob(raw)!=FROZEN_BLOB:fail("FROZEN_BLOB_DRIFT")
    m=load(raw)
    if m.get("schema")!="forge.r36-f3.pre-execution-hypothesis-portfolio.v1" or m.get("status")!="DEVELOPMENT_SCREEN_NOT_YET_EXECUTED":fail("PORTFOLIO_SCHEMA")
    c=m.get("constraints",{})
    required={"new_scientific_first_uses":0,"new_scientific_dispatches":0,
              "first_use_claims_created":0,"paid_model_calls":0,
              "external_FSA_required":False,"new_controller":False,
              "ckb_authority_mutated":False,"isolated_from_other_research_chats":True,
              "max_dev_candidates_per_lane":4,"max_select_per_lane":1,
              "no_old_holdout_tuning":True,"no_post_sealed_reselection":True,
              "independent_scientific_review_required":True}
    if any(c.get(k)!=v for k,v in required.items()):fail("BUDGET_OR_AUTHORITY_DRIFT")
    ids=[]
    reserved=[]
    for lane in ("wingless","yggdrasil"):
        p=m.get(lane,{})
        cand=p.get("candidates")
        if not isinstance(cand,list) or len(cand)!=4:fail("CANDIDATE_COUNT")
        if p.get("selection_rule",{}).get("only_development_data") is not True or p["selection_rule"].get("select_exactly")!=1:fail("SELECTION_IS_NOT_FROZEN")
        if p["selection_rule"].get("independent_selection_witness_required") is not True:fail("DEV_WITNESS_MISSING")
        for x in cand:
            if not all(isinstance(x.get(k),str) and x[k] for k in ("id","method","hypothesis","mechanism")):fail("UNSPECIFIED_HYPOTHESIS")
            ids.append(x["id"])
            if x.get("no_sealed_tuning",x.get("no_budget_increase")) is not True:fail("CANDIDATE_UNSAFE")
    w=m["wingless"];y=m["yggdrasil"]
    w_dev=w["development_blocks"];w_seal=w["reserved_sealed_heldout_seeds"]
    if len(w_dev)!=3 or any(len(b)!=16 for b in w_dev) or len(w_seal)!=48:fail("W_COHORT_SHAPE")
    w_all=sum(w_dev,[])+w_seal
    if len(set(w_all))!=96 or min(w_all)<15000 or max(w_all)>=15500:fail("W_COHORT_OVERLAP")
    y_dev=y["development_seeds"];y_seal=y["reserved_sealed_heldout_seeds"]
    if len(y_dev)!=8 or len(y_seal)!=16 or len(set(y_dev+y_seal))!=24 or min(y_dev+y_seal)<67000 or max(y_dev+y_seal)>=67400:fail("Y_COHORT_OVERLAP")
    pairs=y["legal_novel_pairs"]
    if pairs!=[[8,10],[11,13]] or len(set(sum(pairs,[])))!=4 or any(set(z).intersection({0,1}) for z in pairs):fail("Y_ILLEGAL_OR_REUSED_SENSOR_PAIR")
    if y["immutable_limits"]!={"public_scalar_reads_per_trial":10,"active":7,"retained":9,"total_arms":16,
         "pair_members_must_exclude":[0,1],"no_source_mutation":True,"external_models":0}:fail("Y_OBSERVATION_BUDGET")
    if w["training_limits"].get("epochs")!=32 or w["training_limits"].get("feature_dim")!=16 or w["training_limits"].get("training_sources")!=3:fail("W_COMPUTE_BUDGET")
    if len(set(ids))!=8 or len(set([w["planned_original_id"],y["planned_original_id"]]+ids))!=10:fail("COLLIDING_IDENTITIES")
    required_selection=m["frozen_selection_requires"]
    if not all(required_selection.get(k) is True for k in ("all_candidates_implemented_and_dev_tested",
        "trained_once_on_development_only","independent_dev_score_recomputation",
        "disjoint_new_sealed_first_use","one_selected_id_per_lane_before_sealed",
        "no_scientific_original_created_by_this_portfolio")):fail("SELECTION_REQUIREMENTS_UNFROZEN")
    for lane in EXPECTED:
        p=m["parent_evidence"][lane];want=EXPECTED[lane]
        if p["experiment_id"]!=want["id"] or p["outcome"]!=want["outcome"] or p["run_id"]!=want["run"] or p["prereg_blob"]!=want["prereg"] or p["original_artifact_id"]!=want["original_artifact"] or p["review_artifact_id"]!=want["review_artifact"]:fail("PARENT_SOURCE_DRIFT")
    return m
def verify_parent(lane,review_raw,run,job_listing,artifact_listing):
    p=EXPECTED[lane];v=load(review_raw)
    if any((v.get("schema")!=p["schema"],v.get("experiment_id")!=p["id"],
            v.get("prereg_blob")!=p["prereg"],v.get("outcome")!=p["outcome"],
            v.get("independently_validated") is not True,v.get("original_replay_allowed") is not False,
            type(v.get("original_sha256")) is not str or len(v.get("original_sha256",""))!=64)):fail("PARENT_UNQUALIFIED_"+lane)
    if run.get("id")!=p["run"] or run.get("run_attempt")!=1 or run.get("status")!="completed" or run.get("conclusion")!=p["run_conclusion"]:fail("PARENT_GITHUB_RUN_DRIFT_"+lane)
    jobs=job_listing.get("jobs",[])
    for name in (p["original_job"],p["review_job"]):
        if sum(z.get("name")==name and z.get("conclusion")=="success" for z in jobs)!=1:fail("PARENT_SCIENTIFIC_JOB_FAILED_"+lane)
    artifacts=artifact_listing.get("artifacts",[])
    for artifact_id in (p["original_artifact"],p["review_artifact"]):
        matches=[a for a in artifacts if a.get("id")==artifact_id and a.get("expired") is False]
        if len(matches)!=1:fail("PARENT_EVIDENCE_ARTIFACT_DRIFT_"+lane)
        if artifact_id==p["review_artifact"] and matches[0].get("name")!=p["review_artifact_name"]:fail("PARENT_REVIEW_ARTIFACT_NAME_"+lane)
    return {"experiment_id":p["id"],"verified_outcome":p["outcome"],"original_sha256":v["original_sha256"],"independent_review":True}
def verify(frozen,reviews,github):
    x=verify_portfolio(frozen)
    parents={lane:verify_parent(lane,reviews[lane],github[lane]["run"],github[lane]["jobs"],github[lane]["artifacts"]) for lane in EXPECTED}
    return {"schema":"forge.r36-f3.development-screen-admission.v1",
        "status":"PARENT_VERIFIED_PORTFOLIO_FROZEN_SCREEN_NOT_YET_RUN",
        "frozen_portfolio_blob":FROZEN_BLOB,"parents":parents,
        "candidate_count":{"wingless":4,"yggdrasil":4},
        "scientific_first_uses_consumed":0,"new_scientific_originals_executed":0,
        "selected_scientific_winners":0,"new_science_dispatch_authorized":False,
        "paid_model_calls":0,"fsa_activated":False,"ckb_authority_changed":False}
def main():
    p=argparse.ArgumentParser()
    for x in ("frozen","wingless_review","yggdrasil_review","wingless_run","wingless_jobs","wingless_artifacts","yggdrasil_run","yggdrasil_jobs","yggdrasil_artifacts","out"):
        p.add_argument("--"+x.replace("_","-"),required=True)
    args=p.parse_args()
    def get(name):return pathlib.Path(getattr(args,name)).read_bytes()
    github={lane:{kind:load(get(lane+"_"+kind)) for kind in ("run","jobs","artifacts")} for lane in EXPECTED}
    if args.frozen!="research/r36_f3_screen/frozen_portfolio.json":fail("FROZEN_PATH")
    frozen=subprocess.check_output(["git","show","HEAD:research/r36_f3_screen/frozen_portfolio.json"])
    admission=verify(frozen,{"wingless":get("wingless_review"),"yggdrasil":get("yggdrasil_review")},github)
    pathlib.Path(args.out).write_text(json.dumps(admission,indent=2,sort_keys=True)+"\n")
    print("R36_F3_BOTH_REAL_PARENTS=VERIFIED")
    print("R36_F3_FROZEN_DEV_HYPOTHESES=8")
    print("R36_F3_SEALED_SCIENTIFIC_ORIGINALS=ZERO")
if __name__=="__main__":main()
