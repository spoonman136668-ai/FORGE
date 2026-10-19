"""F124-BN v2 independently born A: double triangular reversible GF2.

Never imports a predictor; immutable original birth after learned mechanism.
Only reserved 12 development tasks are constructible, not 128 holdouts.
"""
from __future__ import annotations
import copy,hashlib,random
FIT=range(918000,918012)
HOLDOUT=range(918100,918228)
SALT=b"F124BN-V2-TRIANGULAR-DOUBLE-PASS-SOURCE-A-v1"


def need(ok,k):
    if not ok:raise ValueError("BN_A_"+k)


def bits(x):
    return [(x>>j)&1 for j in range(16)]


def intval(arr):
    return sum(v<<j for j,v in enumerate(arr))


def forward(x,key):
    operations,bias=key
    for dst,src in operations:
        x^=((x>>src)&1)<<dst
    return x^bias


def inverse(y,key):
    operations,bias=key
    x=y^bias
    for dst,src in reversed(operations):
        x^=((x>>src)&1)<<dst
    return x


def truth(graph,key):
    active=[(graph["start"],None)]
    for role in graph["roles"]:
        next_states=[]
        for node,carry in active:
            for edge in graph["edges"]:
                if edge["from"]==node and edge["role"]==role:
                    mapped=inverse(intval(edge["src_bits"]),key)
                    if carry is None or mapped==carry:
                        next_states.append((edge["to"],intval(edge["dst_bits"])))
        active=next_states
    return sum(node==graph["target"] for node,carry in active)


def make(case):
    need(type(case) is int and case in FIT,"PROTECTED_OR_UNKNOWN_CASE")
    rng=random.Random(int.from_bytes(hashlib.sha256(
        SALT+b"/"+str(case).encode()).digest(),"big"))
    operations=[]
    # Two independent reversible triangular sweeps, unlike the v1 source.
    for dst in range(1,16):
        operations.append((dst,rng.randrange(dst)))
    for dst in range(14,-1,-1):
        operations.append((dst,rng.randrange(dst+1,16)))
    key=(tuple(operations),rng.randrange(65536))
    xs=rng.sample(range(65536),48)
    flip=set(rng.sample(range(48),6))
    public=[(x,forward(x,key)^(1 if i in flip else 0))
            for i,x in enumerate(xs)]
    d=7+(case-FIT.start)%4
    nonce=hashlib.sha256(SALT+b"/nonce/"+str(case).encode()).hexdigest()[:12]
    roles=[f"rel_task_{nonce}:step{j}" for j in range(d)]
    carry=rng.sample(range(65536),d+1)
    path=[{"from":f"p{j}","to":f"p{j+1}","role":roles[j],
           "src_bits":bits(forward(carry[j],key)),
           "dst_bits":bits(carry[j+1])} for j in range(d)]
    cut=2+(case-FIT.start)%(d-3)
    side=[]
    for j in range(6):
        decoy=rng.randrange(65536)
        if j==0:
            while decoy==carry[cut]:
                decoy=rng.randrange(65536)
        side.append({"from":f"detached{j}","to":f"terminal{j}",
                     "role":roles[(cut+j)%d],
                     "src_bits":bits(forward(decoy,key)),
                     "dst_bits":bits(rng.randrange(65536))})
    pos=path+side
    neg=copy.deepcopy(pos)
    neg[cut]["src_bits"],neg[d]["src_bits"]=neg[d]["src_bits"],neg[cut]["src_bits"]
    rng.shuffle(pos)
    rng.shuffle(neg)
    demo=[{"input_bits":bits(x),"output_bits":bits(y)}
          for x,y in public[:24]]
    basis={"start":"p0","target":f"p{d}","roles":roles,"demos":demo}
    yes={**basis,"edges":pos}
    no={**basis,"edges":neg}
    inventory=lambda graph:sorted(tuple(e[t]) for e in graph["edges"] for t in ("src_bits","dst_bits"))
    topology=lambda graph:sorted((e["from"],e["to"],e["role"]) for e in graph["edges"])
    need(truth(yes,key)==1 and truth(no,key)==0,"INDEPENDENT_TRUTH")
    need(inventory(yes)==inventory(no) and topology(yes)==topology(no)
         and len(pos)>=13 and len(flip)==6,"MATCHED_HARD_NEGATIVE")
    return {"FIT":public[:40],"CHECK":public[40:],
            "positive":yes,"hard_negative":no}, {
            "source_key_private":key,"truth_positive":1,"truth_negative":0,
            "noise_indices_private":tuple(sorted(flip)),"source_case":case}
