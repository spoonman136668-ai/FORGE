"""F125-R frozen source validation. No learner and no dataset generation."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f125r-path-preserving-composition-freeze.json"
PARENT=ROOT/"reference/research-intake/f124r-sparse-causal-routing-freeze.json"
FROZEN_BLOB="0a2030f17123b7e096c42e730f3a536f014275bd"
PARENT_BLOB="891c950e1d25eea90fbe5191abf8e9c1ab4eac7f"
PARENT_HEAD="6fbfff31ed4795bfe1a0880fd0d941cc200936f8"
SCHEMA="forge.autonomy.f125r.path-preserving-composition-freeze.v1"

class Invalid(ValueError): pass
def need(ok, code):
    if not ok: raise Invalid("F125R_SOURCE_"+code)

def blob(raw):
    raw=raw.replace(b"\r\n",b"\n")
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def validate(x):
    need(isinstance(x,dict) and x.get("schema")==SCHEMA
         and x.get("status")=="PREIMPLEMENTATION_SOURCE_ONLY_NOT_SCIENCE"
         and x["parent"]["f124r_qualified_head"]==PARENT_HEAD
         and x["parent"]["f124r_freeze_blob"]==PARENT_BLOB
         and x["parent"]["f124r_ci_run"]==39049181882
         and x["parent"]["parallel_f124c_not_a_code_dependency"] is True,
         "PARENT_DRIFT")
    n=x["negative_evidence"]
    need(n["F124R_Wingless"]=={"sparse2":30,"best_fixed":62,"fresh_dense":63,
         "true_route_retained":36,"pairs":64}
         and n["F124R_Yggdrasil"]=={"sparse2":34,"best_fixed":62,
         "fresh_dense":62,"true_route_retained":40,"pairs":64}
         and n["F124R_max_attainable_control_margin"]==0.03125
         and n["F124R_required_control_margin"]==0.05
         and n["F124R_primitive_cost_proxy_sparse_over_dense"]==
         [5.56208645,5.58109193], "NEGATIVE_EVIDENCE_REWRITTEN")
    m=x["mechanism"]
    need(m["name"]=="Public-token-keyed path-preserving sum-product composition"
         and m["trainable_parameters"]==20
         and m["maximum_active_states_per_hop"]==256
         and m["no_topk_pruning"] is True
         and m["all_visible_paths_retained_below_budget"] is True
         and m["no_oracle_path_or_labels_as_features"] is True
         and m["graph_edge_order_invariance"] is True
         and m["state_key"]==["public_node_id","raw_16_bit_incoming_dst_token"]
         and m["optimizer"]=={"epochs":100,"rate":0.22,"clip":1,
             "initialization":"fixed precommitted vector with 20 bounded values",
             "full_batch":True,"train_only":True}, "MECHANISM_CHANGED")
    e=x["source"]
    need(e["family"]=="F125R-NEW-ADVERSARIAL-BINDING-FAMILY"
         and e["train_hops"]==[3,5] and e["protected_confirm_hops"]==[6,8]
         and e["train_public_path_count"]==[6,10]
         and e["protected_confirm_path_count"]==[8,14]
         and e["fresh_graph_local_raw_16bit_salt"] is True
         and e["source_vectors_per_lane"]==2
         and e["no_protected_generation_in_preimplementation"] is True,
         "FRESH_SOURCE_CHANGED")
    c=x["cohorts"]
    need(c["Wingless"]=={"TRAIN":[100100,100131],"CONFIRM":[100200,100263]}
         and c["Yggdrasil"]=={"TRAIN":[101100,101131],"CONFIRM":[101200,101263]}
         and c["train_pairs_per_vector"]==32
         and c["confirm_pairs_per_vector"]==64
         and c["confirm_reserved"] is True
         and c["F123_F124R_F124C_reserved_CONFIRM_untouched"] is True,
         "PROTECTED_SPLIT_CHANGED")
    seen=set()
    for lane in ("Wingless","Yggdrasil"):
        for phase,length in (("TRAIN",32),("CONFIRM",64)):
            lo,hi=c[lane][phase]
            group=set(range(lo,hi+1))
            need(len(group)==length and not group.intersection(seen),
                 "COHORT_OVERLAP")
            seen.update(group)
    v=x["evaluation"]
    need(v["minimum_absolute_paired_gain_per_lane"]==0.05
         and v["must_pass_both_lanes"] is True
         and v["no_depth_alias_collision_stratum_degradation"] is True
         and v["F123_dense_noninferiority_required"] is True,
         "SUCCESS_THRESHOLD_CHANGED")
    h=v["headroom_eligibility"]
    need(h["minimum_TRAIN_ceiling_minus_best_fixed_fraction"]==0.08
         and h["training_only"] is True
         and "UNINFORMATIVE_HEADROOM" in h["rule"]
         and "Do not reseed" in h["rule"], "HEADROOM_RULE_DRIFT")
    r=v["resource"]
    need(r["maximum_s2_successor_primitive_operations_fraction_of_dense"]==.75
         and r["per_lane"] is True
         and r["no_free_index_hash_sort_or_merge"] is True
         and r["memory_states_limit"]==256, "RESOURCE_TARGET_CHANGED")
    need(set(x["controls"])=={"CTRL_F123_DENSE_B","CTRL_F124R_SPARSE2",
         "CTRL_F122_NO_ROUTING","CTRL_FIXED_SOFT_PATH","CTRL_ROLE_ONLY",
         "CTRL_QUERY_ONLY","CTRL_EXACT_SYMBOLIC_CEILING",
         "CTRL_DISABLE_KEY_MERGE"}, "FIXED_CONTROLS_CHANGED")
    auth=x["authority"]
    need(set(auth)=={"protected_confirmation_read","scientific_first_use",
         "scientific_acceptance","optimizer_promotion","accepted_ref_mutation",
         "scientific_originals_executed","codex_calls","paid_model_calls",
         "new_scheduler","ckb_plane_contact","cloudflare_writes",
         "mind_palace_writes","wingless_yggdrasil_repo_writes","merged"}
         and all(val is False or type(val) is int and val==0
                 for val in auth.values()), "PRIVILEGE_ESCALATION")
    need(x["current_gate"].startswith("Freeze F125-R source") and
         "No learner code" in x["current_gate"], "STAGE_ESCALATION")
    return x

def frozen():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    need(blob(raw)==FROZEN_BLOB,"SOURCE_BLOB_DRIFT")
    need(blob(PARENT.read_bytes())==PARENT_BLOB,"PARENT_BLOB_DRIFT")
    obj=json.loads(raw)
    validate(obj)
    return obj,hashlib.sha256(raw).hexdigest()

def receipt(sha):
    need(isinstance(sha,str) and re.fullmatch("[0-9a-f]{40}",sha),
         "MISSING_SHA")
    obj,h=frozen()
    return {"schema":"forge.autonomy.f125r.source-admission.v1",
        "source_sha":sha,"freeze_git_blob":FROZEN_BLOB,
        "freeze_sha256":h,"parent_sha":PARENT_HEAD,
        "parent_protocol_git_blob":PARENT_BLOB,
        "graph_cases_generated":0,"model_trained":False,
        "protected_confirmation_read":False,
        "scientific_first_use":False,"scientific_accepted":False,
        "optimizer_promoted":False,"accepted_ref_mutations":0}

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    doc=receipt(args.source_sha)
    out=Path(args.output)
    need(out.parent.is_dir() and not out.exists(),"RECEIPT_ALREADY_PRESENT")
    out.open("xb").write((json.dumps(doc,sort_keys=True,
         separators=(",",":"))+"\n").encode())
    print("F125R_FROZEN_SOURCE=PASS")
    print("F125R_CONFIRM_EXECUTED=false")

if __name__=="__main__":
    try: main()
    except (Invalid,KeyError,TypeError,ValueError,OSError) as e:
        print("F125R_PREIMPLEMENTATION_QUARANTINED="+str(e),file=sys.stderr)
        raise SystemExit(1)
