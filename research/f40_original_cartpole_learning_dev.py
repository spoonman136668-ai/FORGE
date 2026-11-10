#!/usr/bin/env python3
"""F40 source-only DEV: train on real pinned CartPole, then cold evaluate.

No protected first-use, owner/controller, workflow, scientific acceptance or deployment.
"""
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import sys
import time

import numpy as np

ORIGINAL = 'e6be96abfb0a9df36da5e7884522c4f1f2432e53'
TRAIN_SEEDS = (601, 607, 613, 617)
EVAL_SEEDS = (701, 709, 719, 727, 733, 739, 743, 751)
KINDS = ('causal-linear-mpc', 'behavior-rule', 'trained-linear-imitation',
         'trained-fitted-q', 'wrong-action', 'no-learned-dynamics')
FIRST_USE_FORBIDDEN = (59, 83)
SEQUENCES = tuple(itertools.product((0, 1), repeat=4))


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def public_obs(obs):
    raw = obs.tolist() if hasattr(obs, 'tolist') else obs
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        raise ValueError('F40_BAD_PUBLIC_OBSERVATION_SHAPE')
    vec = [float(v) for v in raw]
    if not all(math.isfinite(v) for v in vec):
        raise ValueError('F40_BAD_PUBLIC_OBSERVATION_VALUE')
    return vec


def behavior_action(state):
    return int(state[2] + .5 * state[3] >= 0)


def features(states):
    s = np.asarray(states, dtype=float).reshape(-1, 4)
    return np.column_stack((np.ones(len(s)), s, s*s, s[:, 0]*s[:, 2], s[:, 1]*s[:, 3]))


def linear_design(states, actions):
    s = np.asarray(states, dtype=float).reshape(-1, 4)
    a = np.asarray(actions, dtype=int)
    if len(a) != len(s) or np.any((a != 0) & (a != 1)):
        raise ValueError('F40_BAD_TRAINING_ACTION')
    return np.column_stack((s, 2*a-1, np.ones(len(s))))


def ridge(x, y, penalty):
    return np.linalg.solve(x.T @ x + penalty*np.eye(x.shape[1]), x.T @ y)


def fit_models(samples):
    if not samples:
        raise ValueError('F40_NO_REAL_TRAINING_TRANSITIONS')
    s = np.array([x['s'] for x in samples], dtype=float)
    a = np.array([x['a'] for x in samples], dtype=int)
    nxt = np.array([x['next'] for x in samples], dtype=float)
    rewards = np.array([x['reward'] for x in samples], dtype=float)
    done = np.array([x['done'] for x in samples], dtype=float)
    if not np.all(np.isfinite(s)) or not np.all(np.isfinite(nxt)) or not np.all(np.isfinite(rewards)):
        raise ValueError('F40_NONFINITE_TRAINING')
    if np.any((a != 0) & (a != 1)) or np.any((done != 0) & (done != 1)):
        raise ValueError('F40_BAD_TRAINING_LABELS')
    normal = ridge(linear_design(s, a), nxt, .001)
    inverted = ridge(linear_design(s, 1-a), nxt, .001)
    identity = np.zeros((6, 4), dtype=float)
    identity[:4] = np.eye(4)
    bc = ridge(np.column_stack((s, np.ones(len(s)))), a.astype(float), .001)
    phi = features(s)
    phi_next = features(nxt)
    q = np.zeros((2, 11), dtype=float)
    # Fixed batch fitted Q iteration: both action updates use the prior iteration.
    masks = [a == act for act in (0, 1)]
    if not all(np.any(m) for m in masks):
        raise ValueError('F40_BOTH_REAL_ACTIONS_REQUIRED')
    for _ in range(30):
        targets = rewards + .99*(1-done)*np.maximum(phi_next @ q[0], phi_next @ q[1])
        next_q = np.empty_like(q)
        for act, mask in enumerate(masks):
            next_q[act] = ridge(phi[mask], targets[mask], .01)
        q = next_q
    model = {'causal-linear-mpc': normal.tolist(),
             'wrong-action': inverted.tolist(),
             'no-learned-dynamics': identity.tolist(),
             'trained-linear-imitation': bc.tolist(), 'trained-fitted-q': q.tolist()}
    return json.loads(canonical(model))


