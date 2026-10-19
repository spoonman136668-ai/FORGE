"""T15 Mass prospective source-only 3-role compositional transfer grammar.
TRAIN shows only one elementary role per task, OPEN demands ordered
three/four-role compositions not seen during TRAIN. Held outputs are scorer-only.
Import does not originate or consume source identities.
"""
import random
TRAIN=tuple(range(-53023,-52999))
OPEN=tuple(range(-53107,-53099))
def compose(p,q):
    return tuple(q[p[i]] for i in range(16))
def birth(seed,m):
    assert seed in TRAIN or seed in OPEN,"UNREGISTERED_T15_SEED"
    # Unknown source semantics: only public witnesses below are sent to model.
    seeded=random.Random(151593)
    P=tuple(seeded.sample(range(16),16))
    Q=tuple(seeded.sample(range(16),16))
    R=tuple(seeded.sample(range(16),16))
    ops={"P":P,"Q":Q,"R":R}
    rng=random.Random(150371+abs(seed)*7979)
    if seed in TRAIN:
        word=("PQR"[abs(seed)%3],)
    else:
        word=(("P","Q","R"),("R","Q","P"),("P","R","P","Q"),("Q","P","R","Q"))[abs(seed)%4]
    perm=tuple(range(16))
    for name in word:perm=compose(perm,ops[name])
    xs=rng.sample(range(65536),40)
    output=[m.forward(x,m.pack(perm)) for x in xs]
    corrupt=set(rng.sample(range(16),2))
    fit=tuple((xs[i],output[i]^(1 if i in corrupt else 0)) for i in range(16))
    check=tuple((xs[i],output[i]) for i in range(16,20))
    witnesses=tuple((x,m.apply_sbox(x,perm))
       for x in (xs[:8] if seed in TRAIN else xs[:2]))
    held=tuple(zip(xs[20:36],output[20:36]))
    assert len(fit)==16 and len(check)==4 and len(held)==16
    return word,fit,check,witnesses,held
