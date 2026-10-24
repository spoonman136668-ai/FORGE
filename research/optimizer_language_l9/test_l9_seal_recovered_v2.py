"""L9 mixed V1 GRU and V2 recovered Transformer numerical seal: negative-control unit tests.

Synthetic metadata only; no corpus, model evaluation, AUDIT_DEV or official TEST.
"""
import copy,json,tempfile,unittest
from pathlib import Path
import l9_seal_recovered_v2 as v2
class MixedSealTests(unittest.TestCase):
    def synthetic_v2(self):
        scores=[]
        for epoch,checkpoint,chrf in zip(v2.EPOCHS,v2.CKPT[('SMALL_TRANSFORMER',1702)],(0,0.011066673,0.055673619)):
            scores.append(dict(arm='SMALL_TRANSFORMER',seed=1702,epoch=epoch,role='L9_SELECT',
               records=v2.SELECT,checkpoint_sha256=checkpoint,triple_denominator=v2.TRIPLES,
               triple_proxy_hits=0,missing_triples_proxy=v2.TRIPLES,
               requested_content_proxy_coverage=0,chrF_single_reference_proxy=None,
               chrf_single_reference_proxy=chrf,retained_model_bytes=1721741,
               evaluation_wall_seconds=5.2,evaluation_cpu_seconds=10.4,explicit_abstentions=2000))
            scores[-1].pop('chrF_single_reference_proxy')
        return dict(schema='forge.optimizer.language.l9.transformer-select-encoder-reuse-v2-development-only',
          status='PROSPECTIVE_RECOVERY_SELECT_NOT_V1_EVIDENCE',arm='SMALL_TRANSFORMER',seed=1702,
          source_role_sha256=v2.ROLE,model_suite_git_blob=v2.SUITE,
          train_count=v2.TRAIN,select_count=v2.SELECT,scientific_go=False,
          audit_dev_reference_consumed=False,official_test_consumed=False,
          selected_metric_is_nonadjudicated_proxy=True,fit_receipt_sha256=v2.EXPECTED[('SMALL_TRANSFORMER',1702)][1],
          original_failure_run_id=40046319723,original_failure_job_id=120728754198,
          cross_os_synthetic_prefit_run=40050110176,
          not_interchangeable_with_frozen_v1_receipt=True,new_independent_seal_and_acceptance_required=True,
          original_failure_receipt_sha256='a'*64,original_workflow_receipt_sha256='b'*64,
          original_timeout_log_sha256='c'*64,synthetic_prefit_receipt_sha256='d'*64,
          development_equivalence_fixtures=[dict(epoch=e,index=i,identical=True) for e in v2.EPOCHS for i in v2.PARITY_IDXS],
          all_epoch_metrics=scores,selected_epoch=12,
          selected_checkpoint_sha256=v2.CKPT[('SMALL_TRANSFORMER',1702)][2])
    def validate(self,x):
        return v2.validate_neural(json.dumps(x,sort_keys=True).encode('utf-8'),'SMALL_TRANSFORMER',1702)
    def test_successful_synthetic_v2_is_never_v1(self):
        row=self.validate(self.synthetic_v2())
        self.assertEqual(row['evaluation_identity'],'RECOVERED_V2_TIMEOUT')
        self.assertEqual(row['selected']['epoch'],12)
    def test_frozen_metric_mutations_fail(self):
        mutations=[('role','L9_AUDIT_DEV'),('checkpoint_sha256','0'*64),('records',2000),
           ('triple_denominator',6134),('triple_proxy_hits',1),
           ('chrf_single_reference_proxy',float('nan')),('epoch',13)]
        for key,val in mutations:
            data=self.synthetic_v2();data['all_epoch_metrics'][1][key]=val
            with self.subTest(field=key),self.assertRaises(ValueError):self.validate(data)
    def test_identity_and_go_mutations_fail(self):
        mutations=[('schema','forge.optimizer.language.l9.neural-select-development-v1'),
          ('original_failure_run_id',0),('original_failure_job_id',0),
          ('fit_receipt_sha256','0'*64),('audit_dev_reference_consumed',True),
          ('scientific_go',True),('original_timeout_log_sha256','bad'),
          ('not_interchangeable_with_frozen_v1_receipt',False),('selected_epoch',8)]
        for key,val in mutations:
            data=self.synthetic_v2();data[key]=val
            with self.subTest(field=key),self.assertRaises(ValueError):self.validate(data)
    def test_parity_missing_or_tampered_fails(self):
        for kind in ('missing','duplicate','incorrect','false'):
            data=self.synthetic_v2()
            p=data['development_equivalence_fixtures']
            if kind=='missing':p.pop()
            if kind=='duplicate':p[-1]=p[0]
            if kind=='incorrect':p[0]['index']=80
            if kind=='false':p[0]['identical']=False
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.validate(data)
    def test_partial_selection_never_seals(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with self.assertRaises(FileNotFoundError):
                v2.seal(root/'candidate.json',root/'receipts',root/'sealed.json')
            self.assertFalse((root/'sealed.json').exists())
    def test_required_grid_and_scientific_boundary(self):
        self.assertEqual(set(v2.EXPECTED),{('GRU_SEQ2SEQ',1701),('GRU_SEQ2SEQ',1702),
                                         ('SMALL_TRANSFORMER',1701),('SMALL_TRANSFORMER',1702)})
        self.assertIn('development-only',v2.SCHEMA)
if __name__=='__main__':unittest.main()
