"""FIT-local source-free research tests. No original scientific case access."""
import unittest,copy,ast,inspect
import torch
import lcrm01d_candidate as candidate
import lcrm01d_peer as peer
import lcrm01d_sourceonly as toy
import lcrm01d_public as public
import lcrm01d_trial as trial
import lcrm01d_symbolic as symbolic

class FrozenSourceOnlySequence(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
    cls.eps=toy.fixture()
    cls.cm=trial.train(candidate.Candidate,cls.eps[:20])
    cls.pm=trial.train(peer.Peer,cls.eps[:20])
 def test_roster_and_source_seed(self):
    self.assertEqual(len(self.eps),24)
    self.assertTrue(all(len(e['events'])==8 for e in self.eps))
 def test_no_oracle_import_in_models(self):
    for mod in (candidate,peer):
      imported=[]
      for n in ast.walk(ast.parse(inspect.getsource(mod))):
        if isinstance(n,ast.Import):imported.extend(a.name for a in n.names)
        if isinstance(n,ast.ImportFrom):imported.append(n.module or '')
      self.assertFalse(any('sourceonly' in v or 'symbolic' in v for v in imported))
 def test_matched_parameter_count(self):
    c=sum(p.numel() for p in self.cm.parameters())
    p=sum(p.numel() for p in self.pm.parameters())
    self.assertEqual((c,p),(436,436))
 def test_equal_data_training_digest(self):
    self.assertEqual(trial.main('candidate')['FIT_sha256'],trial.main('peer')['FIT_sha256'])
 def test_candidate_learns_weights(self):
    torch.manual_seed(412)
    old=candidate.Candidate()
    self.assertFalse(torch.equal(old.source.weight,self.cm.source.weight))
 def test_fit_only_no_extra_labels(self):
    p=public.episode_tensor(self.eps[:20])
    self.assertEqual(tuple(p['y'].shape),(20,8,4))
    with self.assertRaises(ValueError):public.episode_tensor(self.eps[:8])
 def test_rollout_ignores_test_observed_labels(self):
    val=self.eps[20:]
    altered=copy.deepcopy(val)
    for ep in altered:
      for e in ep['events']:e['observed'] ^= 15
    for model in (self.cm,self.pm):
      with torch.no_grad():
        a=model(public.episode_tensor(val),teacher=False)[0]
        b=model(public.episode_tensor(altered),teacher=False)[0]
      self.assertTrue(torch.equal(a,b))
 def test_relation_ablation_alters_predictions(self):
    val=public.episode_tensor(self.eps[20:])
    with torch.no_grad():
      a=self.cm(val,teacher=False)[0];b=self.cm(val,teacher=False,ablate=True)[0]
    self.assertFalse(torch.equal(a,b))
 def test_independently_trained_recurrent_control(self):
    self.assertIsNot(type(self.cm),type(self.pm))
    self.assertEqual(trial.EPOCHS,80)
 def test_symbolic_source_neutral_gf2_is_stronger(self):
    v=symbolic.fit(self.eps[:20]);s=symbolic.score(v,self.eps[20:])
    self.assertEqual(s['exact_episodes'],4)
    self.assertEqual(s['abstained_events'],0)
 def test_source_only_fit_cv_is_not_science(self):
    for arm in ('candidate','peer','ablation'):
      d=trial.main(arm)
      self.assertEqual(d['FIT_internal_train'],20)
      self.assertFalse(d['counterfactual_admitted'])
      self.assertEqual(d['original_scientific_firstuse'],0)
 def test_identical_frozen_training_information(self):
    a=trial.main('candidate');b=trial.main('peer')
    self.assertEqual(a['epochs'],b['epochs'])
    self.assertEqual(a['parameters'],b['parameters'])
    self.assertEqual(a['FIT_sha256'],b['FIT_sha256'])

if __name__=='__main__':unittest.main()
