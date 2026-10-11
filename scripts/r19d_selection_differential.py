"""Cross-execute exact pinned CKB R1 shortlist and FORGE Go, same synthetic inputs."""
import importlib,os,sys,json,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(os.environ["CKB_SOURCE"])))
ckb=importlib.import_module("portfolio")
exe=os.environ["FORGE_SELECT_EXE"]
H="e"*64
cases=[
 [("family_a",9,3),("family_b",8,2),("family_a",7,3)],
 [("family_b",8,6),("family_a",9,3),("family_b",7,3)],
 [("family_a",9,2),("family_b",8,2),("family_a",7,2),("family_b",6,2)],
 [("family_a",9,4),("family_b",8,3),("family_a",7,4)],
]
for index,rows in enumerate(cases):
 families=sorted(set(f for f,_,_ in rows))
 contract=dict(schema="ckb.research-portfolio-contract.v1",generation_id="generation_test",
  contract_sha="a"*40,historical_data_sha=H,baseline_sha="b"*40,
  family_ids=families,frozen=True,max_screens_per_family=4,max_finalists_total=3,
  max_finalists_per_family=2,screen_compute_budget=20,sealed_compute_budget=8,max_candidate_parameters=100)
 screens=[];candidates=[]
 for i,(fam,score,cost) in enumerate(rows):
  code=("%040x"%(i+1));screen=("%064x"%(i+1));name=f"candidate_{i}"
  screens.append(dict(candidate_id=name,family_id=fam,code_sha=code,parent_shas=[],
   operator_id="operator_one",signature=f"signature_{i}",data_class="historical",
   data_sha=H,score=score,screen_cost=2,estimated_sealed_cost=cost,parameters=2,
   sealed_outcomes_accessed=False,post_freeze_mutation=False,screen_complete=True))
  candidates.append(dict(id=name,family=fam,source_sha=code,screen_sha=screen,
   historical_class="SUPPORTED",score=score,screen_compute=2,sealed_compute=cost))
 reference=ckb.shortlist(contract,screens)
 frozen=dict(schema="forge.evoportfolio.frozen.v1",lane="Wingless",epoch=1,
  historical_source_sha=H,max_screen_compute=20,max_sealed_compute=8,max_finalists=3,
  max_per_family=2,max_screens_per_family=4,candidates=candidates)
 proc=subprocess.run([exe],input=json.dumps(frozen),text=True,capture_output=True,timeout=15)
 assert proc.returncode==0,(index,proc.stderr)
 got=json.loads(proc.stdout)
 want=[r["candidate_id"] for r in reference["selected"]]
 assert got==want,(index,want,got)
 print("R19D_EXECUTABLE_SHORTLIST_PARITY=PASS",index,want)
print("R19D_BOUNDED_FOUR_CASES=PASS")
