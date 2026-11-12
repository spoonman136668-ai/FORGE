"""F59 inert synthetic contract fixtures; absolutely no original Acrobot reset."""
import ast
import hashlib
import inspect
import json
import math
import unittest

import f59_original_fit_transition_archive as f


POS = [1., 0., 1., 0., 0., 0.]
LOW_NEG = [1., 0., 1., 0., 0., -.1]
LOW_POS = [1., 0., 1., 0., 0., .1]
HIGH_NEG = [1., 0., 1., 0., 0., -.21]
HIGH_POS = [1., 0., 1., 0., 0., .21]


def external_hash(blob):
    return hashlib.sha256(blob).hexdigest()


def full_receipt():
    a = f.FITEvidenceArchive()
    for i, root in enumerate(f.FIT_ROOTS):
        for episode in range(f.EPISODES_PER_ROOT):
            a.open_episode(root, episode, root*100+episode)
            a.append(POS, (i*8+episode)%3, -1., POS, True, False)
    return a


class F59Tests(unittest.TestCase):
    def test_original_pinned_source_and_absent_authority(self):
        self.assertEqual(f.PROTOCOL, '730721b5dc39c713b4af12b58f694e8823e2b9c5')
        self.assertEqual(f.F51_BLOB, 'd3114ac66589e6b9f623318da721449090cfd54a')
        self.assertEqual(f.F56_BEHAVIOR_BLOB, '00a6901daa1b479e96d923bf46daa5a1f1be45b4')
        obj=f.FITEvidenceArchive()._payload()
        self.assertFalse(obj['source']['source_authenticated'])
        self.assertFalse(obj['source']['scientific_accepted'])
        self.assertFalse(obj['source']['original_first_use_permitted'])
        self.assertEqual(f.MAX_ROWS,24000)

    def test_original_behavior_action_probability_exact(self):
        
        for got, expected in zip(f.behavior_probs(LOW_NEG), [.56,.24,.2]):
            self.assertAlmostEqual(got, expected)
        
        for got, expected in zip(f.behavior_probs(LOW_POS), [.2,.24,.56]):
            self.assertAlmostEqual(got, expected)
        
        for got, expected in zip(f.behavior_probs(HIGH_NEG), [.6,.2,.2]):
            self.assertAlmostEqual(got, expected)
        
        for got, expected in zip(f.behavior_probs(HIGH_POS), [.2,.2,.6]):
            self.assertAlmostEqual(got, expected)
        for s in (LOW_NEG,LOW_POS,HIGH_NEG,HIGH_POS):
            self.assertAlmostEqual(sum(f.behavior_probs(s)),1.)
            self.assertGreaterEqual(min(f.behavior_probs(s)),.2-1e-12)

    def test_complete_raw_48_episode_export_and_independent_digest(self):
        a=full_receipt()
        raw,digest=a.seal_complete()
        self.assertEqual(external_hash(raw),digest)
        obj=json.loads(raw)
        self.assertEqual(obj['rows'],48)
        self.assertEqual(len(obj['episodes']),48)
        self.assertEqual(len(obj['records']),48)
        self.assertTrue(obj['complete'])
        self.assertEqual(obj['records'][0]['obs'],POS)
        self.assertEqual(obj['records'][0]['next_obs'],POS)
        self.assertEqual(obj['records'][0]['episode_seed'],f.FIT_ROOTS[0]*100)
        self.assertEqual(obj['records'][-1]['episode_seed'],f.FIT_ROOTS[-1]*100+7)
        restored=f.FITEvidenceArchive.restore(raw,digest,minimum_rows=48)
        self.assertEqual(restored.seal_complete(),(raw,digest))

    def test_cold_continuation_uses_actual_public_next_state(self):
        a=f.FITEvidenceArchive()
        a.open_episode(f.FIT_ROOTS[0],0,f.FIT_ROOTS[0]*100)
        a.append(POS,0,-1.,LOW_NEG,False,False)
        raw,h=a.snapshot()
        b=f.FITEvidenceArchive.restore(raw,h,minimum_rows=1)
        self.assertEqual(b.snapshot(),(raw,h))
        for obj in (a,b):
            obj.append(LOW_NEG,1,-1.,LOW_POS,True,False)
            obj.open_episode(f.FIT_ROOTS[0],1,f.FIT_ROOTS[0]*100+1)
            obj.append(HIGH_POS,2,0.,POS,True,False)
        self.assertEqual(a.snapshot(),b.snapshot())
        self.assertEqual(len(a.episodes),2)
        self.assertAlmostEqual(a.records[1]['behavior_probability'],.24)

    def test_forbidden_seed_episode_order_duplicate_and_extra(self):
        a=f.FITEvidenceArchive()
        with self.assertRaises(ValueError):a.open_episode(31011,0,3101100)
        with self.assertRaises(ValueError):a.open_episode(f.FIT_ROOTS[1],0,f.FIT_ROOTS[1]*100)
        with self.assertRaises(ValueError):a.open_episode(f.FIT_ROOTS[0],1,f.FIT_ROOTS[0]*100+1)
        a.open_episode(f.FIT_ROOTS[0],0,f.FIT_ROOTS[0]*100)
        with self.assertRaises(ValueError):a.open_episode(f.FIT_ROOTS[0],0,f.FIT_ROOTS[0]*100)
        a.append(POS,0,-1.,POS,True,False)
        with self.assertRaises(ValueError):a.append(POS,0,-1.,POS,True,False)
        b=full_receipt()
        with self.assertRaises(ValueError):b.open_episode(f.FIT_ROOTS[-1],7,f.FIT_ROOTS[-1]*100+7)

    def test_discontinuous_or_invalid_observed_state_rejected(self):
        a=f.FITEvidenceArchive();a.open_episode(f.FIT_ROOTS[0],0,f.FIT_ROOTS[0]*100)
        for bad in ([math.nan,0,1,0,0,0],[2,0,1,0,0,0],
                    [0,0,1,0,0,0],[1,0,1,0,0,40],
                    [1,0,1,0,0,True],[1,0]):
            with self.assertRaises(ValueError):a.append(bad,0,-1.,POS,False,False)
        a.append(POS,0,-1.,LOW_NEG,False,False)
        with self.assertRaises(ValueError):a.append(POS,1,-1.,POS,False,False)
        self.assertEqual(len(a.records),1)

    def test_bad_action_reward_flags_and_timelimit(self):
        a=f.FITEvidenceArchive();a.open_episode(f.FIT_ROOTS[0],0,f.FIT_ROOTS[0]*100)
        for action in (-1,3,True,1.5):
            with self.assertRaises(ValueError):a.append(POS,action,-1.,POS,False,False)
        for reward in (math.inf,math.nan,1.,-.5,True):
            with self.assertRaises(ValueError):a.append(POS,0,reward,POS,False,False)
        with self.assertRaises(ValueError):a.append(POS,0,-1.,POS,1,False)
        with self.assertRaises(ValueError):a.append(POS,0,-1.,POS,True,True)
        with self.assertRaises(ValueError):a.append(POS,0,-1.,POS,False,True)
        self.assertEqual(a.records,[])

    def test_500_step_original_timelimit_and_exhaustion(self):
        a=f.FITEvidenceArchive();a.open_episode(f.FIT_ROOTS[0],0,f.FIT_ROOTS[0]*100)
        for t in range(499):
            a.append(POS,t%3,-1.,POS,False,False)
        with self.assertRaises(ValueError):a.append(POS,0,-1.,POS,False,False)
        a.append(POS,0,-1.,POS,False,True)
        self.assertEqual(a.episodes[0]['steps'],500)
        with self.assertRaises(ValueError):a.append(POS,0,-1.,POS,True,False)
        data,d=a.snapshot()
        self.assertEqual(f.FITEvidenceArchive.restore(data,d,500).snapshot(),(data,d))

    def test_partial_archive_cannot_be_falsely_sealed(self):
        a=f.FITEvidenceArchive()
        with self.assertRaises(ValueError):a.seal_complete()
        a.open_episode(f.FIT_ROOTS[0],0,f.FIT_ROOTS[0]*100)
        with self.assertRaises(ValueError):a.seal_complete()
        raw,d=a.snapshot()
        self.assertEqual(f.FITEvidenceArchive.restore(raw,d,0).snapshot(),(raw,d))
        a.append(POS,0,-1.,POS,True,False)
        with self.assertRaises(ValueError):a.seal_complete()

    def test_tamper_rollback_and_forged_conditional_propensity(self):
        a=full_receipt();raw,d=a.seal_complete()
        for val,hash_,floor in ((raw+b' ',d,48),(raw,'0'*64,48),(raw,d,49)):
            with self.assertRaises(ValueError):f.FITEvidenceArchive.restore(val,hash_,floor)
        obj=json.loads(raw)
        obj['records'][0]['behavior_probability']=0.9
        altered=f.canonical(obj)
        with self.assertRaises(ValueError):f.FITEvidenceArchive.restore(altered,external_hash(altered),0)
        obj=json.loads(raw)
        obj['episodes'][0]['trace_sha256']='0'*64
        altered=f.canonical(obj)
        with self.assertRaises(ValueError):f.FITEvidenceArchive.restore(altered,external_hash(altered),0)
        obj=json.loads(raw)
        obj['records'][1]['seq']=100
        altered=f.canonical(obj)
        with self.assertRaises(ValueError):f.FITEvidenceArchive.restore(altered,external_hash(altered),0)

    def test_duplicate_json_keys_rejected_with_external_hash(self):
        raw,d=f.FITEvidenceArchive().snapshot()
        malformed=raw.replace(b'"schema":',b'"schema":"fake","schema":',1)
        with self.assertRaises(ValueError):
            f.FITEvidenceArchive.restore(malformed,external_hash(malformed),0)
        self.assertTrue(d)

    def test_inert_source_no_environment_or_dispatch(self):
        source=inspect.getsource(f)
        imports=set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node,ast.Import):imports.update(a.name for a in node.names)
            elif isinstance(node,ast.ImportFrom):imports.add(node.module)
        self.assertEqual(imports,{'hashlib','json','math','re'})
        self.assertNotIn('gymnasium',source.lower())
        self.assertNotIn('env.step(',source)
        self.assertNotIn('requests',source)
        self.assertNotIn('subprocess',source)


if __name__=='__main__':unittest.main()
