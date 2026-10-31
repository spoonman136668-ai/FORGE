"""E-D102: offline fail-closed readiness check; cannot grant science approval."""
import json,sys
REQUIRED={'source':('commit_sha','memory_blob','runtime_receipt_uri'),'freeze':('approval_ref','split_registry_sha256','reviewer_ref'),'budget':('episodes','environment_steps','cpu_seconds','peak_rss_bytes','train_updates'),'interface':('observations','actions','reset_policy','termination_policy'),'witness':('independent_run_ref','original_logs_sha256')}
def audit(m):
    problems=[]
    if m.get('status')!='FROZEN_APPROVED':problems.append('status_not_frozen_approved')
    for section,fields in REQUIRED.items():
        val=m.get(section)
        if not isinstance(val,dict):
            problems.append('missing_section_'+section);continue
        for field in fields:
            v=val.get(field)
            if v is None or isinstance(v,str) and not v.strip() or isinstance(v,(dict,list)) and not v: problems.append('missing_'+section+'.'+field)
    src=m.get('source') if isinstance(m.get('source'),dict) else {}
    if src.get('commit_sha')!='7f5853792ea7f04f75614661006d87fcf949f26d':problems.append('unverified_source_commit')
    if src.get('memory_blob')!='660b0a1b769948034c87bb421759c2b9a4f24548':problems.append('unverified_memory_blob')
    if m.get('holdout_access')!='PROHIBITED_UNTIL_INDEPENDENT_APPROVAL':problems.append('holdout_guard_missing')
    for k in REQUIRED['budget']:
        v=m.get('budget',{}).get(k) if isinstance(m.get('budget'),dict) else None
        if type(v) not in (int,float) or v<=0:problems.append('invalid_budget_'+k)
    return {'verdict':'NOT_QUALIFIED' if problems else 'SCHEMA_COMPLETE_REQUIRES_INDEPENDENT_VERIFICATION','reasons':sorted(set(problems))}
if __name__=='__main__':
    m=json.load(sys.stdin)
    r=audit(m)
    print(json.dumps(r,sort_keys=True))
    sys.exit(2 if r['verdict']=='NOT_QUALIFIED' else 0)
