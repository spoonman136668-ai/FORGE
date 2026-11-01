"""H53 original V26 native read-only ledger verification.

Never open a write-capable SQLite handle. The original Database verifier remains
authoritative; the successor observer is an additional conservative witness.
"""
from __future__ import annotations
from contextlib import closing
import pathlib
import sqlite3
from f139 import h53_audit_guards as guard
from f139 import h53_successor_readonly_observer as witness
import importlib.util
import sys
from contextlib import contextmanager

@contextmanager
def original_database_class(root: pathlib.Path):
    """Load original native verifier only from preauthenticated V26 checkout."""
    root = pathlib.Path(root).resolve(strict=True)
    source = root / "f139" / "local_controller.py"
    guard.demand(source.is_file(), "ORIGINAL_NATIVE_MODULE_MISSING")
    old_path = list(sys.path)
    old_modules = {k:v for k,v in sys.modules.items() if k == "f139" or k.startswith("f139.")}
    try:
        for key in old_modules:
            sys.modules.pop(key, None)
        sys.path.insert(0, str(root))
        spec = importlib.util.spec_from_file_location("f139.local_controller", source)
        guard.demand(spec is not None and spec.loader is not None, "NATIVE_IMPORT_SPEC")
        module = importlib.util.module_from_spec(spec)
        # Native G54 verification imports this canonical name again and requires
        # exact class identity. Register before execution, as normal import does.
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        yield module.Database
    finally:
        for key in list(sys.modules):
            if key == "f139" or key.startswith("f139."):
                sys.modules.pop(key, None)
        sys.modules.update(old_modules)
        sys.path[:] = old_path

def verify_native(db: pathlib.Path, *, original_root: pathlib.Path):
    db = pathlib.Path(db).resolve(strict=True)
    with original_database_class(original_root) as Database:
        cold = Database.open_readonly(db)
        try:
            cold.verify()
            meta = cold.meta()
            guard.demand(meta["source_sha"] == guard.SOURCE, "NATIVE_SOURCE_DRIFT")
            guard.demand(meta["head_seq"] >= witness.BASELINE_SEQ, "NATIVE_HEAD_REGRESSION")
        finally:
            cold.close()
    uri = db.as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=20)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        query_only = conn.execute("PRAGMA query_only").fetchone()[0]
        conn.execute("BEGIN")
        quick_check = conn.execute("PRAGMA quick_check").fetchone()[0]
        row = conn.execute("SELECT * FROM meta WHERE id=1").fetchone()
        guard.demand(row is not None, "NATIVE_META_MISSING")
        m = dict(row)
        baseline = conn.execute("SELECT sha FROM events WHERE seq=?", (witness.BASELINE_SEQ,)).fetchone()
        guard.demand(baseline is not None, "NATIVE_BASELINE_MISSING")
        guard.ledger_guard(source_sha=m["source_sha"],enabled=m["enabled"],
                           legacy_suspended=m["legacy_suspended"],
                           head_seq=m["head_seq"],baseline_sha=baseline["sha"],
                           query_only=query_only,quick_check=quick_check,cold_verified=True)
    observed = witness.ledger_observation(db)
    guard.demand(observed["head_seq"] >= witness.BASELINE_SEQ, "WITNESS_HEAD_REGRESSION")
    return {"native_cold_verify": "PASS", "query_only": True,
            "baseline_seq": observed["baseline_seq"],
            "head_seq": observed["head_seq"],
            "head_sha256": observed["head_sha256"],
            "new_events_observed": observed["new_events_observed"],
            "post_baseline_events": observed["post_baseline_events"][-100:],
            "post_baseline_events_truncated": len(observed["post_baseline_events"]) > 100,
            "unattended_cycle_verified": False}
