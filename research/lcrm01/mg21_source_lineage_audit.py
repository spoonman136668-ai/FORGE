#!/usr/bin/env python3
"""MG21 immutable prospective lineage gate. No environment imports or reset/step.

This checks all explicitly pinned prior source contracts, not unrelated unknown
private experiments. Any missing historical ref fails closed; no seed reassignment.
"""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg21_original_fresh_cohort_prereg.json"
SCHEMA="itd02.mg21.fresh-original-world-cohort-source-lineage.v1"
FAMILIES=("MiniGrid-DoorKey-6x6-v0","MiniGrid-UnlockPickup-v0",
          "MiniGrid-BlockedUnlockPickup-v0","MiniGrid-KeyCorridorS3R1-v0")
PARENT="be533627e9cbc7f35314257ceadbf21f5e873d4e"
PINNED_GO="ebbadd157cc1df6eabfa5a550c8876ca87dc91e9"
PINNED_YGG="f0dd99d59ce00da7ad17ff49900a1af6d2322a77"
PINNED_FARAMA="7f5853792ea7f04f75614661006d87fcf949f26d"

def encode(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")

def hash_value(v):
    return hashlib.sha256(encode(v)).hexdigest()

def command(*args):
    return subprocess.check_output(["git",*args],cwd=HERE.parents[1],stderr=subprocess.PIPE)

def audit():
    p=json.loads(PREREG.read_text(encoding="utf-8"))
    if (p.get("schema")!=SCHEMA or
        p.get("phase")!="PROSPECTIVE_FROZEN_BEFORE_NEW_ORIGINAL_FARAMA_DEV_ACTION" or
        p.get("parent_original_selected_smoke")!=PARENT or
        p.get("source_pins")!={"Farama":PINNED_FARAMA,
                               "Wingless_MG19":PINNED_GO,
                               "Yggdrasil_MG19":PINNED_YGG} or
        p["fit"]["source_records_per_actor"]!=0 or
        p["heldout"]!={"status":"NOT_ASSIGNED_NOT_RELEASED","seeds":[],
                        "prohibited_use_until_independent_authority":True} or
        not all(p["boundaries"].values())):
        raise ValueError("MG21_PROSPECTIVE_SOURCE_LINEAGE_DRIFT")
    cohorts=p["dev"]["original_farama_envs"]
    seeds=[seed for row in cohorts for seed in row["seeds"]]
    if ([row["environment"] for row in cohorts]!=list(FAMILIES)
        or [row["seeds"] for row in cohorts]!=[[946101,946103],[946201,946203],
                                              [946301,946303],[946401,946403]]
        or len(seeds)!=8 or len(set(seeds))!=8 or
        p["dev"]["per_episode_source_action_cap"]!=128 or
        p["dev"]["arms"]!=[
          "wingless_MG19_native","yggdrasil_MG19_local_cells",
          "independent_public_transition_count_conventional","uniform_original_random"]
        or p["dev"]["live_external_actions"]!=0):
        raise ValueError("MG21_DEV_FRESH_COHORT_OR_EQUAL_ARM_DRIFT")
    quarantine=p["quarantined_forever"]["seeds"]
    if quarantine!=[917001,917003,918201] or set(seeds)&set(quarantine):
        raise ValueError("MG21_ORIGINAL_SMOKE_SEED_REUSED")
    history=p["prior_custody_sources"]
    if len(history)!=10 or len({x["label"] for x in history})!=10:
        raise ValueError("MG21_HISTORICAL_ORIGINAL_WORLD_LINEAGE_INCOMPLETE")
    receipts=[]
    for item in history:
        if (item.get("repository")!="spoonman136668-ai/FORGE" or
            not re.fullmatch("[a-f0-9]{40}",item.get("commit","")) or
            not item.get("path","").startswith(("research/lcrm01/","docs/research/")) or
            not item["path"].endswith((".json",".md"))):
            raise ValueError("MG21_INVALID_HISTORICAL_PIN")
        try:
            data=command("show",item["commit"]+":"+item["path"])
            canonical_commit=command("rev-parse",item["commit"]+"^{commit}").decode().strip()
        except subprocess.CalledProcessError as exc:
            raise ValueError("MG21_PINNED_SOURCE_UNAVAILABLE:"+item["label"]) from exc
        if canonical_commit!=item["commit"]:
            raise ValueError("MG21_NONCANONICAL_COMMIT")
        text=data.decode("utf-8")
        matches=[seed for seed in seeds if re.search(r"(?<![0-9])"+str(seed)+r"(?![0-9])",text)]
        if matches:
            raise ValueError("MG21_PROSPECTIVE_DEV_SEED_ALREADY_EXPOSED:"+item["label"]+":"+str(matches))
        receipts.append({"label":item["label"],"commit":item["commit"],
                         "path":item["path"],"source_sha256":hashlib.sha256(data).hexdigest(),
                         "dev_overlap":0})
    # Check the unchanged parent ancestry and the prospective frozen contract.
    parent=command("merge-base","--is-ancestor",PARENT,"HEAD")
    assert parent==b""
    contract_hash=hashlib.sha256(PREREG.read_bytes()).hexdigest()
    out={"schema":"itd02.mg21.original-world-seed-lineage-custody-receipt.v1",
         "classification":"MG21_FROZEN_FRESH_DEV_COHORT_HISTORY_SCOPE_PASS_NO_SCIENCE",
         "frozen_contract_sha256":contract_hash,
         "dev_families":list(FAMILIES),"dev_seed_count":len(seeds),
         "dev_source_seed_identities":cohorts,
         "source_history_count":len(receipts),"historical_pins":receipts,
         "historical_source_refs_exact":True,
         "known_historical_original_world_seed_overlap":0,
         "unscanned_private_or_external_custody_not_claimed":True,
         "sealed_cohort_seeds_released":0,
         "new_original_world_actions":0,"learning_evidence":False,
         "forge_controller_or_accepted_model_modified":False,
         "original_source_pins":p["source_pins"],
         "canonical_custody_sha256":hash_value(receipts)}
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    result=audit()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("MG21_HISTORICAL_SOURCE_SEED_LINEAGE_PASS_NO_SCIENCE",result["canonical_custody_sha256"])
if __name__=="__main__":
    main()
