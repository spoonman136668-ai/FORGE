"""F113: pre-frozen full-factorial Wingless source-binding falsification.

PUBLIC SYNTHETIC development; no training on F113 tests, first-use science,
Codex, research dispatch or optimizer promotion. The old F112 model is unchanged.
"""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import random
import re

import f112_learned_relations as parent

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f113-orthogonal-source-binding-freeze.json"
FREEZE_BLOB="3fa7586aa22326723fa6daf0751658d13a827876"
PARENT_BLOB="838050a30a37961525eba29cab42a32f651c8ca0"
PARENT_FREEZE_BLOB="c42f5baaaa4cd77395229a153b059bcd4fa08181"
SCHEMA="forge.autonomy.f113.query-depth-orthogonal-source-binding-public.v1"
RANGES=((68700,68747),(68800,68847),(68900,68947))
SHA40=re.compile(r"^[a-f0-9]{40}$")

class Rejected(ValueError):
    pass

def require(condition,reason):
    if not condition:raise Rejected("F113_"+reason)

def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def canonical(path):
    return Path(path).read_bytes().replace(b"\r\n",b"\n")

def freeze():
    require(git_blob(canonical(FREEZE))==FREEZE_BLOB,"FROZEN_PREREG_DRIFT")
    require(git_blob(canonical(ROOT/"nativeevidence/f112_learned_relations.py"))
            ==PARENT_BLOB,"PARENT_MODEL_DRIFT")
    require(git_blob(canonical(ROOT/"reference/research-intake/f112-learned-relations-freeze.json"))
            ==PARENT_FREEZE_BLOB,"PARENT_SOURCE_POLICY_DRIFT")
    parent.freeze() # pins the F111 source and F112 scientific negative outcome.
    cfg=json.loads(canonical(FREEZE))
    require(cfg.get("schema")==
            "forge.autonomy.f113.query-depth-orthogonal-source-binding-public-freeze.v1",
            "SCHEMA_CHANGED")
    p=cfg["parent"]
    require(p.get("f112_exact_head")==
            "9bd5269582e537cf5e7537c1298ec29611ddec16" and
            p.get("f112_source_git_blob")==PARENT_BLOB and
            p.get("f112_freeze_git_blob")==PARENT_FREEZE_BLOB,
            "SOURCE_PARENT_IDENTITY_CHANGED")
    arm=cfg["intervention"]
    require([v.get("seeds") for v in arm.get("diagnostic_blocks",[])] ==
            [[68700,68747],[68800,68847],[68900,68947]] and
            [v.get("cohort") for v in arm["diagnostic_blocks"]]==[1,2,3] and
            arm["pairs_each"]==48,
            "DIAGNOSTIC_SPLIT_CHANGED")
    scr=arm["evaluation"]
    require(scr["source_binding_screen_if"].startswith(
            "Unchanged learned feature model >=36/48") and
            scr["incremental_learning_screen_if"].startswith(
            "Against identically-featured fixed/untrained similarity: >=18"),
            "FROZEN_SCREENS_CHANGED")
    require(all(value is True for value in cfg["authority"].values()),
            "EXTERNAL_OR_SCIENTIFIC_AUTHORITY_CHANGED")
    return cfg,hashlib.sha256(canonical(FREEZE)).hexdigest()

