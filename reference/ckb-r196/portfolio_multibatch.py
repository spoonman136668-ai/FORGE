"""Combine independently verified free-fanout batches into a bounded portfolio.

Each input is an authority-free advisory produced by fanout_adapter. The
aggregate is advisory only; no external calls or scientific classification.
"""
from __future__ import annotations

from typing import Any

from portfolio import check, digest, identity, shortlist, validate_contract

SOURCE_KEYS = {
    "schema", "contract_sha", "binding_sha256", "baseline_sha",
    "selection_metric_name", "higher_is_better",
    "normalized_manifest_sha256", "summary_sha256",
    "historical_data_sha256", "package_sha", "program", "screens", "shortlist",
    "scientific_classification", "dispatch_authority", "promotion_authority",
    "accepted_ref_mutation", "advisory_sha256"
}


def combine_batches(contract: dict, batches: list[dict]) -> dict:
    """Exactly one global budget, diversity filter, and shortlist.

    Do not merge Wingless and Yggdrasil into one research program. Cross-
    project results have different environments, resources, and invariants.
    """
    validate_contract(contract)
    check(type(batches) is list and 1 <= len(batches) <= 20,
          "BATCH_COUNT_INVALID")
    screens = []
    sources = []
    identities = set()
    candidate_ids = set()
    program = None
    metric_name = None
    higher_is_better = None
    for batch in batches:
        check(type(batch) is dict and set(batch) == SOURCE_KEYS,
              "BATCH_SCHEMA_MISMATCH")
        ident = identity(batch["advisory_sha256"], "ADVISORY")
        check(len(ident) == 64 and ident ==
              digest({k: v for k, v in batch.items() if k != "advisory_sha256"}),
              "BATCH_TAMPERED")
        check(ident not in identities, "BATCH_DUPLICATE")
        identities.add(ident)
        check(batch["schema"] == "ckb.fanout-portfolio-advisory.v1" and
              batch["contract_sha"] == contract["contract_sha"] and
              batch["baseline_sha"] == contract["baseline_sha"] and
              batch["historical_data_sha256"] == contract["historical_data_sha"],
              "BATCH_FROZEN_IDENTITY_MISMATCH")
        check(batch["program"] in ("Wingless", "Yggdrasil"),
              "BATCH_PROGRAM_INVALID")
        check(batch["scientific_classification"] is None and
              batch["dispatch_authority"] is False and
              batch["promotion_authority"] is False and
              batch["accepted_ref_mutation"] is False,
              "BATCH_AUTHORITY_INVALID")
        check(type(batch["selection_metric_name"]) is str and
              bool(batch["selection_metric_name"].strip()) and
              type(batch["higher_is_better"]) is bool,
              "BATCH_METRIC_INVALID")
        if program is None:
            program = batch["program"]
            metric_name = batch["selection_metric_name"]
            higher_is_better = batch["higher_is_better"]
        else:
            check(batch["program"] == program, "CROSS_PROGRAM_MERGE_FORBIDDEN")
            check(batch["selection_metric_name"] == metric_name and
                  batch["higher_is_better"] == higher_is_better,
                  "INCOMPARABLE_METRICS")
        for field in ("binding_sha256", "normalized_manifest_sha256",
                      "summary_sha256"):
            check(len(identity(batch[field], field.upper())) == 64,
                  "SOURCE_SHA_LENGTH")
        check(len(identity(batch["package_sha"], "PACKAGE")) == 40,
              "SOURCE_PACKAGE_SHA_LENGTH")
        rows = batch["screens"]
        check(type(rows) is list and rows and
              type(batch["shortlist"]) is dict and
              batch["shortlist"] == shortlist(contract, rows),
              "SOURCE_SHORTLIST_INVALID")
        for row in rows:
            cid = row["candidate_id"]
            check(cid not in candidate_ids, "CROSS_BATCH_CANDIDATE_DUPLICATE")
            candidate_ids.add(cid)
            screens.append(row)
        sources.append({
            "advisory_sha256": ident,
            "binding_sha256": batch["binding_sha256"],
            "manifest_sha256": batch["normalized_manifest_sha256"],
            "summary_sha256": batch["summary_sha256"],
            "package_sha": batch["package_sha"],
            "screen_count": len(rows)
        })
    selection = shortlist(contract, screens)  # global, not per-batch limits
    result = {
        "schema": "ckb.portfolio-multibatch-advisory.v1",
        "contract_sha": contract["contract_sha"],
        "baseline_sha": contract["baseline_sha"],
        "historical_data_sha256": contract["historical_data_sha"],
        "program": program,
        "selection_metric_name": metric_name,
        "higher_is_better": higher_is_better,
        "sources": sorted(sources, key=lambda r: r["advisory_sha256"]),
        "screened_count": len(screens),
        "shortlist": selection,
        "scientific_classification": None,
        "dispatch_authority": False,
        "promotion_authority": False,
        "accepted_ref_mutation": False
    }
    return {**result, "advisory_sha256": digest(result)}
