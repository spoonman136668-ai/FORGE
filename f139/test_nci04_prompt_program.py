"""Typed-program compiler falsification; candidate execution is test-only."""
from fractions import Fraction
import itertools
from pathlib import Path
import unittest

from f139 import nci04_model_free_search as search
from f139.nci04_genenv_source import source_for_vector
from f139.nci04_native_contract import digest
from f139.nci04_prompt_program import (
    BRANCHES,MARKER,SEED,ProgramRejected,build_plan,recover_program,
    public_choice_gap,public_rate_preflight,public_success_count_order,
    same_ordering,source_for_program,
)
from f139.nci04_prompt_source import frozen_digest

BEFORE = Path(__file__).with_name("fixtures").joinpath("model_free_yggdrasil_992ef.py").read_bytes()
LEGACY = tuple(source_for_vector(BEFORE,v)[0] for v in itertools.product((0,1),repeat=3) if any(v))


def plan(sources=LEGACY,**overrides):
    args = dict(history_sources=sources,consumed_sha256={digest(x) for x in sources},
        historical_ast_sha256={search.normalized(x) for x in sources},
        history_sha256="a"*64,mechanism_sha256="b"*64)
    return build_plan(BEFORE,**{**args,**overrides})


def oracle(program,counts):
    """Independent rational oracle over the original unsimplified grammar."""
    words = program.split(" ")
    def value(pos,success,failure):
        token = words[pos]
        if pos not in BRANCHES:
            return dict(success=success,failure=failure,total=success+failure,
                        zero=0,one=1,two=2)[token],pos+1
        a,pos = value(pos+1,success,failure)
        b,pos = value(pos,success,failure)
        return {"add":lambda:a+b,"mul":lambda:a*b,"min":lambda:min(a,b),
                "max":lambda:max(a,b)}[token](),pos
    rates = []
    for failure,success in counts:
        if failure+success == 0:
            return None
        n,pos = value(1,success,failure)
        d,pos = value(pos,success,failure)
        if d <= 0:
            return None
        rates.append(Fraction(n,d))
    return None if rates[0] == rates[1] else 0 if rates[0] > rates[1] else 1


