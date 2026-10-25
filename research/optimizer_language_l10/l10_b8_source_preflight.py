#!/usr/bin/env python3
"""L10-B8 pre-admission metadata lint, NEVER scientific first-use authority.

No source generator, corpus reader, seed, model, evaluation, network, or runner.
A valid candidate structure has not been authenticated by the external owner.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath

SCHEMA = "forge.optimizer.language.l10.b8.prospective-source-candidate-metadata-v1"
FAMILY_KIND = "de_novo_open_formal_semantic_worlds_with_independently_specified_meaning"
ROLE = "L10_PROSPECTIVE_NEW_SOURCE_FAMILY"
RESULT = "METADATA_SHAPE_VALID_NOT_AUTHENTICATED_NOT_ADMITTED"
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
FAMILY = re.compile(r"l10p-[a-z0-9-]{6,54}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
BLOCKED_TERMS = (
    "examples", "samples", "raw_source", "raw_corpus", "source_rows",
    "secret", "private_key", "credential", "token", "protected_seed",
    "source_payload", "label_text", "reference_text", "score_rows",
)
EXPECTED_ROOT = {
    "schema", "family_id", "family_kind", "generator", "grammar",
    "scorer", "custody", "information_regime", "data_access", "counts",
}
IDENTITY_KEYS = {"repository", "commit_sha", "blob_sha", "path"}
CUSTODY_KEYS = {
    "source_owner", "scorer_owner", "candidate_owner",
    "source_birth", "owner_receipt", "fsa_admission",
}
INFO_KEYS = {
    "mapping_regime", "public_relation_codes", "lexicon_rights",
    "model_truth_fields_exposed", "scorer_source_access",
}
ACCESS_KEYS = {
    "role", "examples_generated", "protected_seed_exposed",
    "protected_bytes_exposed", "l9_data_reused",
}
COUNTS_KEYS = {
    "prospective_examples", "selected_models", "protected_source_observations",
}


def demand(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError("L10_B8_METADATA_DENIED:" + reason)


def exact(value: object, fields: set[str], label: str) -> dict:
    demand(type(value) is dict and set(value) == fields, label + "_FIELDS")
    return value


def source_identity(value: object, label: str) -> dict:
    v = exact(value, IDENTITY_KEYS, label)
    demand(type(v["repository"]) is str and REPO.fullmatch(v["repository"]) is not None,
           label + "_REPOSITORY")
    for k in ("commit_sha", "blob_sha"):
        demand(type(v[k]) is str and HEX40.fullmatch(v[k]) is not None,
               label + "_" + k.upper())
    p = v["path"]
    demand(type(p) is str and 1 <= len(p) <= 240 and
           not p.startswith(("/", ".")) and "\\" not in p and
           all(part not in ("", ".", "..") for part in p.split("/")) and
           str(PurePosixPath(p)) == p, label + "_PATH")
    return v


def check_manifest(value: object) -> dict:
    """Return ONLY a structural lint finding; never a scientific GO.

    Static source refs or claimed distinct owners cannot authenticate source
    authorship, owner receipts, actual isolation, dataset birth or first-use.
    No filesystem, GitHub, environment, corpus or protected source is read.
    """
    m = exact(value, EXPECTED_ROOT, "ROOT")
    demand(m["schema"] == SCHEMA, "SCHEMA")
    family = m["family_id"]
    demand(type(family) is str and FAMILY.fullmatch(family) is not None and
           not any(old in family.lower() for old in
                   ("webnlg", "e2e", "dart", "cogs", "totto", "dev-", "l9")),
           "UNFAMILIAR_FAMILY_ID")
    demand(m["family_kind"] == FAMILY_KIND, "FROZEN_FAMILY_KIND")
    identities = {k: source_identity(m[k], k.upper())
                  for k in ("generator", "grammar", "scorer")}
    unique = {(x["repository"], x["commit_sha"], x["path"])
              for x in identities.values()}
    demand(len(unique) == 3, "GENERATOR_GRAMMAR_SCORER_COLLAPSED")
    demand(identities["scorer"]["repository"] != identities["generator"]["repository"],
           "SCORER_NOT_SEPARATE_SOURCE")
    c = exact(m["custody"], CUSTODY_KEYS, "CUSTODY")
    for key in ("source_owner", "scorer_owner", "candidate_owner"):
        demand(type(c[key]) is str and
               re.fullmatch(r"[a-zA-Z0-9_.-]{3,80}", c[key]) is not None,
               "CUSTODY_OWNER_" + key.upper())
    demand(len({c["source_owner"], c["scorer_owner"],
                c["candidate_owner"]}) == 3, "CUSTODY_SEPARATION_CLAIM")
    demand(c["source_birth"] == "UNBORN" and
           c["owner_receipt"] == "NOT_PRESENT" and
           c["fsa_admission"] == "DENIED", "NO_SOURCE_BIRTH_AUTHORITY")
    info = exact(m["information_regime"], INFO_KEYS, "INFORMATION")
    demand(info["mapping_regime"] == "KNOWN_MAPPING" and
           info["public_relation_codes"] == ["P0", "P1", "P2"] and
           info["lexicon_rights"] == "MATCHED_PUBLIC_ONLY" and
           info["model_truth_fields_exposed"] is False and
           info["scorer_source_access"] == "SEPARATE_OWNER_ONLY",
           "INFORMATION_LEAK_OR_REGIME_DRIFT")
    a = exact(m["data_access"], ACCESS_KEYS, "ACCESS")
    demand(a["role"] == ROLE and type(a["examples_generated"]) is int and
           a["examples_generated"] == 0 and
           a["protected_seed_exposed"] is False and
           a["protected_bytes_exposed"] is False and
           a["l9_data_reused"] is False, "PROTECTED_SOURCE_BOUNDARY")
    counts = exact(m["counts"], COUNTS_KEYS, "COUNTS")
    demand(all(type(x) is int and x == 0 for x in counts.values()),
           "PROSPECTIVE_DATA_OR_MODEL_SELECTION")
    # A canonical digest is not a witness signature or actual source hash.
    raw = json.dumps(m, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("utf-8")
    return {
        "schema": "forge.optimizer.language.l10.b8.metadata-lint-result-v1",
        "status": RESULT,
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "prospective_examples_read": 0,
        "original_sources_authenticated": False,
        "independent_owner_receipts_authenticated": False,
        "scientific_first_use_admitted": False,
        "protected_corpus_evaluated": False,
        "comparison_scored": False,
        "requires_independent_FSA_review": True,
    }


if __name__ == "__main__":
    raise SystemExit("L10_B8_NO_STANDALONE_PROSPECTIVE_EXECUTION")
