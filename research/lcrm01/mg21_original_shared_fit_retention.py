"""MG21 source-original shared experience and cold-retention engineering."""
import argparse,base64,hashlib,json
from pathlib import Path
import gymnasium as gym
import minigrid
from mg17_original_family_source_qual import attest_source,frozen,digest
from mg18_native_mission_boundary_audit import WingBridge
from mg21_native_retention_actors import family_fit,prepare,ROLES
from mg21_native_original_probe import probe
from mg21_original_tabular_control import Tabular
from research.native.itd02.mg19.genuine_mission_cells import MissionCells

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg21_original_source_shared_fit_prereg.json"
SOURCE="7f5853792ea7f04f75614661006d87fcf949f26d"
FAMILIES=("MiniGrid-DoorKey-6x6-v0","MiniGrid-UnlockPickup-v0",
 "MiniGrid-BlockedUnlockPickup-v0","MiniGrid-KeyCorridorS3R1-v0")

def protocol():
 p=json.loads(FROZEN.read_text(encoding="utf-8"))
 w=p["world"]
 if (p["schema"]!="itd02.mg21.original-source-shared-fit-cold-retention-engineering.v1" or
     p["phase"]!="FROZEN_BEFORE_ENGINEERING_EXECUTABLE__NO_SCIENTIFIC_FIRST_USE" or
     p["parent"]["Farama_MiniGrid"]!=SOURCE or
     tuple(w["families"])!=FAMILIES or
     w["quarantined_fit_seed"]!=918301 or w["quarantined_probe_seed"]!=918303 or
     w["original_fit_cap"]!=24 or w["original_eval_cap"]!=24 or
     not w["permanently_disqualify_both_seeds_from_scientific_fit_dev_sealed"] or
     not all(p["authority"].values())):
  raise ValueError("MG21_FROZEN_BEFORE_SOURCE_PROTOCOL_DRIFT")
 return p

def cold_retention(role,actor,go_binary,expected):
 if role=="random":return {"bytes":0,"sha256":None}
 if role.startswith("go_"):
  state=actor.snapshot();cold=WingBridge(go_binary)
  try:
   ack=cold.request("load",state=base64.b64encode(state).decode("ascii"))
   if ack.get("updates",0)!=expected or cold.snapshot()!=state:
    raise ValueError("MG21_GO_COLD_RETENTION_FAILED")
  finally:cold.close()
 elif role.startswith("ygg_"):
  state=actor.checkpoint()
  if actor.samples!=expected or MissionCells.restore(state).checkpoint()!=state:
   raise ValueError("MG21_YGG_COLD_RETENTION_FAILED")
 else:
  state=actor.checkpoint()
  if actor.samples!=expected or Tabular.restore(state).checkpoint()!=state:
   raise ValueError("MG21_CONTROL_COLD_RETENTION_FAILED")
 return {"bytes":len(state),"sha256":hashlib.sha256(state).hexdigest()}

def execute(source_root,go_binary):
 p=protocol()
 if not Path(minigrid.__file__).resolve().is_relative_to(source_root.resolve()):
  raise ValueError("MG21_SOURCE_NOT_ORIGINAL_PIN")
 orig=frozen();attest_source(source_root,orig)
 registrations={f["id"]:f["entry_point"] for f in orig["families"]}
 all_rows=[];fit_receipts=[]
 for family in FAMILIES:
  if gym.spec(family).entry_point!=registrations[family]:
   raise ValueError("MG21_SOURCE_REGISTRY_CHANGED")
  start,fit=family_fit(gym,family,p["world"]["quarantined_fit_seed"],24)
  fit_receipts.append({"family":family,"original_start_sha256":digest(start),
        "original_source_events":fit,"source_fit_sha256":digest(fit),
        "shared_original_fit_count":len(fit)})
  group=[]
  for role in ROLES:
   actor,adapter=prepare(role,fit,go_binary,family)
   count=len(fit) if role.endswith("_fit") else 0
   try:
    record=probe(gym,family,role,p["world"]["quarantined_probe_seed"],
                 24,actor,adapter,count)
    record["source_fit_sha256"]=digest(fit) if count else None
    record["cold_retention"]=cold_retention(role,actor,go_binary,
                                            count+record["probe_steps"])
    group.append(record)
   finally:
    if role.startswith("go_"):actor.close()
  if (len(group)!=7 or len({r["start_sha256"] for r in group})!=1 or
      any(r["probe_steps"] not in range(1,25) for r in group) or
      any(r["source_fit_sha256"]!=digest(fit)
          for r in group if r["fit_samples"])):
   raise ValueError("MG21_ORIGINAL_PARITY_OR_SHARED_FIT_DRIFT")
  all_rows.extend(group)
 if len(all_rows)!=28 or len(fit_receipts)!=4:
  raise ValueError("MG21_MISSING_ORIGINAL_WORLD_ARM")
 return {"schema":"itd02.mg21.shared-real-original-fit-retention.v1",
         "classification":"LONG_SOURCE_ENGINEERING_NO_LEARNING_SUCCESS_CLAIM",
         "original_source":SOURCE,
         "native_sources":{"wingless":p["parent"]["Wingless_MG19"],
                           "yggdrasil":p["parent"]["Yggdrasil_MG19"]},
         "quarantined_fit_seed":918301,"quarantined_probe_seed":918303,
         "source_fit_receipts":fit_receipts,
         "original_native_probe_records":all_rows,
         "canonical_sha256":digest({"fits":fit_receipts,"probes":all_rows})}