class TypedProgramTests(unittest.TestCase):
    def test_all_seven_consumed_sources_leave_a_fresh_bounded_population(self):
        p = plan()
        self.assertGreater(len(p.bindings),0)
        self.assertLessEqual(len(p.bindings),16)
        self.assertEqual(len(p.bindings),len(p.frozen["operations"]))
        self.assertEqual(len(p.frozen["parent"].split(" ")),20)
        self.assertEqual(len({search.normalized(b.source.after) for b in p.bindings}),len(p.bindings))
        self.assertTrue(all(b.source.after_sha256 not in {digest(x) for x in LEGACY}
                            for b in p.bindings))

    def test_recovered_generated_sources_continue_without_resetting_negatives(self):
        sources = LEGACY
        consumed = {digest(x) for x in sources}
        for _ in range(12):
            p = plan(sources)
            self.assertIsNotNone(p)
            child = p.bindings[0].source.after
            self.assertNotIn(digest(child),consumed)
            self.assertIsNotNone(recover_program(BEFORE,child))
            consumed.add(digest(child))
            sources += (child,)
        self.assertEqual(len(consumed),19)
        self.assertTrue({digest(x) for x in LEGACY} <= consumed)

    def test_public_rate_preflight_rejects_real_v36_negatives_but_keeps_history(self):
        # Exact public-counter programs from original V36 task negatives
        # i1483 (tautological tie) and i1484 (failure-rate inversion).
        negatives = (
            "rate min max success total add total zero add add total zero add zero zero",
            "rate min min failure total add total zero add add total zero add zero zero",
            "rate add add failure zero add zero zero add add total zero add zero zero",
        )
        for program in negatives:
            with self.subTest(program=program):
                self.assertFalse(public_rate_preflight(program))
                # Existing source identities stay reconstructible for custody.
                # Historical decoding is never requalified by this new filter.
                historical = source_for_program(BEFORE, program)
                reconstructed = recover_program(BEFORE, historical)
                self.assertIsNotNone(reconstructed)
                self.assertEqual(source_for_program(BEFORE, reconstructed), historical)
        self.assertTrue(public_rate_preflight(SEED))
        laplace = "rate add add success one add zero zero add add total two add zero zero"
        self.assertTrue(public_rate_preflight(laplace))

    def test_pr830_domain_equivalence_rejected_without_rewriting_history(self):
        # The exact natural F139 Yggdrasil PR #830 head program simplifies to
        # success / total only on the genuine nonnegative, nonempty domain:
        # min(success,total,success*total) == success.
        programs = (
            "rate min min success total mul success total add add total zero add zero zero",
            "rate min min total success mul total success add add total zero add zero zero",
            "rate min add success zero add total zero add add total zero add zero zero",
        )
        for program in programs:
            with self.subTest(program=program):
                self.assertFalse(public_rate_preflight(program))
                # Prospective rejection cannot erase or re-hash earlier drafts:
                # the historical decoder still reconstructs the exact bytes.
                original_bytes = source_for_program(BEFORE, program)
                self.assertNotEqual(original_bytes, BEFORE)
                recovered = recover_program(BEFORE, original_bytes)
                self.assertIsNotNone(recovered)
                self.assertEqual(source_for_program(BEFORE, recovered),
                                 original_bytes)

        # Independent rational oracle, including both arm orders and ties.
        baseline = SEED
        cases = [(failure, success)
                 for trials in (1, 2, 7, 16)
                 for success in range(trials + 1)
                 for failure in (trials - success,)]
        cases.extend(((0, 65535), (65535, 0), (65535, 65535)))
        for first in cases:
            for second in cases:
                counts = (first, second)
                expected = oracle(baseline, counts)
                self.assertEqual(oracle(programs[0], counts), expected)

    def test_proven_public_choice_alias_is_filtered_without_erasing_history(self):
        # Distinct original Yggdrasil PR #843/#844 hashes: under nonnegative
        # counts, success*success <= success*total and
        # failure*success <= success*total. Both reduce to success*total.
        p843 = ("rate max mul success success mul success total "
                "add add total zero add zero zero")
        p844 = ("rate max mul failure success mul success total "
                "add add total zero add zero zero")
        p845 = ("rate add mul failure success mul success total "
                "add add total zero add zero zero")
        a, b = source_for_program(BEFORE, p843), source_for_program(BEFORE, p844)
        self.assertNotEqual(a, b)
        self.assertEqual(recover_program(BEFORE, a) is not None, True)
        self.assertEqual(recover_program(BEFORE, b) is not None, True)
        self.assertTrue(public_rate_preflight(p843))
        self.assertTrue(public_rate_preflight(p844))
        self.assertTrue(same_ordering(public_choice_gap(p843),
                                      public_choice_gap(p844)))
        self.assertFalse(same_ordering(public_choice_gap(p843),
                                       public_choice_gap(p845)))
        for c0 in range(5):
            for s0 in range(5):
                for c1 in range(5):
                    for s1 in range(5):
                        if (c0+s0)*(c1+s1) == 0:
                            continue
                        counts = ((c0,s0),(c1,s1))
                        self.assertEqual(oracle(p843,counts), oracle(p844,counts))
        # Even a scientifically rejected historical source remains a known
        # behavior; it is not a valid mutation parent or a fresh discovery.
        result = plan(LEGACY + (a,), eligible_parent_sha256=set())
        self.assertIsNotNone(result)
        for binding in result.bindings:
            current = recover_program(BEFORE, binding.source.after)
            self.assertFalse(same_ordering(public_choice_gap(current),
                                           public_choice_gap(p843)))

    def test_original_success_count_family_has_global_symbolic_certificate(self):
        # These five immutable original owner-produced Yggdrasil PRs are
        # different source identities but have identical action-choice behavior.
        programs = {
            838: ("rate mul add success success mul success total "
                  "add add total zero add zero zero"),
            842: ("rate mul mul success success mul success total "
                  "add add total zero add zero zero"),
            843: ("rate max mul success success mul success total "
                  "add add total zero add zero zero"),
            844: ("rate max mul failure success mul success total "
                  "add add total zero add zero zero"),
            846: ("rate add add failure success mul success total "
                  "add add total zero add zero zero"),
        }
        controls = {
            830: ("rate min min success total mul success total "
                  "add add total zero add zero zero"),
            845: ("rate add mul failure success mul success total "
                  "add add total zero add zero zero"),
            847: ("rate mul add failure success mul success total "
                  "add add total zero add zero zero"),
        }
        for number, program in programs.items():
            with self.subTest(pr=number):
                self.assertTrue(public_success_count_order(program))
        for number, program in controls.items():
            with self.subTest(proven_distinct_class=number):
                self.assertFalse(public_success_count_order(program))

        # An independent exact-rational implementation checks observed
        # choices AND ties for both action orders; it is NOT the proof.
        cases = [(f, s) for f in range(6) for s in range(6) if f+s]
        for a in cases:
            for b in cases:
                counts = (a, b)
                baseline = oracle(programs[843], counts)
                for number, program in programs.items():
                    with self.subTest(counts=counts, pr=number):
                        self.assertEqual(oracle(program, counts), baseline)

        # Non-eligible negatives remain consumed, immutable, and cannot
        # regenerate a globally equivalent new source.
        prior = source_for_program(BEFORE, programs[838])
        self.assertEqual(recover_program(BEFORE, prior), programs[838])
        proposal = plan(LEGACY + (prior,), eligible_parent_sha256=set())
        self.assertIsNotNone(proposal)
        self.assertGreater(len(proposal.bindings), 0)
        for candidate in proposal.bindings:
            fresh = recover_program(BEFORE, candidate.source.after)
            self.assertFalse(public_success_count_order(fresh))

    def test_domain_proof_does_not_reject_actual_counter_dependent_rates(self):
        # min(success,total) is exactly success; the *denominator* matters.
        # total+1 changes decisions at unequal exposure but preserves the
        # required matched-exposure ordering and abstention checks.
        changed = (
            "rate min add success zero add total zero add add total one add zero zero"
        )
        self.assertTrue(public_rate_preflight(changed))
        self.assertNotEqual(source_for_program(BEFORE, changed), BEFORE)
        counts = ((0, 1), (3, 7))
        self.assertNotEqual(oracle(changed, counts), oracle(SEED, counts))
        laplace = "rate add add success one add zero zero add add total two add zero zero"
        self.assertTrue(public_rate_preflight(laplace))
        self.assertEqual(source_for_program(BEFORE, laplace), LEGACY[3])

    def test_new_proposals_preserve_public_matched_exposure_order(self):
        proposal = plan()
        self.assertIsNotNone(proposal)
        self.assertGreater(len(proposal.bindings), 0)
        self.assertTrue(all(public_rate_preflight(
            binding.prompt.split(" history ", 1)[0])
            for binding in proposal.bindings))
        # Negative candidates remain consumed, never eligible as parents.
        negatives = (
            source_for_program(BEFORE,
                "rate min max success total add total zero add add total zero add zero zero"),
            source_for_program(BEFORE,
                "rate min min failure total add total zero add add total zero add zero zero"),
        )
        later = plan(LEGACY + negatives, eligible_parent_sha256=set())
        self.assertIsNotNone(later)
        self.assertEqual(later.parent_program, SEED)
        self.assertTrue({digest(x) for x in negatives}.isdisjoint(
            {b.source.after_sha256 for b in later.bindings}))

    def test_generated_arithmetic_matches_independent_fraction_oracle_and_keeps_memory(self):
        for binding in plan().bindings:
            source = binding.source.after
            namespace = {}
            exec(compile(source,"qualified-development-fixture","exec"),namespace)
            cls = namespace["PublicCausalCells"]
            program = recover_program(BEFORE,source)
            for index in range(96):
                counts = ((index%7,(index*3+1)%7),((index*5+2)%7,(index*2+3)%7))
                cells = cls()
                cells._counts[0] = [list(x) for x in counts]
                before = cells.snapshot()
                self.assertEqual(cells.choose(0),oracle(program,counts))
                self.assertEqual(cells.snapshot(),before)
                self.assertEqual(len(before),164)
                self.assertEqual(cells.LEARNED_BYTES,128)
                cells._counts[0].reverse()
                swapped = cells.choose(0)
                expected = oracle(program,counts)
                self.assertEqual(swapped,None if expected is None else 1-expected)
                self.assertIsNone(cells.choose(0,retained=True))

    def test_sources_preserve_all_original_methods_except_choice(self):
        import ast
        def methods(raw):
            cls = next(x for x in ast.parse(raw).body if isinstance(x,ast.ClassDef))
            return {x.name:ast.dump(x,include_attributes=False) for x in cls.body
                    if isinstance(x,ast.FunctionDef) and x.name != "choose"}
        expected = methods(BEFORE)
        self.assertTrue(all(methods(b.source.after) == expected for b in plan().bindings))

    def test_baseline_affine_replays_and_original_laplace_share_original_identities(self):
        self.assertEqual(source_for_program(BEFORE,SEED),BEFORE)
        doubled = SEED.replace("success zero","success success",1)
        self.assertEqual(source_for_program(BEFORE,doubled),BEFORE)
        laplace = "rate add add success one add zero zero add add total two add zero zero"
        self.assertEqual(source_for_program(BEFORE,laplace),LEGACY[3])
        scaled = "rate mul add success one add one one add add total two add zero zero"
        self.assertEqual(source_for_program(BEFORE,scaled),LEGACY[3])

    def test_history_is_bound_in_actual_prompt_plan_without_source_nonce_replays(self):
        a,b = plan(),plan(history_sha256="c"*64)
        self.assertNotEqual(frozen_digest(a.frozen),frozen_digest(b.frozen))
        self.assertEqual([x.source.after_sha256 for x in a.bindings],
                         [x.source.after_sha256 for x in b.bindings])
        self.assertIn(" history "+" ".join(["a"*16]*4),a.frozen["parent"])

    def test_raw_and_ast_negative_sets_are_both_used_for_preflight(self):
        p = plan()
        child = p.bindings[0].source
        for overrides in (dict(consumed_sha256={child.after_sha256}),
                          dict(historical_ast_sha256={search.normalized(child.after)})):
            new = plan(**overrides)
            self.assertNotIn(child.after_sha256,[b.source.after_sha256 for b in new.bindings])

    def test_marker_is_only_a_lookup_hint_not_source_provenance(self):
        child = plan().bindings[0].source.after
        with self.assertRaisesRegex(ProgramRejected,"HISTORY_SOURCE_DRIFT"):
            recover_program(BEFORE,child+b"\nx=1\n")
        forged = BEFORE+MARKER.encode()+SEED.encode()+b"\n"
        with self.assertRaises(ProgramRejected):
            recover_program(BEFORE,forged)

    def test_equivalent_tokens_cannot_change_source_identity_before_native_intake(self):
        # The public-rate prefilter may reorder the first fresh candidate.
        # Find a real commutative spelling alias instead of assuming that
        # candidate zero contains a particular "failure zero" token pair.
        child = alias = canonical = None
        for binding in plan().bindings:
            original = binding.source.after
            program = recover_program(BEFORE, original)
            words = program.split(" ")
            for pos in sorted(BRANCHES):
                if (pos + 2 >= len(words) or pos + 1 in BRANCHES
                        or pos + 2 in BRANCHES or words[pos+1] == words[pos+2]):
                    continue
                swapped = words.copy()
                swapped[pos+1], swapped[pos+2] = swapped[pos+2], swapped[pos+1]
                candidate_alias = " ".join(swapped)
                if source_for_program(BEFORE, candidate_alias) == original:
                    child, canonical, alias = original, program, candidate_alias
                    break
            if alias is not None:
                break
        self.assertIsNotNone(alias, "NO_EQUIVALENT_TOKEN_ALIAS_IN_FRESH_BATCH")
        self.assertNotEqual(alias, canonical)
        self.assertEqual(source_for_program(BEFORE, alias), child)
        # Original publication custody has the raw hash before native intake.
        # The new source's AST is deliberately absent from this fixture.
        new = plan(consumed_sha256={digest(child)},historical_ast_sha256=set())
        self.assertNotIn(search.normalized(child),
                         [search.normalized(b.source.after) for b in new.bindings])

    def test_untyped_tokens_capacity_growth_and_invalid_context_fail_closed(self):
        for invalid in (SEED+" zero",SEED.replace("add","__import__",1),
                        SEED.replace("success","42",1),SEED.replace("rate","eval",1)):
            with self.subTest(program=invalid),self.assertRaises(ProgramRejected):
                source_for_program(BEFORE,invalid)
        for overrides in (dict(max_candidates=17),dict(max_candidates=True),
                          dict(history_sha256="wrong"),dict(history_sources=LEGACY*600)):
            with self.subTest(keys=list(overrides)),self.assertRaises(ProgramRejected):
                plan(**overrides)
        with self.assertRaisesRegex(ValueError,"FROZEN_SOURCE_DRIFT"):
            source_for_program(BEFORE+b"\n",SEED)


if __name__ == "__main__":
    unittest.main()
