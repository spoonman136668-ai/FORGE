"""Independently born F124-BN B: nonlinear reversible mixed word grammar.

Separate source-only algorithm and original Git birth after frozen mechanism.
The target 128-case replication remains inaccessible and unconstructed.
"""
from __future__ import annotations
import copy,hashlib,random
FIT=range(917000,917012)
HOLDOUT=range(917100,917228)
SALT=b"F124BN-NONLINEAR-COUPLED-WORD-SOURCE-B-v1"


def need(ok,k):
    if not ok: raise ValueError("BN_B_"+k)


def bits(x):
    return [(x>>j)&1 for j in range(16)]


def intval(a):
    return sum(v<<i for i,v in enumerate(a))


def rot(x,n):
    return ((x<<n)|(x>>(16-n)))&65535


def unrot(x,n):
    return ((x>>n)|(x<<(16-n)))&65535


def forward(x,key):
    for mul,add,shift,mask in key:
        x=rot((x*mul+add)&65535,shift)^mask
    return x


def inverse(y,key):
    for mul,add,shift,mask in reversed(key):
        y=((unrot(y^mask,shift)-add)*pow(mul,-1,65536))&65535
    return y


def routes(graph,key):
    active=[(graph["start"],None)]
    for role in graph["roles"]:
        following=[]
        for node,prev in active:
            for edge in graph["edges"]:
                if edge["from"]!=node or edge["role"]!=role:continue
                decoded=inverse(intval(edge["src_bits"]),key)
                if prev is None or decoded==prev:
                    following.append((edge["to"],intval(edge["dst_bits"])))
        active=following
    return sum(node==graph["target"] for node,c in active)


def make(case):
    need(type(case) is int and case in FIT,"DENY_HELDOUT_OR_CONSUMED")
    rng=random.Random(int.from_bytes(hashlib.sha256(
        SALT+b"/"+str(case).encode()).digest(),"big"))
    key=tuple((rng.randrange(32768)*2+1,rng.randrange(65536),
               rng.randint(1,15),rng.randrange(65536)) for _ in range(2))
    xs=rng.sample(range(65536),48)
    corrupt=set(rng.sample(range(48),6))
    public=[(x,forward(x,key)^(1 if i in corrupt else 0))
            for i,x in enumerate(xs)]
    depth=7+(case-FIT.start)%4
    nonce=hashlib.sha256(SALT+b"/role/"+str(case).encode()).hexdigest()[:12]
    roles=[f"rel_task_{nonce}:step{j}" for j in range(depth)]
    carries=rng.sample(range(65536),depth+1)
    chain=[{"from":f"x{j}","to":f"x{j+1}","role":roles[j],
            "src_bits":bits(forward(carries[j],key)),
            "dst_bits":bits(carries[j+1])} for j in range(depth)]
    cut=2+(case-FIT.start)%(depth-3)
    side=[]
    for j in range(6):
        distract=rng.randrange(65536)
        if j==0:
            while distract==carries[cut]:
                distract=rng.randrange(65536)
        side.append({"from":f"side{j}","to":f"sink{j}",
                     "role":roles[(cut+j)%depth],
                     "src_bits":bits(forward(distract,key)),
                     "dst_bits":bits(rng.randrange(65536))})
    positive=chain+side
    negative=copy.deepcopy(positive)
    negative[cut]["src_bits"],negative[depth]["src_bits"]=(
        negative[depth]["src_bits"],negative[cut]["src_bits"])
    rng.shuffle(positive)
    rng.shuffle(negative)
    demos=[{"input_bits":bits(x),"output_bits":bits(y)}
           for x,y in public[:24]]
    main={"start":"x0","target":f"x{depth}","roles":roles,"demos":demos}
    yes={**main,"edges":positive}
    no={**main,"edges":negative}
    tokens=lambda g:sorted(tuple(e[k]) for e in g["edges"] for k in ("src_bits","dst_bits"))
    top=lambda g:sorted((e["from"],e["to"],e["role"]) for e in g["edges"])
    need(routes(yes,key)==1 and routes(no,key)==0,"SYMBOLIC_CAUSAL_TRUTH")
    need(tokens(yes)==tokens(no) and top(yes)==top(no) and len(positive)>=13,
         "MATCHED_NEGATIVE")
    return {"FIT":public[:40],"CHECK":public[40:],"positive":yes,
            "hard_negative":no},{"key_private":key,"truth_positive":1,
            "truth_negative":0,"corrupted_private":tuple(sorted(corrupt)),
            "case_private":case}
