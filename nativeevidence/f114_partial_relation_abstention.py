"""F114: information-limited source retrieval with public role witnesses and abstention.

The preregistration was committed before this source and any F114 evaluation.
All samples are PUBLIC synthetic development; no scientific first-use, Codex,
paid inference, native science dispatch, optimizer promotion or external control.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import sys

import f112_learned_relations as f112

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "reference/research-intake/f114-partial-relation-abstention-freeze.json"
FREEZE_BLOB = "c2a4587aae1e1a0f05089d2c9e01fbfdc3f90002"
F113_BLOB = "6d190a7410135c1a035d48165912e27d01f74ae0"
F112_BLOB = "838050a30a37961525eba29cab42a32f651c8ca0"
SCHEMA = "forge.autonomy.f114.partial-relation-selective-retrieval-public.v1"
SHA40 = re.compile("^[a-f0-9]{40}$")
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
RANGES = ((69600, 69647), (69700, 69747), (69800, 69847))
COHORTS = ("W114-U", "W114-R", "W114-I")

class Invalid(ValueError): pass
def need(ok, reason):
    if not ok:
        raise Invalid("F114_" + reason)
def gitblob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
def normalized(path):
    return Path(path).read_bytes().replace(b"\r\n", b"\n")
def freeze():
    raw = normalized(FREEZE)
    need(gitblob(raw) == FREEZE_BLOB and
         gitblob(normalized(ROOT / "nativeevidence/f113_orthogonal_source_binding.py")) == F113_BLOB and
         gitblob(normalized(ROOT / "nativeevidence/f112_learned_relations.py")) == F112_BLOB,
         "FROZEN_PREREG_OR_PARENT_DRIFT")
    c = json.loads(raw)
    need(c["schema"] == "forge.autonomy.f114.partial-relation-abstention-prereg.v1" and
         c["parent"]["f113_head"] == "88924d2e73d694076a5aa45bcdec3e89b3f41dac" and
         c["parent"]["f113_implementation_blob"] == F113_BLOB and
         c["parent"]["f112_model_blob"] == F112_BLOB,
         "PARENT_IDENTITY_CHANGED")
    need([x["seeds"] for x in c["cohorts"]] == [[69600,69647],[69700,69747],[69800,69847]] and
         all(x["cases"] == 48 for x in c["cohorts"]) and
         c["generator"]["max_observation_sources"] == 4 and
         c["generator"]["source_id_ascii_length"] == 12 and
         c["frozen_thresholds"]["impossibility"].startswith("For the 24 publicly identical I twins,"),
         "SOURCE_FAMILY_OR_FALSIFICATION_DRIFT")
    need(all(x is True for x in c["authority"].values()), "SCIENTIFIC_AUTHORITY_DRIFT")
    return c, hashlib.sha256(raw).hexdigest()

@dataclass(frozen=True)
class Public:
    requested_code: str
    source_codes: tuple[str, ...]
    source_roles: tuple[int, ...]
    query_role: int
    observation_order: tuple[int, ...]
    query_depth: int
    # No true source, cohort, seed, twin index, observation sign, label or answer.

@dataclass(frozen=True)
class Offline:
    public: Public
    true_tag: int
    case_id: int
    positive_values: tuple[float, ...]
    negative_values: tuple[float, ...]

def levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        row = [i]
        for j, y in enumerate(b, 1):
            row.append(min(row[-1] + 1, prev[j] + 1,
                           prev[j-1] + (x != y)))
        prev = row
    return prev[-1]

def mutate_at(rng, s, pos):
    repl = rng.choice(tuple(x for x in ALPHABET if x != s[pos]))
    return s[:pos] + repl + s[pos+1:]

def frame(base_seed: int, family: int, base_target: int):
    rng = random.Random(base_seed * 19873 + family * 109 + 114)
    target_code = "".join(rng.choice(ALPHABET) for _ in range(12))
    changed_at = rng.randrange(2,10)
    query = mutate_at(rng,target_code,changed_at)
    rival_at = (changed_at+3) % 12
    rival_code = mutate_at(rng,query,rival_at)
    roles = [rng.randrange(4) for _ in range(4)]
    query_role = rng.randrange(4)
    codes = [None] * 4
    codes[base_target] = target_code
    rival = (base_target+2)%4
    if family in (1,2):
        codes[rival] = rival_code
        roles[base_target] = query_role
        roles[rival] = (query_role+1)%4 if family==1 else query_role
    for i in range(4):
        if codes[i] is None:
            while True:
                value = "".join(rng.choice(ALPHABET) for _ in range(12))
                if value not in codes and levenshtein(value,query)>=5:
                    codes[i]=value
                    break
    order = list(range(4))
    rng.shuffle(order)
    qdepth = (base_seed-RANGES[family][0])%4
    meta = Public(query,tuple(codes),tuple(roles),query_role,tuple(order),qdepth)
    distances = [levenshtein(query,x) for x in codes]
    min_tags = [i for i,d in enumerate(distances) if d==1]
    expected = {0:1,1:2,2:2}[family]
    need(len(min_tags)==expected and base_target in min_tags and
         (family==0 or rival in min_tags) and
         len(set(codes))==4 and
         query not in codes and
         all(len(v)==12 for v in codes) and
         sorted(order)==list(range(4)),
         "SOURCE_LEXICAL_IDENTIFIABILITY_INVALID")
    if family==1:
        need([t for t in min_tags if roles[t]==query_role]==[base_target],
             "PUBLIC_RELATION_WITNESS_INVALID")
    if family==2:
        need(all(roles[t]==query_role for t in min_tags),
             "PUBLIC_AMBIGUITY_NOT_PROVEN")
    return meta,base_target,rival

def case(seed,family):
    need(type(seed) is int and type(family) is int and
         family in range(3) and
         RANGES[family][0] <= seed <= RANGES[family][1],
         "SOURCE_OUTSIDE_FROZEN_COHORT")
    offset=seed-RANGES[family][0]
    if family==2:
        baseindex=offset//2
        base_seed=RANGES[family][0]+baseindex*2
        base_tag=(baseindex//4+family)%4
    else:
        base_seed=seed
        base_tag=(offset//4+family)%4
    public,t,rival=frame(base_seed,family,base_tag)
    truth=(rival if (family==2 and offset%2==1) else t)
    rng=random.Random(base_seed*701 + family*359 + 114)
    signs=[1.0 if rng.randrange(2) else -1.0 for _ in range(4)]
    pos=signs.copy()
    neg=signs.copy()
    pos[truth]=1.0
    neg[truth]=-1.0
    plus=tuple(pos[i] for i in public.observation_order)
    minus=tuple(neg[i] for i in public.observation_order)
    need(sum(x!=y for x,y in zip(plus,minus))==1,
         "COUNTERFACTUAL_ONLY_ONE_SIGN_MUST_CHANGE")
    return Offline(public,truth,seed,plus,minus)

def groups():
    result=tuple(tuple(case(seed,i) for seed in range(lo,hi+1))
                 for i,(lo,hi) in enumerate(RANGES))
    need(all(len(x)==48 for x in result) and
         len(set(x.case_id for group in result for x in group))==144,
         "COHORT_IDENTITY_DRIFT")
    for family,cohort in enumerate(result):
        if family<2:
            count=Counter((x.public.query_depth,x.true_tag) for x in cohort)
            need(len(count)==16 and all(count[(q,t)]==3 for q in range(4)
                                         for t in range(4)),
                 "SOURCE_DEPTH_TARGET_SHORTCUT")
        else:
            for i in range(0,48,2):
                a,b=cohort[i:i+2]
                need(a.public==b.public and
                     a.true_tag != b.true_tag and
                     (a.true_tag+2)%4 == b.true_tag and
                     a.case_id!=b.case_id,
                     "IRREDUCIBLE_TWIN_NOT_IDENTICAL_PUBLIC")
    return result

def nearest(meta):
    distances=[levenshtein(meta.requested_code,s) for s in meta.source_codes]
    minimum=min(distances)
    return tuple(i for i,d in enumerate(distances) if d==minimum),minimum

def certificate(meta):
    candidates,dist=nearest(meta)
    if dist>1:
        return None
    if len(candidates)==1:
        return candidates[0]
    witnessed=[tag for tag in candidates
               if meta.source_roles[tag]==meta.query_role]
    return witnessed[0] if len(witnessed)==1 else None

def forced_string(meta):
    return min(nearest(meta)[0])

def forced_relation(meta):
    chosen=certificate(meta)
    return chosen if chosen is not None else forced_string(meta)

def parent_learned(meta,trained):
    # The old parent model receives ONLY zero evidence placeholders;
    # true labels, source seeds and actual sign observations are excluded.
    p=f112.WCase(0,0,meta.source_codes,meta.requested_code,
                 (0.0,)*4,(0.0,)*4,meta.query_depth,meta.observation_order)
    index=trained.choose(p)
    return meta.observation_order[index]

def assess(cases, policy):
    details=[]
    for case in cases:
        selected=policy(case.public)
        need(selected is None or
             (type(selected) is int and 0<=selected<4),
             "FORBIDDEN_POLICY_OUTPUT")
        if selected is None:
            status="abstain"
        else:
            i=case.public.observation_order.index(selected)
            # Only one sign can be read once selection is irrevocably made.
            status=("correct" if case.positive_values[i]>0 and
                    case.negative_values[i]<0 else "wrong")
        details.append({"id":case.case_id,"status":status,"chosen_tag":selected,
                        "public_sha256":hashlib.sha256(json.dumps({
                          "query":case.public.requested_code,
                          "codes":case.public.source_codes,
                          "roles":case.public.source_roles,
                          "query_role":case.public.query_role,
                          "order":case.public.observation_order,
                          "depth":case.public.query_depth
                        },sort_keys=True).encode()).hexdigest(),
                        "true_tag_offline":case.true_tag})
    cnt=Counter(x["status"] for x in details)
    coverage=cnt["correct"]+cnt["wrong"]
    return {"total":len(details),"coverage":coverage,
            "correct":cnt["correct"],"wrong":cnt["wrong"],
            "abstained":cnt["abstain"],
            "selective_error_rate":(cnt["wrong"]/coverage if coverage else None),
            "utility_correct1_wrong4_abstain01":
               round(cnt["correct"]-4*cnt["wrong"]-0.1*cnt["abstain"],5),
            "cases":details}

def evaluate(head):
    need(isinstance(head,str) and SHA40.fullmatch(head) is not None,
         "SOURCE_COMMIT_INVALID")
    _,frozen_hash=freeze()
    data=groups()
    trained=f112.LearnedRelationAttention().train(f112.wing_cohorts()[0])
    need(trained.updates==100 and trained.parameters==6,
         "PARENT_TRAINING_DRIFT")
    arms={"certificate_abstain":certificate,
          "forced_lexical_tie":forced_string,
          "forced_public_role_or_tie":forced_relation,
          "unchanged_f112_six_weight_learned":
             lambda p:parent_learned(p,trained),
          "always_abstain":lambda p:None}
    blocks=[]
    for label,cases in zip(COHORTS,data):
        scores={name:assess(cases,fn) for name,fn in arms.items()}
        blocks.append({"name":label,"pairs":48,"policies":scores})
    cert=[b["policies"]["certificate_abstain"] for b in blocks]
    need([c["coverage"] for c in cert]==[48,48,0] and
         sum(c["wrong"] for c in cert)==0 and
         [c["abstained"] for c in cert]==[0,0,48],
         "CERTIFICATE_PUBLIC_SAFETY_FALSIFIED")
    need(all(b["policies"]["forced_public_role_or_tie"]["correct"]==
             (48 if i<2 else 24)
             for i,b in enumerate(blocks)),
         "TWIN_IDENTIFIABILITY_CONTROL_FALSIFIED")
    # Check all arms of the impossible-identifiability twins (including
    # learned) obey the precommitted 24/48 bound.
    for name,score in blocks[2]["policies"].items():
        if name!="always_abstain":
            need(score["correct"]<=24,"IMPOSSIBLE_TWIN_LABEL_LEAKAGE")
    return {
        "schema":SCHEMA,"source_sha":head,
        "f114_freeze_sha256":frozen_hash,
        "f113_parent_sha":"88924d2e73d694076a5aa45bcdec3e89b3f41dac",
        "cohorts":blocks,"public_pairs":144,"public_identical_unresolvable_twins":24,
        "trained_F114_parameters":0,"parent_learned_parameters":6,
        "parent_F112_train_examples":96,"parent_training_updates":100,
        "all_pairs_retained":True,
        "certificate_resolvable_covered":96,
        "certificate_unresolvable_abstained":48,
        "certificate_covered_wrong":0,
        "irresolvable_forced_correct":24,
        "public_selective_retrieval_screen_passed":True,
        "learned_superiority_claimed":False,
        "independent_scientific_acceptance":False,
        "protected_first_use_authorized":False,
        "optimizer_promotion_authorized":False,
        "accepted_ref_mutations":0,
        "new_scientific_originals":0,
        "codex_calls":0,"paid_model_calls":0,
        "external_controller_accessed":False,
        "MindPalace_written":False
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-ref",required=True)
    args=parser.parse_args()
    print(json.dumps(evaluate(args.source_ref),sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    main()
