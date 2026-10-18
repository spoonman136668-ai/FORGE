PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;
CREATE TABLE meta (
  id INTEGER PRIMARY KEY CHECK(id=1),
  schema TEXT NOT NULL,
  source_sha TEXT NOT NULL,
  epoch INTEGER NOT NULL CHECK(epoch>0),
  enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
  legacy_suspended INTEGER NOT NULL CHECK(legacy_suspended IN (0,1)),
  day TEXT NOT NULL,
  starts INTEGER NOT NULL CHECK(starts>=0),
  head_seq INTEGER NOT NULL CHECK(head_seq>=0),
  head_hash TEXT NOT NULL
);
CREATE TABLE tasks (
  ticket TEXT PRIMARY KEY,
  lane TEXT NOT NULL CHECK(lane IN ('Wingless','Yggdrasil','Qualification')),
  source_sha TEXT NOT NULL,
  stage TEXT NOT NULL CHECK(stage IN ('READY','START_RISK','WAIT_PROVIDER','VERIFIED','QUARANTINED')),
  manifest_sha TEXT NOT NULL,
  run_id INTEGER UNIQUE,
  started_at TEXT,
  completed_at TEXT,
  evidence_dir TEXT,
  evidence_sha TEXT,
  quarantine_reason TEXT
);
CREATE UNIQUE INDEX only_one_active_f139_task ON tasks((1)) WHERE stage IN ('START_RISK','WAIT_PROVIDER');
CREATE TABLE events (
  seq INTEGER PRIMARY KEY CHECK(seq>0),
  kind TEXT NOT NULL,
  payload TEXT NOT NULL,
  prior_sha TEXT NOT NULL,
  sha TEXT NOT NULL UNIQUE
);
CREATE TRIGGER prevent_event_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'F139_APPEND_ONLY'); END;
CREATE TRIGGER prevent_event_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'F139_APPEND_ONLY'); END;
CREATE TRIGGER prevent_task_delete BEFORE DELETE ON tasks BEGIN SELECT RAISE(ABORT,'F139_TASK_HISTORY_IMMUTABLE'); END;
