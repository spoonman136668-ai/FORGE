"""F110-O dry-run provenance plan for a future complete Freebase graph.

Never reads/downloads graph, never treats caller's claimed checksum as
independently witnessed, and NEVER admits graph execution. Source existence,
custody authority, and full streaming design are separate future gates.
"""
from __future__ import annotations
import re

FIELDS=(
    "publisher_source_url",
    "independent_archive_sha256",
    "archive_bytes",
    "independent_extracted_edge_sha256",
    "extracted_edge_bytes",
    "original_license_and_attribution",
    "exact_complete_edge_count",
    "entity_namespace",
    "role_namespace",
    "read_only_streaming_index_version",
    "bounded_decompression_plan",
    "complete_source_reconciliation_plan",
    "bounded_frontier_resource_policy",
    "independent_evaluation_custodian",
)
HEX=re.compile(r"[0-9a-f]{64}\Z",flags=re.ASCII)
NAMESPACE=re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,127}\Z",flags=re.ASCII)
MAX_ARCHIVE_BYTES=16*1024*1024*1024
MAX_EXTRACTED_BYTES=128*1024*1024*1024

def _metadata_valid(name,value)->bool:
    if name in ("independent_archive_sha256","independent_extracted_edge_sha256"):
        return isinstance(value,str) and HEX.fullmatch(value) is not None
    if name in ("archive_bytes","extracted_edge_bytes","exact_complete_edge_count"):
        if isinstance(value,bool) or not isinstance(value,int):
            return False
        upper=MAX_ARCHIVE_BYTES if name=="archive_bytes" else (
              MAX_EXTRACTED_BYTES if name=="extracted_edge_bytes" else 10**10)
        return 0<value<=upper
    if name in ("entity_namespace","role_namespace"):
        return isinstance(value,str) and NAMESPACE.fullmatch(value) is not None
    if not isinstance(value,str) or len(value)>256 or not value:
        return False
    return all(32<=ord(x)<=126 for x in value)

def evaluate_manifest(candidate=None)->dict:
    # Developer-owned claims are not source evidence, even when well formed.
    if not isinstance(candidate,dict):
        candidate={}
    missing=tuple(key for key in FIELDS
                  if key not in candidate or not _metadata_valid(key,candidate[key]))
    return {
        "status":"FREEBASE_GRAPH_SOURCE_NOT_QUALIFIED",
        "admitted":False,
        "source_metadata_field_total":len(FIELDS),
        "missing_or_invalid_metadata_fields":list(missing),
        "claimed_complete_metadata_is_independent_evidence":False,
        "original_freebase_archive_cryptographically_verified":False,
        "original_full_edge_corpus_read":False,
        "streaming_index_qualified":False,
        "independent_evaluator_custody_verified":False,
        "read_only_original_graph_qualified":False,
        "real_graph_calls":0,
        "original_graph_partial_sampling_allowed":False,
        "original_freebase_archive_auto_download_allowed":False,
    }
