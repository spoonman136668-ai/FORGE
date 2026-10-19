"""T16 Mass: public-only learned cross-role structure, new source family.
Three related but undisclosed source-native nibble permutations:
P an unknown 16! bijection; Q=P inverse; R=P composed with P.
TRAIN 24 disjoint public single-role tasks with sparse witnesses.
OPEN previously absent relation compositions 3/4 steps, sparse/noisy FIT.
Do not give true P/Q/R or relation tags to learner/controls: only role
symbols, TRAIN public observations and OPEN public words are available.
"""
import random
TRAIN=tuple(range(-63023,-62999))
OPEN=tuple(range(-63107,-63099))
def compose(p,q):
    return tuple(q[p[i]] for i in range(16))
def birth(seed,m):
    assert seed in TRAIN or seed in OPEN,"T16_NOT_PREREGISTERED"
    parent=random.Random(161623).sample(range(16),16)
    inv=[0]*16
    for i,v in enumerate(parent):inv[v]=i
    ops={"P":tuple(parent),"Q":tuple(inv),
         "R":compose(parent,parent)}
    rng=random.Random(166367+abs(seed)*7331)
    word=("PQR"[abs(seed)%3],) if seed in TRAIN else (
        ("P","R","Q"),("R","Q","P"),("P","Q","R","Q"),("R","P","Q","P"))[abs(seed)%4]
    relation=tuple(range(16))
    for r in word:relation=compose(relation,ops[r])
    xs=rng.sample(range(65536),40)
    ys=[m.forward(x,m.pack(relation)) for x in xs]
    # Two corruptions in FIT are public and identical for all controls.
    corrupt=set(rng.sample(range(16),2))
    fit=tuple((xs[i],ys[i]^(1 if i in corrupt else 0)) for i in range(16))
    check=tuple(zip(xs[16:20],ys[16:20]))
    # TRAIN sparse single-role first-round public observations; OPEN two
    # composition witnesses, both equally accessible to all algorithms.
    witness=tuple((x,m.apply_sbox(x,relation)) for x in xs[:3 if seed in TRAIN else 2])
    held=tuple(zip(xs[20:36],ys[20:36]))
    return word,fit,check,witness,held
