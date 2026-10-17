"""F111: frozen PUBLIC non-additive source representations and graph distractor controls.

This is designed to FALSIFY additive-offset transfer. Strong nonlearned table
lookup has identical public evidence metadata and reads exactly one observation.
Reuses original F109 fits, without training on these assessment cohorts.
No protected science, Codex, paid inference or native dispatch.
"""
import argparse
from dataclasses import dataclass,replace
import hashlib
import json
import os
from pathlib import Path
import random
import re
import sys

import f103_yggdrasil_public_binding as ybind
import f109_failure_driven_mechanisms as f109
import f110_capacity_transfer as f110

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f111-nonadditive-transfer-freeze.json"
FREEZE_BLOB="a20419f49bf80fffb38413673dfb3dd29ec81ed9"
F110_BLOB="fbcfa96e40a827d76c035206857a21b67ec60162"
SCHEMA="forge.autonomy.f111.nonadditive-representation-and-adversarial-topology-freeze.v1"
REPORT="forge.autonomy.f111.nonadditive-representation-strong-information-controls-public.v1"
SOURCE=re.compile(r"^[0-9a-f]{40}$")
class Quarantined(ValueError):pass
def need(ok,reason):
    if not ok:raise Quarantined("F111_"+reason)
def blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def canonical(path):
    return Path(path).read_bytes().replace(b"\r\n",b"\n")

def freeze():
    raw=canonical(FREEZE)
    need(blob(raw)==FREEZE_BLOB and
         blob(canonical(ROOT/"nativeevidence/f110_capacity_transfer.py"))==
             F110_BLOB,"ORIGINAL_FROZEN_SOURCE_DRIFT")
    cfg=json.loads(raw)
    need(cfg.get("schema")==SCHEMA and
         cfg.get("parent_f110_exact_head_sha")==
           "bc793d9d702a06f28bae452777c5c63cd39a2430" and
         cfg.get("parent_f110_code_blob")==F110_BLOB and
         cfg.get("parent_f110_freeze_blob")=="e191c4b3959d580b15390bd2eb8dca3b21eb2fc7",
         "PARENT_IDENTITY_CHANGED")
    blocks=cfg["wingless"]["new_public_diagnostic_blocks"]
    expected=[("W-R1",[67100,67147]),("W-R2",[67200,67247]),("W-R3",[67300,67347])]
    need([(b.get("name"),b.get("seeds")) for b in blocks]==expected and
         all(b.get("cases")==48 for b in blocks) and
         [(b.get("name"),b.get("seeds")) for b in cfg["yggdrasil"][
           "new_public_diagnostic_blocks"]]==[
           ("Y-R1",[67400,67447]),("Y-R2",[67500,67547]),("Y-R3",[67600,67647])],
         "COHORT_IDENTITY_DRIFT")
    w=cfg["wingless"]
    need(w["training"]=="NO_RETRAINING_REUSE_F109_FROZEN_96_TRAIN_PAIR_FIT_100_UPDATES" and
         w["new_equal_information_comparator"]==
             "public_metadata_table_lookup_by_query_source_id" and
         w["comparator_observes_exactly_one_evidence_value"] is True and
         w["comparator_uses_same_public_metadata_as_model"] is True and
         w["legacy_router_adapter"]==
             "only_canonical_offset_zero_available_for_nonadditive_mapping_no_hidden_correct_offset" and
         w["do_not_retrain_after_diagnostics"] is True and
         w["no_superiority_if_explicit_metadata_lookup_matches_or_beats_learned"] is True and
         w["cross_family_claim_thresholds"]=={
           "minimum_legacy_router_pair_accuracy_each_block":0.75,
           "minimum_gain_against_equal_information_table_control":0.125,
           "minimum_worst_family_accuracy":0.6},"SCREEN_OR_TRAINING_RETUNED")
    y=cfg["yggdrasil"]
    need(y["source_graph_edges"]==12 and y["hops"]==4 and
         y["screen_superiority_net_pairs_min"]==18 and
         y["do_not_tune_after_assessment"] is True and
         y["coded_control_strictly_separate_from_inference"] is True,
         "YGG_GRAPH_CONTRACT_DRIFT")
    guards=cfg["authority"]
    need(all(guards.get(k) is True for k in (
        "no_codex","no_paid_api","no_work_scheduling","no_new_scheduler",
        "no_protected_first_use","no_accepted_science","no_accepted_ref_mutation",
        "no_optimizer_promotion","no_wingless_yggdrasil_repo_writes",
        "no_ckb_plane_contact","no_cloudflare_write","no_mind_palace_write",
        "no_native_research_dispatch","no_autonomous_GPT_or_scientific_claim")),
        "UNAUTHORIZED_SCIENCE")
    return cfg,hashlib.sha256(raw).hexdigest()

