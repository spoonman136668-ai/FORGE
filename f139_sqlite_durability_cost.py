"""Disposable-only SQLite WAL durability cost diagnostic.

Compares synchronous=FULL with synchronous=NORMAL solely to estimate the
cost of the durability barrier. NORMAL is NEVER a proposed production mode.
Each replicate uses a new database, fresh connection, identical event writes,
and full close/reopen chain verification.
"""
import argparse
import statistics
import tempfile
import time
from pathlib import Path

from f139.local_controller import Database

SOURCE = "a" * 40
WRITES = 50


def run_replicate(root: Path, mode: str, replicate: int):
    path = root / f"{mode}-{replicate}.sqlite"
    db = Database.initialize(path, SOURCE)
    try:
        expected = 2 if mode == "FULL" else 1
        db.conn.execute(f"PRAGMA synchronous={mode}")
        actual = db.conn.execute("PRAGMA synchronous").fetchone()[0]
        if actual != expected:
            raise AssertionError(f"F139_G114K_SYNCHRONOUS_MISMATCH:{mode}:{actual}")
        if db.conn.execute("PRAGMA journal_mode").fetchone()[0].lower() != "wal":
            raise AssertionError("F139_G114K_WAL_REQUIRED")
        samples = []
        for index in range(WRITES):
            started = time.perf_counter()
            with db.transaction():
                db.event("FIXTURE_UNTRUSTED", {
                    "diagnostic": "RAR-G114K",
                    "mode": mode,
                    "replicate": replicate,
                    "index": index,
                })
            samples.append(time.perf_counter() - started)
        before = db.meta()
    finally:
        db.close()

    # A fresh connection must verify the complete chain after close/reopen.
    reopened = Database(path)
    try:
        reopened.verify()
        after = reopened.meta()
        if before != after or after["head_seq"] != WRITES:
            raise AssertionError("F139_G114K_REOPEN_CHAIN_MISMATCH")
    finally:
        reopened.close()
    return samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--replicates", type=int, default=10)
    args = parser.parse_args()
    if not 3 <= args.replicates <= 20:
        parser.error("replicates must be 3..20")
    results = {"FULL": [], "NORMAL": []}
    with tempfile.TemporaryDirectory(prefix="f139-g114k-durability-") as temp:
        root = Path(temp)
        # Alternate modes to reduce monotonic runner-load bias.
        for rep in range(args.replicates):
            order = ("FULL", "NORMAL") if rep % 2 == 0 else ("NORMAL", "FULL")
            for mode in order:
                results[mode].extend(run_replicate(root, mode, rep))
    print(f"F139_G114K_REPLICATES={args.replicates}")
    print(f"F139_G114K_WRITES_PER_REPLICATE={WRITES}")
    print(f"F139_G114K_FRESH_DATABASES={args.replicates * 2}")
    for mode, values in results.items():
        ordered = sorted(values)
        p95 = ordered[max(0, (len(ordered) * 95 + 99) // 100 - 1)]
        print(f"F139_G114K_{mode}_COUNT={len(values)}")
        print(f"F139_G114K_{mode}_MIN_MS={ordered[0] * 1000:.3f}")
        print(f"F139_G114K_{mode}_MEDIAN_MS={statistics.median(ordered) * 1000:.3f}")
        print(f"F139_G114K_{mode}_P95_MS={p95 * 1000:.3f}")
        print(f"F139_G114K_{mode}_MAX_MS={ordered[-1] * 1000:.3f}")
    print("F139_G114K_REOPEN_VERIFY=PASS")
    print("F139_G114K_DIAGNOSTIC_ONLY_NO_PRODUCTION_PRAGMA_CHANGE=PASS")


if __name__ == "__main__":
    main()
