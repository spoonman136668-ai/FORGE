#!/usr/bin/env python3
"""F85: source-bound dual-lane FIT negative quarantine for optimizer intake.

Read original archived bytes via the existing F83/F84 validators. An authentic
FIT outcome is never an accepted scientific original or a Dream/Pareto label.
No network, mutations, controller, experiment or model API in this module.
"""
import argparse
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "nativefirstuse"))
sys.path.insert(0, str(ROOT / "research" / "f84"))
import f83_actual_heldout as y83
import f84_wingless_fit as w84

SCHEMA = "forge.f85.authentic-dual-fit-optimizer-quarantine.v1"
class Denied(ValueError):
    pass

def need(value, reason):
    if not value:
        raise Denied("F85_" + reason)

def strict_json(raw):
    need(0 < len(raw) <= 131072, "METADATA_SIZE")
    def pairs(items):
        obj = {}
        for k,v in items:
            need(k not in obj, "DUPLICATE_JSON_KEY")
            obj[k] = v
        return obj
    obj = json.loads(raw, object_pairs_hook=pairs,
                     parse_constant=lambda _: (_ for _ in ()).throw(Denied("F85_NONFINITE")))
    need(type(obj) is dict, "METADATA_SHAPE")
    return obj

def digest(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True,
           separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()

def quarantine(w, y):
    need(type(w) is dict and type(y) is dict, "RECORD_TYPES")
    # Deliberately exact: interface widening requires separately reviewed
    # source-identity and affected-interface qualification.
    wk = {"schema","run","artifact","source_sha","digest","fit_cases",
          "exact_correct","strongest_fair_correct","headroom_pp",
          "required_headroom_pp","first_use_authorized",
          "independent_original_accepted","dream_rsi_pareto_policy_gain_qualified",
          "originals_dispatched","disposition"}
    yk = {"schema","project","run","artifact","source_sha","archive_sha256",
          "cases","learned_correct","strongest_fair_correct","gain_pp",
          "fit_validation_consumed_once","independently_accepted_original",
          "dream_rsi_pareto_policy_gain_qualified","first_use_authorized",
          "new_original_dispatched","disposition"}
    need(set(w) == wk and set(y) == yk, "AUDITOR_INTERFACE_DRIFT")
    need(w["schema"] == "forge.f84.wingless-real-fit-negative.v1" and
         w["run"] == w84.RUN and w["artifact"] == w84.ART and
         w["source_sha"] == w84.SHA and w["digest"] == w84.DIGEST and
         type(w["fit_cases"]) is int and w["fit_cases"] == 128 and
         type(w["exact_correct"]) is int and w["exact_correct"] == 104 and
         type(w["strongest_fair_correct"]) is int and
         w["strongest_fair_correct"] == 102 and
         type(w["headroom_pp"]) is float and w["headroom_pp"] == 1.5625 and
         type(w["required_headroom_pp"]) is int and
         w["required_headroom_pp"] == 5 and
         w["disposition"] == "AUTHENTIC_FIT_NEGATIVE_NOT_ACCEPTED_SCIENCE",
         "WINGLESS_NEGATIVE_PIN")
    need(y["schema"] == "forge.f83.authentic-heldout-negative-review.v1" and
         y["project"] == "Yggdrasil" and y["run"] == y83.RUN and
         y["artifact"] == y83.ARTIFACT and y["source_sha"] == y83.SOURCE and
         y["archive_sha256"] == y83.ARCHIVE and
         type(y["cases"]) is int and y["cases"] == 32 and
         type(y["learned_correct"]) is int and y["learned_correct"] == 11 and
         type(y["strongest_fair_correct"]) is int and
         y["strongest_fair_correct"] == 24 and
         type(y["gain_pp"]) is float and y["gain_pp"] == -40.625 and
         y["fit_validation_consumed_once"] is True and
         y["disposition"] ==
         "AUTHENTIC_PROSPECTIVE_FIT_VALIDATION_NEGATIVE_NOT_ACCEPTED_SCIENCE",
         "YGGDRASIL_NEGATIVE_PIN")
    for key in ("first_use_authorized","independent_original_accepted",
                "dream_rsi_pareto_policy_gain_qualified"):
        need(w[key] is False, "WINGLESS_AUTHORITY_DRIFT")
    need(type(w["originals_dispatched"]) is int and
         w["originals_dispatched"] == 0, "WINGLESS_DISPATCH_DRIFT")
    for key in ("first_use_authorized","independently_accepted_original",
                "dream_rsi_pareto_policy_gain_qualified","new_original_dispatched"):
        need(y[key] is False, "YGGDRASIL_AUTHORITY_DRIFT")
    need(w["run"] != y["run"] and w["artifact"] != y["artifact"] and
         w["source_sha"] != y["source_sha"], "LANE_ALIAS")
    return {
        "schema": SCHEMA,
        "stage": "READ_ONLY_AUTHENTIC_FIT_NEGATIVE_QUARANTINE",
        "source_auditors": ["F84_WINGLESS_ARCHIVE_RECOUNT",
                            "F83_YGGDRASIL_HELDOUT_RECOUNT"],
        "observations": [
            {"lane":"Wingless","run":w["run"],"artifact":w["artifact"],
             "source_sha":w["source_sha"],"archive_digest":w["digest"],
             "auditor_output_sha256":digest(w),
             "cases":128,"candidate_correct":104,"control_correct":102,
             "difference_pp":1.5625,"scientific_label_admitted":False},
            {"lane":"Yggdrasil","run":y["run"],"artifact":y["artifact"],
             "source_sha":y["source_sha"],"archive_digest":y["archive_sha256"],
             "auditor_output_sha256":digest(y),
             "cases":32,"candidate_correct":11,"control_correct":24,
             "difference_pp":-40.625,"scientific_label_admitted":False}],
        "authentic_fit_negatives_retained":2,
        "accepted_originals_added":0,
        "dream_rsi_training_labels_added":0,
        "pareto_scientific_wins_added":0,
        "theta_policy_updates_authorized":False,
        "promptbreeder_dgm_genenv_proposal_scope_only":True,
        "f82_historical_policy_archive_unchanged":True,
        "owner_first_use_authorized":False,
        "original_dispatch_authorized":False,
        "cloudflare_written":False,
        "ckb_authority_mutated":False,
        "optimizer_improvement_demonstrated":False
    }

def verify_archives(wrun,wmeta,wzip,yrun,ymeta,yzip):
    # The raw-byte audits are authoritative for these *diagnostic* outcomes;
    # no caller-supplied 'verified=true' assertion is accepted.
    return quarantine(w84.audit(wrun,wmeta,wzip),
                      y83.verify(yrun,ymeta,yzip))

def main():
    p = argparse.ArgumentParser()
    for name in ("wingless_run","wingless_artifact","wingless_zip",
                 "yggdrasil_run","yggdrasil_artifact","yggdrasil_zip","out"):
        p.add_argument("--"+name.replace("_","-"), required=True)
    a = p.parse_args()
    wrun = strict_json(pathlib.Path(a.wingless_run).read_bytes())
    wmeta = strict_json(pathlib.Path(a.wingless_artifact).read_bytes())
    yrun = strict_json(pathlib.Path(a.yggdrasil_run).read_bytes())
    ymeta = strict_json(pathlib.Path(a.yggdrasil_artifact).read_bytes())
    wzip = pathlib.Path(a.wingless_zip).read_bytes()
    yzip = pathlib.Path(a.yggdrasil_zip).read_bytes()
    need(len(wzip) < 2*1024*1024 and len(yzip) <= 8*1024*1024,
         "ARCHIVE_SIZE")
    output = verify_archives(wrun,wmeta,wzip,yrun,ymeta,yzip)
    pathlib.Path(a.out).write_text(json.dumps(output,sort_keys=True,
          indent=2)+"\n",encoding="utf-8")
    print("F85_AUTHENTIC_DUAL_LANE_FIT_NEGATIVES=QUARANTINED")
    print("F85_OPTIMIZER_TRAINING_AND_ORIGINAL_DISPATCH=DENIED")

if __name__ == "__main__":
    try:
        main()
    except (Denied,w84.Denied,y83.NotQualified,ValueError,TypeError,
            KeyError,OSError,UnicodeError):
        print("F85_AUDIT=BLOCKED",file=sys.stderr)
        raise SystemExit(1)