def read_parent(source,root,cfg):
    root=Path(root).resolve()
    report=root/cfg["source_report"]
    receipt=root/cfg["source_receipt"]
    raw=report.read_bytes()
    line=receipt.read_bytes().decode("utf-8-sig").strip()
    m=re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)",line)
    need(bool(m) and m.group(2)==report.name and
         hashlib.sha256(raw).hexdigest()==m.group(1),
         "F110_RECEIPT_TAMPER")
    data=json.loads(raw.decode("utf-8-sig"))
    reference=f110.evaluate(source,root)
    need(data==reference and data.get("schema")==f110.REPORT and
         data.get("source_sha")==source and
         data.get("protected_first_use_authorized") is False and
         data.get("independently_accepted_science")==0 and
         data.get("accepted_ref_mutations")==0 and
         data.get("codex_calls")==0,"F110_EVIDENCE_REPLAY_OR_AUTHORITY")
    for lane in ("Wingless","Yggdrasil"):
        rows=[x for x in data.get("lanes",[]) if x.get("lane")==lane]
        need(len(rows)==1 and len(rows[0].get("blocks",[]))==3,
             "INCOMPLETE_PARENT_F110_"+lane)
        expect=cfg["previous_results_required"][lane]
        if lane=="Wingless":
            values=[b["paired_correct"]["learned_offset_routing_64"]
                    for b in rows[0]["blocks"]]
            control=[b["paired_correct"]["capacity_matched_query_only_64"]
                     for b in rows[0]["blocks"]]
            need(values==expect["model_correct_each"] and
                 control==expect["capacity_control_correct_each"] and
                 rows[0]["candidate_parameters"]==expect["model_parameters"] and
                 rows[0]["matched_control_parameters"]==expect["matched_control_parameters"] and
                 rows[0]["capacity_matched_public_transfer_passed"] is True,
                 "F110_WING_POSITIVE_NOT_INTACT")
        else:
            s=[b["paired_correct"]["strict_slot_candidate_20"] for b in rows[0]["blocks"]]
            p=[b["paired_correct"]["soft_slot_parent_20"] for b in rows[0]["blocks"]]
            need(s==expect["candidate_correct_each"] and
                 p==expect["parent_correct_each"] and
                 rows[0]["strict_slot_transfer_superiority_passed"] is False,
                 "F110_YGG_NEGATIVE_RELABEL")
    return hashlib.sha256(raw).hexdigest()

@dataclass(frozen=True)
class WingCase:
    public: f109.WCase
    # Public semantic source IDs, in tag order; arbitrary per-case permutations.
    ids_by_tag:tuple
    encoding:str
    block:str
    public_source_codes_by_tag:tuple
    public_requested_source_code:str

