"""New source A, born AFTER the F124-BO learner and frozen protocol.

Original 12 public FIT cases only. Private odd modular transformation
composed with XOR mask, 48 public support points (six noisy FIT/CHECK bits),
causally correct graph and matched false graph. No learner import.
"""
from __future__ import annotations
import copy
import hashlib
import random

SALT=b"F124BO-MODULAR-RELATIONS-A-NEW-ORIGINAL-20261018"
FIT=range(920000,920012)
RESERVED=range(920100,920228)


def need(ok,why):
    if not ok:raise ValueError("F124BO_SOURCE_A_"+why)


def bits(x):
    return [(x>>i)&1 for i in range(16)]


def integer(x):
    return sum(bit<<i for i,bit in enumerate(x))


def forward(x,key):
    a,b,c=key
    return ((a*x+b)&65535)^c


def inverse(y,key):
    a,b,c=key
    return ((((y^c)-b)*pow(a,-1,65536))&65535)


def true_path(graph,key):
    states=[(graph["start"],None)]
    for role in graph["roles"]:
        follows=[]
        for node,last in states:
            for e in graph["edges"]:
                if e["from"]!=node or e["role"]!=role:continue
                source=inverse(integer(e["src_bits"]),key)
                if last is None or last==source:
                    follows.append((e["to"],integer(e["dst_bits"])))
        states=follows
    return sum(node==graph["target"] for node,last in states)


def make(seed):
    need(type(seed) is int and seed in FIT,
         "UNKNOWN_OR_PROTECTED_OR_CONSUMED_ID")
    r=random.Random(int.from_bytes(hashlib.sha256(
        SALT+b"/task/"+str(seed).encode()).digest(),"big"))
    key=(r.randrange(32768)*2+1,r.randrange(65536),r.randrange(65536))
    xs=r.sample(range(65536),48)
    corrupt=set(r.sample(range(48),6))
    public=[(x,forward(x,key)^(1 if i in corrupt else 0))
            for i,x in enumerate(xs)]
    length=7+((seed-FIT.start)%4)
    task=hashlib.sha256(SALT+b"/role/"+str(seed).encode()).hexdigest()[:12]
    roles=[f"rel_task_{task}:new{j}" for j in range(length)]
    keys=r.sample(range(65536),length+1)
    path=[{"from":f"node{j}","to":f"node{j+1}","role":roles[j],
           "src_bits":bits(forward(keys[j],key)),
           "dst_bits":bits(keys[j+1])} for j in range(length)]
    cut=2+(seed-FIT.start)%(length-3)
    distractors=[]
    for j in range(7):
        bad=r.randrange(65536)
        if j==0:
            while bad==keys[cut]:bad=r.randrange(65536)
        distractors.append(
          {"from":f"detached{j}","to":f"terminal{j}",
           "role":roles[(cut+j)%length],
           "src_bits":bits(forward(bad,key)),
           "dst_bits":bits(r.randrange(65536))})
    positive=path+distractors
    negative=copy.deepcopy(positive)
    negative[cut]["src_bits"],negative[length]["src_bits"]=(
        negative[length]["src_bits"],negative[cut]["src_bits"])
    r.shuffle(positive)
    r.shuffle(negative)
    demos=[{"input_bits":bits(x),"output_bits":bits(y)}
           for x,y in public[:24]]
    common={"start":"node0","target":f"node{length}",
            "roles":roles,"demos":demos}
    yes={**common,"edges":positive}
    no={**common,"edges":negative}
    tokens=lambda g:sorted(tuple(e[key]) for e in g["edges"]
                           for key in ("src_bits","dst_bits"))
    structure=lambda g:sorted((e["from"],e["to"],e["role"])
                           for e in g["edges"])
    need(true_path(yes,key)==1 and true_path(no,key)==0,
         "INDEPENDENT_CAUSAL_LABELS")
    need(tokens(yes)==tokens(no) and structure(yes)==structure(no)
         and len(positive)>=14 and len(corrupt)==6,
         "MATCHED_SOURCE_NEGATIVE")
    return {"FIT":public[:40],"CHECK":public[40:],
            "positive":yes,"hard_negative":no},{
        "private_relation_key":key,"private_corruption_ids":sorted(corrupt),
        "private_true_positive_count":1,"private_true_negative_count":0,
        "private_source_name":"MODULAR_ODD_XOR",
        "source_case":seed}
