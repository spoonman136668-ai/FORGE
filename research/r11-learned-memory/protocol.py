"""R11 frozen source/custody gate. No scientific first use or replay."""
import hashlib,json,math
PIN="754a3a924efaeb9cdf4ca99998391d0a02d1224bf8bc43bf6ac764ea934c2031"
def stop(s):raise ValueError("R11_"+s)
def parse(raw,cap=70000):
    if type(cap) is not int or not 0<cap<=1000000 or not isinstance(raw,bytes) or not 0<len(raw)<cap:stop("JSON_SIZE")
    def dedupe(pairs):
        result={}
        for k,v in pairs:
            if k in result:stop("DUPLICATE_KEY")
            result[k]=v
        return result
    return json.loads(raw,object_pairs_hook=dedupe,parse_constant=lambda _:stop("NONFINITE"))
def sha(raw):return hashlib.sha256(raw).hexdigest()
def freeze(raw):
    f=parse(raw)
    if (f.get("schema")!="forge.r11.learned-when-to-retain.development.v1" or
        f.get("lane")!="Wingless" or f.get("scope")!="TRAIN_ONLY_PUBLIC_DEVELOPMENT_NO_SCIENTIFIC_ORIGINAL"):stop("FROZEN_SCOPE")
    p=f.get("parent",{})
    if p.get("sha256")!=PIN or p.get("run_id")!=38663053332 or p.get("artifact_id")!=11939807429 or p.get("schema")!="forge.r10.independent-two-method-real-development-review.v1":stop("PARENT_IDENTITY")
    outcomes=p.get("frozen_outcomes",[])
    if len(outcomes)!=2 or outcomes[0].get("id")!="W36-C4" or outcomes[1].get("id")!="W36-C2" or outcomes[0].get("development_gate_passed") is not False or outcomes[1].get("development_gate_passed") is not False or abs(outcomes[0].get("mean_gain",-100)-0.018229166666666685)>1e-12 or abs(outcomes[1].get("mean_gain",-100)+0.052662037037037035)>1e-12:stop("NEGATIVE_RETUNED")
    pins=f.get("pinned",{})
    if (pins.get("wingless_sha")!="b1e4972f04142f1f35f76f9483b12491dec4846c" or pins.get("r34_blob")!="7e3db618c055e5228f9b07639e4555bc9250008e" or
        pins.get("r36_sha")!="7f2f791f98d92ad932e0f530a7d23d0330a15643" or pins.get("r36_blob")!="d75f36f25aca35e30a90bd50e31c8e0d90cedc28"):stop("SOURCE_DRIFT")
    method=f.get("method",{})
    wanted={"identifier":"W-FORGE-R11-LEARNED-RETENTION-CTRL-01","model_dimension":16,"epochs":32,
       "source_count":3,"train_rows_per_source":576,"persistent_memory_slots_per_source":32,
       "proxy_rule":"index_plus_epoch_modulo_5_equals_zero",
       "hard_selection":"32_lowest_current_signed_margins",
       "coverage_selection":"two_lowest_signed_margins_per_dominant_abs_feature_coordinate_then_fill",
       "controller":"per_source_logit_trained_by_heldback_training_proxy_one_step_loss",
       "initial_logit":0,"controller_lr":4.0,"model_lr":0.1,"logit_clip":4.0,"loss_delta_clip":0.5,
       "memory_mix":"round_sigmoid_times_32_hard_slots_remaining_diverse_unique_then_fill",
       "all_proxy_data_from_training":True,"no_validation_feedback_to_memory":True}
    if method!=wanted:stop("MODEL_OR_CONTROLLER_RETUNE")
    if f.get("controls")!=["hard_minimax_32_epochs","W36-C4_fixed_top_loss_96_slots_32_epochs"]:stop("CONTROL_REMOVED")
    d=f.get("development",{})
    blocks=lambda start:[[start+k+i for i in range(16)] for k in (0,32,64)]
    if (d.get("train_blocks")!=blocks(28000) or d.get("reserved_future_sealed_seeds")!=list(range(28200,28248)) or
        d.get("reserved_future_replication_training")!=blocks(29000) or d.get("reserved_future_replication_sealed")!=list(range(29200,29248)) or
        d.get("validation")!="other_two_development_blocks_only" or d.get("minimum_worst_source_gain_per_fold")!=0.02 or
        d.get("max_individual_source_harm")!=0.05 or d.get("minimum_overall_accuracy")!=0.55 or
        d.get("eligible_only_if_all_three_folds") is not True or d.get("no_post_result_controller_retuning") is not True):stop("COHORT_OR_GATE_DRIFT")
    a=f.get("authority",{})
    if a!={"new_scientific_originals":0,"first_use_claims":0,"external_FSA":False,
      "scientific_accepted":False,"cloudflare_mutation":False,"paid_model_calls":0}:stop("CLAIMED_AUTHORITY")
    ids=sum(d["train_blocks"],[])+d["reserved_future_sealed_seeds"]+sum(d["reserved_future_replication_training"],[])+d["reserved_future_replication_sealed"]
    if len(ids)!=192 or len(set(ids))!=192:stop("SEED_REUSE")
    return f
def verify_parent(raw,f):
    if sha(raw)!=PIN:stop("PARENT_BYTES")
    p=parse(raw)
    if (p.get("schema")!=f["parent"]["schema"] or p.get("prospective_method_proposal") is not None or
       p.get("method_superiority_established") is not False or
       p.get("new_scientific_first_use_authorized") is not False or
       p.get("originals_executed")!=0 or p.get("scientific_accepted") is not False or
       p.get("sealed_cohort_accessed") is not False):stop("PARENT_UNQUALIFIED")
    d={x.get("id"):x for x in p.get("ranked_heldout_blind_development_candidates",[])}
    if set(d)!={"W36-C2","W36-C4"}:stop("PARENT_MISSING_CANDIDATE")
    for item in f["parent"]["frozen_outcomes"]:
        prev=d[item["id"]]
        if (prev.get("development_gate_passed") is not False or abs(prev.get("mean_min_family_gain",-99)-item["mean_gain"])>1e-10):stop("PARENT_NEGATIVE_DRIFT")
    return p
