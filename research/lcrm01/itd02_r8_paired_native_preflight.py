#!/usr/bin/env python3
"""Paired native checkpoint smoke: identical legal synthetic observations, no worlds.

Each original model retains its own choice and matching feedback custody.
All test operations happen in disposable cold processes after loading artifacts.
"""
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

from k4u_native_minigrid import WingBridge

PINS = {
    "r5": ("r5-native-fit-snapshot.bin", "r5-native-fit-receipt.json",
           "357acd102b3909c4c27131bdec258b7532f6d1a01b70d67ef4cb01e9ed8e8c56"),
    "r8": ("r8-native-fit-snapshot.bin", "native-fit-receipt.json",
           "cb873b9371b1a374a213b0dfd19357915c69a44d4fcdd550c5179d4bfa0b9a0a"),
}

def read_checkpoint(path, method):
    filename, receipt_name, expected = PINS[method]
    with zipfile.ZipFile(path) as z:
        if set(z.namelist()) != {filename, receipt_name}:
            raise ValueError("R8_PAIR_ARTIFACT_MEMBERS_DRIFT")
        data = z.read(filename)
        receipt = json.loads(z.read(receipt_name))
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("R8_PAIR_CHECKPOINT_HASH_DRIFT")
    if any((receipt.get("snapshot_sha256") != expected,
            receipt.get("native_fit_updates") != 12000,
            receipt.get("fit_public_transitions") != 12000,
            receipt.get("fit_seed_range") != [81400, 81423],
            receipt.get("check_episodes") != 0,
            receipt.get("development_episodes") != 0,
            receipt.get("scientific_accepted") is not False)):
        raise ValueError("R8_PAIR_RECEIPT_DRIFT")
    return data

def smoke(model, executable, snapshot):
    bridge = WingBridge(executable)
    try:
        bridge.restore(snapshot)
        if bridge.snapshot() != snapshot:
            raise ValueError("R8_PAIR_RESTORE_DRIFT")
        bridge.request("episode_start")
        # Legal public schema; deliberate fixture, never an original MiniGrid reset.
        state = {"X": 3, "Y": 3, "GoalX": 6, "GoalY": 6,
                 "Direction": 0, "FrontBlocked": False}
        from k4u_native_minigrid import wingless_wire_grid
        before = wingless_wire_grid(state)
        a = bridge.request("choose", before=before)["action"]
        if type(a) is not int or a not in (0, 1, 2):
            raise ValueError("R8_PAIR_ILLEGAL_ACTION")
        if model == "r5":
            after = dict(before)
            if a == 0: after["direction"] = 3
            if a == 1: after["direction"] = 1
        else:
            after = dict(before)
            if a == 0: after["direction"] = 3
            if a == 1: after["direction"] = 1
        feedback = bridge.request("feedback", before=before, action=a, after=after)
        if feedback.get("steps") != 1:
            raise ValueError("R8_PAIR_SELECTED_FEEDBACK_DRIFT")
        return {"selected_action": a, "feedback_steps": 1, "native_checkpoint_hash": PINS[model][2]}
    finally:
        bridge.close()

def main():
    r5, r8 = (read_checkpoint(sys.argv[i], method)
              for i, method in ((1, "r5"), (2, "r8")))
    results = {"r5": smoke("r5", os.environ["ITD02_R5_BRIDGE"], r5),
               "r8": smoke("r8", os.environ["ITD02_R8_BRIDGE"], r8)}
    print(json.dumps({"gate": "ITD02_R8_R5_PAIRED_NATIVE_FIXTURE",
                      "result": "PASS", "models": results,
                      "original_world_resets": 0, "check_episodes": 0,
                      "development_episodes": 0, "scientific_first_use": False,
                      "scientific_accepted": False}, sort_keys=True))

if __name__ == "__main__":
    main()
