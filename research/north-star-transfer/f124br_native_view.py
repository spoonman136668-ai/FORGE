"""F124-BR lower-allocation native graph adapter, not a new model.

Same exact graph grammar/demonstration validations as F124-AJ public_task.
Borrow source+destination bit lists READ-ONLY while constructing the native
graph; replace src_bits lists with learned inverses, leave dst_bits untouched.
This avoids allocating two copied 16-bit arrays per original edge before
the same frozen native scorer. Never alter user/source graph, model, threshold,
Yggdrasil native implementation, data provenance or role semantics.
"""
from __future__ import annotations

import re

TAG = re.compile(r"^rel_task_([a-f0-9]{12}):(.+)$")


def need(ok,reason):
    if not ok:
        raise ValueError("F124BR_NATIVE_" + reason)


def bits16(value):
    need(type(value) is int and 0<=value<=65535,"BIT_DOMAIN")
    return [(value>>j)&1 for j in range(16)]


def public_native_view(graph):
    need(type(graph) is dict and
         set(graph)=={"start","target","roles","edges","demos"},
         "SOURCE_ONLY_PUBLIC_INPUT")
    roles=graph["roles"]
    need(type(roles) is list and 7<=len(roles)<=15,
         "PUBLIC_BOUNDED_ROLE_DEPTH")
    matches=[TAG.fullmatch(role) for role in roles]
    need(all(m is not None for m in matches),"OPAQUE_TASK_ROLE_GRAMMAR")
    task=matches[0].group(1)
    need(all(m.group(1)==task for m in matches),"TASK_ID_UNIFORM")
    demos=graph["demos"]
    need(type(demos) is list and len(demos)==24,"PUBLIC_24_SUPPORT_PAIRS")
    for row in demos:
        need(type(row) is dict and
             set(row)=={"input_bits","output_bits"} and
             all(type(row[key]) is list and len(row[key])==16
                 and all(type(v) is int and v in (0,1) for v in row[key])
                 for key in ("input_bits","output_bits")),
             "SUPPORT_PAIR_VALIDITY")
    edges=[]
    for original in graph["edges"]:
        m=TAG.fullmatch(original["role"])
        need(m is not None and m.group(1)==task,"PUBLIC_EDGE_TASK_CONSISTENCY")
        # Borrow native input bit arrays only until decoding. Never write to
        # these original objects; the result gets new src_bits arrays.
        edges.append({
            "from":original["from"],"to":original["to"],
            "role":m.group(2),
            "src_bits":original["src_bits"],
            "dst_bits":original["dst_bits"]
        })
    return {"start":graph["start"],"target":graph["target"],
            "roles":[m.group(2) for m in matches],
            "edges":edges},demos,task


def decoded_native(graph,model,program,native,*,legacy_parser=None):
    """Byte-for-byte identical normalized graph and native scorer inputs.

    Test-only legacy parser may be injected for equivalence checks, never
    selected using benchmark result or source-family labels.
    """
    if legacy_parser is None:
        result,demos,nonce=public_native_view(graph)
    else:
        result,demos,nonce=legacy_parser.public_task(graph)
    native.frozen.prior.parent.validate_15(result)
    for edge in result["edges"]:
        y=0
        for j,b in enumerate(edge["src_bits"]):
            y|=b<<j
        source=model.inverse(y,program)
        edge["src_bits"]=bits16(source)
    native.frozen.prior.parent.validate_15(result)
    return result,demos,nonce


def score_exact_native_pair(graphs,model,program,native,base,delta,
                            *,legacy_parser=None):
    """Keep only bounded scalar/work diagnostics. Native scorer is unchanged."""
    scored=[]
    for graph in graphs:
        normalized,demos,nonce=decoded_native(
            graph,model,program,native,legacy_parser=legacy_parser)
        score,raw,ratio,work=native.ygg_transition(
            normalized,list(base),list(delta),.1)
        need(work["max_active"]<=7 and work["max_retained"]<=9,
             "ORIGINAL_7_ACTIVE_9_RETAINED")
        scored.append({
            "score":score,"raw":raw,"ratio":ratio,
            "work":work, "nonce":nonce
        })
    return scored
