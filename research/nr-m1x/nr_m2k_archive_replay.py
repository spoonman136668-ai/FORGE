"""NR-M2K: read-only original MG56 artifact replay into the exact NR-M2J analyzer.

No HTTP, no original Farama import/reset/step, no actor or model actions.
The input is permanently EXPOSED original development evidence. Even if its
pinned artifact hash matches, this reader cannot grant science first-use.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import zipfile

from nr_m2j_source_cycles import audit_exposed_episode
from nr_m2i_decision_evidence import canonical, sha256

PREREG = pathlib.Path(__file__).with_name("NR_M2K_PREREG.json")
ROLE_ON = "mg56_mission_conditioned_symbolic_novelty_prediction_enabled"
ROLE_OFF = "mg56_mission_conditioned_symbolic_novelty_prediction_disabled"
ROLES = frozenset((ROLE_ON, ROLE_OFF))
EXPECTED_PROCESS_MEMBERS = frozenset((
    "first.json", "second.json", "first.log", "second.log", "comparison.log",
    "first-resources.json", "second-resources.json",
    "mg33c-synthetic.json",
))
SCHEMA = "forge.nr-m2k.original-mg56-exposed-dev-dual-source-replay.v1"
MAX_ZIP = 16_000_000
MAX_PROCESS_BYTES = 515_000_000

def _byte_sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _config():
    d = json.loads(PREREG.read_text(encoding="utf8"))
    if (d["schema"] != "forge.nr-m2k.authentic-original-dev-archive-readonly-replay-prereg.v1"
        or d["phase"] != "FROZEN_SOURCE_ONLY_ARCHIVE_QUALIFICATION_BEFORE_NEW_EXECUTABLE"
        or d["parent"]["pr"] != 1267):
        # Never infer source admission from a configuration's declared values.
        raise ValueError("M2K_ORIGINAL_SOURCE_PROTOCOL_DRIFT")
    if d["parent"]["exact_fully_qualified_head"] != "508f70fd3b5c8ff2291b57de36e7b1dc80d7b301":
        raise ValueError("M2K_PARENT_IDENTITY_DRIFT")
    if d["original_owner"]["zip_sha256"] != "25575d33723017be52ed57f014c6cea8baaa34bb9bc1616ad876f372d66b2a2c":
        raise ValueError("M2K_ARCHIVE_IDENTITY_DRIFT")
    if d["original_owner"]["source_canonical_sha256"] != "69dbc08751f65013874eec1c1e32c108fb51fb356820474b1702bf08bae6e019":
        raise ValueError("M2K_ORIGINAL_SOURCE_CUSTODY_DRIFT")
    if any(d["no_authority"].values()):
        raise ValueError("M2K_NO_FIRST_USE_BOUNDARY_DRIFT")
    return d

def _process(container, member, d):
    if (type(container) is not dict or
        container.get("schema") != "itd02.mg56.original-public-mission-symbolic-novelty-predictor.dev.v1" or
        container.get("canonical_source_sha256") != d["original_owner"]["source_canonical_sha256"]):
        raise ValueError("M2K_ORIGINAL_PROCESS_SOURCE_SHA_MISMATCH")
    source = container.get("source")
    if (type(source) is not dict or
        source.get("schema") != container["schema"] or
        source.get("source_original_Farama") != "7f5853792ea7f04f75614661006d87fcf949f26d" or
        source.get("scientific_first_use") is not False or
        source.get("zero_external_actions") is not True or
        source.get("original_selected_action_count") != d["original_owner"]["original_selected_actions"]):
        raise ValueError("M2K_ORIGINAL_SOURCE_ROLE_OR_AUTHORITY_DRIFT")
    episodes = source.get("original_234_episodes")
    if type(episodes) is not list or len(episodes) != d["original_owner"]["original_episodes"]:
        raise ValueError("M2K_ORIGINAL_EPISODE_COHORT_DRIFT")
    if sum(x["original_source_actions"] for x in episodes) != d["original_owner"]["original_selected_actions"]:
        raise ValueError("M2K_ORIGINAL_ACTION_TOTAL_DRIFT")
    chosen = [x for x in episodes if x.get("role") in ROLES]
    if len(chosen) != 18:
        raise ValueError("M2K_CANDIDATE_EPISODE_COUNT_DRIFT")
    identities = set()
    reports = []
    for ep in chosen:
        ident = (ep["family"], ep["seed_dev_exposed"], ep["role"])
        if ident in identities:
            raise ValueError("M2K_DUPLICATED_ORIGINAL_SEED_ROLE")
        identities.add(ident)
        result = audit_exposed_episode(ep["source_events"], ep["source_events_sha256"])
        if (result["selected_original_actions"] != ep["original_source_actions"] or
            result["source_episode_sha256"] != ep["source_events_sha256"] or
            result["positive_original_terminal_goal_steps"] != ep["original_terminal_goal_rewards"] or
            ep["public_start_sha256"] != ep["source_events"][0]["before_sha256"]):
            raise ValueError("M2K_MG56_EPISODE_COUNTER_DISAGREEMENT")
        reports.append({
            "family": ep["family"], "seed": ep["seed_dev_exposed"],
            "role": ep["role"], "source_events_sha256": ep["source_events_sha256"],
            "source_original_actions": result["selected_original_actions"],
            "source_selected_turns": result["source_selected_turn_actions"],
            "two_step_cycles": result["two_step_cycles"],
            "four_step_cycles": result["four_step_cycles"],
            "closed_cycle_action_cost": result["closed_cycle_action_cost"],
            "closed_cycle_zero_new_exact_views": result["closed_cycle_zero_new_exact_public_action_cost"],
            "closed_cycle_zero_new_symbolic_scenes": result["closed_cycle_zero_new_symbolic_scene_action_cost"],
            "genuine_original_goals": result["positive_original_terminal_goal_steps"],
            "cycle_detail_sha256": sha256(canonical(result["cycles"])),
        })
    if len({(x["family"], x["seed"]) for x in reports}) != 9:
        raise ValueError("M2K_ORIGINAL_SOURCE_FAMILY_SEEDS_NOT_NINE")
    return sorted(reports,key=lambda x:(x["family"],x["seed"],x["role"]))

def _summarize(rows):
    summary = {}
    for arm,role in (("enabled",ROLE_ON),("disabled",ROLE_OFF)):
        rr = [x for x in rows if x["role"] == role]
        if len(rr) != 9:
            raise ValueError("M2K_MISSING_ORIGINAL_ROLE")
        summary[arm] = {
            "source_actions":sum(x["source_original_actions"] for x in rr),
            "two_step_cycles":sum(x["two_step_cycles"] for x in rr),
            "four_step_cycles":sum(x["four_step_cycles"] for x in rr),
            "cycle_action_cost":sum(x["closed_cycle_action_cost"] for x in rr),
            "zero_new_exact_view_actions":sum(x["closed_cycle_zero_new_exact_views"] for x in rr),
            "zero_new_symbolic_scene_actions":sum(x["closed_cycle_zero_new_symbolic_scenes"] for x in rr),
            "genuine_goals":sum(x["genuine_original_goals"] for x in rr),
        }
    return summary

def replay_archive(path):
    """Run on a previously downloaded, owner-pinned ZIP. Pure read-only."""
    d = _config()
    path = pathlib.Path(path)
    if not path.is_file() or path.stat().st_size > MAX_ZIP:
        raise ValueError("M2K_ZIP_MISSING_OR_TOO_LARGE")
    zip_sha = _byte_sha256(path)
    if zip_sha != d["original_owner"]["zip_sha256"]:
        raise ValueError("M2K_ZIP_BYTE_IDENTITY_MISMATCH")
    process_reports = []
    with zipfile.ZipFile(path,"r") as archive:
        infos = archive.infolist()
        if (len(infos) != len(EXPECTED_PROCESS_MEMBERS) or
            {v.filename for v in infos} != EXPECTED_PROCESS_MEMBERS or
            any(v.is_dir() or v.file_size > (MAX_PROCESS_BYTES if v.filename.endswith(".json") and v.filename in ("first.json","second.json") else 1_000_000)
                or v.flag_bits & 1 or ".." in v.filename or "/" in v.filename for v in infos)):
            raise ValueError("M2K_ORIGINAL_ZIP_MEMBER_CUSTODY_DRIFT")
        for member in ("first.json","second.json"):
            with archive.open(member,"r") as stream:
                container = json.load(stream)
            process_reports.append(_process(container,member,d))
            del container
    if process_reports[0] != process_reports[1]:
        raise ValueError("M2K_TWO_ORIGINAL_SOURCE_PROCESSES_DISAGREE")
    summary = _summarize(process_reports[0])
    expected = d["expected_development_diagnostics"]
    if (summary["enabled"]["source_actions"] != expected["enabled_source_actions"] or
        summary["disabled"]["source_actions"] != expected["disabled_source_actions"] or
        summary["enabled"]["two_step_cycles"] != expected["enabled_cycle_two"] or
        summary["enabled"]["four_step_cycles"] != expected["enabled_cycle_four"] or
        summary["enabled"]["cycle_action_cost"] != expected["enabled_cycle_action_cost"] or
        summary["enabled"]["zero_new_exact_view_actions"] != expected["enabled_cycle_zero_new_exact_views_action_cost"] or
        summary["enabled"]["zero_new_symbolic_scene_actions"] != expected["enabled_cycle_zero_new_symbolic_scenes_action_cost"] or
        summary["disabled"]["cycle_action_cost"] != expected["disabled_cycle_action_cost"] or
        summary["enabled"]["genuine_goals"] != expected["enabled_genuine_original_goals"] or
        summary["disabled"]["genuine_goals"] != expected["disabled_genuine_original_goals"] or
        summary["enabled"]["source_actions"] + summary["disabled"]["source_actions"] != expected["candidate_selected_actions"]):
        raise ValueError("M2K_EXPOSED_ORIGINAL_DEV_OBSERVATIONS_DISAGREE")
    return {
        "schema": SCHEMA, "archive_sha256": zip_sha,
        "processes_verified":2,
        "source_owner_first_use":False,
        "original_world_executed_by_replay":False,
        "source_owner_attestation":"EXTERNAL_OWNER_SOURCE_CUSTODY_REQUIRED",
        "exposed_dev_only":True,
        "matched_episodes_per_process":18,
        "per_episode_report_sha256":sha256(canonical(process_reports[0])),
        "diagnostics":summary,
        "scientific_acceptance":"NOT_ESTABLISHED",
    }

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--artifact",required=True,help="Existing verified original ZIP; never downloads or executes a world")
    args=parser.parse_args()
    print(json.dumps(replay_archive(args.artifact),sort_keys=True,separators=(",",":")))
