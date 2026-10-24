#!/usr/bin/env python3
"""Seal original candidate and GRU SELECT with separately identified recovered Transformer v2 receipts.

Development metadata only. No model fit, inference, AUDIT_DEV or official TEST.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
ROLE='b9995c1846f5e1d99bf8bc4083dde0ebb41140906284bcf050a7ed6fe0efe726'
SUITE='710ce648a30ffc55647f689c5f4aa3ac13b07066'
SCHEMA='forge.optimizer.language.l9.select-seal-mixed-recovery-v2-development-only'
TRAIN=8480
SELECT=2154
TRIPLES=6135
EPOCHS=(4,8,12)
CANDIDATE_SHA='01f08870677067ca0f0dcfdff004d1ef04cea8465da0d025f904634e2bcd5d47'
PARITY_IDXS=(0,1,53,217,431,719,1077,1435,1795,2153)
EXPECTED={
 ('GRU_SEQ2SEQ',1701):('762d7471d0e3f7b24f8789c6b323624f0c86996614d477b5f354651ba19d5474','9b0350270d9868a8542a298eeaac8b33646ce1bf0ad81ae0e7e206210e40448b',None),
 ('GRU_SEQ2SEQ',1702):('511ad147152fd7e45eab915da2bdd74d2872a50cc6b4a20fe4ab9c5b677bc1e6','6194e3b91dba147d5c68ff99d6953d2c82ddef832baf46e7e82a0287521f9d7a',None),
 ('SMALL_TRANSFORMER',1701):(None,'ab1ef4066a30a4f3d4be2b1b72b9c0ff48511cc353c4e5de5e1d5523199938c5',(40045716995,120726845017)),
 ('SMALL_TRANSFORMER',1702):(None,'39858e1c21d8b2e03463b2b244ba46693171564038b4787858ba052a27e51ed8',(40046319723,120728754198)),
}
CKPT={
 ('GRU_SEQ2SEQ',1701):('9fa97bc5d0494a414af4c6d012d9beea68d99c52d40c1db7f09af7e4d7487b47','1c923058ad9f6a570044c8573caf5cafb1a6971fc5b31de55e3febd39ec2f63d','a24469cf00be1c028cd5dfb25649f7bcc523b35792eb4680fe19aa8912f01daa'),
 ('GRU_SEQ2SEQ',1702):('b53c85a2584eacc00f8ce579bbb8e51a02d0eb1ef2b73ca6415133c62270b36e','6c329a05bb64523e88bdf1a8203142dbb9805f4be80f3c3268f62a6a7821aa9e','1097e800b6ddc2acaa90df62943c6db1a34b1e1e62e51daf056f95303bb8d048'),
 ('SMALL_TRANSFORMER',1701):('5bc25aa6f0ff02690a8fec14a31b1d7ce5a6adf8a9355088327a2bcd22acd23e','971919768cf8a62ef46df604d3b8754bf105db1afdf762dcae61b0d30e9602a3','bf731132c64dbfd82ea5bc6121d0006c34527101b040119f9d11d83931a99a84'),
 ('SMALL_TRANSFORMER',1702):('31e39af09253a7ed6950ead93a834469a62ac6908dcfcc1cdeacde4e3d885238','b414a71193c12cd54db71403af0c5edd50ac905372cf6d9920e5026e80f7bbb8','e5e7baaf4a0ad3be69213933419da96fb85842a0b40adafdecd587d00fccf5a0'),
}
def require(ok,msg):
    if not ok: raise ValueError(msg)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def is_sha(v):return isinstance(v,str) and len(v)==64 and all(c in '0123456789abcdef' for c in v)
def score(v,arm,seed,epoch,checkpoint):
    require(isinstance(v,dict),'metric malformed')
    for k,w in {'arm':arm,'seed':seed,'epoch':epoch,'role':'L9_SELECT',
                'records':SELECT,'checkpoint_sha256':checkpoint,
                'triple_denominator':TRIPLES}.items():
        require(v.get(k)==w,'metric identity drift: '+k)
    hits=v.get('triple_proxy_hits')
    missing=v.get('missing_triples_proxy')
    require(type(hits)==int and 0<=hits<=TRIPLES and type(missing)==int and missing==TRIPLES-hits,'coverage numerators drift')
    for k in ('requested_content_proxy_coverage','chrf_single_reference_proxy','evaluation_wall_seconds','evaluation_cpu_seconds'):
        n=v.get(k)
        require(type(n) in (float,int) and math.isfinite(n) and n>=0,'invalid '+k)
    require(v['requested_content_proxy_coverage']<=1 and v['chrf_single_reference_proxy']<=1,'proxy >1')
    require(abs(v['requested_content_proxy_coverage']-hits/TRIPLES)<=1.1e-9,'coverage ratio drift')
    require(type(v.get('retained_model_bytes'))==int and 0<v['retained_model_bytes']<=3145728,'checkpoint budget')
    abst=v.get('explicit_abstentions')
    require(type(abst)==int and 0<=abst<=SELECT,'abstention count')
    return {k:v[k] for k in ('epoch','checkpoint_sha256','triple_proxy_hits','triple_denominator',
              'requested_content_proxy_coverage','chrf_single_reference_proxy','missing_triples_proxy',
              'retained_model_bytes','explicit_abstentions','evaluation_wall_seconds','evaluation_cpu_seconds')}
def validate_neural(raw,arm,seed):
    require((arm,seed) in EXPECTED,'outside registered arms/seeds')
    d=json.loads(raw)
    require(isinstance(d,dict),'receipt object required')
    raw_sha=sha(raw)
    original_sha,fit_sha,original=EXPECTED[(arm,seed)]
    if original_sha:require(raw_sha==original_sha,'original GRU receipt bytes changed')
    is_v2=arm=='SMALL_TRANSFORMER'
    must={'arm':arm,'seed':seed,'source_role_sha256':ROLE,'model_suite_git_blob':SUITE,
          'train_count':TRAIN,'select_count':SELECT,'scientific_go':False,
          'audit_dev_reference_consumed':False,'official_test_consumed':False,
          'selected_metric_is_nonadjudicated_proxy':True,'fit_receipt_sha256':fit_sha,
          'schema':('forge.optimizer.language.l9.transformer-select-encoder-reuse-v2-development-only' if is_v2 else 'forge.optimizer.language.l9.neural-select-development-v1'),
          'status':('PROSPECTIVE_RECOVERY_SELECT_NOT_V1_EVIDENCE' if is_v2 else 'SELECT_ONLY_DEVELOPMENT_CHECKPOINT_CHOICE')}
    for k,w in must.items():require(d.get(k)==w,'receipt identity drift: '+k)
    if is_v2:
        for k,w in {'original_failure_run_id':original[0],'original_failure_job_id':original[1],
                    'cross_os_synthetic_prefit_run':40050110176,
                    'not_interchangeable_with_frozen_v1_receipt':True,
                    'new_independent_seal_and_acceptance_required':True}.items():
            require(d.get(k)==w,'v2 admission drift: '+k)
        for k in ('original_failure_receipt_sha256','original_workflow_receipt_sha256','original_timeout_log_sha256','synthetic_prefit_receipt_sha256'):
            require(is_sha(d.get(k)),'attestation SHA missing: '+k)
        fixtures=d.get('development_equivalence_fixtures')
        require(isinstance(fixtures,list) and len(fixtures)==30,'parity fixture count')
        matched={(x.get('epoch'),x.get('index')) for x in fixtures if isinstance(x,dict) and x.get('identical') is True}
        require(matched=={(e,i) for e in EPOCHS for i in PARITY_IDXS},'development parity mismatch')
    rows=d.get('all_epoch_metrics')
    require(isinstance(rows,list) and len(rows)==3 and [v.get('epoch') for v in rows]==list(EPOCHS),'epoch grid mismatch')
    scored=[score(v,arm,seed,e,k) for v,e,k in zip(rows,EPOCHS,CKPT[(arm,seed)])]
    best=min(scored,key=lambda x:(-x['requested_content_proxy_coverage'],
              -x['chrf_single_reference_proxy'],x['missing_triples_proxy'],
              x['retained_model_bytes'],x['epoch']))
    require(d.get('selected_epoch')==best['epoch'] and d.get('selected_checkpoint_sha256')==best['checkpoint_sha256'],'checkpoint-selection drift')
    return {'arm':arm,'seed':seed,'evaluation_identity':'RECOVERED_V2_TIMEOUT' if is_v2 else 'ORIGINAL_V1',
            'raw_receipt_sha256':raw_sha,'original_run_failure':original[0] if original else None,
            'selected':best,'all_checkpoint_metrics':scored}
def validate_candidate(raw):
    require(sha(raw)==CANDIDATE_SHA,'candidate exact-byte drift')
    c=json.loads(raw)
    for k,w in {'schema':'forge.optimizer.language.l9.train-select-development-v1',
      'status':'DEVELOPMENT_TRAIN_SELECT_NOT_AUDIT','split_role_sha256':ROLE,
      'frozen_suite_sha_from_receipt':SUITE,'official_test_consumed':False,
      'scientific_go':False,'split_counts':{'train':TRAIN,'select':SELECT,'audit_dev_model_consumption':0},
      'candidate_config_selected':{'min_template_support':1,'max_templates_per_predicate':4,'joiner':' '}}.items():
        require(c.get(k)==w,'candidate identity drift: '+k)
    grid=c.get('candidate_selection')
    require(isinstance(grid,list) and len(grid)==8,'candidate config grid')
    chosen=[v for v in grid if v.get('config')==c['candidate_config_selected']]
    require(len(chosen)==1,'selected candidate choice drift')
    require(all(v.get('select_records')==SELECT for v in grid),'candidate scored incomplete')
    require(c.get('retrieval_select',{}).get('select_records')==SELECT,'retrieval scored incomplete')
    return {'selected_config':c['candidate_config_selected'],
            'requested_content_proxy_coverage':chosen[0]['requested_content_proxy_coverage'],
            'chrF_single_reference_proxy':chosen[0]['chrf_single_reference_proxy'],
            'retrieval_requested_content_proxy':c['retrieval_select']['requested_content_proxy_coverage']}
def seal(candidate_path,neural_dir,out):
    require(not out.exists(),'seal cannot overwrite')
    candidate=validate_candidate(candidate_path.read_bytes())
    cases=[]
    for arm in ('GRU_SEQ2SEQ','SMALL_TRANSFORMER'):
        for seed in (1701,1702):
            cases.append(validate_neural((neural_dir/f'{arm}-{seed}.json').read_bytes(),arm,seed))
    result={'schema':SCHEMA,'status':'ALL_FOUR_NUMERIC_DEV_CHOICES_VALIDATED_MIXED_V1_GRU_V2_TRANSFORMER',
      'role_identity_sha256':ROLE,'model_suite_git_blob':SUITE,
      'candidate_receipt_sha256':CANDIDATE_SHA,'candidate':candidate,'neural_cases':cases,
      'original_transformer_v1_timed_out':True,'recovered_transformer_v2_never_rebranded_v1':True,
      'separate_semantic_audit_admission_required':True,'audit_dev_reference_consumed':False,
      'official_test_consumed':False,'scientific_go':False,
      'resource_comparison_caution':'Cross-workflow runner wall times are not exact matched FLOPs/energy. Original timeout negatives preserved; lexical proxies are not independently adjudicated semantics.'}
    out.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(result,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()
    out.write_bytes(raw)
    print('L9_MIXED_V2_DEV_SEAL_PASS sha256='+sha(raw),flush=True)
    print('L9_UNFAMILIAR_AUDIT_UNTOUCHED=TRUE',flush=True)
    print('L9_SCIENTIFIC_GO=FALSE',flush=True)
    return result
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--candidate-receipt',type=Path,required=True)
    p.add_argument('--neural-receipts-dir',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    seal(a.candidate_receipt,a.neural_receipts_dir,a.out)
if __name__=='__main__':main()
