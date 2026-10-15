"""Frozen R12 method contract. No release, worker, or scientific authority."""
import hashlib,json,math
SCHEMA="forge.r12.learned-role-compression.development.v1"
PARENT_SHA="c47cd167f988e0dbe3258b14f82cb4b785966b3939fee5fa5b970f96cf4063b6"
class Blocked(ValueError):pass
def deny(reason):raise Blocked("R12_BLOCKED_"+reason)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def parse(raw,cap=30000):
    if not isinstance(raw,bytes) or len(raw)<1 or len(raw)>cap or cap>600000:deny("JSON_BYTES")
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:deny("DUPLICATE_JSON_KEY")
            d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:deny("NONFINITE"))
def manifest(raw):
    x=parse(raw)
    if (x.get("schema")!=SCHEMA or x.get("scope")!="DEVELOPMENT_ONLY_SYNTHETIC_RELATIONAL_METHOD_SCREEN_NOT_WINGLESS_ORIGINAL"
        or x.get("objective")!="LEARN_TWO_LINK_ROLE_CODE_FOR_QUERY_BLIND_MEMORY_ON_NOVEL_VARIABLE_BINDING_GRAPHS"):deny("METHOD_SCOPE")
    p=x.get("parent",{})
    if (p.get("independent_review_run_id")!=38665222559 or
        p.get("independent_review_artifact_id")!=11940945840 or
        p.get("independent_review_json_sha256")!=PARENT_SHA or
        p.get("all_three_folds_passed") is not False or
        p.get("fold_worst_source_gains")!=[0,0.008680555555555525,-0.21354166666666663]):deny("PARENT_PIN")
    e=x.get("encoder",{})
    if (e.get("role_vocab_size")!=4 or e.get("code_dimensions")!=2 or e.get("code_levels_per_dim")!=3
        or e.get("learnable_scalar_count")!=8 or
        e.get("initial_weights")!=[-1.8,-0.6,0.6,1.8,-1.5,-0.5,0.5,1.5]
        or e.get("second_role_coefficient")!=0.45 or e.get("quantization_thresholds")!=[-0.5,0.5]
        or e.get("train_step_schedule")!=[0.9,0.45,0.22]
        or e.get("training_method")!="coordinate_search_train_only_future_query_accuracy"):deny("ENCODER_DRIFT")
    t=x.get("task",{})
    if (t.get("memory_slot_budget")!=16 or t.get("compressed_links_per_slot")!=2 or
        t.get("base_chain_hops")!=4 or t.get("base_path_count")!=4 or
        t.get("stress_chain_hops")!=6 or t.get("stress_path_count")!=3 or
        t.get("decoys_per_path")!=2 or t.get("entity_pool_size")!=128 or
        t.get("roles_renamed_and_entities_permuted_each_seed") is not True or
        t.get("encoder_sees_future_query") is not False):deny("TASK_OR_MEMORY_BUDGET")
    s=x.get("seeds",{})
    for label,start,count in (("train",30000,24),("development",31000,16),
                              ("structural_stress",32000,16),("reserved_sealed",33000,32)):
        if s.get(label)!=list(range(start,start+count)):deny("SEED_IDENTITY")
    if set(s["train"])&set(s["development"]+s["structural_stress"]+s["reserved_sealed"]):deny("COHORT_LEAK")
    if x.get("controls")!=["chronological_raw_16_edges","fixed_hash_two_link_16_slots",
          "exact_pair_two_link_16_slot_oracle","query_role_shuffled_negative"]:deny("CONTROL_DRIFT")
    d=x.get("decision",{})
    if (d.get("minimum_dev_gain_vs_fixed_hash")!=0.05 or d.get("minimum_stress_gain_vs_fixed_hash")!=0.05
        or d.get("noninferiority_to_exact_oracle_required") is not False
        or d.get("no_post_result_retuning") is not True):deny("PREREG_DECISION")
    a=x.get("authority",{})
    if (a.get("first_use_claims")!=0 or a.get("scientific_originals_executed")!=0
        or a.get("independent_FSA_qualified") is not False or a.get("scientific_accepted") is not False
        or a.get("paid_api_calls")!=0 or a.get("cloudflare_changed") is not False
        or a.get("no_new_controller") is not True):deny("FALSE_AUTHORITY")
    return x
def parent(raw,plan):
    if digest(raw)!=plan["parent"]["independent_review_json_sha256"]:deny("PARENT_CHANGED")
    r=parse(raw)
    if (r.get("schema")!="forge.r11.independent-learned-retention-development.v1" or
        r.get("all_three_folds_passed") is not False or
        r.get("retention_gates_independently_reconstructed") is not True or
        r.get("actual_training_reconstructed") is not True or
        r.get("scientific_accepted") is not False or
        r.get("first_use_authorized") is not False or
        len(r.get("results",[]))!=3):deny("PARENT_REVIEW_NOT_AUTHENTIC")
    for item,gain in zip(r["results"],plan["parent"]["fold_worst_source_gains"]):
        if not math.isfinite(item.get("worst_family_gain",float("nan"))) or abs(item["worst_family_gain"]-gain)>1e-12:deny("PARENT_FINDING_CHANGED")
    return r
