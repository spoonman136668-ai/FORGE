"""Optimizer K5C-S0 original-source-grounded memory necessity witness.

No import, reset, step, FIT/CHECK/DEV sampling, or trained agent.
This is a handwritten public-observation abstraction of pinned POPGym
ConcentrationHard source at proroklab/popgym@410d5aa626dae8024f498354d8781a0d1870c399.
Original file Git blob: 8f0d2d316c1ae63a7965ce1c56295a9aa403bbb9.
"""
from __future__ import annotations
from hashlib import sha256
import json
import unittest

ORIGINAL_SOURCE_COMMIT = "410d5aa626dae8024f498354d8781a0d1870c399"
ORIGINAL_SOURCE_BLOB = "8f0d2d316c1ae63a7965ce1c56295a9aa403bbb9"
DECK_BLOB = "12bcabfa9a96fd1261809ef0a446c74d3f3bfa86"
HIDDEN = 13   # source: facedown_card=len(unique ranks), ranks 0..12
CARDS = 52

# Each rank occurs four times, exactly as source Deck(num_decks=1).ranks_idx.
# Handcrafted legal arrangements, NOT the output of original Deck.shuffle.
TAIL = tuple(rank for rank in range(2,13) for _ in range(4))
WORLD_A = (0,1,0,1,0,0,1,1) + TAIL
WORLD_B = (1,0,0,1,1,1,0,0) + TAIL


def public_current(deck: tuple[int,...], in_play: tuple[int,...] = (),
                   matched: tuple[int,...] = ()) -> tuple[int,...]:
    """Source get_obs(): facedown sentinel except currently exposed positions.

    The source computes the observation before discarding two nonmatching flips,
    so the caller can observe earlier nonmatches at the time they occur.
    """
    result = [HIDDEN]*CARDS
    for i in (*matched,*in_play):
        result[i] = deck[i]
    return tuple(result)


def public_history(deck):
    # A deterministic legal sequence: flip position 0, then 1 (a mismatch),
    # those two are discarded face-down, then flip position 2 (rank 0).
    first = public_current(deck,(0,))
    second = public_current(deck,(0,1))
    assert deck[0] != deck[1], "WITNESS_NOT_AN_ORIGINAL_SOURCE_MISMATCH"
    third = public_current(deck,(2,))
    return first,second,third


def matching_second_action(deck, action):
    # After first card pos2 is rank0, original source disallows same index
    # as a valid pair. Source rewards equality of the two ranks if distinct.
    return int(action != 2 and 0 <= action < CARDS and deck[action] == deck[2])


def memory_decision(history):
    # Derive rank0 position from observed BEFORE-hidden information only.
    first,second,now = history
    value = now[2]
    choices = [i for i in (0,1) if second[i] == value]
    assert len(choices) == 1
    return choices[0]


def audit():
    h_a = public_history(WORLD_A)
    h_b = public_history(WORLD_B)
    legal_actions = tuple(range(CARDS))
    common_successes = tuple(a for a in legal_actions
                             if matching_second_action(WORLD_A,a)
                             and matching_second_action(WORLD_B,a))
    win_a = tuple(a for a in legal_actions if matching_second_action(WORLD_A,a))
    win_b = tuple(a for a in legal_actions if matching_second_action(WORLD_B,a))
    result = {
      "status":"SOURCE_ONLY_PUBLIC_MEMORY_NECESSITY_PROVED",
      "original_source_commit":ORIGINAL_SOURCE_COMMIT,
      "original_concentration_git_blob":ORIGINAL_SOURCE_BLOB,
      "original_deck_git_blob":DECK_BLOB,
      "original_source_executed":False,
      "original_environment_resets":0,
      "original_environment_steps":0,
      "protected_roles_consumed":0,
      "lawful_two_world_rank_counts_equal":all(WORLD_A.count(i)==WORLD_B.count(i)==4 for i in range(13)),
      "same_first_actions":[0,1,2],
      "same_last_action":2,
      "current_public_observations_identical":h_a[-1]==h_b[-1],
      "previous_public_histories_distinguishable":h_a[:-1]!=h_b[:-1],
      "guaranteed_match_actions_world_a":win_a,
      "guaranteed_match_actions_world_b":win_b,
      "common_guaranteed_match_action":list(common_successes),
      "memory_choice_world_a":memory_decision(h_a),
      "memory_choice_world_b":memory_decision(h_b),
      "memory_choice_successes_both":bool(matching_second_action(WORLD_A,memory_decision(h_a))
        and matching_second_action(WORLD_B,memory_decision(h_b))),
      "memoryless_first_match_max_success_under_two_equiprobable_worlds":max(
        (matching_second_action(WORLD_A,a)+matching_second_action(WORLD_B,a))/2
         for a in legal_actions),
      "scientific_accepted":False,
      "tested_native_learner":False,
      "novelty_claim":False,
    }
    assert result["lawful_two_world_rank_counts_equal"]
    assert result["current_public_observations_identical"]
    assert result["previous_public_histories_distinguishable"]
    assert result["common_guaranteed_match_action"]==[]
    assert result["memory_choice_successes_both"]
    assert result["memoryless_first_match_max_success_under_two_equiprobable_worlds"]==0.5
    return result


class SourceContract(unittest.TestCase):
    def test_original_deck_validity(self):
        self.assertTrue(all(len(d)==52 and set(d)==set(range(13)) and
                            all(d.count(i)==4 for i in range(13))
                            for d in (WORLD_A,WORLD_B)))
    def test_first_two_are_real_nonsuccessful_pair(self):
        self.assertTrue(all(d[0]!=d[1] for d in (WORLD_A,WORLD_B)))
    def test_first_two_public_histories_are_distinguishable(self):
        self.assertNotEqual(public_history(WORLD_A)[:2],public_history(WORLD_B)[:2])
    def test_current_public_observation_alias(self):
        a=public_history(WORLD_A)[-1];b=public_history(WORLD_B)[-1]
        self.assertEqual(a,b)
        self.assertEqual(a.count(HIDDEN),51)
        self.assertEqual(a[2],0)
    def test_no_reactive_solution_can_match_both(self):
        common=[i for i in range(CARDS) if matching_second_action(WORLD_A,i)
                and matching_second_action(WORLD_B,i)]
        self.assertEqual(common,[])
    def test_memory_recovers_distinct_correct_actions(self):
        self.assertEqual(memory_decision(public_history(WORLD_A)),0)
        self.assertEqual(memory_decision(public_history(WORLD_B)),1)
        self.assertTrue(all(matching_second_action(d,memory_decision(public_history(d)))
                            for d in (WORLD_A,WORLD_B)))
    def test_source_free_and_no_original_science(self):
        x=audit()
        self.assertFalse(x["original_source_executed"])
        self.assertEqual((x["original_environment_resets"],x["original_environment_steps"],
                          x["protected_roles_consumed"]),(0,0,0))
        self.assertEqual(x["memoryless_first_match_max_success_under_two_equiprobable_worlds"],.5)
        self.assertFalse(x["scientific_accepted"])

if __name__=="__main__":
    print(json.dumps(audit(),sort_keys=True,indent=2))
