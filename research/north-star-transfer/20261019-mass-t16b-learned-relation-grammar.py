"""T16B Mass Research learned relationship *grammar*, not source-tag priors.

Source-blind PUBLIC TRAIN-only evidence supports a minimum-description-length
model over observed role maps. A learned representation is a basis 8-byte
bijection plus per-role opcodes (self, inverse, square or independent), not
a hard-coded P/Q/R relation. The exact same hypothesis class MUST be
available to independently trained strongest controls in original science.
No prospective task generator, hidden target, or consumed source imported.
"""
from itertools import product

OPS=("independent","self","inverse","square")

def compose(p,q):
    return tuple(q[p[i]] for i in range(16))

def invert(p):
    result=[0]*16
    for i,v in enumerate(p):result[v]=i
    return tuple(result)

def public_votes(cases):
    votes={}
    for role,pairs in cases:
        v=votes.setdefault(role,[[0]*16 for _ in range(16)])
        for x,y in pairs:
            assert 0<=x<1<<16 and 0<=y<1<<16
            for shift in (0,4,8,12):
                v[(x>>shift)&15][(y>>shift)&15]+=1
    assert votes and len(votes)<=8
    return votes

def greedy_assignment(table):
    """A separate equal-information empirical control can use same data."""
    pairs=sorted((-table[i][j],i,j) for i in range(16) for j in range(16))
    perm=[None]*16;used=set()
    for neg,i,j in pairs:
        if perm[i] is None and j not in used:
            perm[i]=j;used.add(j)
    assert sorted(perm)==list(range(16))
    return tuple(perm)

def public_error(votes,perm):
    return sum(sum(row)-row[perm[i]] for i,row in enumerate(votes))

def transform(base,op,original=None):
    if op=="independent":
        assert original is not None
        return original
    if op=="self":return base
    if op=="inverse":return invert(base)
    if op=="square":return compose(base,base)
    raise ValueError("UNKNOWN_ROLE_GRAMMAR")

def discover(public_cases):
    """Train a relationship grammar from PUBLIC observations alone.
    The MDL complexity constant is frozen before any scientific original.
    A relation is not accepted just because a source is named 'Q' or 'R'.
    """
    votes=public_votes(public_cases)
    roles=tuple(sorted(votes))
    independent={role:greedy_assignment(votes[role]) for role in roles}
    best=None;best_key=None
    for anchor in roles:
        others=[r for r in roles if r!=anchor]
        basis=independent[anchor]
        for code_tuple in product(OPS,repeat=len(others)):
            ops={anchor:"self"}
            ops.update(zip(others,code_tuple))
            perms={r:transform(basis,ops[r],independent[r]) for r in roles}
            miss=sum(public_error(votes[r],perms[r]) for r in roles)
            # Each independent permutation uses 8 bytes; 1 opcode byte
            # suffices for each relationship relative to the anchor.
            bytes_required=8+sum(8 if ops[r]=="independent" else 1 for r in others)
            # One mistaken public nibble costs more than one byte of model.
            criterion=miss*8+bytes_required
            key=(criterion,miss,bytes_required,anchor,code_tuple)
            if best_key is None or key<best_key:
                best_key=key;best=(anchor,ops,perms,miss,bytes_required)
    anchor,ops,perms,miss,bytes_required=best
    return {"roles":roles,"anchor":anchor,"operations":ops,
            "maps":perms,"model_bytes":bytes_required,
            "public_mismatches":miss,"train_nibble_observations":
                sum(sum(map(sum,votes[r])) for r in roles),
            "relationship_learned_from_public":True,
            "source_defined_relationship_assumed":False}

def equal_data_independent(public_cases):
    votes=public_votes(public_cases)
    maps={r:greedy_assignment(table) for r,table in votes.items()}
    return {"maps":maps,"public_mismatches":sum(
          public_error(votes[r],maps[r]) for r in maps),
          "model_bytes":8*len(maps)}

def infer_word(maps,roles):
    """Exact ordered composition; no target hidden answers."""
    p=tuple(range(16))
    for role in roles:
        p=compose(p,maps[role])
    return p
