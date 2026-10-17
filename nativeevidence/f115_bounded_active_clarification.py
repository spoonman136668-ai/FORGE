"""F115: one-shot paid public relationship query versus safe abstention.

Only PUBLIC synthetic experimental data; no original research, learned active
policy, independent signing, GPT autonomy, external controller or Codex.
Preregistered in a separate first commit before this code or test access.
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

import f114_partial_relation_abstention as parent

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT/"reference/research-intake/f115-bounded-active-clarification-freeze.json"
FREEZE_BLOB = "05b0848e03d41a6d341b0009a4262c2d02f19790"
PARENT_BLOB = "3d3c47748b8f146419e688f49067b06466749319"
PARENT_PREREG_BLOB = "c2a4587aae1e1a0f05089d2c9e01fbfdc3f90002"
PARENT_HEAD = "8a2be937cad270b89cedd9672772aca345f1cbb5"
RANGES = ((70000,70047),(70100,70147),(70200,70247),(70300,70347))
NAMES = ("W115-U","W115-R","W115-S","W115-N")
SCHEMA = "forge.autonomy.f115.bounded-one-query-relational-clarification-public.v1"
SHA40 = re.compile("^[0-9a-f]{40}$")
ROLE_LINK = "public-two-hop-source-link"
class Invalid(ValueError):pass
def need(flag,reason):
    if not flag:raise Invalid("F115_"+reason)
def gitblob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def readbytes(path):
    return Path(path).read_bytes().replace(b"\r\n",b"\n")
def freeze():
    raw=readbytes(FREEZE)
    need(gitblob(raw)==FREEZE_BLOB and
         gitblob(readbytes(ROOT/"nativeevidence/f114_partial_relation_abstention.py"))
         ==PARENT_BLOB and
         gitblob(readbytes(ROOT/"reference/research-intake/f114-partial-relation-abstention-freeze.json"))
         ==PARENT_PREREG_BLOB, "FROZEN_SOURCE_OR_PREREG_DRIFT")
    parent.freeze()
    cfg=json.loads(raw)
    need(cfg["schema"]=="forge.autonomy.f115.frozen-active-relational-clarification-public.v1" and
         cfg["parent"]["f114_exact_head"]==PARENT_HEAD and
         cfg["parent"]["f114_python_git_blob"]==PARENT_BLOB and
         cfg["parent"]["f114_prereg_git_blob"]==PARENT_PREREG_BLOB and
         [c["seeds"] for c in cfg["cohort_contract"]]==
         [[70000,70047],[70100,70147],[70200,70247],[70300,70347]] and
         [c["pairs"] for c in cfg["cohort_contract"]]==[48]*4,
         "FROZEN_COHORT_OR_PARENT_IDENTITY")
    p=cfg["protocol"]
    need(p["utility"]=={"correct":1,"wrong":-4,
         "abstain":-0.1,"charged_relation_query":-0.25} and
         p["one_charged_relation_ledger_query_max"] is True and
         p["no_query_on_U_or_R_for_conditional_policy"] is True and
         p["query_on_S_and_N_when_initial_certificate_abstains"] is True and
         cfg["precommitted_evaluation"]["selective_criterion"].startswith(
         "Conditional active policy retrieves 48/48 U"),
         "FROZEN_SELECTION_OR_COST_CHANGED")
    need(all(x is True for x in cfg["authority"].values()),
         "AUTHORITY_BOUNDARY_CHANGED")
    return cfg,hashlib.sha256(raw).hexdigest()

@dataclass(frozen=True)
class RelationLink:
    source_code:str
    relation:str
    requested_code:str

@dataclass(frozen=True)
class World:
    public:parent.Public
    # World truth is for the offline evaluator and synthetic world constructor
    # only. It is NOT passed to any selection/query policy.
    true_tag:int
    case_id:int
    positive_values:tuple[float,...]
    negative_values:tuple[float,...]
    ledger_links:tuple[RelationLink,...]

class Port:
    """A single prepaid on-demand observation of public synthetic graph edges.

    Query function is handed to the actor; all result signs and target labels
    remain in the evaluator's World object, never returned by this API.
    """
    def __init__(self,links):
        self._links=tuple(links)
        self.calls=0
    def read(self):
        need(self.calls==0,"ADDITIONAL_RELATION_QUERY_DENIED")
        self.calls+=1
        return self._links

def case(seed,group):
    need(type(seed) is int and type(group) is int and 0<=group<4 and
         RANGES[group][0]<=seed<=RANGES[group][1],"SOURCE_OUTSIDE_FROZEN_COHORT")
    offset=seed-RANGES[group][0]
    if group<2:
        base_seed=seed
        tag=(offset//4+group)%4
        shape=group
    else:
        base_seed=RANGES[group][0]+2*(offset//2)
        tag=(offset//2+group)%4
        shape=2
    # The F114 SOURCE-GRAMMAR helper is reused with completely new F115 IDs
    # and never uses F114 test cases. No prior evaluation result enters policy.
    public,base_tag,rival=parent.frame(base_seed,shape,tag)
    # Preserve the same public q/tag balancing in U and R.
    public=parent.Public(public.requested_code,public.source_codes,
        public.source_roles,public.query_role,public.observation_order,
        offset%4 if group<2 else (offset//2)%4)
    truth=(rival if group>=2 and offset%2 else base_tag)
    rng=random.Random(base_seed*173 + group*1009 + 115)
    signs=[1.0 if rng.randrange(2) else -1.0 for _ in range(4)]
    plus=signs.copy()
    minus=signs.copy()
    plus[truth]=1.0
    minus[truth]=-1.0
    positive=tuple(plus[t] for t in public.observation_order)
    negative=tuple(minus[t] for t in public.observation_order)
    # This is an EXTRA public synthetic relation observation, not a signature
    # from an independent source. It is constructed from this world's graph
    # before reading any target sign. It is only exposed AFTER one paid call.
    links=(
       (RelationLink(public.source_codes[truth],ROLE_LINK,public.requested_code),)
       if group==2 else ()
    )
    need(sum(x!=y for x,y in zip(positive,negative))==1 and
         truth in range(4),"INVALID_COUNTERFACTUAL_WORLD")
    return World(public,truth,seed,positive,negative,links)

def cohorts():
    blocks=tuple(tuple(case(seed,g) for seed in range(lo,hi+1))
                 for g,(lo,hi) in enumerate(RANGES))
    need([len(x) for x in blocks]==[48]*4 and
         len({x.case_id for group in blocks for x in group})==192,
         "SOURCE_IDENTITY_REUSE")
    for i,block in enumerate(blocks):
        if i<2:
            counts=Counter((x.public.query_depth,x.true_tag) for x in block)
            need(len(counts)==16 and
                 all(counts[(q,t)]==3 for q in range(4) for t in range(4)),
                 "PUBLIC_SHORTCUT_REINTRODUCED")
            need(all(parent.certificate(w.public)==w.true_tag for w in block),
                 "FREE_PUBLIC_CERTIFICATE_BROKEN")
        else:
            for j in range(0,48,2):
                a,b=block[j:j+2]
                need(a.public==b.public and
                     b.true_tag==(a.true_tag+2)%4 and
                     parent.certificate(a.public) is None and
                     (len(a.ledger_links)==len(b.ledger_links)==1 if i==2
                      else len(a.ledger_links)==len(b.ledger_links)==0),
                     "TWIN_OR_CHARGED_EVIDENCE_CONFOUNDED")
                if i==2:
                    need(a.ledger_links[0].source_code==a.public.source_codes[a.true_tag] and
                         b.ledger_links[0].source_code==b.public.source_codes[b.true_tag] and
                         a.ledger_links!=b.ledger_links,
                         "ACTIVE_RELATION_NOT_WORLD_SPECIFIC")
    return blocks

def choose_after_ledger(meta,links):
    near,distance=parent.nearest(meta)
    if distance>1:
        return None
    # Verify public schema and anchor against the pre-query source pool.
    usable=set()
    for link in links:
        if not isinstance(link,RelationLink):
            return None
        if (link.relation!=ROLE_LINK or
            link.requested_code!=meta.requested_code):
            return None
        for tag in near:
            if (meta.source_codes[tag]==link.source_code and
                meta.source_roles[tag]==meta.query_role):
                usable.add(tag)
    return next(iter(usable)) if len(usable)==1 else None

def conditional(meta,read):
    free=parent.certificate(meta)
    if free is not None:
        return free
    return choose_after_ledger(meta,read())

def always_query(meta,read):
    extra=read()
    free=parent.certificate(meta)
    return free if free is not None else choose_after_ledger(meta,extra)

def no_query(meta,read):
    return parent.certificate(meta)

def forced(meta,read):
    return parent.forced_relation(meta)

def always_abstain(meta,read):
    return None

ARMS={
    "no_query_certificate":no_query,
    "conditional_one_query":conditional,
    "always_query":always_query,
    "forced_public_role_tie":forced,
    "always_abstain":always_abstain,
}

def assess(cases,choose):
    rows=[]
    for world in cases:
        port=Port(world.ledger_links)
        # Actor sees only metadata and port.read. Offline label is inaccessible.
        target=choose(world.public,port.read)
        need((target is None or
              (type(target) is int and 0<=target<4)) and port.calls<=1,
              "UNAUTHORIZED_SOURCE_OR_QUERY")
        if target is None:
            result="abstain"
        else:
            idx=world.public.observation_order.index(target)
            result=("correct" if world.positive_values[idx]>0 and
                    world.negative_values[idx]<0 else "wrong")
        public_hash=hashlib.sha256(json.dumps({
          "requested_code":world.public.requested_code,
          "source_codes":world.public.source_codes,
          "source_roles":world.public.source_roles,
          "query_role":world.public.query_role,
          "query_depth":world.public.query_depth,
          "observation_order":world.public.observation_order,
        },sort_keys=True).encode()).hexdigest()
        rows.append(dict(case_id=world.case_id,public_sha256=public_hash,
                         true_tag_OFFLINE_ONLY=world.true_tag,
                         selected=target,outcome=result,
                         relation_queries=port.calls))
    totals=Counter(r["outcome"] for r in rows)
    queries=sum(r["relation_queries"] for r in rows)
    c,w,a=totals["correct"],totals["wrong"],totals["abstain"]
    utility=round(c-4*w-.1*a-.25*queries,6)
    return dict(total=len(rows),correct=c,wrong=w,abstained=a,
                coverage=c+w,queries=queries,utility=utility,
                covered_error=(w/(c+w) if c+w else None),rows=rows)

def evaluate(head):
    need(type(head) is str and SHA40.fullmatch(head) is not None,
         "CURRENT_SOURCE_HEAD_NOT_PINNED")
    _,digest=freeze()
    data=cohorts()
    results=[]
    for group,cases in zip(NAMES,data):
        results.append(dict(cohort=group,pairs=48,
              policies={name:assess(cases,fn) for name,fn in ARMS.items()}))
    arms={name:[r["policies"][name] for r in results] for name in ARMS}
    conditional_rows=arms["conditional_one_query"]
    expected_correct=[48,48,48,0]
    expected_abstain=[0,0,0,48]
    need([r["correct"] for r in conditional_rows]==expected_correct and
         [r["wrong"] for r in conditional_rows]==[0]*4 and
         [r["abstained"] for r in conditional_rows]==expected_abstain and
         [r["queries"] for r in conditional_rows]==[0,0,48,48],
         "SELECTIVE_CHARGED_CERTIFICATE_FALSIFIED")
    need([r["queries"] for r in arms["always_query"]]==[48]*4 and
         [r["correct"] for r in arms["no_query_certificate"]]==[48,48,0,0] and
         [r["abstained"] for r in arms["no_query_certificate"]]==[0,0,48,48] and
         [r["correct"] for r in arms["forced_public_role_tie"]]==[48,48,24,24],
         "CONTROL_SOURCE_OR_TWIN_SYMMETRY_INVALID")
    totals={name:dict(correct=sum(r["correct"] for r in items),
                wrong=sum(r["wrong"] for r in items),
                abstained=sum(r["abstained"] for r in items),
                queries=sum(r["queries"] for r in items),
                utility=round(sum(r["utility"] for r in items),6))
            for name,items in arms.items()}
    need(totals["conditional_one_query"]["utility"] >
         totals["no_query_certificate"]["utility"] and
         totals["conditional_one_query"]["utility"] >
         totals["always_query"]["utility"],"FROZEN_NET_UTILITY_NEGATIVE")
    return dict(schema=SCHEMA,source_sha=head,
       prereg_sha256=digest,parent_F114_head=PARENT_HEAD,
       scientific_classification="PUBLIC_COSTED_ONE_QUERY_FEASIBILITY_NOT_LEARNED_AUTONOMY",
       new_public_pairs=192,identical_prior_public_twin_pairs=48,
       query_cost_per_call=0.25,utility_correct=1,utility_wrong=-4,
       utility_abstain=-0.1,
       all_frozen_cases_retained=True,
       no_F115_training=True,thresholds_retuned=False,
       outcome_by_cohort=results,totals_by_arm=totals,
       public_selective_information_screen_passed=True,
       learned_or_general_scientific_superiority=False,
       original_scientific_first_use=False,independently_scientifically_accepted=False,
       accepted_ref_mutations=0,optimizer_promotions=0,
       native_original_dispatches=0,codex_calls=0,paid_inference_calls=0,
       CKB_contacted=False,MindPalace_written=False)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-ref",required=True)
    a=p.parse_args()
    print(json.dumps(evaluate(a.source_ref),sort_keys=True,separators=(",",":")))
if __name__=="__main__":
    main()
