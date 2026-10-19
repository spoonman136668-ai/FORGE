"""F124-CH E/F INTERNALLY authored source-only causal laws.

Source code and first-use seeds originate in a separate GitHub Actions job
BEFORE evaluation. No imports of CB/CC or any research learned arm.
The two families deliberately differ from the hand-constructed prior
4-nibble fixed-permutation and optional-XOR learned hypothesis family.
This is NOT externally originated or independently reproduced science.
"""
from __future__ import annotations
import copy
import hashlib
import json
import random

FAMILIES={"E":928000,"F":929000}
DEV_COUNT=12
FIT_COUNT=40
CHECK_COUNT=8
CORRUPTED_FIT={1,5,12,19,24,35}


def need(ok,reason):
    if not ok:raise ValueError("F124CH_SOURCE_"+reason)


def rol(x,shift,bits):
    mask=(1<<bits)-1
    return ((x<<shift)|(x>>(bits-shift)))&mask


def split4(x):
    need(type(x) is int and 0<=x<65536,"PUBLIC_16BIT_INPUT")
    return [(x>>(4*j))&15 for j in range(4)]


def join4(x):
    need(len(x)==4 and all(0<=v<=15 for v in x),"OUTPUT_16BIT_NIBBLE")
    return sum(v<<(4*j) for j,v in enumerate(x))


def E_forward(x,param):
    a,b,c,context=split4(x)
    k0,k1,k2,salt=param
    if (context^salt)&1:a,b=b,a
    u=(a+((5*c+3*context+k0)&15))&15
    v=b^rol(u,1,4)^k1
    w=(c+rol(v,1,4)+(u^context)+k2)&15
    return join4((u,v,w,context))


def E_inverse(y,param):
    u,v,w,context=split4(y)
    k0,k1,k2,salt=param
    c=(w-rol(v,1,4)-(u^context)-k2)&15
    b=v^rol(u,1,4)^k1
    a=(u-((5*c+3*context+k0)&15))&15
    if (context^salt)&1:a,b=b,a
    return join4((a,b,c,context))


def nonlinear(x,key):
    return ((x*x)^rol(x,3,8)^key)&255


def F_forward(x,param):
    need(type(x) is int and 0<=x<65536,"PUBLIC_16BIT_INPUT")
    k0,k1,k2,k3=param
    l=x&255;r=(x>>8)&255
    branch=7 if ((l^k0)&1) else 1
    r1=(r+rol(l,3,8)+nonlinear(l,k1)+branch)&255
    l1=l^((rol(r1,2,8)+nonlinear(r1,k2))&255)
    r2=r1^nonlinear(l1,k3)
    l2=(l1+rol(r2,3,8)+nonlinear(r2,k0))&255
    return l2|(r2<<8)


def F_inverse(y,param):
    need(type(y) is int and 0<=y<65536,"PUBLIC_16BIT_INPUT")
    k0,k1,k2,k3=param
    l2=y&255;r2=y>>8
    l1=(l2-rol(r2,3,8)-nonlinear(r2,k0))&255
    r1=r2^nonlinear(l1,k3)
    l=l1^((rol(r1,2,8)+nonlinear(r1,k2))&255)
    branch=7 if ((l^k0)&1) else 1
    r=(r1-rol(l,3,8)-nonlinear(l,k1)-branch)&255
    return l|(r<<8)


def forward(family,value,param):
    need(family in FAMILIES,"UNISSUED_SOURCE_FAMILY")
    return E_forward(value,param) if family=="E" else F_forward(value,param)


def inverse(family,value,param):
    need(family in FAMILIES,"UNISSUED_SOURCE_FAMILY")
    return E_inverse(value,param) if family=="E" else F_inverse(value,param)


def bits(x):
    return [(x>>i)&1 for i in range(16)]


def integer(v):
    need(type(v) is list and len(v)==16
         and all(type(x) is int and x in (0,1) for x in v),
         "SOURCE_GRAPH_16_BITS")
    return sum(x<<i for i,x in enumerate(v))


