"""Source-only defensive tests, NOT simulator regression."""
import unittest
import ast
from k4b_replay_state_repair import (
    source_replace, OLD_IMPORT, OLD_GET, OLD_SET, NEW_GET, NEW_SET)


class ReplayCandidateSafety(unittest.TestCase):
    def setUp(self):
        self.source = (OLD_IMPORT + '\nclass CausalWorld:\n'
                       '    def get_state(self):\n' + OLD_GET + '\n'
                       '    def set_state(self, new_full_state):\n' + OLD_SET)

    def test_reaching_reward_state_bounded_and_syntax_valid(self):
        new = source_replace(self.source)
        ast.parse(new)
        self.assertIn("state['episode_length'] = self._episode_length", new)
        self.assertIn("self._episode_length = new_full_state['episode_length']", new)
        self.assertIn("reaching_reward_history", new)
        self.assertIn("REACHING_REWARD_HISTORY_DRIFT", new)
        self.assertIn("np.random.set_state", new)
        self.assertIn("random.setstate", new)
        self.assertIn("ENVIRONMENT_RNG_TYPE_DRIFT", new)
        self.assertNotIn(OLD_GET, new)
        self.assertNotIn(OLD_SET, new)

    def test_second_application_denied(self):
        new = source_replace(self.source)
        with self.assertRaisesRegex(RuntimeError, 'UNEXPECTED_OR_AMBIGUOUS'):
            source_replace(new)

    def test_unknown_source_denied(self):
        with self.assertRaisesRegex(RuntimeError,'UNEXPECTED_OR_AMBIGUOUS'):
            source_replace(self.source.replace('import copy','import cpy'))

    def test_ambiguity_denied(self):
        with self.assertRaisesRegex(RuntimeError,'UNEXPECTED_OR_AMBIGUOUS'):
            source_replace(self.source + OLD_SET)


if __name__ == '__main__':
    unittest.main()
