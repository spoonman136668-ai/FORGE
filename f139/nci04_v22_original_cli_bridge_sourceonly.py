"""Source-only CLI identity adapter for the existing F139 original owner.

The installed python -m f139.local_controller defines its live Database and
GitHub types in __main__, while V19/V21 proofs use f139.local_controller's
canonical imported types. Only reopen the SAME original SQLite under the
already-held kernel-backed mutex. This adapter is not imported by run_once.
No new controller, scheduler, model defaults, credentials, provider or writer.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_owner_model_free_bootstrap import original_canonical_db
from f139.nci04_v21_original_renewal_composition import (
    run_original_renewal_source_only,
)


class OriginalCLIBridgeDenied(ValueError):
    pass


def _original_api_identity(db: object, api: object, db_path: Path) -> None:
    """Authenticate the actual CLI class rather than trusting its class name."""
    main = sys.modules.get("__main__")
    canonical = type(api) is GitHub
    cli = (
        type(api).__module__ == "__main__"
        and type(api).__name__ == "GitHub"
        and main is not None
        and type(api) is getattr(main, "GitHub", None)
        and type(db) is getattr(main, "Database", None)
        and isinstance(getattr(main, "__file__", None), str)
        and Path(main.__file__).resolve(strict=True) ==
            (Path(__file__).resolve().parent / "local_controller.py").resolve(strict=True)
    )
    lock_class = getattr(main, "SingleOwner", None) if cli else SingleOwner
    if (not (canonical or cli)
            or not isinstance(db_path, Path)
            or not db_path.is_file()
            or not isinstance(lock_class, type)
            or lock_class.__name__ != "SingleOwner"
            or lock_class.held(db_path.with_suffix(".lock")) is not True):
        raise OriginalCLIBridgeDenied("F139_V22_NOT_ORIGINAL_RUNNING_MUTEX")


def run_original_cli_v21_source_only(
    db: object, api: object, db_path: Path, *,
    utc_day: str,
    packet_for_terminal: Callable[[dict], dict],
    public_reader: Callable[[str], dict],
    owner_witness: Callable[[], bool],
    token: str,
    transport: Callable[[bytes, str], bytes],
) -> dict:
    """No implicit token/env/network/owner activation; all capabilities injected.

    A future guarded release must explicitly call this under the ORIGINAL
    controller mutex and must independently authenticate its source, native
    terminal, credential permission, one-POST budget and rollback custody.
    """
    _original_api_identity(db, api, db_path)
    if (not callable(owner_witness) or owner_witness() is not True
            or not all(callable(x) for x in (packet_for_terminal,
                                            public_reader, transport))
            or not callable(getattr(api, "native_repo_get", None))
            or not callable(getattr(api, "owner_model_write", None))):
        raise OriginalCLIBridgeDenied("F139_V22_EXPLICIT_CAPABILITY_REQUIRED")
    # This is a production Windows-owner witness, not just the in-process
    # lock registry. Hosted tests may only stub it with isolated fake state.
    from f139.local_controller import native_original_running_publisher_profile
    if native_original_running_publisher_profile(db_path) is not True:
        raise OriginalCLIBridgeDenied("F139_V22_ORIGINAL_WINDOWS_OWNER_NOT_ATTESTED")

    canonical_db, close = original_canonical_db(db, db_path)
    try:
        return run_original_renewal_source_only(
            canonical_db, utc_day=utc_day,
            packet_for_terminal=packet_for_terminal,
            public_reader=public_reader,
            original_get=api.native_repo_get,
            original_write=api.owner_model_write,
            owner_witness=owner_witness,
            token=token, transport=transport)
    finally:
        if close:
            canonical_db.close()
