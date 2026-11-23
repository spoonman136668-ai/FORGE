"""Original pinned CKB R7 attest_r168 vs FORGE Go acceptance, synthetic-only."""
import importlib,sys,os,json,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(os.environ["CKB_SOURCE"])))
ckb=importlib.import_module("portfolio_r7")
exe=os.environ["FORGE_R7_EXE"]
pins=ckb.SOURCE_PINS
for lane,source in pins.items():
 raw=dict(schema="ckb-plane.research-source-qualification.r168",lane=lane,
  candidate_sha256=source["candidate_sha256"],parent_sha=source["parent_sha"],
  status=source["status"],focused_go_test_invocations=source["focused_go_test_invocations"],
  verified_source_files=source["verified_source_files"],
  predecessor_receipt_sha256="a"*64,full_historical_disjointness_proven=False,
  prospective_source_verification_count=0,sealed_outcomes_seen=False,
  scientific_classification="NOT_EVALUATED",source_qualification_authority=False,
  ready_research_authority=False,dispatch_authority=False,
  accepted_ref_mutation=False,production_authority=False,broker_access=False,
  ktrade_access=False,model_calls=0)
 cases=[("valid",raw)]
 for field,value in [("ready_research_authority",True),("full_historical_disjointness_proven",True),
    ("source_qualification_authority",True),("scientific_classification","SUPPORTED"),
    ("status","READY"),("predecessor_receipt_sha256","invalid")]:
  x=dict(raw);x[field]=value;cases.append((field,x))
 for name,x in cases:
  try: ckb.attest_r168(lane,x);accepted=True
  except ckb.check.__globals__["ContractError"]:accepted=False
  # Maintain exact field-name mapping from source contract.
  mapping={"schema":"Schema","lane":"Lane","candidate_sha256":"CandidateSHA256",
    "parent_sha":"ParentSHA","status":"Status","focused_go_test_invocations":"FocusedGoTestInvocations",
    "verified_source_files":"VerifiedSourceFiles","predecessor_receipt_sha256":"PredecessorReceiptSHA256",
    "full_historical_disjointness_proven":"FullHistoricalDisjointnessProven",
    "prospective_source_verification_count":"ProspectiveSourceVerificationCount",
    "sealed_outcomes_seen":"SealedOutcomesSeen","scientific_classification":"ScientificClassification",
    "source_qualification_authority":"SourceQualificationAuthority","ready_research_authority":"ReadyResearchAuthority",
    "dispatch_authority":"DispatchAuthority","accepted_ref_mutation":"AcceptedRefMutation",
    "production_authority":"ProductionAuthority","broker_access":"BrokerAccess",
    "ktrade_access":"KTRADEAccess","model_calls":"ModelCalls"}
  proc=subprocess.run([exe],input=json.dumps({mapping[k]:v for k,v in x.items()}),
    text=True,capture_output=True,timeout=15)
  assert proc.returncode==0,(lane,name,proc.stderr)
  got=proc.stdout.strip()=="ADVISORY_ONLY"
  assert got==accepted,(lane,name,accepted,got)
  print("R19I_CKB_R7_ATTESTATION_PARITY=PASS",lane,name)
print("R19I_SOURCE_PINNED_EXECUTABLE_PARITY=PASS")
