"""Q21 source-only trained-control guards. Test fixtures are handcrafted public rows."""
import math
import unittest

import models as m
import sourcefree as p


def toy(s=0):
    observations = ([(0,0),(0,1),(1,1),(1,0),(0,0)] if s==0
                    else [(1,0),(0,0),(1,1),(0,1),(0,0)])
    return (p.FAMILIES[0],tuple(observations),(0,1,0,1))


class Q21TrainedComparatorGuards(unittest.TestCase):
    def test_public_only_rows_reject_privileged_metadata(self):
        with self.assertRaisesRegex(ValueError,'PRIVATE_FIELDS'):
            m.checked([toy() + ({'latent':0},)])
        with self.assertRaisesRegex(ValueError,'MIXED_FAMILY'):
            m.checked([toy(),(p.FAMILIES[1],toy()[1],toy()[2])])

    def test_logistic_gradient_matches_finite_difference(self):
        weights=m.init_weights(m.MODEL_NAMES[0],16,0)
        rows=[toy(),toy(1)]
        gradient=m.gradient_logit(weights,rows)
        for index in (0,3,8,15):
            hi=weights[:];lo=weights[:]
            hi[index]+=1e-5;lo[index]-=1e-5
            numerical=(m.mean_nll(rows,lambda row:m.logit_predictions(hi,row))-
                       m.mean_nll(rows,lambda row:m.logit_predictions(lo,row)))/2e-5
            self.assertAlmostEqual(numerical,gradient[index],places=7)

    def test_recurrent_backprop_matches_finite_difference(self):
        rows=[toy(),toy(1)]
        for hidden,kind in ((2,m.MODEL_NAMES[1]),(4,m.MODEL_NAMES[2])):
            weights=m.init_weights(kind,m.rnn_shape(hidden)[-1],0)
            gradient=m.gradient_rnn(weights,rows,hidden)
            for index in (0,hidden*hidden,hidden*hidden+5*hidden,
                          m.rnn_shape(hidden)[-1]-1):
                hi=weights[:];lo=weights[:]
                hi[index]+=1e-5;lo[index]-=1e-5
                numerical=(m.mean_nll(rows,lambda row:m.rnn_predictions(hi,row,hidden))-
                           m.mean_nll(rows,lambda row:m.rnn_predictions(lo,row,hidden)))/2e-5
                self.assertAlmostEqual(numerical,gradient[index],places=7)

    def test_unsupervised_hmm_forward_backward_and_em(self):
        for hidden in (2,4):
            prior=m.hmm_init(hidden,0)
            obs,alpha,beta,gamma,scale=m.forward_backward(prior,toy())
            self.assertEqual(len(obs),5)
            self.assertEqual(len(beta),5)
            for row in alpha+gamma:
                self.assertAlmostEqual(sum(row),1,places=12)
            updated=m.hmm_em_step(prior,[toy(),toy(1)])
            for mat in updated['transition']:
                for row in mat:
                    self.assertAlmostEqual(sum(row),1,places=12)
            self.assertTrue(math.isfinite(m.mean_nll([toy()],
                                lambda row:m.hmm_predictions(updated,row))))

    def test_budgets_cannot_change_for_full_fitting(self):
        with self.assertRaisesRegex(ValueError,'FROZEN_GRADIENT_BUDGET'):
            m.fit_gradient(m.MODEL_NAMES[0],[toy()],[toy(1)],epochs=1)
        with self.assertRaisesRegex(ValueError,'FROZEN_HMM_BUDGET'):
            m.fit_hmm(2,[toy()],[toy(1)],epochs=1)

    def test_logistic_fit_uses_frozen_budget_only_on_toy_rows(self):
        model,receipt=m.fit_gradient(m.MODEL_NAMES[0],[toy(),toy(1)],[toy()])
        self.assertGreater(receipt['selected_epoch'],0)
        self.assertEqual(len(m.model_predict(model,toy())),4)
        self.assertEqual(m.checkpoint_sha(model),m.checkpoint_sha(model))
        self.assertEqual(receipt['rss_qualification'],'NATIVE_PEAK_RSS_PENDING')

    def test_rnn_2_and_4_state_frozen_fit_only_on_toy_rows(self):
        for kind in (m.MODEL_NAMES[1],m.MODEL_NAMES[2]):
            model,receipt=m.fit_gradient(kind,[toy(),toy(1)],[toy()])
            self.assertTrue(math.isfinite(receipt['fit_validation_nll']))
            self.assertEqual(len(m.model_predict(model,toy())),4)

    def test_hmm_2_and_4_state_frozen_fit_only_on_toy_rows(self):
        for hidden in (2,4):
            model,receipt=m.fit_hmm(hidden,[toy(),toy(1)],[toy()])
            self.assertTrue(math.isfinite(receipt['fit_validation_nll']))
            self.assertEqual(len(m.model_predict(model,toy())),4)

    def test_episode_clustered_bootstrap_is_deterministic(self):
        first=m.paired_episode_bootstrap([.5,.7,.8],[.4,.6,.9],'fixture')
        second=m.paired_episode_bootstrap([.5,.7,.8],[.4,.6,.9],'fixture')
        self.assertEqual(first,second)
        self.assertEqual(first['resampling_unit'],'EPISODE')
        with self.assertRaisesRegex(ValueError,'FROZEN_BOOTSTRAP'):
            m.paired_episode_bootstrap([.5,.7],[.4,.6],'fixture',replicates=10)

if __name__=='__main__':
    unittest.main()
