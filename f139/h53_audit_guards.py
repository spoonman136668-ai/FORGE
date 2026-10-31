"""Pure H53 one-shot admission checks. No network, scheduler or SQLite writes."""
import ntpath
SOURCE = "49c7b15343bea3c201fb52b498d8c0f397384afe"
RUNNER = "FORGE-CODEX-REMOTE"
OWNER = "spoonman136668-ai"
REF = "refs/heads/audit/f139-v26-h53-original-successor-ro-once-20261031"
TASK = "FORGE-F139-UnifiedController"
DB_SUFFIX = "FORGE-F139/state.sqlite"

def demand(ok, reason):
    if not ok:
        raise RuntimeError("F139_H53_" + reason)

def event_guard(event, *, actor, repository, ref, attempt, runner, sha):
    demand(repository == "spoonman136668-ai/FORGE" and actor == OWNER, "ACTOR")
    demand(ref == REF and event.get("ref") == REF, "REF")
    demand(event.get("created") is True and event.get("deleted") is False
           and event.get("forced") is False and event.get("before") == "0"*40
           and event.get("after") == sha and event.get("sender", {}).get("login") == OWNER,
           "INITIAL_PUSH")
    demand(attempt == "1" and runner == RUNNER, "RUNNER_OR_REPLAY")

def ruleset_guard(rulesets, ref=REF):
    valid = [r for r in rulesets if
             r.get("enforcement") == "active" and r.get("target") == "branch"
             and r.get("conditions", {}).get("ref_name", {}).get("include") == [ref]
             and r.get("conditions", {}).get("ref_name", {}).get("exclude") == []
             and not r.get("bypass_actors")
             and {"update", "deletion"} <= {x.get("type") for x in r.get("rules", [])}]
    demand(len(valid) == 1, "IMMUTABLE_RULESET")

def approval_guard(comments, sha):
    token = "F139-H53-ORIGINAL-READONLY-ONCE " + sha
    matching = [c for c in comments if c.get("body") == token
                and c.get("user", {}).get("login") == OWNER
                and c.get("author_association") == "OWNER"]
    demand(len(matching) == 1, "EXACT_OWNER_APPROVAL")

def source_guard(*, parents, changed, installed_sha, installed_dirty, audit_sha,
                 workflow_path, observer_path):
    demand(parents == [audit_sha, SOURCE], "NOT_DIRECT_V26_CHILD")
    demand(sorted(changed) == sorted([workflow_path, observer_path]), "SOURCE_DIFF")
    demand(installed_sha == SOURCE and not installed_dirty, "INSTALLED_SOURCE_DRIFT")

def owner_guard(*, task_name, task_state, task_sid, runner_sid, actions,
                triggers, poll_seconds, db_path, expected_db):
    demand(task_name == TASK and task_state in ("Running", "Ready"), "OWNER_TASK")
    demand(task_sid == runner_sid and bool(task_sid), "OWNER_SID")
    demand(actions == 1 and triggers == 3 and poll_seconds == 300, "OWNER_TOPOLOGY")
    demand(ntpath.normcase(ntpath.normpath(db_path)) == ntpath.normcase(ntpath.normpath(expected_db))
           and ntpath.normcase(ntpath.normpath(db_path)).endswith(ntpath.normcase(DB_SUFFIX.replace("/", "\\"))), "OWNER_DATABASE")

def ledger_guard(*, source_sha, enabled, legacy_suspended, head_seq, baseline_sha,
                 query_only, quick_check, cold_verified):
    demand(query_only == 1 and quick_check == "ok" and cold_verified, "READONLY_COLD_VERIFY")
    demand(source_sha == SOURCE and enabled == 1 and legacy_suspended == 1, "LEDGER_POLICY")
    demand(head_seq >= 350 and baseline_sha ==
           "17614edebb1b067de8112615637160e2bd7e71a4b3ac05dbab78fc360eba3d97",
           "LEDGER_BASELINE")
