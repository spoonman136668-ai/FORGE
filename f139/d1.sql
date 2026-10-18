-- F139-A inert, local/Cloudflare D1 schema. Does not seed jobs or enable dispatch.
-- Run only in an explicitly isolated FORGE D1 database after backup qualification.
CREATE TABLE IF NOT EXISTS f139_controller (
  id INTEGER PRIMARY KEY CHECK(id=1),
  revision INTEGER NOT NULL CHECK(revision>=0),
  state_json TEXT NOT NULL,
  event_hash TEXT NOT NULL CHECK(length(event_hash)=64),
  event_kind TEXT NOT NULL,
  previous_hash TEXT NOT NULL CHECK(length(previous_hash)=64)
);
CREATE TABLE IF NOT EXISTS f139_events (
  revision INTEGER PRIMARY KEY CHECK(revision>0),
  event_hash TEXT NOT NULL UNIQUE CHECK(length(event_hash)=64),
  previous_hash TEXT NOT NULL CHECK(length(previous_hash)=64),
  event_kind TEXT NOT NULL,
  state_json TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS f139_append_event AFTER UPDATE OF revision ON f139_controller
BEGIN
  INSERT INTO f139_events(revision,event_hash,previous_hash,event_kind,state_json)
    VALUES(NEW.revision,NEW.event_hash,NEW.previous_hash,NEW.event_kind,NEW.state_json);
END;
CREATE TABLE IF NOT EXISTS f139_tasks (
  ticket TEXT PRIMARY KEY,
  lane TEXT NOT NULL CHECK(lane IN ('Wingless','Yggdrasil','Qualification')),
  source_sha TEXT NOT NULL CHECK(length(source_sha)=40),
  priority INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS f139_completed (
  ticket TEXT PRIMARY KEY,
  run_id INTEGER NOT NULL UNIQUE CHECK(run_id>0),
  source_sha TEXT NOT NULL CHECK(length(source_sha)=40),
  FOREIGN KEY(ticket) REFERENCES f139_tasks(ticket)
);
CREATE TRIGGER IF NOT EXISTS f139_no_event_update BEFORE UPDATE ON f139_events
BEGIN SELECT RAISE(ABORT,'F139_APPEND_ONLY_EVENT'); END;
CREATE TRIGGER IF NOT EXISTS f139_no_event_delete BEFORE DELETE ON f139_events
BEGIN SELECT RAISE(ABORT,'F139_APPEND_ONLY_EVENT'); END;
CREATE TRIGGER IF NOT EXISTS f139_no_completion_update BEFORE UPDATE ON f139_completed
BEGIN SELECT RAISE(ABORT,'F139_APPEND_ONLY_COMPLETION'); END;
CREATE TRIGGER IF NOT EXISTS f139_no_completion_delete BEFORE DELETE ON f139_completed
BEGIN SELECT RAISE(ABORT,'F139_APPEND_ONLY_COMPLETION'); END;
INSERT OR IGNORE INTO f139_controller(id,revision,state_json,event_hash,event_kind,previous_hash) VALUES(
  1,0,
  '{"schema":"forge.f139.unified-development-controller.v1","version":0,"epoch":1,"stage":"IDLE","active":null,"run_id":null,"started_at":null,"daily_starts":0,"utc_day":"1970-01-01","last_hash":"0000000000000000000000000000000000000000000000000000000000000000"}',
  '0000000000000000000000000000000000000000000000000000000000000000',
  'INITIAL_INERT','0000000000000000000000000000000000000000000000000000000000000000');
-- No f139_tasks rows are inserted: shadow mode and no dispatch by default.
