"""T16-D lossless *structural* CLUTRR metadata translator and admission screen.

No external dataset bytes, source generation, trained models, private answers,
network access, global custody or original experiments are present. This tool
DOES NOT establish a semantics-preserving mapping from kinship reasoning to
Wingless F11/S3, Yggdrasil four-type causal memory, or Mass 16-symbol S-box.
"""
from __future__ import annotations
import json
from pathlib import Path

HERE=Path(__file__).parent
PIN={
 "external_commit":"d045fae289d3746503677ceed7631c999202501e",
 "external_tree":"738d52b48d147d394b4f1502c79e17c3728efe33",
 "rules_blob":"c96bb657d987751ea1b9b5732dcaf08718d908b0",
 "relations_blob":"abe30331fd85e4361f13d2a0aac15534de75499c",
 "generator_blob":"2f9f2d2dbf895de7a16b373f7edf486b1755b88a",
 "baseline_commit":"303ed9a48f82a59b4eb34ac5bd5866f0d82c5552"
}
# Exact upstream taxonomy present in pinned CLUTRR rules; names here are
# metadata labels, NOT decoded dataset values or source-born evidence.
FAMILY_RELS=(
 "child","inv-child","SO","sibling","grand","inv-grand",
 "in-law","inv-in-law","sibling-in-law","un","inv-un","no-relation"
)
REQUIRED_FIELDS=("schema","external_commit","external_tree",
 "rules_blob","relations_blob","generator_blob","baseline_commit",
 "license","reuse_rights_independently_cleared",
 "independent_source_origin_signed","independent_firstuse_signed",
 "global_firstuse_cas_attested","native_semantic_equivalence_signed",
 "strong_controls_frozen","end_to_end_metering_frozen",
 "unseen_family_screened","source_dataset_bytes_opened")

def exact_meta(meta):
    if type(meta) is not dict or set(meta)!=set(REQUIRED_FIELDS):
        raise ValueError("CLUTRR_SOURCE_PROVENANCE_SCHEMA_DRIFT")
    if meta.get("schema")!="northstar.t16d.clutrr.metadata.v1":
        raise ValueError("CLUTRR_NOT_FROZEN_METADATA")
    for k,expected in PIN.items():
        if meta[k]!=expected:raise ValueError("CLUTRR_EXTERNAL_PIN_DRIFT_"+k)
    if meta["license"]!="CC-BY-NC-4.0":
        raise ValueError("CLUTRR_UNREVIEWED_LICENSE_DRIFT")
    for f in ("reuse_rights_independently_cleared",
      "independent_source_origin_signed","independent_firstuse_signed",
      "global_firstuse_cas_attested","native_semantic_equivalence_signed",
      "strong_controls_frozen","end_to_end_metering_frozen",
      "unseen_family_screened","source_dataset_bytes_opened"):
        if type(meta[f]) is not bool:raise ValueError("CLUTRR_UNTRUSTED_BOOLEAN")
    return meta

def translate_public_edges(edges):
    """Reversible structural dictionary only. Records are synthetic examples;
    any real source collection must first satisfy independent source custody.

    No relabeling to native 0-3 roles is done. No kinship inference or
    hidden target labels are manufactured.
    """
    if type(edges) is not list or len(edges)>72:
        raise ValueError("CLUTRR_UNBOUNDED_EDGE_LIST")
    triples=[]
    for edge in edges:
        if (type(edge) is not dict or set(edge)!=set(("source","relation","target")) or
            type(edge["source"]) is not int or
            type(edge["target"]) is not int or
            not (0<=edge["source"]<1<<24 and 0<=edge["target"]<1<<24) or
            type(edge["relation"]) is not str or
            edge["relation"] not in FAMILY_RELS):
            raise ValueError("CLUTRR_STRUCTURAL_ROW_AMBIGUOUS")
        triples.append((edge["source"],edge["relation"],edge["target"]))
    if len(set(triples))!=len(triples):
        raise ValueError("CLUTRR_DUPLICATE_PROVENANCE_UNKNOWN")
    rels=tuple(sorted({r for _,r,_ in triples}))
    ids=tuple(sorted({v for x,_,y in triples for v in (x,y)}))
    index={v:i for i,v in enumerate(ids)}
    return {
       "schema":"northstar.t16d.clutrr.structural-only.v1",
       "roles":rels,
       "nodes":ids,
       "dictionary_edges":tuple((index[a],rels.index(r),index[b]) for a,r,b in triples),
       "lossless_relation_labels":True,
       "kinship_semantics_verified":False,
       "native_operator_isomorphism_proven":False
    }

