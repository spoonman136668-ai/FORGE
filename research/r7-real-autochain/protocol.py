"""R7 immutable development original protocol; no FSA or authority writer."""
import hashlib,json,pathlib,re
SCHEMA="forge.r7.two-new-real-wingless-firstuse.freeze.v1"
STAGES=("W-FORGE-R7-QUARTILE-REPLICATION-01","W-FORGE-R7-QUARTILE-TRANSFER-02")
WING_SHA="b1e4972f04142f1f35f76f9483b12491dec4846c"
LEGACY_SHA="ec42db7c182395a95096fa55285e413fc63fdcc8"
LEGACY_BLOB="c5ee11c469f34289b7af81a46eedacf722e6333f"
PARENT="W-FORGE-R35-TRAIN-QUARTILE-01"
OUTCOMES=("ROBUST_QUARTILE_GAIN","PARTIAL_QUARTILE_GAIN","NO_CONFIRMED_QUARTILE_GAIN")
def reject(code):
    raise ValueError("R7_FIRSTUSE_"+code)
def load(raw):
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result: reject("DUPLICATE_JSON_FIELD")
            result[k]=v
        return result
    return json.loads(raw,object_pairs_hook=unique,
      parse_constant=lambda x:reject("NONFINITE_JSON"))
def digest(raw):return hashlib.sha256(raw).hexdigest()
def gitblob(raw):return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\\x00"+raw).hexdigest()
def protocol(raw):
    if not 0<len(raw)<18000:reject("MANIFEST_SIZE")
    x=load(raw)
    if x.get("schema")!=SCHEMA or x.get("source_commit")!=WING_SHA or x.get("forge_legacy_method_commit")!=LEGACY_SHA or x.get("forge_legacy_r35_method_blob")!=LEGACY_BLOB or x.get("parent_original_id")!=PARENT or x.get("parent_required_outcome")!="NO_CONFIRMED_QUARTILE_GAIN":reject("SOURCE_OR_PARENT_DRIFT")
    if x.get("scope")!="PUBLIC_DEVELOPMENT_SCIENCE_ONLY_NO_F3_CUSTODY_OR_SCIENTIFIC_ACCEPTANCE" or x.get("max_real_originals")!=2 or x.get("runner_budget_minutes")!=60 or x.get("paid_api_calls")!=0 or x.get("rerun_allowed") is not False or x.get("first_use_claim_before_compute") is not True or x.get("independent_reviewer_required") is not True:reject("BUDGET_DRIFT")
    if x.get("method")!="EXACT_FROZEN_R35_TRAIN_ONLY_QUARTILE_VS_HARD_MINIMAX_NO_RETUNING" or x.get("fixed_training_epochs")!=32 or x.get("fixed_lr")!=0.1 or x.get("fixed_family_quantile")!=0.25 or x.get("fixed_arms")!=["hard_minimax_train_only_control","train_only_per_source_bottom_quartile_candidate"]:reject("METHOD_DRIFT")
    if x.get("fixed_criteria")!={"robust_min_worst_family_gain":0.05,"partial_min_worst_family_gain":0.02,"strict_max_family_harm":0.05,"min_accuracy":0.55}:reject("THRESHOLD_DRIFT")
    stages=x.get("stages")
    if not isinstance(stages,list) or len(stages)!=2:reject("STAGE_COUNT")
    allseeds=set()
    for i,s in enumerate(stages):
        if s.get("experiment_id")!=STAGES[i] or s.get("parent_experiment_id")!=(PARENT if i==0 else STAGES[0]):reject("STAGE_ID")
        blocks=s.get("development_blocks");heldout=s.get("sealed_heldout_seeds")
        bases=(18000,18032,18064,18200) if i==0 else (19000,19032,19064,19200)
        if not isinstance(blocks,list) or len(blocks)!=3 or any(blocks[j]!=list(range(bases[j],bases[j]+16)) for j in range(3)) or heldout!=list(range(bases[3],bases[3]+48)):reject("COHORT_DRIFT")
        seeds=sum(blocks,[])+heldout
        if len(set(seeds))!=96 or allseeds.intersection(seeds):reject("REUSED_OR_CROSS_STAGE_SEED")
        allseeds.update(seeds)
    if x.get("source_classification")!="DEVELOPMENT_ONLY_NO_INDEPENDENT_SEALED_FIRST_USE" or x.get("classification_rules")!=list(OUTCOMES):reject("FALSE_AUTHORITY")
    return x
def parent_ok(raw,stage):
    x=load(raw)
    if not isinstance(x,dict) or x.get("original_replay_allowed") is not False or x.get("independently_validated") is not True or x.get("science_production_accepted") is not False:reject("PARENT_NOT_REVIEWED")
    if stage==0:
        if x.get("schema")!="forge.r35.independent-original-review.v1" or x.get("experiment_id")!=PARENT or x.get("outcome")!="NO_CONFIRMED_QUARTILE_GAIN":reject("R35_PARENT_IDENTITY")
    else:
        if x.get("schema")!="forge.r7.independent-development-review.v1" or x.get("experiment_id")!=STAGES[0] or x.get("outcome") not in OUTCOMES or x.get("stage_index")!=0:reject("STAGE1_PARENT_IDENTITY")
    return x
def claim_ok(raw,manifest_raw,stage,run_id,head_sha):
    c=load(raw)
    if c!={"schema":"forge.r7.firstuse-budget-consumed.v1","branch":"research/forge-r7-real-autochain-firstuse",
      "experiment_ids":list(STAGES),"first_uses_consumed":2,"reruns_allowed":False,
      "source_manifest_sha256":digest(manifest_raw),"run_id":run_id,"head_sha":head_sha,
      "external_fsa_activated":False,"independent_custody_qualified":False,
      "scientific_accepted":False,"paid_api_calls":0}:reject("CLAIM_DRIFT")
    if stage not in (0,1):reject("UNKNOWN_STAGE")
    return c
