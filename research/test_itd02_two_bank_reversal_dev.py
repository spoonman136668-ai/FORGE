"""Frozen source-free reversal+recurrence DEV, no external environment or FSA."""
import json
import math
import time
import unittest
from collections import deque
from itd02_online_consequence_memory import OnlineConsequenceMemory as M
from itd02_two_bank_reversal_dev import TwoBankMemory, sha

PUBLIC=(0.,0.)
PHASES=((40,(1.,-1.)),(16,(-1.,1.)),(12,(1.,-1.)),(12,(-1.,1.)))
NOISE=(0.,.04,.08,.12)

class Rolling:
    def __init__(self,window):
        self.window=window;self.rows=[deque(maxlen=window) for _ in range(2)]
    def observe(self,obs,action,y): self.rows[action].append(y)
    def propose(self,obs):
        def estimate(a):
            # Same λ=.1 and public observation [0,0]; exact full ridge fit.
            return sum(self.rows[a])/(len(self.rows[a])+.1)
        return max((0,1),key=lambda a:(estimate(a),-a))

class SwitchingBayes:
    """Two empirical effect banks and hazard-filtered likelihood (no mode tags).

    A strong conventional comparator with the same observed action history,
    no future outcomes or source-mode access. History means are fitted online.
    """
    def __init__(self):
        self.rows=[[[],[]],[[],[]]]
        self.probs=[1.,0.]
        self.known_second=False
    def mean(self,mode,arm):
        z=self.rows[mode][arm]
        return sum(z)/(len(z)+.1)
    def observe(self,obs,a,y):
        if not self.known_second:
            if len(self.rows[0][a])>=3 and abs(y-self.mean(0,a))>=.9:
                self.known_second=True
                self.rows[1][a].append(y)
                self.probs=[.02,.98]
            else:self.rows[0][a].append(y)
            return
        # HMM prediction, then Gaussian observation likelihood (σ=.25).
        prior=[.98*self.probs[0]+.02*self.probs[1],
               .98*self.probs[1]+.02*self.probs[0]]
        score=[prior[i]*math.exp(-.5*((y-self.mean(i,a))/.25)**2)
               for i in (0,1)]
        total=sum(score)
        if total<=1e-280:
            # Unexpected third mode: no authority to label it original science.
            posterior=prior
        else: posterior=[x/total for x in score]
        self.probs=posterior
        selected=max((0,1),key=lambda i:posterior[i])
        self.rows[selected][a].append(y)
    def propose(self,obs):
        expected=[sum(self.probs[i]*self.mean(i,a) for i in (0,1)) for a in (0,1)]
        return max((0,1),key=lambda a:(expected[a],-a))