def reconstruct(translated):
    nodes=translated["nodes"];roles=translated["roles"]
    return tuple((nodes[a],roles[r],nodes[b]) for a,r,b in translated["dictionary_edges"])

def lane_screen(meta,fixture_edges):
    meta=exact_meta(meta)
    translated=translate_public_edges(fixture_edges)
    roles=translated["roles"]
    nodes=translated["nodes"]
    # Family relations are relational predicates, not necessarily
    # bijections. Sibling can have multiple targets for one source.
    multifunc=any(a==c and rel==other and b!=d
                 for a,rel,b in reconstruct(translated)
                 for c,other,d in reconstruct(translated))
    estimated_native_bytes=24+2+3*len(nodes)+2*len(fixture_edges)
    reasons={
      "Wingless":["CLUTRR_KINSHIP_NOT_F11_OR_S3_PUBLIC_BIJECTION"],
      "Yggdrasil":["NO_SIX_HOP_NATIVE_QUERY_SEMANTIC_PROOF"],
      "MassResearch":["CLUTRR_RELATIONAL_PREDICATES_NOT_16_ELEMENT_SBOX"]
    }
    if len(roles)>4:
        reasons["Yggdrasil"].append("MORE_THAN_FOUR_NATIVE_TYPED_RELATIONS")
    if estimated_native_bytes>144:
        reasons["Yggdrasil"].append("SERIAL_NATIVE_144B_LOWER_BOUND_EXCEEDED")
    if multifunc:
        reasons["Wingless"].append("NONFUNCTIONAL_KINSHIP_COUNTEREXAMPLE")
        reasons["MassResearch"].append("NONBIJECTIVE_ROLE_COUNTEREXAMPLE")
    if not meta["reuse_rights_independently_cleared"]:
        for v in reasons.values():v.append("LICENSE_RIGHTS_NOT_INDEPENDENTLY_CLEARED")
    if not meta["independent_source_origin_signed"] or not meta["independent_firstuse_signed"]:
        for v in reasons.values():v.append("SEPARATE_SOURCE_AND_FIRSTUSE_CUSTODY_MISSING")
    if not meta["global_firstuse_cas_attested"]:
        for v in reasons.values():v.append("GLOBAL_FIRSTUSE_ATTESTATION_MISSING")
    # A bool set by a caller is NOT externally verified evidence. The
    # scientific gate remains closed even if the synthetic fixture claims
    # all authorizations. Keep this as a preflight/reason classifier only.
    return {
       "schema":"northstar.t16d.clutrr.native-adapter-preflight.v1",
       "external_source_commit":PIN["external_commit"],
       "independent_external_repo_authorship_known":True,
       "independent_scientific_firstuse_proven":False,
       "fixture_edges":len(fixture_edges),
       "native_unique_roles":len(roles),
       "native_unique_nodes":len(nodes),
       "native_lower_bound_bytes":estimated_native_bytes,
       "kinship_relation_nonfunctional_example":multifunc,
       "structural_dictionary_lossless":reconstruct(translated)==tuple(
          (x["source"],x["relation"],x["target"]) for x in fixture_edges),
       "per_lane":{k:{"eligible":False,"reasons":sorted(set(v))}
                   for k,v in reasons.items()},
       "dataset_opened":False,
       "original_cohort_generated":False,
       "original_execution_authorized":False,
       "independent_cognition_accepted":False,
       "optimizer_admission":False
    }

def template_metadata():
    x={"schema":"northstar.t16d.clutrr.metadata.v1",**PIN,
       "license":"CC-BY-NC-4.0"}
    for f in REQUIRED_FIELDS[8:]:
        x[f]=False
    return x

if __name__=="__main__":
    print(json.dumps(lane_screen(template_metadata(),[]),sort_keys=True))
