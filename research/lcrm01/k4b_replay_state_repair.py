#!/usr/bin/env python3
"""Create a bounded *candidate* CausalWorld replay fix, without editing upstream.

Strictly matches known source fragments of rr-learning/CausalWorld at
1045277101a92c506db42704da28f6e7227d401b. Writes candidate source to
an independent output; never executes it or authorizes a scientific experiment.
"""
import argparse
import ast
import pathlib
import subprocess
import sys

PIN = '1045277101a92c506db42704da28f6e7227d401b'
REL = pathlib.Path('causal_world/envs/causalworld.py')

OLD_IMPORT = 'import copy\nimport logging\n'
NEW_IMPORT = 'import copy\nimport random\nimport logging\n'

OLD_GET = '''        state = dict()
        state['pybullet_state'] = self._task._save_pybullet_state()
        state['control_index'] = self._robot._control_index
        return state
        # return self._task.save_state()
'''
NEW_GET = '''        state = dict()
        state['pybullet_state'] = self._task._save_pybullet_state()
        state['control_index'] = self._robot._control_index
        state['episode_length'] = self._episode_length
        state['numpy_rng_state'] = copy.deepcopy(np.random.get_state())
        state['python_rng_state'] = copy.deepcopy(random.getstate())
        if hasattr(self.np_random, 'bit_generator'):
            state['environment_rng_kind'] = 'generator'
            state['environment_rng_state'] = copy.deepcopy(
                self.np_random.bit_generator.state)
        else:
            state['environment_rng_kind'] = 'legacy'
            state['environment_rng_state'] = copy.deepcopy(
                self.np_random.get_state())
        for field in ('_last_action', '_last_clipped_action',
                      '_last_applied_joint_positions'):
            state[field] = copy.deepcopy(getattr(self._robot, field))
        state['task_solved'] = bool(self._task._task_solved)
        if self._task._task_name == 'reaching':
            state['reaching_reward_history'] = {
                'previous_end_effector_positions': copy.deepcopy(
                    self._task.previous_end_effector_positions),
                'previous_joint_velocities': copy.deepcopy(
                    self._task.previous_joint_velocities),
            }
        return state
'''

OLD_SET = '''        self._task._restore_pybullet_state(new_full_state['pybullet_state'])
        self._robot._control_index = new_full_state['control_index']
        self._robot.update_latest_full_state()
        return
'''
NEW_SET = '''        # K4B bounded replay candidate only: no interventions between save/restore.
        # Fail on absent fields rather than silently treating snapshots as complete.
        self._task._restore_pybullet_state(new_full_state['pybullet_state'])
        self._robot._control_index = new_full_state['control_index']
        self._robot.update_latest_full_state()
        self._episode_length = new_full_state['episode_length']
        np.random.set_state(copy.deepcopy(new_full_state['numpy_rng_state']))
        random.setstate(copy.deepcopy(new_full_state['python_rng_state']))
        kind = new_full_state['environment_rng_kind']
        if kind == 'generator' and hasattr(self.np_random, 'bit_generator'):
            self.np_random.bit_generator.state = copy.deepcopy(
                new_full_state['environment_rng_state'])
        elif kind == 'legacy' and hasattr(self.np_random, 'set_state'):
            self.np_random.set_state(copy.deepcopy(
                new_full_state['environment_rng_state']))
        else:
            raise RuntimeError('ENVIRONMENT_RNG_TYPE_DRIFT')
        for field in ('_last_action', '_last_clipped_action',
                      '_last_applied_joint_positions'):
            setattr(self._robot, field, copy.deepcopy(new_full_state[field]))
        self._task._task_solved = new_full_state['task_solved']
        if self._task._task_name == 'reaching':
            reward_state = new_full_state['reaching_reward_history']
            if set(reward_state) != {
                    'previous_end_effector_positions',
                    'previous_joint_velocities'}:
                raise RuntimeError('REACHING_REWARD_HISTORY_DRIFT')
            self._task.previous_end_effector_positions = copy.deepcopy(
                reward_state['previous_end_effector_positions'])
            self._task.previous_joint_velocities = copy.deepcopy(
                reward_state['previous_joint_velocities'])
        return
'''


def source_replace(src):
    for before, after in ((OLD_IMPORT, NEW_IMPORT), (OLD_GET, NEW_GET),
                          (OLD_SET, NEW_SET)):
        if src.count(before) != 1:
            raise RuntimeError('UNEXPECTED_OR_AMBIGUOUS_SOURCE_FRAGMENT')
        src = src.replace(before, after, 1)
    ast.parse(src)
    return src


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    a = p.parse_args(argv)
    repo = a.repo.resolve()
    if not (repo / '.git').exists():
        raise RuntimeError('NOT_A_GIT_CHECKOUT')
    sha = subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if sha != PIN:
        raise RuntimeError('WRONG_SOURCE_COMMIT:' + sha)
    if subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip():
        raise RuntimeError('SOURCE_DIRTY')
    source = (repo / REL).read_text(encoding='utf-8')
    out = a.output.resolve()
    if out.exists():
        raise RuntimeError('OUTPUT_EXISTS')
    out.parent.mkdir(parents=True,exist_ok=True)
    result = source_replace(source)
    out.write_text(result,encoding='utf-8')
    print('K4B_CANDIDATE_SOURCE_CREATED=' + str(out))
    print('K4B_ORIGINAL_SOURCE_UNCHANGED=TRUE')
    print('K4B_RUNTIME_QUALIFICATION=NOT_RUN')
    return 0


if __name__ == '__main__':
    sys.exit(main())
