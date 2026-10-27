#!/usr/bin/env python3
"""Native R5 matched FIT training; no heldout original-world evaluation."""
import hashlib
import json
import os
from pathlib import Path

import k4x_curriculum_intervention as k4x
import k4y_native_affordance as k4y
from k4u_native_minigrid import WingBridge
from itd02_r8_original_world_preflight import preflight

FIT = tuple(range(81400, 81424))


def main():
    preflight()
    executable = Path(os.environ["ITD02_R5_BRIDGE"])
    if not executable.is_file():
        raise ValueError("R5_BRIDGE_MISSING")
    old_seeds, old_fit = k4y.SEEDS, k4x.FIT_SEEDS
    try:
        k4y.SEEDS = {**old_seeds, "FIT": FIT}
        stream, starts, audit, _, conventional = k4y.fit()
    finally:
        k4y.SEEDS, k4x.FIT_SEEDS = old_seeds, old_fit
    if (conventional is None or len(stream) != 12000 or not starts or
        any(audit[f]["public_steps"] != 6000 for f in ("empty", "fourrooms"))):
        raise ValueError("R5_MATCHED_FIT_SOURCE_NOT_QUALIFIED")
    owner = WingBridge(executable)
    try:
        for index, e in enumerate(stream, 1):
            if (e.get("family") not in ("empty", "fourrooms")
                or type(e.get("seed")) is not int or e["seed"] not in FIT
                or type(e.get("action")) is not int or e["action"] not in (0, 1, 2)):
                raise ValueError("R5_MATCHED_FIT_EVENT_INVALID")
            owner.learn(e["before"], e["action"], e["after"], e["reward"], e["terminal"])
        before = owner.request("snapshot")
        if before.get("updates") != len(stream):
            raise ValueError("R5_MATCHED_NATIVE_UPDATES_DRIFT")
        raw = owner.snapshot()
    finally:
        owner.close()
    if not raw:
        raise ValueError("R5_MATCHED_NATIVE_SNAPSHOT_EMPTY")
    cold = WingBridge(executable)
    try:
        cold.restore(raw)
        if cold.snapshot() != raw:
            raise ValueError("R5_MATCHED_NATIVE_COLD_RESTORE_DRIFT")
    finally:
        cold.close()
    out = Path(os.environ["RUNNER_TEMP"]) / "itd02-r8-r5-fit"
    out.mkdir(parents=True, exist_ok=True)
    snapshot = out / "r5-native-fit-snapshot.bin"
    receipt_file = out / "r5-native-fit-receipt.json"
    if snapshot.exists() or receipt_file.exists():
        raise ValueError("R5_MATCHED_NATIVE_REFUSE_OVERWRITE")
    snapshot.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    if hashlib.sha256(snapshot.read_bytes()).hexdigest() != digest:
        raise ValueError("R5_MATCHED_NATIVE_SAVED_HASH_DRIFT")
    receipt = {
        "gate": "ITD02_R8_MATCHED_R5_NATIVE_FIT",
        "result": "NATIVE_R5_MATCHED_FIT_SNAPSHOT_COLD_RESTORED",
        "source_wingless_r5_commit": "978825064dd6076058a1a38ae1a9a3d80e28d99e",
        "source_minigrid_commit": "7f5853792ea7f04f75614661006d87fcf949f26d",
        "fit_seed_range": [81400, 81423],
        "fit_public_transitions": 12000,
        "native_fit_updates": 12000,
        "snapshot_sha256": digest,
        "snapshot_bytes": len(raw),
        "cold_restore_identical": True,
        "check_episodes": 0, "development_episodes": 0,
        "scientific_first_use": False, "scientific_accepted": False,
    }
    receipt_file.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
