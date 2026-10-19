"""T14 Mass source generator: novel OPEN two-/three-step relation compositions.
TRAIN teaches independent role transformations; OPEN contains never-TRAIN
compositions of role operators. Held final outputs may be used ONLY by scorer.
All examples use PUBLIC input, role specification and noisy FIT / CHECK.
"""
import random
TRAIN=tuple(range(-43015,-42999))
OPEN=tuple(range(-43107,-43099))
def compose(p,q):
    return tuple(q[p[i]] for i in range(16))
def birth(seed,m):
    assert seed in TRAIN or seed in OPEN
    base=random.Random(143891)
    P=tuple(base.sample(range(16),16))
    Q=tuple(base.sample(range(16),16))
    rng=random.Random(19519+abs(seed)*9119)
    if seed in TRAIN:
        roles=("P",) if (-seed)%2 else ("Q",)
    else:
        roles=(("P","Q"),("Q","P"),("P","Q","P"),("Q","P","Q"))[(-seed)%4]
    op=tuple(range(16))
    for name in roles:op=compose(op,P if name=="P" else Q)
    packed=m.pack(op)
    xs=rng.sample(range(65536),36)
    pure=[m.forward(x,packed) for x in xs]
    corruption=set(rng.sample(range(16),2))
    FIT=tuple((x,y^(1 if j in corruption else 0)) for j,(x,y) in enumerate(zip(xs[:16],pure[:16])))
    CHECK=tuple(zip(xs[16:20],pure[16:20]))
    # TRAIN intermediate disclosures are about a single known-role operation;
    # OPEN exposes only two first-round full composition witnesses.
    witness=tuple((x,m.apply_sbox(x,op)) for x in (xs[:16] if seed in TRAIN else xs[:2]))
    held=tuple(zip(xs[20:],pure[20:]))
    return roles,FIT,CHECK,witness,held
