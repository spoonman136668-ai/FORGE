#!/usr/bin/env python3
"""MG24: prospectively frozen original-world development seed custody.

No MiniGrid or environment imports. Checks every MG21 historical source
pin and newer real-world research contracts with immutable Git readback.
The audit is explicitly scoped; external/private source completeness not claimed.
"""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg24_fresh_development_prereg.json"
FAMILIES=("MiniGrid-DoorKey-6x6-v0","MiniGrid-UnlockPickup-v0",
          "MiniGrid-BlockedUnlockPickup-v0","MiniGrid-KeyCorridorS3R1-v0")
SEEDS=((948101,948103),(948201,948203),(948301,948303),(948401,948403))
SOURCE_PINS=(
 ("MG17","9aaa71e902c478da70e1d0b905cc95134c3e2cae","research/lcrm01/mg17_original_family_source_prereg.json"),
 ("MG18","04f1da41df262a296c3058905bc8fcc24bda9328","research/lcrm01/mg18_native_mission_admission_prereg.json"),
 ("MG19","9715598cd35001a184f8ef12d0f0360fa933313f","research/lcrm01/mg19_native_genuine_mission_prereg.json"),
 ("MG20","be533627e9cbc7f35314257ceadbf21f5e873d4e","research/lcrm01/mg20_original_native_selected_source_prereg.json"),
 ("MG20-readonly","34ff0c9519e0c3f1c3447937591769b20f78052e","research/lcrm01/mg20_authentic_source_readonly_prereg.json"),
 ("MG16","e6f6c0e196571d73031a95174ef6f519214d4bac","research/lcrm01/mg16_original_credit_run_prereg.json"),
 ("MG17C","cccd5c428c7412274504e8721fe83e58a28359f1","research/lcrm01/mg17c_original_local_effect_prereg.json"),
 ("AC31","aafe7e488413ea4ff093ab30cf8311d88abed5eb","docs/research/AC-31-ORIGINAL-MULTIFAMILY-NATIVE-PREREGISTRATION.md"),
 ("AC32","70f516d3189f0bdc759cfe49e27043dfa971a477","docs/research/AC-32-FRESH-ORIGINAL-FARAMA-PREREG.md"),
 ("MG16F","675be1815253c85354a00fd39e81d176d7f3ad52","research/lcrm01/mg16_learning_factorial_prereg.json"),
 ("MG21-fresh-DEV","bad469f4f8a630b453cd6f386e4bb04bd9cdf578","research/lcrm01/mg21_original_fresh_cohort_prereg.json"),
 ("MG21-engineering","cf8dd74690d29db238b39f049c6ffc42e80aad47","research/lcrm01/mg21_original_source_shared_fit_prereg.json"),
 ("MG22-retrospective","6a667dd74bc7c2c03228b26d6ee7104c477f35c4","research/lcrm01/mg22_original_public_effect_prereg.json"),
 ("MG23-prospective","1ea80e1458c60ea63fa6345fe57b42da4de3aff0","research/lcrm01/mg23_native_target_delayed_credit_prereg.json"),
 ("MG23-conventional","46d32c4c4b9c0093367719f91aa1785b9f423034","research/lcrm01/mg23_independent_control_prereg.json")
)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def cmd(*args):return subprocess.check_output(["git",*args],cwd=HERE.parents[1],stderr=subprocess.PIPE).strip()
def validate():
 p=json.loads(PREREG.read_text(encoding="utf-8"))
 d=p["development"]
 if (p["schema"]!="itd02.mg24.authentic-original-fresh-development-and-controls.v1"
     or p["phase"]!="PROSPECTIVE_PRE_EXECUTABLE_SOURCE_LINEAGE__NO_SCIENTIFIC_FIRST_USE"
     or p["parents"]["forge_mg23_control_head"]!="46d32c4c4b9c0093367719f91aa1785b9f423034"
     or p["parents"]["farama"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
     or [x["environment"] for x in d["source_family_seeds"]]!=list(FAMILIES)
     or [x["seeds"] for x in d["source_family_seeds"]]!=[list(x) for x in SEEDS]
     or d["max_actions_per_episode"]!=128 or d["original_action_space"]!=list(range(7))
     or len(p["arms"])!=9 or len(set(p["arms"]))!=9
     or not all(v for v in p["scope"].values()) or
     not all(v for v in p["controls"].values()) or
     not all(v for v in d.values() if type(v)is bool)):
  raise ValueError("MG24_PROSPECTIVE_SOURCE_BOUNDARY_DRIFT")
 new=[s for row in SEEDS for s in row]
 excluded=p["restricted_seeds"]["previous_exposed_development"]+p["restricted_seeds"]["previous_engineering"]
 if len(new)!=8 or len(set(new))!=8 or set(new)&set(excluded):
  raise ValueError("MG24_KNOWN_SOURCE_SEED_COLLISION")
 old=[]
 for label,commit,path in SOURCE_PINS:
  if not re.fullmatch(r"[a-f0-9]{40}",commit):
   raise ValueError("MG24_INVALID_HISTORY_COMMIT")
  try:
   source=cmd("show",commit+":"+path)
   actual=cmd("rev-parse",commit+"^{commit}").decode()
  except subprocess.CalledProcessError as e:
   raise ValueError("MG24_MISSING_PINNED_SOURCE:"+label) from e
  if actual!=commit:
   raise ValueError("MG24_UNAUTHENTICATED_SOURCE_COMMIT:"+label)
  matches=[s for s in new if re.search(rb"(?<![0-9])"+str(s).encode()+rb"(?![0-9])",source)]
  if matches:raise ValueError("MG24_EXISTING_SOURCE_SEED_EXPOSED:"+label+":"+str(matches))
  old.append({"label":label,"commit":commit,"path":path,"sha256":sha(source),"overlap":0})
 if cmd("merge-base","--is-ancestor",p["parents"]["forge_mg23_control_head"],"HEAD")!=b"":
  raise ValueError("MG24_PARENT_NOT_ANCESTOR")
 out={"schema":"itd02.mg24.fresh-original-source-dev-lineage-receipt.v1",
      "classification":"FROZEN_SCOPED_DEV_LINEAGE_PASS_NO_FIRST_USE_SCIENCE",
      "candidate_development_seeds":d["source_family_seeds"],
      "historical_contract_readbacks":old,"historical_contract_count":len(old),
      "verified_overlap":0,"unscanned_external_private_sources_not_attested":True,
      "new_original_world_actions":0,"scientific_first_use":False,
      "sealed_source_seeds_assigned":False,
      "prereg_sha256":sha(PREREG.read_bytes())}
 out["canonical_receipt_sha256"]=sha(json.dumps(old,sort_keys=True,separators=(",",":")).encode())
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--output",required=True,type=Path)
 args=ap.parse_args()
 out=validate();args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n",encoding="utf-8")
 print("MG24_INDEPENDENT_HISTORICAL_FRESH_DEV_SCOPE_PASS_NO_SCIENCE "+out["canonical_receipt_sha256"])
if __name__=="__main__":main()
