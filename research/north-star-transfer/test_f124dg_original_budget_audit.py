"""F124-DG strict sourcefree audit acceptance at authentic full-rank stopping."""
from __future__ import annotations
import unittest
import f124dg_readonly_active_audit as audit

def case(initial,received,budget,rank=None):
    final=initial+received if rank is None else rank
    return {
      "extra_oracle_budget":budget,
      "new_oracle_queries_consumed":received,
      "original_FIT_rank":initial,
      "final_rank":final,
      "full_hypothesis_dimension":163,
      "rank_gain_from_extra_information":final-initial,
      "rank_saturated_before_query_budget":received<budget,
      "queries_distinct":True,
      "query_budget_is_MAXIMUM_not_forced_redundant_observations":True}

class ExactOriginalAuditAcceptance(unittest.TestCase):
    def test_no_extra_information_budget(self):
        self.assertTrue(audit.exact_equal_information_stop(case(140,0,0)))
    def test_exact_allocated_16_queries(self):
        self.assertTrue(audit.exact_equal_information_stop(case(130,16,16)))
    def test_48_query_budget_ends_at_independently_proved_rank163(self):
        self.assertTrue(audit.exact_equal_information_stop(case(134,29,48)))
        self.assertTrue(audit.exact_equal_information_stop(case(163,0,48)))
    def test_under_budget_without_full_rank_denied(self):
        self.assertFalse(audit.exact_equal_information_stop(case(134,25,48)))
    def test_over_budget_denied(self):
        self.assertFalse(audit.exact_equal_information_stop(case(114,49,48)))
    def test_rank_faked_denied_even_when_full(self):
        self.assertFalse(audit.exact_equal_information_stop(case(133,28,48,163)))
    def test_early_stop_flag_wrong_denied(self):
        x=case(134,29,48);x["rank_saturated_before_query_budget"]=False
        self.assertFalse(audit.exact_equal_information_stop(x))
    def test_queries_not_distinct_denied(self):
        x=case(134,29,48);x["queries_distinct"]=False
        self.assertFalse(audit.exact_equal_information_stop(x))
    def test_spurious_full_rank_denied(self):
        self.assertFalse(audit.exact_equal_information_stop(case(162,2,16,164)))
    def test_exact_data_only_no_source_generator_import(self):
        import ast
        from pathlib import Path
        tree=ast.parse(Path(audit.__file__).read_text())
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                imports.extend(x.name for x in node.names)
            elif isinstance(node,ast.ImportFrom):
                imports.append(node.module or "")
        self.assertNotIn("f124dg_new_sourcefree_oracle",imports)
        self.assertNotIn("f124dg_budgeted_active_trial",imports)

if __name__=="__main__":unittest.main()
