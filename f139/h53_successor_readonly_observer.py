"""H53 read-only successor witness. No controller invocation or writes.

Development-only source. A separate guarded, approved one-shot workflow must
authenticate the original Windows owner and invoke this witness.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import datetime as dt
import hashlib
import json
import pathlib
import sqlite3
import subprocess

BASELINE_SEQ = 350
BASELINE_SHA = "17614edebb1b067de8112615637160e2bd7e71a4b3ac05dbab78fc360eba3d97"
SOURCE_SHA = "49c7b15343bea3c201fb52b498d8c0f397384afe"
TASK_NAME = "FORGE-F139-UnifiedController"


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeError("F139_H53_" + code)


def canonical(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


# Read-only PowerShell cmdlets. No task registration, start, stop or change.
SCHEDULER_SCRIPT = """
$ErrorActionPreference='Stop'
$t=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController'
$i=Get-ScheduledTaskInfo -TaskName 'FORGE-F139-UnifiedController'
$channel='Microsoft-Windows-TaskScheduler/Operational'
$log=Get-WinEvent -ListLog $channel -ErrorAction Stop
$events=@()
$eventStatus='LOG_DISABLED'
if ($log.IsEnabled) {
  try {
    $events=@(Get-WinEvent -FilterHashtable @{LogName=$channel;StartTime=(Get-Date).AddDays(-2)} -ErrorAction Stop |
      Where-Object {$_.Message -like '*FORGE-F139-UnifiedController*'} |
      Select-Object -First 100 TimeCreated,Id,RecordId,LevelDisplayName,Message)
    $eventStatus=if ($events.Count -eq 0) {'NO_MATCHING_EVENTS'} else {'OBSERVED'}
  } catch {
    if ($_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*') {
      $eventStatus='NO_MATCHING_EVENTS'
    } else { throw }
  }
}
[pscustomobject]@{name=$t.TaskName;state=[string]$t.State;last_run=$i.LastRunTime.ToString('o');last_result=[int64]$i.LastTaskResult;next_run=$i.NextRunTime.ToString('o');event_log_enabled=[bool]$log.IsEnabled;event_status=$eventStatus;event_count=$events.Count;events=@($events | ForEach-Object {
 [pscustomobject]@{time=$_.TimeCreated.ToString('o');id=$_.Id;record_id=$_.RecordId;level=$_.LevelDisplayName}
})} | ConvertTo-Json -Depth 5 -Compress
"""


def scheduler_observation() -> dict:
    result = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-Command", SCHEDULER_SCRIPT],
                            capture_output=True, text=True, check=True, timeout=45)
    obj = json.loads(result.stdout)
    require(obj["name"] == TASK_NAME and obj["state"] in ("Running", "Ready"), "OWNER_TASK_DRIFT")
    return obj


def ledger_observation(db: pathlib.Path) -> dict:
    # immutable=1 is inappropriate for a live WAL database; use ro/query_only
    # with a single consistent SQLite read transaction.
    uri = db.resolve(strict=True).as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=20)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        require(conn.execute("PRAGMA query_only").fetchone()[0] == 1, "NOT_QUERY_ONLY")
        conn.execute("BEGIN")
        require(conn.execute("PRAGMA quick_check").fetchone()[0] == "ok", "QUICK_CHECK")
        meta = dict(conn.execute("SELECT * FROM meta WHERE id=1").fetchone())
        require(meta["source_sha"] == SOURCE_SHA and meta["enabled"] == 1, "SOURCE_POLICY_DRIFT")
        require(meta["head_seq"] >= BASELINE_SEQ, "HEAD_REGRESSION")
        previous = "0" * 64
        expected_seq = 1
        baseline_found = False
        subsequent = []
        for row in conn.execute("SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq"):
            e = dict(row)
            seq = e["seq"]
            require(seq == expected_seq and e["prior_sha"] == previous, "CHAIN_LINK_DRIFT")
            expected_seq += 1
            payload = json.loads(e["payload"])
            expected = hashlib.sha256(canonical({
                "seq": seq, "prior_sha": e["prior_sha"],
                "kind": e["kind"], "payload": payload
            })).hexdigest()
            require(expected == e["sha"], "CHAIN_HASH_DRIFT")
            if seq == BASELINE_SEQ:
                require(e["sha"] == BASELINE_SHA, "BASELINE_HASH_DRIFT")
                baseline_found = True
            if seq > BASELINE_SEQ:
                subsequent.append({"seq": seq, "kind": e["kind"],
                                   "ticket": payload.get("ticket") if isinstance(payload, dict) else None,
                                   "sha": e["sha"]})
            previous = e["sha"]
        require(baseline_found and meta["head_seq"] == BASELINE_SEQ + len(subsequent),
                "CHAIN_LENGTH_DRIFT")
        require(meta["head_hash"] == previous, "HEAD_HASH_DRIFT")
        return {"baseline_seq": BASELINE_SEQ, "baseline_sha256": BASELINE_SHA,
                "head_seq": meta["head_seq"], "head_sha256": previous,
                "post_baseline_events": subsequent,
                "new_events_observed": len(subsequent) > 0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=pathlib.Path)
    args = parser.parse_args()
    scheduler = scheduler_observation()
    ledger = ledger_observation(args.database)
    # New events are not automatically unattended execution proof. Their
    # origin and terminal receipts require independent authenticated review.
    print(json.dumps({
        "schema": "forge.f139.h53.original-owner-successor-readonly.v1",
        "observed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_sha": SOURCE_SHA,
        "scheduler": scheduler,
        "ledger": ledger,
        "unattended_cycle_verified": False,
        "unattended_cycle_status": "REQUIRES_EVENT_AND_PROVIDER_RECEIPT_CORRELATION",
        "original_database_writes": 0,
        "owner_task_mutations": 0,
        "scientific_first_use_authorized": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
