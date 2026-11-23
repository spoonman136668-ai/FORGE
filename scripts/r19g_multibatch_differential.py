"""Execute original content-pinned CKB R6 multi-batch vs FORGE native Go."""
import importlib,sys,os,json,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(os.environ["CKB_SOURCE"])))
p=importlib.import_module("portfolio")
r6=importlib.import_module("portfolio_multibatch")
assert r6.SOURCE_KEYS
exe=os.environ["FORGE_R6_EXE"]
H="e"*64
cases=[
 ([("family_a",9,3),("family_b",8,2),("family_a",7,3)],[[0],[1,2]]),
 ([("family_b",8,6),("family_a",9,3),("family_b",7,3)],[[0,2],[1]]),
 ([("family_a",9,2),("family_b",8,2),("family_a",7,2),("family_b",6,2)],[[0,1],[2,3]]),
 ([("family_a",9,4),("family_b",8,3),("family_a",7,4)],[[0],[1],[2]]),
]
for n,(rows,groups) in enumerate(cases):
 families=sorted({f for f,_,_ in rows})
 contract=dict(schema="ckb.research-portfolio-contract.v1",generation_id="generation_test",
  contract_sha="a"*40,historical_data_sha=H,baseline_sha="b"*40,
  family_ids=families,frozen=True,max_screens_per_family=4,max_finalists_total=3,
  max_finalists_per_family=2,screen_compute_budget=20,sealed_compute_budget=8,max_candidate_parameters=100)
 screens=[];candidates=[]
 for i,(fam,score,cost) in enumerate(rows):
  code=f"{i+1:040x}";screen=f"{i+1:064x}";name=f"candidate_{i}";sig=f"signature_{i}"
  screens.append(dict(candidate_id=name,family_id=fam,code_sha=code,parent_shas=[],
   operator_id="operator_one",signature=sig,data_class="historical",data_sha=H,
   score=score,screen_cost=2,estimated_sealed_cost=cost,parameters=2,
   sealed_outcomes_accessed=False,post_freeze_mutation=False,screen_complete=True))
  candidates.append(dict(id=name,family=fam,signature=sig,source_sha=code,screen_sha=screen,
   historical_class="SUPPORTED",score=score,screen_compute=2,sealed_compute=cost))
 batches=[]
 for group in groups:
  subset=[screens[i] for i in group]
  b=dict(schema="ckb.fanout-portfolio-advisory.v1",contract_sha=contract["contract_sha"],
   binding_sha256="1"*64,baseline_sha=contract["baseline_sha"],
   selection_metric_name="historical_gain",higher_is_better=True,
   normalized_manifest_sha256="2"*64,summary_sha256="3"*64,
   historical_data_sha256=H,package_sha="4"*40,program="Wingless",
   screens=subset,shortlist=p.shortlist(contract,subset),
   scientific_classification=None,dispatch_authority=False,promotion_authority=False,
   accepted_ref_mutation=False)
  b["advisory_sha256"]=p.digest(b)
  batches.append(b)
 original=r6.combine_batches(contract,batches)
 frozen=dict(schema="forge.evoportfolio.frozen.v1",lane="Wingless",epoch=1,
  historical_source_sha=H,max_screen_compute=20,max_sealed_compute=8,
  max_finalists=3,max_per_family=2,max_screens_per_family=4,candidates=candidates)
 proc=subprocess.run([exe],input=json.dumps({"frozen":frozen,"groups":groups}),text=True,capture_output=True,timeout=15)
 assert proc.returncode==0,(n,proc.stderr)
 result=json.loads(proc.stdout)
 expected=[c["candidate_id"] for c in original["shortlist"]["selected"]]
 assert result["ids"]==expected,(n,expected,result)
 assert result["spent"]==2*len(rows),(n,result)
 assert result["reserved"]==int(original["shortlist"]["sealed_compute_reserved"]),(n,result)
 assert original["dispatch_authority"] is False
 print("R19G_CKB_R6_EXECUTABLE_PARITY=PASS",n)
print("R19G_ALL_FOUR_COMPARISONS_PASS")