def public_case(seed, block):
    require(0<=block<3 and RANGES[block][0]<=seed<=RANGES[block][1],
            "SOURCE_OUT_OF_FROZEN_RANGE")
    offset=seed-RANGES[block][0]
    query=offset%4
    chosen=((offset//4)+block)%4
    # F112 public source-code grammar retained unchanged. Fresh unseen IDs.
    codes=parent.codebook(seed,block+1,0)
    request=codes[chosen]
    rng=random.Random((seed<<10)+(block+1)*2707+113)
    order=list(range(4));rng.shuffle(order)
    distractor=[1.0 if rng.getrandbits(1) else -1.0 for _ in range(4)]
    positive=distractor.copy()
    negative=distractor.copy()
    positive[chosen]=1.0
    negative[chosen]=-1.0
    case=parent.WCase(seed,block+1,codes,request,
                     tuple(positive[t] for t in order),
                     tuple(negative[t] for t in order),query,tuple(order))
    require(case.true_tag()==chosen and
            sum(a!=b for a,b in zip(case.positive_values,case.negative_values))==1 and
            parent.exact_lookup(case,case.positive_values) and
            not parent.exact_lookup(case,case.negative_values),
            "INVALID_FROZEN_COUNTERFACTUAL")
    return case

def public_groups():
    blocks=tuple(tuple(public_case(seed,i) for seed in range(lo,hi+1))
                for i,(lo,hi) in enumerate(RANGES))
    all_seeds=[p.seed for group in blocks for p in group]
    require(len(set(all_seeds))==144 and len(all_seeds)==144 and
            all(len(group)==48 for group in blocks),
            "SOURCE_IDENTITY_REUSE")
    for group in blocks:
        cross=Counter((p.query_depth,p.true_tag()) for p in group)
        require(len(cross)==16 and
                all(cross[(q,tag)]==3 for q in range(4) for tag in range(4)),
                "QUERY_TARGET_FACTORIAL_LEAKAGE")
        require(len({code for p in group for code in p.source_codes})==192,
                "SYNTHETIC_ID_COLLISION")
    old_train,old_diag=parent.wing_cohorts()
    old_seeds={p.seed for p in old_train}
    old_seeds.update(p.seed for group in old_diag for p in group)
    require(set(all_seeds).isdisjoint(old_seeds),
            "PARENT_TRAIN_OR_DIAGNOSTIC_REUSE")
    return blocks

def shortcut_only(case,values):
    # Explicit weak control: assumes query depth identifies source tag.
    # It has no source code equality, lookup table or hindsight label.
    index=case.observation_depths.index(case.query_depth)
    return values[index]>0

def paired_correct(fn,case):
    return bool(fn(case,case.positive_values) and
                not fn(case,case.negative_values))

def models():
    train,_=parent.wing_cohorts()
    learned=parent.LearnedRelationAttention().train(train)
    qtrain=tuple(parent.f109.WCase(
        parent.f110.wobserve.Case(p.seed,p.cohort,0,p.query_depth,
            p.observation_depths,p.positive_values,p.negative_values),
        0,p.cohort) for p in train)
    blind=parent.f110.CapacityMatchedQueryOnly().train(qtrain)
    oldtrain,_=parent.f109.wing_cohorts()
    legacy=parent.f109.LearnedSourceRouting().train(oldtrain)
    require(learned.parameters==6 and learned.updates==100 and
            blind.parameters==64 and blind.steps==100 and
            legacy.steps==100,
            "PARENT_TRAIN_SOURCE_OR_BUDGET_CHANGED")
    return {
        "unchanged_learned_engineered_six":learned.predicts,
        "untrained_identical_six_features":parent.fixed_similarity,
        "full_public_symbolic_lookup_one_read":parent.exact_lookup,
        "query_only_64_train_control":lambda p,v:parent.original_query_only(p,v,blind),
        "legacy_offset_64_original_train":lambda p,v:parent.legacy_offset(p,v,legacy),
        "query_depth_only_shortcut_one_read":shortcut_only,
    }

def evaluate(source_sha):
    require(isinstance(source_sha,str) and SHA40.fullmatch(source_sha),
            "EXACT_SOURCE_SHA_INVALID")
    cfg,prereg_sha256=freeze()
    arms=models()
    groups=public_groups()
    blocks=[]
    for group_index,group in enumerate(groups):
        rows=[]
        for p in group:
            decisions={name:paired_correct(fn,p) for name,fn in arms.items()}
            # Ground truth is inspected only in the evaluation; no predictor
            # receives this true_tag, which is NOT part of WCase's public API.
            row=dict(seed=p.seed,query_depth=p.query_depth,
                     true_tag_offline_only=p.true_tag(),
                     public_metadata_sha256=hashlib.sha256(
                         json.dumps([p.source_codes,p.requested_code,
                                     p.observation_depths],sort_keys=True
                                   ).encode()).hexdigest(),
                     paired_correct_by_arm=decisions)
            rows.append(row)
        correct={name:sum(row["paired_correct_by_arm"][name] for row in rows)
                 for name in arms}
        require(correct["full_public_symbolic_lookup_one_read"]==48 and
                correct["query_depth_only_shortcut_one_read"]==12,
                "BROKEN_STRONG_OR_WEAK_CONTROL")
        bucket=Counter((p.query_depth,p.true_tag()) for p in group)
        learned_per_tag=[sum(row["paired_correct_by_arm"]["unchanged_learned_engineered_six"]
                             for row in rows if row["true_tag_offline_only"]==tag)
                         for tag in range(4)]
        blocks.append(dict(name=cfg["intervention"]["diagnostic_blocks"][group_index]["name"],
                           seeds=list(RANGES[group_index]),pairs=48,
                           full_factorial_4x4_each_cell_count=3,
                           per_tag_learned_correct_of_12=learned_per_tag,
                           paired_correct=correct,individual_rows=rows))
    flat=[row for block in blocks for row in block["individual_rows"]]
    learned_name="unchanged_learned_engineered_six"
    fixed_name="untrained_identical_six_features"
    wins=sum(row["paired_correct_by_arm"][learned_name] and
             not row["paired_correct_by_arm"][fixed_name] for row in flat)
    losses=sum(row["paired_correct_by_arm"][fixed_name] and
               not row["paired_correct_by_arm"][learned_name] for row in flat)
    source_screen=all(block["paired_correct"][learned_name]>=36 and
                      min(block["per_tag_learned_correct_of_12"])>=8
                      for block in blocks)
    incremental_screen=(source_screen and wins-losses>=18 and
                        all(b["paired_correct"][learned_name]>=
                            b["paired_correct"][fixed_name] for b in blocks))
    symbolic=sum(b["paired_correct"]["full_public_symbolic_lookup_one_read"]
                 for b in blocks)
    learned=sum(b["paired_correct"][learned_name] for b in blocks)
    return {
        "schema":SCHEMA,"source_sha":source_sha,
        "parent_exact_f112_head":cfg["parent"]["f112_exact_head"],
        "parent_f112_source_git_blob":PARENT_BLOB,
        "frozen_F113_prereg_sha256":prereg_sha256,
        "public_training_examples_reused":96,
        "new_public_counterfactual_pairs":144,
        "new_cohorts_full_factorial_balanced":True,
        "diagnostic_training_steps":0,
        "parent_learned_training_steps":100,
        "strong_symbolic_total_correct":symbolic,
        "query_depth_only_total_correct":sum(
            b["paired_correct"]["query_depth_only_shortcut_one_read"]
            for b in blocks),
        "learned_total_correct":learned,
        "learned_only_vs_fixed":wins,
        "fixed_only_vs_learned":losses,
        "net_learned_gain_vs_fixed":wins-losses,
        "source_binding_screen_passed":source_screen,
        "incremental_learning_superiority_screen_passed":incremental_screen,
        "source_binding_disposition":(
            "PUBLIC_BALANCED_SOURCE_BINDING_SCREEN_PASSED_NOT_SCIENCE"
            if source_screen else
            "PUBLIC_BALANCED_SOURCE_BINDING_SCREEN_FAILED_NEGATIVE"),
        "learning_disposition":(
            "PUBLIC_INCREMENTAL_LEARNED_GAIN_VS_FIXED_ONLY_NOT_SCIENCE"
            if incremental_screen else
            "NO_INCREMENTAL_GAIN_VS_IDENTICAL_UNTRAINED_FEATURES"),
        "no_superiority_over_full_public_metadata_lookup":learned<=symbolic,
        "lanes_evaluated":["Wingless"],
        "Yggdrasil_untouched_F112_negative_preserved":True,
        "blocks":blocks,
        "scientific_first_use_authorized":False,
        "independent_scientific_acceptance":False,
        "optimizer_promotion_authorized":False,
        "accepted_ref_mutations":0,
        "new_native_scientific_dispatches":0,
        "codex_calls":0,
        "external_paid_model_calls":0,
        "CKB_accessed":False,
        "MindPalace_written":False,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-ref",required=True)
    args=p.parse_args()
    print(json.dumps(evaluate(args.source_ref),sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    main()