def mpc_action(state, weights):
    w = np.asarray(weights, dtype=float)
    if w.shape != (6, 4):
        raise ValueError('F40_BAD_DYNAMICS_SHAPE')
    best_action, best_score = None, float('inf')
    for sequence in SEQUENCES:
        pred = np.array(state, dtype=float)
        score = 0.0
        for h, action in enumerate(sequence):
            x = np.array([*pred, 2*action-1, 1.0])
            pred = x @ w
            if not np.all(np.isfinite(pred)):
                raise ValueError('F40_MODEL_DIVERGED')
            step_cost = 10*pred[2]**2 + .5*pred[3]**2 + .2*pred[0]**2 + .02*pred[1]**2
            if abs(pred[0]) > 2.4 or abs(pred[2]) > .20943951:
                step_cost += 25
            score += (.92 ** h) * step_cost
        if score < best_score:
            best_score, best_action = score, sequence[0]
    return best_action


def choose(state, kind, model):
    if kind == 'behavior-rule':
        return behavior_action(state)
    if kind == 'trained-linear-imitation':
        value = float(np.dot(np.array([*state, 1.0]), np.array(model[kind])))
        return int(value >= .5)
    if kind == 'trained-fitted-q':
        q = np.asarray(model[kind], dtype=float)
        return int(np.argmax(q @ features([state])[0]))
    return mpc_action(state, model[kind])


def new_cartpole(gym):
    env = gym.make('CartPole-v1', render_mode=None)
    if env.action_space.n != 2:
        env.close()
        raise ValueError('F40_ORIGINAL_ACTION_GRAMMAR_DRIFT')
    return env


def episode(gym, seed, policy, *, cap, rng=None, model=None):
    if seed in FIRST_USE_FORBIDDEN:
        raise ValueError('F40_PROTECTED_FIRST_USE_REFUSED')
    env = new_cartpole(gym)
    try:
        obs, _ignored_info = env.reset(seed=int(seed))
        state = public_obs(obs)
        start = state[:]
        transitions = []
        decision_ns = 0
        for t in range(cap):
            tick = time.perf_counter_ns()
            action = behavior_action(state) if policy == 'training' else choose(state, policy, model)
            if rng is not None and rng.random() < .15:
                action = rng.randrange(2)
            decision_ns += time.perf_counter_ns() - tick
            if action not in (0, 1):
                raise ValueError('F40_BAD_REAL_ACTION')
            nxt_obs, reward, terminated, truncated, _ignored_info = env.step(action)
            nxt = public_obs(nxt_obs)
            reward = float(reward)
            if not math.isfinite(reward) or type(terminated) is not bool or type(truncated) is not bool:
                raise ValueError('F40_BAD_ORIGINAL_STEP')
            done = terminated or truncated
            transitions.append({'s': state, 'a': action, 'next': nxt, 'reward': reward,
                                'done': done, 'terminated': terminated, 'truncated': truncated})
            state = nxt
            if done:
                break
        return {'initial': start, 'transitions': transitions,
                'reward': sum(v['reward'] for v in transitions),
                'decision_ns': decision_ns}
    finally:
        env.close()


def training(gym):
    transcript = []
    coverage = [0, 0]
    for seed in TRAIN_SEEDS:
        for ep in range(32):
            rng = random.Random(0xF400000 + seed*1000 + ep)
            got = episode(gym, seed+1000*ep, 'training', cap=200, rng=rng)
            for step in got['transitions']:
                transcript.append(step)
                coverage[step['a']] += 1
    if not all(coverage):
        raise ValueError('F40_EMPTY_REAL_ACTION_CLASS')
    return transcript, coverage


