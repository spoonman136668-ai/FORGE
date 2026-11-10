#!/usr/bin/env python3
"""DEV-only, pinned original Gymnasium reset/step receipts. Not scientific first-use."""
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys

SOURCE = 'e6be96abfb0a9df36da5e7884522c4f1f2432e53'
TREE = '0a6e6b8c16c9b039fad21128336cecf3a13e0877'
BLOBS = {
    'LICENSE': 'ac10bf443756cdc02724943ac09021092ce9e737',
    'pyproject.toml': 'a97db4c7753eeaa856b113586c2b33a47c906c47',
    'gymnasium/envs/classic_control/cartpole.py': '4fab48a4930e0897b3b2f19c5ef4c4253d7330df',
    'gymnasium/envs/classic_control/mountain_car.py': '5f9199360ab20fda093956f91c28d0af069d555f',
}
WORLDS = [('CartPole-v1', 4, 2), ('MountainCar-v0', 2, 3)]
SEEDS = (547, 557)
LIMIT = 32


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, timeout=15).strip()


def original_pin(root):
    if not (root / '.git').is_dir():
        raise ValueError('PINNED_GIT_CHECKOUT_REQUIRED')
    if git(root, 'rev-parse', 'HEAD') != SOURCE or git(root, 'rev-parse', 'HEAD^{tree}') != TREE:
        raise ValueError('PINNED_GIT_SHA_TREE_DRIFT')
    if git(root, 'status', '--porcelain=v1', '--untracked-files=all', '--ignored=matching'):
        raise ValueError('GIT_WORKTREE_UNCLEAN_INCLUDING_IGNORED')
    for line in git(root, 'ls-files', '-s', '--', 'gymnasium').splitlines():
        if line.split(maxsplit=1)[0] == '120000':
            raise ValueError('PINNED_PACKAGE_SYMLINK_REFUSED')
    for relative, expected in BLOBS.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError('PINNED_FILE_MISSING')
        data = path.read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if actual != expected:
            raise ValueError('PINNED_FILE_BLOB_DRIFT: ' + relative)


def public_obs(x, dimensions):
    data = x.tolist() if hasattr(x, 'tolist') else x
    if not isinstance(data, (tuple, list)) or len(data) != dimensions:
        raise ValueError('OBSERVATION_SHAPE_INVALID')
    result = [float(value) for value in data]
    if any(type(value) is bool or not math.isfinite(value) for value in result):
        raise ValueError('OBSERVATION_NONFINITE')
    return result


def trace(gym, world, dimensions, actions, seed):
    if seed not in SEEDS or seed in (59, 83):
        raise ValueError('FIRST_USE_OR_UNAPPROVED_SEED')
    env = gym.make(world, render_mode=None)
    try:
        if int(env.action_space.n) != actions:
            raise ValueError('ACTION_GRAMMAR_CHANGED')
        obs, _ignored_info = env.reset(seed=seed)
        initial = public_obs(obs, dimensions)
        rng = random.Random(seed ^ 0xF031D02)
        sequence = []
        for t in range(LIMIT):
            action = rng.randrange(actions)
            obs, reward, terminated, truncated, _ignored_info = env.step(action)
            reward = float(reward)
            if not math.isfinite(reward) or type(terminated) is not bool or type(truncated) is not bool:
                raise ValueError('STEP_RESULT_INVALID')
            sequence.append({'t': t, 'a': action, 'observation': public_obs(obs, dimensions),
                             'reward': reward, 'terminated': terminated, 'truncated': truncated})
            if terminated or truncated:
                break
        return {'environment': world, 'seed': seed, 'initial': initial, 'transitions': sequence}
    finally:
        env.close()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def main():
    if len(sys.argv) != 3:
        raise ValueError('USAGE: smoke.py /pinned/Gymnasium /output/receipt.json')
    root = Path(sys.argv[1]).resolve(strict=True)
    output = Path(sys.argv[2]).resolve()
    if output.is_relative_to(root):
        raise ValueError('OUTPUT_MUST_BE_OUTSIDE_PINNED_SOURCE')
    original_pin(root)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    import gymnasium as gym
    if not Path(gym.__file__).resolve().is_relative_to(root):
        raise ValueError('IMPORTED_NONPINNED_GYMNASIUM')
    results = []
    for world, dimensions, actions in WORLDS:
        for seed in SEEDS:
            a = trace(gym, world, dimensions, actions, seed)
            b = trace(gym, world, dimensions, actions, seed)
            if canonical(a) != canonical(b):
                raise ValueError('ORIGINAL_RESET_STEP_REPLAY_MISMATCH')
            results.append({'world': world, 'seed': seed, 'actions': len(a['transitions']),
                            'reward': sum(t['reward'] for t in a['transitions']),
                            'trace_sha256': hashlib.sha256(canonical(a)).hexdigest(),
                            'terminal': a['transitions'][-1]['terminated'],
                            'truncated': a['transitions'][-1]['truncated']})
    if git(root, 'status', '--porcelain=v1', '--untracked-files=all', '--ignored=matching'):
        raise ValueError('PINNED_CHECKOUT_MUTATED_DURING_ORIGINAL_EXECUTION')
    report = {'schema': 'forge.itd02.original-gymnasium-dev-smoke.v3', 'source': SOURCE,
              'tree': TREE, 'results': results, 'science_first_use': False,
              'scientific_accepted': False, 'owner_activation': False,
              'external_counterfactual_api_used': False}
    report['sha256'] = hashlib.sha256(canonical(report)).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical(report) + b'\n')
    print('ITD02_ORIGINAL_GYMNASIUM_DEV_SMOKE=PASS', report['sha256'])
    for item in results:
        print('ITD02_RECEIPT', item)


if __name__ == '__main__':
    main()