def truth(graph,family,param):
    node=graph["start"]
    carried=None
    for role in graph["roles"]:
        options=[edge for edge in graph["edges"]
                 if edge["from"]==node and edge["role"]==role]
        if len(options)!=1:return False
        edge=options[0]
        src=inverse(family,integer(edge["src_bits"]),param)
        if carried is not None and carried!=src:return False
        carried=integer(edge["dst_bits"])
        node=edge["to"]
    return node==graph["target"]


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":")).encode()


def task(family,ordinal,seed):
    need(family in FAMILIES and type(ordinal) is int
         and 0<=ordinal<DEV_COUNT
         and type(seed) is int and seed>0,"EXACT_NEW_SOURCE_BIRTH")
    rng=random.Random(seed)
    param=[rng.randrange(16 if family=="E" else 256) for _ in range(4)]
    xs=rng.sample(range(65536),48)
    public=[(x,forward(family,x,param)^(1 if j in CORRUPTED_FIT else 0))
            for j,x in enumerate(xs)]
    hops=8+(ordinal%2)
    state=rng.sample(range(65536),hops+1)
    tag=hashlib.sha256(canonical([family,ordinal,seed])).hexdigest()[:12]
    roles=[f"causal_{tag}_step_{j}" for j in range(hops)]
    chain=[{"from":f"n{j}","to":f"n{j+1}","role":roles[j],
            "src_bits":bits(forward(family,state[j],param)),
            "dst_bits":bits(state[j+1])} for j in range(hops)]
    others=[]
    for j in range(9):
        v=rng.randrange(65536)
        if j==0:
            need(v!=state[3],"SOURCE_NO_POST_FIRSTUSE_RESEED_ALLOWED")
        others.append({
            "from":f"off{j}","to":f"dead{j}",
            "role":roles[(3+j)%hops],
            "src_bits":bits(forward(family,v,param)),
            "dst_bits":bits(rng.randrange(65536))})
    positive_edges=chain+others
    negative_edges=copy.deepcopy(positive_edges)
    negative_edges[3]["src_bits"],negative_edges[hops]["src_bits"]=(
        negative_edges[hops]["src_bits"],negative_edges[3]["src_bits"])
    rng.shuffle(positive_edges)
    rng.shuffle(negative_edges)
    demos=[{"input_bits":bits(x),"output_bits":bits(y)}
           for x,y in public[:24]]
    graph_base={"start":"n0","target":f"n{hops}",
                "roles":roles,"demos":demos}
    positive={**graph_base,"edges":positive_edges}
    negative={**graph_base,"edges":negative_edges}
    topology=lambda g:sorted((e["from"],e["to"],e["role"])
                              for e in g["edges"])
    inventory=lambda g:sorted(tuple(e[key])
                               for e in g["edges"]
                               for key in ("src_bits","dst_bits"))
    need(truth(positive,family,param) is True
         and truth(negative,family,param) is False,
         "SYMBOLIC_POSITIVE_AND_HARD_NEGATIVE")
    need(topology(positive)==topology(negative)
         and inventory(positive)==inventory(negative),
         "HARD_NEGATIVE_TOPOLOGY_AND_TOKEN_INVENTORY")
    need(len(set(xs))==48
         and len(public)==48 and
         len(public[:40])==40 and len(public[40:])==8,
         "FROZEN_PUBLIC_40_PLUS_8")
    scientific_id=FAMILIES[family]+ordinal
    public_task={
        "task_id":scientific_id,
        "FIT":public[:40],
        "CHECK":public[40:],
        "positive":positive,
        "hard_negative":negative
    }
    return {
        "schema":"mass.f124ch.one-internal-prospective-causal-source.v1",
        "family_source_provenance_only":family,
        "task_identity":scientific_id,
        "birth_seed":str(seed),
        "private_source_param":param,
        "symbolic_ground_truth":{"positive":True,"hard_negative":False},
        "public_task":public_task,
        "public_task_sha256":hashlib.sha256(canonical(public_task)).hexdigest(),
        "internally_authored_not_external":True,
        "replication_cohort_opened":False,
        "prior_924_925_926_927_source_reused":False
    }


if __name__=="__main__":
    raise SystemExit("F124CH_SOURCE_ONLY_NO_LEARNER_IMPORT_OR_DIRECT_EXECUTION")
