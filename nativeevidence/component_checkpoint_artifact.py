"""Read-only forensic verification of source-free native component checkpoint ZIPs.

Not portable-checkpoint.v1 and not model acceptance. Does not execute, import,
extract, evaluate or train artifact contents. Caller must pin source commit.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import zipfile

WING = "wingless.nci04l5b.native-cold-state-sourcefree.dev.v1"
YGG = "ygg.itd02.native-checkpoint-cold-artifact.sourcefree.dev.v1"
PREFIX = "ygg.itd02.native-checkpoint-prefix.sourcefree.dev.v1"
COHORT = "ygg.itd02.public-native-cohort.dev.v1"
JOURNAL = "ygg.itd02.public-fit-source-custody.dev.v1"
NATIVE = "ygg.itd02.native_task_ring_bridge.source_only.v2"
FIXTURE = "7175cd5b9b9ddf35a21b90939cc9250cb32fc6126fd4b4e3bd92e02aa595ee6b"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
WING_FILES = set(("evidence.json", "prefix.snapshot", "full/final.snapshot",
                  "resumed/final.snapshot", "full/go.mod", "resumed/go.mod",
                  "full/probe.go", "resumed/probe.go"))
YGG_FILES = {"evidence.json", "prefix-evidence.json", "cohort/cohort.json"} | {
    f"cohort/episode-{i:06d}/{p}" for i in range(1, 4)
    for p in ("learned-checkpoint.bin", "public-events.jsonl")
}

class Rejected(ValueError):
    pass

def need(ok, why):
    if not ok:
        raise Rejected("FORGE_SOURCEFREE_COMPONENT_" + why)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")

def hex64(value):
    return type(value) is str and SHA64.fullmatch(value) is not None

def unique(pairs):
    result = {}
    for k, v in pairs:
        need(k not in result, "DUPLICATE_JSON_KEY")
        result[k] = v
    return result

def reject_nonfinite(_):
    raise Rejected("FORGE_SOURCEFREE_COMPONENT_NONFINITE_JSON")

def decode(raw):
    try:
        return json.loads(raw, object_pairs_hook=unique,
                          parse_constant=reject_nonfinite)
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, Rejected):
            raise
        raise Rejected("FORGE_SOURCEFREE_COMPONENT_BAD_JSON") from exc

def archive(path, expected):
    path = Path(path)
    need(path.is_file() and not path.is_symlink() and
         0 < path.stat().st_size <= 2 * 1024 * 1024, "ZIP_SIZE")
    try:
        with zipfile.ZipFile(path) as z:
            infos = z.infolist()
            names = [x.filename for x in infos]
            need(len(infos) == len(expected) and len(set(names)) == len(infos)
                 and set(names) == expected, "ZIP_FILE_INVENTORY")
            total = 0
            contents = {}
            for item in infos:
                name = item.filename
                need(not item.is_dir() and not name.startswith("/") and
                     "\\" not in name and
                     all(p not in ("", ".", "..") for p in name.split("/")) and
                     not (item.flag_bits & 1) and
                     not stat.S_ISLNK(item.external_attr >> 16) and
                     item.file_size <= 256 * 1024 and
                     item.compress_type in (zipfile.ZIP_DEFLATED, zipfile.ZIP_STORED),
                     "ZIP_UNTRUSTED_MEMBER")
                total += item.file_size
                need(total <= 2 * 1024 * 1024, "ZIP_EXPANSION")
                payload = z.read(item)
                need(len(payload) == item.file_size, "ZIP_TRUNCATED")
                contents[name] = payload
            return contents
    except (zipfile.BadZipFile, EOFError, OSError,
            RuntimeError, NotImplementedError) as exc:
        raise Rejected("FORGE_SOURCEFREE_COMPONENT_ZIP_INVALID") from exc

def report(project, commit):
    return {"schema": "forge.sourcefree-native-component-archive-readonly.v1",
            "project": project, "source_commit_sha": commit,
            "internal_archive_integrity": "PASS",
            "source_owner_authentication": "UNVERIFIED_EXTERNAL",
            "process_restoration": "CI_REPORTED_NOT_REEXECUTED",
            "component_fixture_only": True,
            "portable_model_accepted": False, "learning_gain": "UNVERIFIED",
            "retention": "UNVERIFIED", "transfer": "UNVERIFIED",
            "matched_control_superiority": "UNVERIFIED",
            "cross_platform_byte_parity": "UNVERIFIED",
            "scientific_acceptance": False, "optimizer_reward": False,
            "model_promotion": False, "controller_mutation": False}

def wingless(path, source_sha):
    z = archive(path, WING_FILES)
    d = decode(z["evidence.json"])
    need(type(d) is dict and d.get("schema") == WING and
         d.get("project") == "Wingless" and
         d.get("source_commit_sha") == source_sha and
         d.get("independent_process_continuation") is True and
         d.get("source_free_generated_fixture") is True and
         d.get("stale_checkpoint_rejected") is True and
         all(d.get(k) is False for k in
             ("scientific_accepted", "promotion_authority",
              "accepted_model_or_portable_state_former",
              "independent_source_first_use")) and
         d.get("matched_baseline_superiority") == "UNVERIFIED" and
         d.get("unfamiliar_transfer") == "UNVERIFIED" and
         type(d.get("learned_observations")) is int and
         d["learned_observations"] == 2 and
         hex64(d.get("source_probe_sha256")), "WING_RECEIPT")
    # The recorded digest is the SHA-256 of the generated probe.go file,
    # not the snapshot. Both original and resumed fixture implementations
    # must match it before any archive-integrity PASS is permitted.
    need(all(sha(z[name]) == d["source_probe_sha256"]
             for name in ("full/probe.go", "resumed/probe.go")),
         "WING_PROBE_HASH")
    # A source-matched probe coupled with a substituted module is also
    # insufficient evidence of the claimed generated native fixture.
    need(all(z[name] ==
             b"module wingless.nci04g5.privateprobe\n\ngo 1.20\n"
             for name in ("full/go.mod", "resumed/go.mod")),
         "WING_MODULE_SOURCE")
    fields = (("prefix.snapshot", "prefix_checkpoint_sha256"),
              ("full/final.snapshot", "uninterrupted_checkpoint_sha256"),
              ("resumed/final.snapshot", "continued_checkpoint_sha256"))
    for path, field in fields:
        need(hex64(d.get(field)) and z[path] and
             sha(z[path]) == d[field], "WING_CHECKPOINT_HASH")
    need(z["full/final.snapshot"] == z["resumed/final.snapshot"] and
         z["prefix.snapshot"] != z["resumed/final.snapshot"],
         "WING_CONTINUATION_MISMATCH")
    r = report("Wingless", source_sha)
    r.update(parent_checkpoint_sha256=d["prefix_checkpoint_sha256"],
             child_checkpoint_sha256=d["continued_checkpoint_sha256"],
             uninterrupted_equals_resumed="PASS", reported_training_observations=2,
             stale_rejection="CI_REPORTED")
    return r

def check_journal(raw, row, episode):
    need(raw.endswith(b"\n") and len(raw) <= 512000,
         "YGG_JOURNAL_INCOMPLETE")
    events = [decode(line) for line in raw.splitlines()]
    kinds = ("header", "reset_intent", "reset_result", "step_intent",
             "step_result", "step_intent", "step_result",
             "checkpoint_intent", "checkpoint_result")
    need(len(events) == len(kinds), "YGG_JOURNAL_EVENT_COUNT")
    prev = "0" * 64
    for i, (entry, kind) in enumerate(zip(events, kinds)):
        need(type(entry) is dict and
             set(entry) == {"seq", "prev", "event", "digest"} and
             type(entry["seq"]) is int and entry["seq"] == i and
             entry["prev"] == prev and hex64(entry["digest"]) and
             type(entry["event"]) is dict and entry["event"].get("kind") == kind,
             "YGG_EVENT_SEQUENCE")
        need(sha(canonical({"seq": i, "prev": prev,
                            "event": entry["event"]})) == entry["digest"],
             "YGG_JOURNAL_HASH_CHAIN")
        prev = entry["digest"]
    need(events[0]["event"] == {
         "kind": "header", "schema": JOURNAL, "source_sha256": FIXTURE,
         "episode": f"ep-{episode:06d}", "max_steps": 2,
         "role": "OWNER_PUBLIC_FIT_DEVELOPMENT_ONLY"
    } and events[1]["event"] == {"kind": "reset_intent"} and
         events[2]["event"] == {
             "kind": "reset_result", "observation": "docked_MRV"
         }, "YGG_SOURCE_BOUNDARY")
    actions = []
    for j in range(2):
        action, outcome = events[3 + 2*j]["event"], events[4 + 2*j]["event"]
        need(set(action) == {"kind", "action", "index"} and
             type(action.get("index")) is int and action["index"] == j and
             type(action.get("action")) is str and
             re.fullmatch(r"[A-Za-z]{1,64}", action["action"]) is not None,
             "YGG_ACTION")
        need(outcome == {"kind": "step_result", "observation": "Nothing",
                         "reward": 0, "terminal": False, "truncated": j == 1},
             "YGG_PUBLIC_CONSEQUENCE")
        actions.append(action["action"])
    need(events[7]["event"] == {
             "kind": "checkpoint_intent", "sha256": row["checkpoint_sha256"]
         } and events[8]["event"] == {
             "kind": "checkpoint_result", "sha256": row["checkpoint_sha256"]
         } and prev == row["journal_head"], "YGG_CHECKPOINT_COMMIT")
    return actions

def yggdrasil(path, source_sha):
    z = archive(path, YGG_FILES)
    d, prefix, cohort = (decode(z[k]) for k in
                         ("evidence.json", "prefix-evidence.json",
                          "cohort/cohort.json"))
    need(type(d) is dict and d.get("schema") == YGG and
         d.get("project") == "Yggdrasil" and
         d.get("source_commit_sha") == source_sha and
         d.get("source_free_fixture_sha256") == FIXTURE and
         d.get("source_authentication") == "SELF_DECLARED_FIXTURE_ONLY" and
         d.get("independent_process_continuation") is True and
         d.get("previous_episodes_skipped_without_replay") == 2 and
         type(d.get("previous_episodes_skipped_without_replay")) is int and
         d.get("native_source_selected_actions") == 6 and
         type(d.get("native_source_selected_actions")) is int and
         all(d.get(k) is False for k in
             ("actual_original_world_executed", "scientific_first_use",
              "scientific_accepted", "successor_authority",
              "promotion_authority", "portable_16_slot_accepted_model")) and
         d.get("retention_vs_fresh_control") == "UNVERIFIED" and
         d.get("unfamiliar_transfer") == "UNVERIFIED", "YGG_RECEIPT")
    need(type(prefix) is dict and prefix.get("schema") == PREFIX and
         prefix.get("project") == "Yggdrasil" and
         prefix.get("source_commit_sha") == source_sha and
         prefix.get("source_free_fixture_sha256") == FIXTURE and
         prefix.get("scientific_first_use") is False and
         prefix.get("promotion_authority") is False, "YGG_PREFIX")
    need(cohort == {
         "schema": COHORT, "episodes": 3, "max_steps": 2,
         "protected_first_use": False,
         "role": "OWNER_PUBLIC_FIT_DEVELOPMENT_ONLY",
         "source_sha256": FIXTURE
    }, "YGG_COHORT")
    rows = d.get("checkpoint_history")
    need(type(rows) is list and len(rows) == 3 and
         all(type(row) is dict for row in rows) and
         prefix.get("checkpoints") == rows[:2] and
         prefix.get("native_model_identities") == rows[1].get("native_model_identities") and
         d.get("native_model_identities") == rows[2].get("native_model_identities") and
         hex64(d.get("parent_checkpoint_sha256")) and
         hex64(d.get("child_checkpoint_sha256")) and
         d["parent_checkpoint_sha256"] == rows[1].get("checkpoint_sha256") and
         d["child_checkpoint_sha256"] == rows[2].get("checkpoint_sha256"),
         "YGG_PARENT_CHILD_IDENTITY")
    identities, hashes, actions = [], [], []
    for i, row in enumerate(rows, 1):
        models = row.get("native_model_identities")
        need(type(row.get("episode")) is int and row["episode"] == i and
             type(row.get("steps")) is int and row["steps"] == 2 and
             type(row.get("checkpoint_bytes")) is int and
             0 < row["checkpoint_bytes"] <= 65536 and
             all(hex64(row.get(k)) for k in
                 ("checkpoint_sha256", "journal_sha256", "journal_head")) and
             type(models) is dict and
             all(hex64(models.get(k)) for k in ("native", "memory")),
             "YGG_ROW")
        root = f"cohort/episode-{i:06d}/"
        raw, journal = (z[root + k] for k in
                        ("learned-checkpoint.bin", "public-events.jsonl"))
        need(len(raw) == row["checkpoint_bytes"] and
             sha(raw) == row["checkpoint_sha256"] and
             sha(journal) == row["journal_sha256"], "YGG_CONTENT_HASH")
        env = decode(raw)
        need(type(env) is dict and set(env) == {"body", "sha256"} and
             type(env.get("body")) is dict and
             env["body"].get("schema") == NATIVE and
             hex64(env.get("sha256")) and
             sha(canonical(env["body"])) == env["sha256"] and
             type(env["body"].get("transitions")) is int and
             env["body"]["transitions"] == 2 * i and
             env["body"].get("observation") is None and
             env["body"].get("frozen_native_sha256") is None,
             "YGG_NATIVE_ENVELOPE")
        actions.extend(check_journal(journal, row, i))
        hashes.append(row["checkpoint_sha256"])
        identities.append(models["native"])
    need(len(set(hashes)) == 3 and len(set(identities)) == 3,
         "YGG_STATE_NOT_CHANGING")
    r = report("Yggdrasil", source_sha)
    r.update(parent_checkpoint_sha256=d["parent_checkpoint_sha256"],
             child_checkpoint_sha256=d["child_checkpoint_sha256"],
             journal_integrity="PASS", reported_episodes=3,
             reported_actions=actions, original_source_executed=False)
    return r

def inspect(path, *, project, source_sha):
    need(project in ("Wingless", "Yggdrasil") and
         type(source_sha) is str and SHA40.fullmatch(source_sha) is not None,
         "EXTERNAL_PROJECT_AND_COMMIT_REQUIRED")
    return (wingless(path, source_sha) if project == "Wingless"
            else yggdrasil(path, source_sha))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--project", required=True, choices=("Wingless","Yggdrasil"))
    p.add_argument("--source-sha", required=True)
    a = p.parse_args()
    print(json.dumps(inspect(a.archive, project=a.project, source_sha=a.source_sha),
                     sort_keys=True, separators=(",", ":")))

if __name__ == "__main__":
    main()