def new_wing_case(seed,block):
    rng=random.Random((seed<<9)+block*101+111)
    ids=list(range(4))
    rng.shuffle(ids)
    # Noncyclic code: force true source mapping not reducible to additive shift.
    if any(all(ids[tag]==(tag+k)%4 for tag in range(4))
           for k in range(4)):
        ids[1],ids[2]=ids[2],ids[1]
    query=(seed//4+block)%4
    tag=ids.index(query)
    order=list(range(4))
    rng.shuffle(order)
    amplitude=(1.,.6,.2)[block]
    distractor_amp=(1.,2.,3.)[block]
    plus=[distractor_amp*(1 if rng.getrandbits(1) else -1) for _ in range(4)]
    minus=plus.copy()
    plus[tag]=amplitude
    minus[tag]=-amplitude
    original=f110.wobserve.Case(seed,block,0,query,tuple(order),
                    tuple(plus[t] for t in order),
                    tuple(minus[t] for t in order))
    wrapped=f109.WCase(original,0,block)
    need(sum(a!=b for a,b in zip(
         original.positive_values,original.negative_values))==1 and
         sorted(ids)==list(range(4)), "INVALID_WING_REPRESENTATION")
    # Three *actual* distinct public source-identifier encodings, not just
    # names for the same offset mapping. Codes are complete public metadata.
    nonce=rng.randrange(100000,999999)
    if block==0:
        semantic_codes=tuple("source-id-"+str(k) for k in range(4))
    elif block==1:
        semantic_codes=tuple("alias/"+str(nonce)+"/"+str(k*17+3) for k in range(4))
    else:
        semantic_codes=tuple("token-"+("x"*(k+1))+"-"+format(nonce+k,"x")
                             for k in range(4))
    source_codes=tuple(semantic_codes[k] for k in ids)
    requested=semantic_codes[query]
    need(len(set(source_codes))==4 and requested in source_codes,
         "PUBLIC_SOURCE_CODE_COLLISION")
    return WingCase(wrapped,tuple(ids),("permutation","alias_table","variable_code")[block],
                    ("W-R1","W-R2","W-R3")[block],source_codes,requested)

def wing_groups():
    groups=[]
    for i,(lo,hi) in enumerate(((67100,67147),(67200,67247),(67300,67347))):
        cases=tuple(new_wing_case(seed,i) for seed in range(lo,hi+1))
        need(len(cases)==48 and len({p.public.base.seed for p in cases})==48,
             "INVALID_WING_TRANSFER_COHORT")
        groups.append(cases)
    return tuple(groups)

def tag_lookup(c,values):
    # Computes matching tag using PUBLIC source-ID table; reads ONE value.
    # Source-ID equality uses the FULL public identifier, not the sign
    # label or a hidden modular offset. The codes differ in all 3 cohorts.
    tag=c.public_source_codes_by_tag.index(c.public_requested_source_code)
    position=c.public.base.observation_depths.index(tag)
    return values[position]>0

def ygg_case(seed,block):
    # Original task-equivalent new seed blocks, but with maximal typed-role
    # collisions and a bijective variable alpha-renaming, not new labels.
    p=f109.ygg_case(seed,instance=block,diagnostic=True)
    if block==0:
        p=replace(p,roles=(0,)*12,query_roles=(0,)*4)
    elif block==1:
        perm=list(range(16))
        random.Random(seed+111).shuffle(perm)
        pos=tuple((perm[a],perm[b]) for a,b in p.positive_variables)
        neg=tuple((perm[a],perm[b]) for a,b in p.negative_variables)
        p=replace(p,positive_variables=pos,negative_variables=neg)
    else:
        p=replace(p,roles=(2,)*12,query_roles=(2,)*4)
    need(ybind.coded_exact_binding_oracle(p,p.positive_variables) and
         not ybind.coded_exact_binding_oracle(p,p.negative_variables),
         "INVALID_YGG_STRONG_CONTROL")
    return p

def ygg_groups():
    return tuple(tuple(ygg_case(seed,i) for seed in range(lo,hi+1))
                 for i,(lo,hi) in enumerate(((67400,67447),(67500,67547),(67600,67647))))

def score_blocks(groups,arms,values,oracle,lane):
    reports=[]
    for i,group in enumerate(groups):
        details=[]
        for c in group:
            pos,neg=values(c)
            need(oracle(c,pos) and not oracle(c,neg),
                 "BAD_SEPARATE_CODED_CONTROL")
            decisions={name:bool(fn(c,pos) and not fn(c,neg))
                       for name,fn in arms.items()}
            details.append(dict(seed=(c.public.base.seed if lane=="Wingless" else c.seed),
                                paired_correct_by_arm=decisions))
        correct={name:sum(x["paired_correct_by_arm"][name] for x in details)
                 for name in arms}
        reports.append(dict(block=i,paired_count=48,correct_pairs=correct,
                            individual_paired_decisions=details))
    return reports

def wing_assessment(cfg):
    training,_=f109.wing_cohorts()
    learned=f109.LearnedSourceRouting().train(training)
    blind=f110.CapacityMatchedQueryOnly().train(training)
    old=f110.wobserve.LearnedObservationSelector().fit(
        tuple(p.base for p in training))
    need(learned.steps==blind.steps==old.training_updates==100 and
         learned.parameters==blind.parameters==64,"WING_SAME_FIT_CONTRACT")
    arms={
      "legacy_learned_offset64":lambda c,v:learned.predicts(c.public,v),
      "capacity_query_only64":lambda c,v:blind.predicts(c.public,v),
      "old_query18":lambda c,v:old.predicts(c.public.base,v),
      "public_table_lookup_one_read":tag_lookup
    }
    groups=wing_groups()
    scores=score_blocks(groups,arms,lambda c:(c.public.base.positive_values,
                    c.public.base.negative_values),tag_lookup,"Wingless")
    model=[s["correct_pairs"]["legacy_learned_offset64"] for s in scores]
    table=[s["correct_pairs"]["public_table_lookup_one_read"] for s in scores]
    blind_scores=[s["correct_pairs"]["capacity_query_only64"] for s in scores]
    net=sum(model)-sum(table)
    thresh=cfg["wingless"]["cross_family_claim_thresholds"]
    passed=(all(a/48>=thresh["minimum_legacy_router_pair_accuracy_each_block"] and
                (a-b)/48>=thresh["minimum_gain_against_equal_information_table_control"]
                for a,b in zip(model,table)) and
            min(model)/48>=thresh["minimum_worst_family_accuracy"])
    return dict(lane="Wingless",blocks=scores,total_pairs=144,
          model_correct_each=model,public_table_correct_each=table,
          capacity_query_only_correct_each=blind_scores,
          pooled_legacy_minus_full_metadata_table=net,
          model_parameters=64,capacity_control_parameters=64,
          legacy_actual_evidence_reads=1,table_actual_evidence_reads=1,
          exact_full_information_metadata_lookup_control=True,
          nonadditive_representation_generalization_screen_passed=passed,
          disposition=("RESTRICTED_PUBLIC_REPRESENTATION_GAIN_NOT_SCIENCE" if passed
                       else "NONADDITIVE_REPRESENTATION_TRANSFER_NOT_PROVEN_NEGATIVE_RETAINED"))

def ygg_assessment(cfg):
    original=ybind.public_cohorts()
    parent=ybind.LearnedVariableBinder().fit(original[0]+original[1])
    blind=ybind.LearnedVariableBinder(blind=True).fit(original[0]+original[1])
    need(parent.training_updates==blind.training_updates==100,
         "YGG_TRAIN_BUDGET_CHANGE")
    arms={
      "unchanged_soft_slot20":lambda p,v:parent.predicts(p,v),
      "strict_slot20":lambda p,v:f109.strict_slot_predict(parent,p,v),
      "blind20":lambda p,v:blind.predicts(p,v)
    }
    groups=ygg_groups()
    scores=score_blocks(groups,arms,lambda p:(p.positive_variables,p.negative_variables),
                        lambda p,v:ybind.coded_exact_binding_oracle(p,v),"Yggdrasil")
    strict=[b["correct_pairs"]["strict_slot20"] for b in scores]
    soft=[b["correct_pairs"]["unchanged_soft_slot20"] for b in scores]
    delta=sum(strict)-sum(soft)
    passed=delta>=cfg["yggdrasil"]["screen_superiority_net_pairs_min"]
    return dict(lane="Yggdrasil",blocks=scores,total_pairs=144,
                strict_correct_each=strict,soft_correct_each=soft,
                net_strict_minus_soft=delta,model_parameters_each=20,graph_edges_each=12,
                stronger_typed_role_collision_control=True,
                strict_slot_superiority_screen_passed=passed,
                disposition=("RESTRICTED_PUBLIC_GRAPH_GAIN_NOT_SCIENCE" if passed
                             else "NO_NEW_YGGDRASIL_SUPERIORITY_NEGATIVE_RETAINED"))

def evaluate(source,root):
    need(type(source) is str and SOURCE.fullmatch(source) is not None and
         (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source),
         "CURRENT_GITHUB_SOURCE_REQUIRED")
    cfg,digest=freeze()
    parent_sha=read_parent(source,root,cfg)
    w=wing_assessment(cfg)
    y=ygg_assessment(cfg)
    return dict(schema=REPORT,source_sha=source,freeze_sha256=digest,
       authenticated_F110_report_sha256=parent_sha,
       evidence_class="FROZEN_PUBLIC_NONADDITIVE_GENERALIZATION_NOT_INDEPENDENT_SCIENCE",
       new_blocks_per_lane=3,new_pairs_per_lane=144,
       complete_source_bound_parent_F110_positive_and_negative_preserved=True,
       outcomes=[w,y],all_288_pairwise_decisions_retained=True,
       independent_scientific_originals=0,science_accepted=0,
       first_use_authorized=False,optimizer_promoted=False,
       accepted_ref_mutations=0,codex_calls=0,paid_model_api_calls=0,
       chatgpt_work_tasks=0,new_schedulers=0,ckb_plane_contact=False,
       cloudflare_writes=0,scientific_custody_established=False)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-ref",required=True)
    parser.add_argument("--evidence-root",required=True)
    args=parser.parse_args()
    print(json.dumps(evaluate(args.source_ref,args.evidence_root),
                     sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    try:main()
    except (Quarantined,f110.Quarantined,f109.Quarantined,
            ybind.Rejected,f110.wobserve.Rejected,OSError,ValueError,KeyError,TypeError) as e:
        print("FORGE_F111_FROZEN_NONADDITIVE_TRANSFER=QUARANTINED "+str(e),file=sys.stderr)
        raise SystemExit(1)
