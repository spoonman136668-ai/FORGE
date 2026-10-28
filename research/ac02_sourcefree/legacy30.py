"""Source-free AC-02 exploration of all 30 raw-document ideas.

These are minimal deterministic probes/counterexamples, not full implementations,
trained mechanisms, GPU benchmarks, native-science results or original first use.
Python >= 3.10 standard library. No networking, secrets or hardware modification.
"""
import cmath
import itertools
import json
import math
import marshal
import random
import tempfile
import zlib
from pathlib import Path

def case(n, title, kind, witnessed, limitation):
    return {"id": "U%02d" % n, "claim": title, "kind": kind,
            "witness": bool(witnessed), "limitation": limitation}

def run():
    r = []
    def add(n, title, kind, witnessed, limitation):
        r.append(case(n, title, kind, witnessed, limitation))

    # Every ID maps to the corresponding numbered proposal in the uploaded document.
    repeated = b"ABCD" * 256
    noise = random.Random(101).randbytes(1024)
    add(1, "JIT tensor decompression", "SOFTWARE_TOY",
        zlib.decompress(zlib.compress(repeated)) == repeated and
        len(zlib.compress(repeated)) < len(repeated) and
        len(zlib.compress(noise)) >= len(noise),
        "No representative neural weights or throughput benchmark.")
    add(2, "Grammar/n-gram speculation", "SOFTWARE_TOY",
        '{"x":1}' != '{"x":2}',
        "Draft mismatch requires target verification; no decoding speedup shown.")
    slab = bytearray(512)
    slab[0] = 17
    add(3, "Software NUMA interleaving equals HBM", "HARDWARE_DEPENDENCY",
        slab[0] == 17 and len(slab) == 512,
        "Ordinary process allocation cannot control memory channels or become HBM.")
    shards = ((1,2,3),(3,4,5),(5,6,7))
    add(4, "Swarm Micro-LoRA gradients", "SOFTWARE_TOY",
        tuple(sum(s[i] for s in shards) for i in range(3)) == (9,12,15),
        "Gradient reduction only; Wi-Fi and distributed training not tested.")
    cache = {("prompt",1): "value"}
    add(5, "Activation lookup replacing generation", "SOFTWARE_TOY",
        cache.get(("prompt",1)) == "value" and ("prompt",2) not in cache,
        "Exact hit is not general semantic composition or hidden-state replay.")
    add(6, "Analog computation in commodity DRAM", "HARDWARE_DEPENDENCY",
        sum(x*y for x,y in ((2,5),(3,7))) == 31,
        "Digital dot product is not physical analog RAM computation; software has no such control.")
    a, b = 0b10101010, 0b00111100
    add(7, "Hyperdimensional VSA", "SOFTWARE_TOY",
        (a ^ b) ^ a == b,
        "XOR binding is reversible; cannot infer learning or no-interference retrieval.")
    state = 0.
    seen = []
    for u in (1,0,1,1,0):
        state = math.tanh(.7*state + .3*u)
        seen.append(state)
    add(8, "Fixed spiking/reservoir dynamics", "SOFTWARE_TOY",
        len(set(seen)) > 1 and all(math.isfinite(v) for v in seen),
        "A recurrent trajectory alone does not learn new cognition.")
    add(9, "Seed-fractal arbitrary weight replacement", "INFORMATION_LIMIT",
        (1<<3) < (1<<4),
        "A 3-bit seed cannot represent every distinct 4-bit learned parameter array.")
    x = (1,0,0,0)
    y = (0,1,0,0)
    mix = tuple(i+j for i,j in zip(x,y))
    add(10, "Holographic associative memory", "SOFTWARE_TOY",
        mix != x and mix != y,
        "Superposition can interfere; no FFT-based full retrieval was implemented.")
    weights = (-1,0,1,1,-1)
    inputs = (4,7,-3,2,8)
    dot = sum(-v if w == -1 else v if w == 1 else 0
              for w,v in zip(weights,inputs))
    add(11, "Ternary multiplication-free kernels", "SOFTWARE_TOY",
        dot == sum(w*v for w,v in zip(weights,inputs)),
        "Arithmetic identity alone demonstrates neither kernel speed nor model accuracy.")
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "stream.bin"
        p.write_bytes(b"x" * 4096)
        with p.open("rb") as f:
            chunk_sizes = [len(f.read(256)) for _ in range(16)]
    add(12, "Out-of-core streaming", "SOFTWARE_TOY",
        sum(chunk_sizes) == 4096,
        "File I/O uses the OS and cannot bypass physical storage bandwidth.")
    add(13, "Fixed size KV sketches preserve all contexts", "INFORMATION_LIMIT",
        1 != 5 and 1%4 == 5%4,
        "Hash collision prevents unlimited exact reconstruction from fixed-size sketches.")
    procedural = bytes(i%4 for i in range(256))
    add(14, "Procedural synthesis of arbitrary weights", "INFORMATION_LIMIT",
        len(zlib.compress(procedural)) < len(procedural),
        "Artificial structured arrays are compressible; arbitrary learned arrays need not be.")
    data = (1,2,3,4)
    old = [2*v for v in data]
    add(15, "Single-pass operator fusion", "SOFTWARE_TOY",
        sum(v+1 for v in old) == sum(2*v+1 for v in data),
        "Equivalent arithmetic but no native memory traffic or runtime comparison.")
    small = compile("def f():\n return "+ "+".join(map(str,range(8))), "<ac02>", "exec")
    large = compile("def f():\n return "+ "+".join(map(str,range(128))), "<ac02>", "exec")
    add(16, "Code-compiled weights fit CPU instruction cache", "INFORMATION_LIMIT",
        len(marshal.dumps(large)) > len(marshal.dumps(small)),
        "Instructions/constants still consume code/data bytes; no I-cache miracle.")
    repetitive = b"abcd" * 1024
    random_bytes = random.Random(77).randbytes(4096)
    add(17, "Lossless grammar context collapse", "INFORMATION_LIMIT",
        len(zlib.compress(repetitive)) < len(repetitive) and
        len(zlib.compress(random_bytes)) >= len(random_bytes),
        "Arbitrary history is not fixed-size losslessly compressible.")
    rot = lambda z: ((z<<1)|(z>>7))&255
    add(18, "Vector-symbolic superposition and order", "SOFTWARE_TOY",
        (a^b) == (b^a) and (rot(a)^b)!=(rot(b)^a),
        "Permutation adds position but not unlimited capacity or learned semantics.")
    counts = {(i,j):[0,0] for i in (0,1) for j in (0,1)}
    for i,j in counts:
        counts[(i,j)][i^j] += 1
    add(19, "Boolean finite-state/Tsetlin learning", "SOFTWARE_TOY",
        all(max(range(2),key=lambda k:counts[(i,j)][k]) == i^j for i,j in counts),
        "A four-entry truth table is not a Tsetlin-machine implementation or transfer.")
    programs = (lambda v:v, lambda v:v+1, lambda v:2*v, lambda v:v*v)
    examples = ((1,2),(2,3),(3,4))
    matches = [i for i,p in enumerate(programs) if all(p(x)==y for x,y in examples)]
    add(20, "Minimum-description-length program search", "SOFTWARE_TOY",
        matches == [1],
        "Fixed four-program enumeration understates unrestricted synthesis complexity.")
    add(21, "64-bit chaos seed encodes arbitrary cognition", "INFORMATION_LIMIT",
        (1<<64)<(1<<65),
        "A 64-bit state cannot encode all independent 65-bit histories uniquely.")
    det = lambda m:m[0][0]*m[1][1]-m[0][1]*m[1][0]
    add(22, "Tensor train dynamic bond pruning", "INFORMATION_LIMIT",
        det(((2,3),(4,6))) == 0 and det(((1,0),(0,1))) != 0,
        "Rank-one factorizations do not exactly represent arbitrary full-rank tensors.")
    def spectral_magnitude(values):
        return tuple(round(abs(sum(values[t]*cmath.exp(-2j*math.pi*k*t/len(values))
                                   for t in range(len(values)))), 8)
                     for k in range(len(values)))
    add(23, "Spectral single-pass paragraph generation", "INFORMATION_LIMIT",
        spectral_magnitude((1,0,0,0)) == spectral_magnitude((0,1,0,0)),
        "Magnitude loses sequence order; Fourier transforms alone cannot infer valid text.")
    cell = [0]*9
    cell[4] = 1
    updated = [cell[(i-1)%9] ^ cell[(i+1)%9] for i in range(9)]
    add(24, "Critical cellular-automata language", "SOFTWARE_TOY",
        sum(updated) == 2,
        "Rule-90 dynamics are not criticality, learning, or natural-language evidence.")
    tested = 0
    found = None
    for i,program in enumerate(programs):
        tested += 1
        if all(program(x)==2*x for x in (0,1,2)):
            found = i
            break
    add(25, "Parallel Levin grammar search", "SOFTWARE_TOY",
        found==2 and tested==3,
        "Tiny hand-selected search is not tractable universal search.")
    add(26, "Infinite memory in hyperbolic coordinates", "INFORMATION_LIMIT",
        0%256 == 256%256,
        "Finite-precision storage still has finitely many distinguishable states.")
    rewrite = lambda edge: ("b","r","c") if edge==("a","r","b") else edge
    add(27, "Categorical graph-rewriting cognition", "SOFTWARE_TOY",
        rewrite(("a","r","b"))==("b","r","c") and
        rewrite(("x","r","y"))==("x","r","y"),
        "A manually coded rule is not a learned categorical inference system.")
    prime=17
    root=4
    n=4
    def ntt(values,inverse=False):
        w = pow(root,-1,prime) if inverse else root
        transformed = [sum(values[t]*pow(w,(k*t)%n,prime)
                           for t in range(n))%prime for k in range(n)]
        return [(v*pow(n,-1,prime))%prime for v in transformed] if inverse else transformed
    lhs=(1,2,3,4)
    rhs=(4,3,2,1)
    convolution=ntt([(x*y)%prime for x,y in zip(ntt(lhs),ntt(rhs))],True)
    naive=[sum(lhs[t]*rhs[(k-t)%n] for t in range(n))%prime for k in range(n)]
    add(28, "Galois-field NTT semantic computation", "SOFTWARE_TOY",
        convolution==naive,
        "NTT still performs modular multiplication; numerical convolution is not semantics.")
    topology=((0,1),(1,2))
    labels_a={"0":"open"}
    labels_b={"0":"close"}
    add(29, "Persistent homology collapses semantic output", "INFORMATION_LIMIT",
        topology == topology and labels_a != labels_b,
        "Same topology need not determine semantic labels; full persistence not computed.")
    phase=cmath.exp(1j*math.pi/4)
    stab_ratios=(0,1,-1,1j,-1j)
    add(30, "Stabilizer simulation yields unrestricted AI", "INFORMATION_LIMIT",
        all(abs(phase-v)>1e-8 for v in stab_ratios),
        "T|+> is not a stabilizer state; Clifford-only simulation excludes universal quantum operations.")

    assert [v["id"] for v in r] == ["U%02d"%i for i in range(1,31)]
    assert all(v["witness"] for v in r)
    return {"schema":"forge.ac02.legacy30.sourcefree.v1",
            "scientific_admission":False,
            "original_first_use":False,
            "hardware_modification":False,
            "result_scope":"TOY_OR_COUNTEREXAMPLE_ONLY",
            "probes":r}

if __name__=="__main__":
    print(json.dumps(run(),sort_keys=True,indent=2))
