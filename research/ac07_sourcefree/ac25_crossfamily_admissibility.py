"""AC-25 read-only independent-family custody and no-false-transfer diagnosis.

Read exact already-qualified AC-24 source evidence plus pinned independently
authored Wingless/Yggdrasil shared public contracts and existing MG11
prospective source protocol. No original source imports, new env actions,
training, hidden-state access or protected-family first use.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

SCHEMA="forge.ac25.direct-crossfamily-transfer-admissibility-v1"
CLASSIFICATION="AC25_DIRECT_DTR_TO_MINIGRID_TRANSFER_NOT_ADMISSIBLE"
ORIGINAL_AC24_HEAD="391415d583e0c611bd1bbc34375b2ac8e562978b"
WING_HEAD="e1048a870785724ab01897c445f04c4c3d9640b1"
YGG_HEAD="851ac5866c0ebb4739272443afa9717f188fb5ef"
SHARED_CONTRACT_BLOB="550d5d2a88c44e3bf40f5ba81650a3006e8fc397"
SHARED_CONTRACT_PATH="research/itd02_crossmodel_public_contract.json"
MG11_HEAD="79a494a30dd54bd0dd1211b41d215ebf05cc29e8"
MG11_PATH="research/lcrm01/mg11_public_selected_novelty_prereg.json"
MG11_BLOB="00bf325dcf07bee87518cb4671be9efa3e903d3c"
AC24_REPORT_HASHES={
    "ubuntu-latest":"d43d3aae3b04a3f0f6c19751e7737b952e512b3a003392f6a3e21e428e7b8366",
    "windows-latest":"4b31b25c974076aaafefa7f80917e3f1bf527d99f3e1edcd3be87bd67b0d28f3",
}
SOURCE_DTR="c94e9a4cd3641588b6b8507e71ccee5c27032bdf"
SOURCE_DTR_BLOB="6af2371dce21804140ea141ccb7be14e003ba275"

def _git(root, *args):
    p=subprocess.run(["git","-C",str(root),*args],
        capture_output=True,text=True,timeout=12)
    if p.returncode:
        raise RuntimeError("AC25_PINNED_GIT_CUSTODY_FAILED")
    return p.stdout.strip()

def verify_repository_file(root,head,path,blob):
    root=Path(root).resolve(strict=True)
    if (_git(root,"rev-parse","HEAD")!=head or
        _git(root,"rev-parse","HEAD:"+path)!=blob or
        _git(root,"status","--porcelain","--untracked-files=no")):
        raise RuntimeError("AC25_ORIGINAL_REPOSITORY_OR_FILE_DRIFT")
    f=root/path
    if not f.is_file():
        raise RuntimeError("AC25_ORIGINAL_CONTRACT_FILE_MISSING")
    # Compare immutable GIT BLOBS, not checkout working-tree newline
    # conversion (Windows may materialize CRLF from identical LF blobs).
    p=subprocess.run(["git","-C",str(root),"show","HEAD:"+path],
        capture_output=True,timeout=12)
    if p.returncode:
        raise RuntimeError("AC25_IMMUTABLE_ORIGINAL_GIT_BLOB_READ_FAILED")
    return p.stdout

def read_existing_ac24(raw,os):
    if os not in AC24_REPORT_HASHES or hashlib.sha256(raw).hexdigest()!=AC24_REPORT_HASHES[os]:
        raise RuntimeError("AC25_EXACT_AC24_REPORT_SHA256_MISMATCH")
    r=json.loads(raw)
    # Metadata-only and structural contract; never learn/tune from DEV labels.
    if (r.get("schema")!="forge.ac24.fresh-original-dtr-public-development-v1" or
        r.get("source_original_commit")!=SOURCE_DTR or
        r.get("source_original_dtr_blob")!=SOURCE_DTR_BLOB or
        r.get("prior_ac23_frozen_commit")!="0d7a46142e0a391eb56dd4a4bfe5078620889fb4" or
        r.get("fit_source_episode_count")!=64 or
        r.get("dev_source_episode_count")!=32 or
        r.get("source_owned_public_actions")!=192 or
        r.get("dev_model_updates")!=0 or
        r.get("model_actions_source_selected") is not False or
        r.get("source_private_oracle_fields_admitted") is not False or
        r.get("source_ctf_do_permission_denied") is not True or
        r.get("original_scientific_first_use") is not False or
        r.get("unfamiliar_family_transfer_tested") is not False or
        r.get("scientific_admission") is not False):
        raise RuntimeError("AC25_AC24_AUTHENTIC_DEVELOPMENT_SCOPE_DRIFT")
    fit=r["source_fit"]["episodes"]
    dev=r["source_dev"]["episodes"]
    if (len(fit)!=64 or len(dev)!=32 or
        [row["seed"] for row in fit]!=list(range(761000,761064)) or
        [row["seed"] for row in dev]!=list(range(761200,761232))):
        raise RuntimeError("AC25_AC24_NEW_SEED_PROVENANCE_DRIFT")
    public_fields={"stage","observation","action","next_observation",
                   "reward","terminated","truncated","valid_actions"}
    for episode in fit+dev:
        if len(episode["events"])!=2:
            raise RuntimeError("AC25_SOURCE_DTR_TEMPORAL_LENGTH_DRIFT")
        for event in episode["events"]:
            if (set(event)!=public_fields or
                event["valid_actions"]!=[0,1] or
                event["action"] not in (0,1)):
                raise RuntimeError("AC25_SOURCE_DTR_ACTION_OR_PUBLIC_FIELD_DRIFT")
    m=r["metrics"]
    if (m["local_self_reconstruction"]["n"]!=32 or
        m["direct_ten_parameter_logistic"]["n"]!=32 or
        m["local_self_reconstruction"]["brier"]<=m["direct_ten_parameter_logistic"]["brier"] or
        m["local_self_reconstruction"]["brier"]<=m["full_history_ema"]["brier"]):
        raise RuntimeError("AC25_AC24_NEGATIVE_CONTROL_MUST_BE_RETAINED")
    return {"sha256":AC24_REPORT_HASHES[os],
            "source_original_commit":r["source_original_commit"],
            "fit_episode_count":64,"dev_episode_count":32,
            "source_actions":192,"legal_action_ids":[0,1],
            "public_event_fields":sorted(public_fields),
            "timesteps_to_terminal":2,
            "model_directed_actions":False,
            "dev_training_updates":0,
            "local_native_development_brier":m["local_self_reconstruction"]["brier"],
            "best_conventional_full_history_ema_brier":m["full_history_ema"]["brier"]}

def classify(dtr,paired,mg11):
    if paired.get("schema")!="itd02.crossmodel.public_environment_contract.v1":
        raise RuntimeError("AC25_PAIRED_PUBLIC_CONTRACT_SCHEMA_DRIFT")
    env=paired["environment"];ctrl=paired["comparison"];ban=paired["restrictions"]
    if (env["id"]!="MiniGrid-Empty-5x5-v0" or
        env["minigrid_version"]!="3.0.0" or env["gymnasium_version"]!="1.2.1" or
        env["public_observation_fields"]!=["image","direction","mission"] or
        len(ctrl["action_semantics"])!=3 or
        ctrl["action_semantics"]!=["left","right","forward"] or
        ctrl["seed_list"]!=[51,52,53] or ctrl["same_max_steps"]!=24 or
        ban.get("reserved_q1_q2_q3_sealed") is not True or
        ban.get("science_first_use") is not False or
        ban.get("forge_controller_untouched") is not True or
        "env.unwrapped" not in env["forbidden_access"] or
        "agent_pos" not in env["forbidden_access"]):
        raise RuntimeError("AC25_PAIRED_ORIGINAL_MINIGRID_CONTRACT_DRIFT")
    if (mg11.get("schema")!="itd02.mg11.original-public-selected-novelty.v1" or
        mg11.get("source_farama")!="7f5853792ea7f04f75614661006d87fcf949f26d" or
        mg11.get("source_FIT_count")!=1664 or
        mg11.get("source_FIT_seeds")!=[50101,50103,50107,50109,50111,50113,50117,50119] or
        mg11.get("development_seeds")!=[71301,71303,71307] or
        mg11.get("max_original_steps")!=192 or
        mg11.get("actual_external_live_actions")!=0 or
        len(mg11["roles"])!=7 or
        "wingless_go_dk12" not in mg11["roles"] or
        "yggdrasil_r16" not in mg11["roles"] or
        mg11.get("new_go")!="1b5b3ed525c8905252b0919790e79c632b82c1e1" or
        mg11.get("new_ygg")!="63dff5d870e158d4197ef39cf86d9339d3eccc16"):
        raise RuntimeError("AC25_AUTHENTIC_MG11_ORIGINAL_SOURCE_PRE_REG_DRIFT")
    # DTR fitted binary terminal classifier was never a source-selected
    # MiniGrid actor. No implicit two-action to 3/7-action projection.
    if dtr["legal_action_ids"]!=[0,1] or dtr["timesteps_to_terminal"]!=2:
        raise RuntimeError("AC25_DTR_INVALID_TRANSFER_START")
    return {
      "classification":CLASSIFICATION,
      "source_roles":"DTR already consumed public development vs independently designed original MiniGrid actors",
      "dtr_action_count":2,
      "paired_empty5_public_action_count":len(ctrl["action_semantics"]),
      "mg11_original_doorkey_public_action_count":7,
      "dtr_source_public_fields":dtr["public_event_fields"],
      "minigrid_source_public_fields":env["public_observation_fields"],
      "dtr_two_stage_binary_outcome":True,
      "paired_empty5_steps":ctrl["same_max_steps"],
      "mg11_original_doorkey_max_steps":mg11["max_original_steps"],
      "valid_native_learned_encoder_for_image_direction_mission":False,
      "valid_cross_family_action_mapping_frozen_before_test":False,
      "same_original_learning_and_action_interface":False,
      "frozen_dtr_reward_predictor_is_minigrid_actor":False,
      "public_visual_and_binary_dtr_observations_interchangeable":False,
      "mg11_continuity_results_owned_by_existing_native_program":True,
      "paired_q1_q2_q3_sealed":True,
      "scientific_first_use":False,
      "scientific_transfer_established":False,
      "scientific_admission":False
    }

def run(dtr_path,os,wing,ygg,mg11,out):
    ac24=read_existing_ac24(Path(dtr_path).read_bytes(),os)
    wingraw=verify_repository_file(wing,WING_HEAD,SHARED_CONTRACT_PATH,SHARED_CONTRACT_BLOB)
    yggraw=verify_repository_file(ygg,YGG_HEAD,SHARED_CONTRACT_PATH,SHARED_CONTRACT_BLOB)
    mgraw=verify_repository_file(mg11,MG11_HEAD,MG11_PATH,MG11_BLOB)
    if wingraw!=yggraw:
        raise RuntimeError("AC25_PAIRED_NATIVE_PUBLIC_SOURCE_CONTRACT_NOT_BYTE_EQUAL")
    p=json.loads(wingraw)
    g=json.loads(mgraw)
    classification=classify(ac24,p,g)
    result={
      "schema":SCHEMA,
      "scope":"READ_ONLY_EXACT_SOURCE_CROSS_FAMILY_TRANSFER_NEGATIVE",
      "ac24_head":ORIGINAL_AC24_HEAD,
      "ac24_original_development":ac24,
      "wingless_paired_source_commit":WING_HEAD,
      "yggdrasil_paired_source_commit":YGG_HEAD,
      "wingless_ygg_public_contract_git_blob":SHARED_CONTRACT_BLOB,
      "wingless_ygg_contract_bytes_identical":True,
      "existing_forge_mg11_source_commit":MG11_HEAD,
      "existing_mg11_original_source_pre_reg_blob":MG11_BLOB,
      "old_models_or_original_source_modified":False,
      "new_original_minigrid_episodes_executed":0,
      "new_original_dtr_episodes_executed":0,
      "protected_family_holdout_read":False,
      "native_training_or_transfer_run":False,
      "controller_queue_authority_modified":False,
      "scientific_first_use":False,
      **classification
    }
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--ac24-report",type=Path,required=True)
    p.add_argument("--os",choices=tuple(AC24_REPORT_HASHES),required=True)
    p.add_argument("--wing",type=Path,required=True)
    p.add_argument("--ygg",type=Path,required=True)
    p.add_argument("--mg11",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    x=p.parse_args()
    r=run(x.ac24_report,x.os,x.wing,x.ygg,x.mg11,x.out)
    print("AC25_PAIRED_PUBLIC_CONTRACT_CUSTODY=PASS")
    print("AC25_DTR_TO_MINIGRID_DIRECT_TRANSFER="+r["classification"])
    print("AC25_NEW_ORIGINAL_SOURCE_EPISODES=ZERO")
    print("AC25_SCIENTIFIC_ADMISSION=NO")
