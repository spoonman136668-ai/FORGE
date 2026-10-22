"""Source-only Q21 evaluator admission checks; all observations are handwritten fixtures."""
import unittest
from unittest.mock import patch
import evaluator as e
import sourcefree as p


def row(shift=0):
    obs=tuple(((t+shift)%2, ((t+shift)//3)%2) for t in range(33))
    act=tuple((t+shift//2)%2 for t in range(32))
    return (p.FAMILIES[0],obs,act)


class Q21EvaluationAdmissionGuards(unittest.TestCase):
    def test_invalid_or_incomplete_role_set_cannot_run(self):
        with self.assertRaisesRegex(ValueError,'ROLE_SET_DRIFT'):
            e.check_role_bound_rows({'FIT_TRAIN':[]},p.FAMILIES[0])

    def test_role_sizes_fail_closed_before_fitting(self):
        with self.assertRaisesRegex(ValueError,'ROLE_EPISODE_COUNT_DRIFT'):
            e.check_role_bound_rows({name:[row(0)] for name in p.ROLES},p.FAMILIES[0])

    def test_private_oracle_metadata_is_rejected(self):
        mock_counts={'FIT_TRAIN':2,'FIT_VALID':2,'DEV':2}
        roles={'FIT_TRAIN':[row(0),row(1)], 'FIT_VALID':[row(2),row(3)],
               'DEV':[row(4),row(5) + ({'latent_label':0},)]}
        with patch.object(p,'ROLE_COUNTS',mock_counts):
            with self.assertRaisesRegex(ValueError,'PRIVATE_FIELDS'):
                e.check_role_bound_rows(roles,p.FAMILIES[0])

    def test_cross_role_episode_reuse_rejected(self):
        mock_counts={'FIT_TRAIN':2,'FIT_VALID':2,'DEV':2}
        roles={'FIT_TRAIN':[row(0),row(1)],'FIT_VALID':[row(2),row(3)],
               'DEV':[row(0),row(5)]}
        with patch.object(p,'ROLE_COUNTS',mock_counts):
            with self.assertRaisesRegex(ValueError,'CROSS_ROLE_EPISODE_REUSE'):
                e.check_role_bound_rows(roles,p.FAMILIES[0])

    def test_timed_fit_and_handcrafted_public_scoring(self):
        model,cost=e.fit_counts_timed([row(0),row(1)],False)
        self.assertGreater(cost['checkpoint_bytes'],0)
        self.assertEqual(cost['rss_qualification'],'NATIVE_PEAK_RSS_PENDING')
        r=e.score_predictions([row(0)],lambda r:p.forecast_counts(model,r,False))
        self.assertEqual(len(r['episode_nll']),1)

    def test_preliminary_no_false_native_acceptance(self):
        d={'frozen_dev_decision':{
             'history_gain_min_nats_per_bit_each_real_family':.012,
             'history_gain_95pct_bootstrap_lower_bound_each_real_family_min':.002,
             'public_oracle_headroom_vs_best_memoryless_min_nats_each_real_family':.015,
             'null_family_max_apparent_history_gain_nats':.005}}
        strong={'gain':{'gain_nats_per_bit':.02,'lower_95':.005},
                'public_oracle_headroom':.03}
        null={'gain':{'gain_nats_per_bit':.002}}
        result=e.preliminary_decision({p.FAMILIES[0]:strong,
                p.FAMILIES[1]:strong,p.FAMILIES[2]:null},d)
        self.assertTrue(result['q21_development_thresholds_met'])
        self.assertEqual(result['gate_status'],'REQUIRES_NATIVE_CKB_QUALIFICATION')
        self.assertEqual(result['ckb_scientific_acceptance'],'NOT_AUTHORIZED')
        self.assertEqual(result['full_integration_regression'],'NOT_RUN')


if __name__=='__main__':unittest.main()