def assess(gym, models, training_hash, source):
    cold_raw = canonical(models)
    warm_model = models
    cold_model = json.loads(cold_raw)
    if canonical(cold_model) != cold_raw:
        raise ValueError('F40_CHECKPOINT_RESTORE_DRIFT')
    report = {'schema': 'forge.eureka.original-cartpole-dev.f40.v1',
              'source': source, 'training_sha256': training_hash,
              'model_checkpoint_sha256': digest(models),
              'training_seeds': TRAIN_SEEDS, 'eval_seeds': EVAL_SEEDS,
              'development_only': True, 'first_use_consumed': False,
              'scientific_accepted': False, 'owner_eligible': False,
              'matched_whole_process_compute_proven': False, 'arms': {}}
    for kind in KINDS:
        arm = {'worlds': [], 'params': 0, 'decision_ns': 0}
        if kind in models:
            arm['params'] = int(np.asarray(models[kind]).size)
        for seed in EVAL_SEEDS:
            cold = episode(gym, seed, kind, cap=500, model=cold_model)
            warm = episode(gym, seed, kind, cap=500, model=warm_model)
            # Do not compare timing noise; compare all source-exposed physical data.
            if canonical(cold['transitions']) != canonical(warm['transitions']) or cold['initial'] != warm['initial']:
                raise ValueError('F40_COLD_WARM_REAL_ACTION_TRACE_MISMATCH')
            transitions = cold['transitions']
            arm['worlds'].append({'seed': seed, 'return': cold['reward'], 'steps': len(transitions),
                                  'actions_sha256': digest([v['a'] for v in transitions]),
                                  'observations_sha256': digest([cold['initial'], [v['next'] for v in transitions]]),
                                  'rewards_sha256': digest([v['reward'] for v in transitions]),
                                  'terminated': transitions[-1]['terminated'],
                                  'truncated': transitions[-1]['truncated'], 'cold_matches': True})
            arm['decision_ns'] += cold['decision_ns']
        arm['mean_return'] = sum(w['return'] for w in arm['worlds']) / len(EVAL_SEEDS)
        report['arms'][kind] = arm
    conventional = max(('behavior-rule','trained-linear-imitation','trained-fitted-q'),
                       key=lambda k: report['arms'][k]['mean_return'])
    cand = report['arms']['causal-linear-mpc']
    best = report['arms'][conventional]
    report['selected_conventional'] = conventional
    report['candidate_mean_gain'] = cand['mean_return'] - best['mean_return']
    report['per_seed_gains_ge_10'] = sum(c['return'] >= b['return']+10 for c,b in zip(cand['worlds'],best['worlds']))
    report['classification'] = 'F40_DEV_NO_GO'
    if (report['candidate_mean_gain'] >= 20 and report['per_seed_gains_ge_10'] >= 6
            and all(cand['mean_return'] >= report['arms'][k]['mean_return']+20
                    for k in ('wrong-action','no-learned-dynamics'))):
        report['classification'] = 'F40_DEV_SIGNAL_UNVERIFIED'
    report['report_sha256'] = digest(report)
    return report


def original_gym(root):
    # Import ITD02 source verifier. Never import alternate unpinned Gymnasium.
    from itd02_original_gymnasium_dev_smoke import original_pin, git
    original_pin(root)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    import gymnasium as gym
    if not Path(gym.__file__).resolve().is_relative_to(root):
        raise ValueError('F40_IMPORTED_NONPINNED_GYMNASIUM')
    return gym, git


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        raise ValueError('F40_USAGE: script.py /original/Gymnasium /out/report.json')
    root = Path(argv[0]).resolve(strict=True)
    dest = Path(argv[1]).resolve()
    if dest.is_relative_to(root):
        raise ValueError('F40_OUTPUT_IN_ORIGINAL_SOURCE_REFUSED')
    try:
        gym, git = original_gym(root)
    except (ImportError, FileNotFoundError) as exc:
        raise RuntimeError('F40_ORIGINAL_RUNTIME_BLOCKED') from exc
    t0 = time.perf_counter()
    train, counts = training(gym)
    t1 = time.perf_counter()
    model = fit_models(train)
    t2 = time.perf_counter()
    result = assess(gym, model, digest(train), ORIGINAL)
    result['train_episodes'] = len(TRAIN_SEEDS)*32
    result['train_transitions'] = len(train)
    result['train_action_counts'] = counts
    result['training_environment_seconds'] = t1-t0
    result['fitting_seconds'] = t2-t1
    result['report_sha256'] = digest({k:v for k,v in result.items() if k!='report_sha256'})
    if git(root, 'status', '--porcelain=v1', '--untracked-files=all', '--ignored=matching'):
        raise ValueError('F40_PINNED_ORIGINAL_CHECKOUT_MUTATED')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(canonical(result)+b'\n')
    print('F40_ORIGINAL_GYMNASIUM_DEV=' + result['classification'], 'digest=' + result['report_sha256'])
    print('F40_TRAIN_TRANSITIONS=' + str(len(train)), 'trained_baseline=' + result['selected_conventional'],
          'candidate_gain=' + str(result['candidate_mean_gain']))
    return result


if __name__ == '__main__':
    main()