def source_fixture(noise):
    seq=0
    for phase_idx,(pairs,values) in enumerate(PHASES):
        for pair_idx in range(pairs):
            for action in (0,1):
                y=values[action]+noise*(1 if (seq//3)%2==0 else -1)
                yield phase_idx,pair_idx,seq,action,y,values
                seq+=1


def trial(noise):
    candidate=TwoBankMemory(2,2,256)
    cold=None
    full=M(2,2,256)
    rolling={n:Rolling(n) for n in (8,16,32)}
    bayes=SwitchingBayes()
    reset=M(2,2,256)  # fixed periodic reset; receives all feedback; no phase labels
    names=('candidate','full','rolling8','rolling16','rolling32','bayes','no-feedback','forced-reset')
    reward={name:0. for name in names}
    counts={name:0 for name in names}
    decisions={name:[] for name in names}
    cold_replays=0
    t0=time.perf_counter()
    for phase,pair,seq,a,y,values in source_fixture(noise):
        # Score after receiving each complete pair, only after initial 2 pairs.
        # Never train on a scored counterfactual option.
        candidate.observe(candidate.completed,PUBLIC,a,y)
        if cold is not None:
            cold.observe(cold.completed,PUBLIC,a,y)
            assert cold.checkpoint()==candidate.checkpoint(), 'COLD_NUMERIC_STATE_DIVERGED'
            cold_replays+=1
        full.observe(full.completed,PUBLIC,a,y)
        for ref in rolling.values():ref.observe(PUBLIC,a,y)
        bayes.observe(PUBLIC,a,y)
        if seq>0 and seq%32==0: reset=M(2,2,256)
        reset.observe(reset.completed,PUBLIC,a,y)
        if a==1 and pair>=2:
            chosen={
                'candidate':candidate.propose(PUBLIC,0.)['action'],
                'full':full.propose(PUBLIC,0.)['action'],
                'rolling8':rolling[8].propose(PUBLIC),
                'rolling16':rolling[16].propose(PUBLIC),
                'rolling32':rolling[32].propose(PUBLIC),
                'bayes':bayes.propose(PUBLIC),
                'no-feedback':0,
                'forced-reset':reset.propose(PUBLIC,0.)['action']}
            for name,v in chosen.items():
                reward[name]+=values[v]
                counts[name]+=1
                decisions[name].append((phase,pair,v))
        if phase==1 and pair==PHASES[1][0]-1 and a==1:
            payload,digest=candidate.checkpoint()
            cold=TwoBankMemory.restore(payload,digest,minimum_completed=112)
            assert cold.checkpoint()==candidate.checkpoint()
    cost=time.perf_counter()-t0
    assert all(n==72 for n in counts.values()),counts
    assert cold_replays==48
    # Include each reversal + prior A recall within the first four action pairs.
    switched={p:all(d[2]==(0 if p%2==0 else 1)
                  for d in decisions['candidate'] if d[0]==p and 2<=d[1]<=3)
              for p in (1,2,3)}
    return dict(noise=noise,score=reward,switched=switched,
                cold_replays=cold_replays,final_counts=[b.counts for b in candidate.banks],
                wall_seconds=cost,cold_checkpoint_exact=cold.checkpoint()==candidate.checkpoint(),
                selected_banks=[candidate.active,full.completed],
                total_events=candidate.completed)

class TwoBankTests(unittest.TestCase):
    def test_actual_prior_failure_mechanism_not_rewritten(self):
        original=M(2,2,256)
        for _ in range(64):
            for a,v in ((0,1.),(1,-1.)):
                original.observe(original.completed,PUBLIC,a,v)
        for _ in range(12):
            for a,v in ((0,-1.),(1,1.)):
                original.observe(original.completed,PUBLIC,a,v)
        self.assertEqual(original.propose(PUBLIC,0.)['action'],0)

    def test_frozen_4_noise_source_no_oracles_and_strong_controls(self):
        out=[trial(n) for n in NOISE]
        for row in out:
            self.assertEqual(row['total_events'],160)
            self.assertTrue(row['cold_checkpoint_exact'])
            self.assertEqual(row['cold_replays'],48)
            self.assertTrue(all(row['switched'].values()),row)
            self.assertGreater(row['score']['candidate'],row['score']['full'])
            strongest=max(row['score'][n] for n in ('rolling8','rolling16','rolling32','bayes'))
            self.assertGreaterEqual(row['score']['candidate'],strongest-7.2)
            self.assertEqual(row['final_counts'],[[52,52],[28,28]])
        print('ITD02_TWO_BANK_NUMERIC_RESULTS='+json.dumps(out,sort_keys=True))

    def test_reuse_prior_bank_after_interference(self):
        learner=TwoBankMemory(max_events=256)
        for rounds,values in PHASES:
            for _ in range(rounds):
                for a in (0,1):learner.observe(learner.completed,PUBLIC,a,values[a])
        self.assertEqual(learner.active,1)
        self.assertEqual(learner.propose(PUBLIC,0.)['action'],1)
        self.assertEqual([b.counts for b in learner.banks],[[52,52],[28,28]])

    def test_cold_continue_and_original_authority_false(self):
        learner=TwoBankMemory(max_events=256)
        for i in range(20):learner.observe(learner.completed,PUBLIC,i%2,1. if i%2==0 else -1.)
        raw,digest=learner.checkpoint()
        cold=TwoBankMemory.restore(raw,digest,minimum_completed=20)
        for i in range(20,40):
            for m in (learner,cold):m.observe(m.completed,PUBLIC,i%2,1. if i%2==0 else -1.)
        self.assertEqual(learner.checkpoint(),cold.checkpoint())
        self.assertFalse(learner.propose(PUBLIC)['can_dispatch_original'])
        self.assertFalse(learner.propose(PUBLIC)['scientific_accepted'])

    def test_reject_wrong_seq_untrusted_input_and_external_rollback(self):
        learner=TwoBankMemory(max_events=2)
        for seq,obs,a,y in ((1,PUBLIC,0,1.),(0,(math.nan,0.),0,1.),
                             (0,PUBLIC,True,1.),(0,PUBLIC,0,math.inf)):
            with self.assertRaises(ValueError):learner.observe(seq,obs,a,y)
        self.assertEqual(learner.completed,0)
        learner.observe(0,PUBLIC,0,1.)
        raw,digest=learner.checkpoint()
        for payload,expected,floor in ((raw+' '.encode(),digest,1),
                                       (raw,'0'*64,1),(raw,digest,2)):
            with self.assertRaises(ValueError):TwoBankMemory.restore(payload,expected,floor)
        with self.assertRaises(ValueError):learner.observe(0,PUBLIC,0,1.)

    def test_third_regime_fails_closed_without_overwriting_prior_banks(self):
        learner=TwoBankMemory(max_events=256)
        for rounds,values in ((40,(1.,-1.)),(16,(-1.,1.))):
            for _ in range(rounds):
                for a in (0,1): learner.observe(learner.completed,PUBLIC,a,values[a])
        self.assertEqual(learner.active,1)
        old=[b.checkpoint() for b in learner.banks]
        # Neither mature bank predicts these distinct third-mode consequences.
        for _ in range(2):
            for a,y in ((0,3.),(1,-3.)):
                learner.observe(learner.completed,PUBLIC,a,y)
        self.assertEqual(learner.active,1)
        self.assertEqual(learner.unresolved,4)
        self.assertEqual([b.checkpoint() for b in learner.banks],old)
        raw,digest=learner.checkpoint()
        restored=TwoBankMemory.restore(raw,digest,minimum_completed=116)
        self.assertEqual(restored.checkpoint(),learner.checkpoint())
        self.assertFalse(restored.propose(PUBLIC)['can_dispatch_original'])

    def test_independent_bank_tamper_and_event_chain_negative(self):
        learner=TwoBankMemory(max_events=12)
        learner.observe(0,PUBLIC,0,1.)
        raw,_=learner.checkpoint()
        content=json.loads(raw)
        content['banks'][0]['sha256']='0'*64
        tampered=json.dumps(content,sort_keys=True,separators=(',',':')).encode()
        with self.assertRaises(ValueError):
            TwoBankMemory.restore(tampered,sha(tampered))
        content=json.loads(raw)
        content['events'][0]['consequence']=-1.
        tampered=json.dumps(content,sort_keys=True,separators=(',',':')).encode()
        with self.assertRaises(ValueError):
            TwoBankMemory.restore(tampered,sha(tampered))

if __name__=='__main__':unittest.main()
