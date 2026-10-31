"""Opt-in, disposable F139 SQLite initialization comparison; not production code.

Run explicitly in an authorized environment:
    python -B f139_sqlite_init_benchmark.py --iterations 5

An experimental result is NOT qualification for a production initializer.
"""
import argparse
import hashlib
from pathlib import Path
import sqlite3
import statistics
import tempfile
import time

from f139.local_controller import Database, SCHEMA, ZERO

SOURCE = "a" * 64
SCHEMA_PATH = Path(__file__).parent / "f139" / "local_schema.sql"
INSERT_META = (
    "INSERT INTO meta(id,schema,source_sha,epoch,enabled,legacy_suspended,"
    "day,starts,head_seq,head_hash) VALUES(1,?,?,1,0,0,'1970-01-01',0,0,?)"
)


def initialize_from_memory_template(path, template):
    """Experimental only: fresh destination, distinct connection and metadata."""
    if path.exists():
        raise AssertionError("REFUSE_EXISTING_DATABASE")
    path.parent.mkdir(parents=True, exist_ok=True)
    destination = sqlite3.connect(str(path), isolation_level=None, timeout=10)
    try:
        template.backup(destination)
        destination.execute("PRAGMA synchronous=FULL")
        destination.execute(INSERT_META, (SCHEMA, SOURCE, ZERO))
    finally:
        destination.close()
    return Database(path)


def snapshot(db):
    db.verify()
    metadata = tuple(db.conn.execute(
        "SELECT schema,source_sha,epoch,enabled,legacy_suspended,"
        "day,starts,head_seq,head_hash FROM meta"
    ).fetchone())
    ddl = tuple((r["type"], r["name"], r["tbl_name"], r["sql"])
                for r in db.conn.execute(
                    "SELECT type,name,tbl_name,sql FROM sqlite_master "
                    "WHERE sql IS NOT NULL ORDER BY type,name"))
    assert db.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0
    assert db.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
    assert db.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert db.conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    return metadata, ddl


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 50:
        parser.error("iterations must be between 1 and 50")
    schema_bytes = SCHEMA_PATH.read_bytes()
    schema_text = schema_bytes.decode("utf-8")
    durations = {"original": [], "experimental": []}
    template = sqlite3.connect(":memory:", isolation_level=None)
    try:
        template.executescript(schema_text)
        with tempfile.TemporaryDirectory(prefix="f139-g114g-offline-") as d:
            root = Path(d)
            for iteration in range(args.iterations):
                # Alternate execution order to reduce trend-based bias.
                order = ("original", "experimental") if iteration % 2 == 0 else (
                    "experimental", "original")
                snapshots = {}
                for method in order:
                    filename = root / f"{iteration}-{method}.sqlite"
                    started = time.perf_counter()
                    db = (Database.initialize(filename, SOURCE) if method == "original"
                          else initialize_from_memory_template(filename, template))
                    try:
                        snapshots[method] = snapshot(db)
                    finally:
                        db.close()
                    durations[method].append(time.perf_counter() - started)
                assert snapshots["original"] == snapshots["experimental"], (
                    "SCHEMA_OR_META_IDENTITY_MISMATCH")
                # No SQLite connection or writable database is shared across trials.
        print(f"F139_G114G_SCHEMA_SHA256={hashlib.sha256(schema_bytes).hexdigest()}")
        print(f"F139_G114G_EQUIVALENT_SNAPSHOTS={args.iterations}")
        for method, samples in durations.items():
            print(f"F139_G114G_{method.upper()}_MEDIAN_SECONDS="
                  f"{statistics.median(samples):.6f}")
        print("F139_G114G_OFFLINE_PROBE_ONLY=PASS")
    finally:
        template.close()


if __name__ == "__main__":
    main()
