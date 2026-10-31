"""Opt-in, disposable F139 SQLite initialization comparison; not production code.

Run explicitly in an authorized environment:
    python -B f139_sqlite_init_benchmark.py --iterations 20

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

SOURCE = "a" * 40
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
    parser.add_argument("--iterations", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 50:
        parser.error("iterations must be between 1 and 50")
    schema_bytes = SCHEMA_PATH.read_bytes()
    # Match Database.initialize: Path.read_text() normalizes platform newlines.
    schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
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
                if snapshots["original"] != snapshots["experimental"]:
                    original_meta, original_ddl = snapshots["original"]
                    experimental_meta, experimental_ddl = snapshots["experimental"]
                    meta_names = ("schema", "source_sha", "epoch", "enabled",
                                  "legacy_suspended", "day", "starts",
                                  "head_seq", "head_hash")
                    differences = [
                        f"meta.{name}: original={left!r} experimental={right!r}"
                        for name, left, right in zip(
                            meta_names, original_meta, experimental_meta)
                            if left != right
                    ]
                    if original_ddl != experimental_ddl:
                        differences.append(
                            f"ddl.length: original={len(original_ddl)} "
                            f"experimental={len(experimental_ddl)}")
                        for index, (left, right) in enumerate(
                                zip(original_ddl, experimental_ddl)):
                            if left != right:
                                differences.append(
                                    f"ddl.first_difference[{index}]: "
                                    f"original={left!r} experimental={right!r}")
                                break
                    raise AssertionError(
                        "SCHEMA_OR_META_IDENTITY_MISMATCH: "
                        + " | ".join(differences[:3]))
                # No SQLite connection or writable database is shared across trials.
        print(f"F139_G114G_SCHEMA_SHA256={hashlib.sha256(schema_bytes).hexdigest()}")
        print(f"F139_G114G_EQUIVALENT_SNAPSHOTS={args.iterations}")
        for method, samples in durations.items():
            ordered = sorted(samples)
            p95 = ordered[max(0, (len(ordered) * 95 + 99) // 100 - 1)]
            prefix = f"F139_G114G_{method.upper()}"
            print(f"{prefix}_SAMPLES_SECONDS="
                  + ",".join(f"{x:.6f}" for x in samples))
            print(f"{prefix}_MIN_SECONDS={ordered[0]:.6f}")
            print(f"{prefix}_MEDIAN_SECONDS={statistics.median(ordered):.6f}")
            print(f"{prefix}_P95_SECONDS={p95:.6f}")
            print(f"{prefix}_MAX_SECONDS={ordered[-1]:.6f}")
        print("F139_G114G_OFFLINE_PROBE_ONLY=PASS")
    finally:
        template.close()


if __name__ == "__main__":
    main()
