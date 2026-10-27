#!/usr/bin/env python3
"""FIT-only original MiniGrid R8 learner training and cold-restored custody.

Never resets a CHECK or DEV world. The independent conventional FIT result
is not substituted for native R8 learning.
"""
import hashlib
import json
import os
from pathlib import Path

import k4x_curriculum_intervention as k4x
import k4y_native_affordance as k4y
from k4u_native_minigrid import WingBridge
from itd02_r8_original_world_preflight import preflight

FIT = tuple(range(81400, 81424))


def native_train(stream, bridge_path):
    if len(stream) != 12000:
        raise ValueError("R8_NATIVE_FIT_COUNT_DRIFT")
    owner = WingBridge(bridge_path)
    try:
        for index, event in enumerate(stream, 1):
            if (type(event.get("seed")) is not int or event["seed"] not in FIT
                or event.get("family") not in ("empty", "fourrooms")
                or type(event.get("action")) is not int
                or event["action"] not in (0, 1, 2)):
                raise ValueError("R8_NATIVE_FIT_EVENT_DRIFT")
            owner.learn(event["before"], event["action"], event["after"],
                        event["reward"], event["terminal"])
        report = owner.request("snapshot")
        if report.get("updates") != 12000:
            raise ValueError("R8_NATIVE_FIT_UPDATES_DRIFT")
        raw = owner.snapshot()
    finally:
        owner.close()
    if not raw:
        raise ValueError("R8_NATIVE_FIT_EMPTY_SNAPSHOT")
    cold = WingBridge(bridge_path)
    try:
        cold.restore(raw)
        check = cold.request("snapshot")
        if check.get("updates") != 12000 or cold.snapshot() != raw:
            raise ValueError("R8_NATIVE_COLD_RESTORE_DRIFT")
    finally:
        cold.close()
    return raw


def main():
    preflight()
    bridge_path = Path(os.environ["ITD02_R8_BRIDGE"])
    if not bridge_path.is_file():
        raise ValueError("R8_NATIVE_BRIDGE_NOT_PINNED")
    old_seeds = k4y.SEEDS
    old_fit = k4x.FIT_SEEDS
    try:
        k4y.SEEDS = {**old_seeds, "FIT": FIT}
        stream, starts, audit, _, control = k4y.fit()
    finally:
        k4y.SEEDS = old_seeds
        k4x.FIT_SEEDS = old_fit
    if control is None or len(stream) != 12000 or not starts:
        raise ValueError("R8_NATIVE_FIT_SOURCE_NOT_QUALIFIED")
    if any(audit.get(f, {}).get("public_steps") != 6000 for f in ("empty", "fourrooms")):
        raise ValueError("R8_NATIVE_FIT_FAMILY_BALANCE_DRIFT")
    raw = native_train(stream, bridge_path)
    root = Path(os.environ["RUNNER_TEMP"]) / "itd02-r8-native-fit"
    root.mkdir(parents=True, exist_ok=True)
    output = root / "r8-native-fit-snapshot.bin"
    if output.exists():
        raise ValueError("R8_NATIVE_FIT_REFUSE_OVERWRITE")
    output.write_bytes(raw)
    receipt = {
        "gate": "ITD02_R8_NATIVE_FIT",
        "result": "NATIVE_FIT_SNAPSHOT_COLD_RESTORED",
        "source_wingless_commit": "9061b256b9d68e4d83b3a10e51fb8b7ef365259f",
        "source_minigrid_commit": "7f5853792ea7f04f75614661006d87fcf949f26d",
        "fit_seed_range": [81400, 81423],
        "fit_public_transitions": len(stream),
        "native_fit_updates": len(stream),
        "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
        "snapshot_bytes": len(raw),
        "cold_restore_identical": True,
        "check_episodes": 0, "development_episodes": 0,
        "scientific_first_use": False, "scientific_accepted": False,
    }
    (root / "native-fit-receipt.json").write_text(json.dumps(receipt, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
