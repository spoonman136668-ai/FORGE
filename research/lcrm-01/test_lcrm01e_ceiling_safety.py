"""Independent exhaustive source-only exact-symbolic admissibility audit."""
import unittest
from collections import defaultdict
import lcrm01e_identifiability as e


class IndependentCeilingSafetyAudit(unittest.TestCase):
    def test_exhaustive_no_false_predictions_observation_and_one_do(self):
        observational=defaultdict(list)
        with_do=defaultdict(list)
        for model in e.MODELS:
            obs=e.observations(model)
            observational[obs].append(model)
            with_do[(obs,e.scm(model,0,('X',1)))].append(model)
        for key, groups, expected_admitted, expected_changed in (
            ('observational', observational, 2048, 0),
            ('one_public_do', with_do, 2560, 512),
        ):
            admitted=changed_admitted=hard_false=0
            for model in e.MODELS:
                obs=e.observations(model)
                version_set=(groups[obs] if key=='observational' else
                             groups[(obs,e.scm(model,0,('X',1)))])
                for u,target,value in e.QUERIES:
                    outcomes={e.scm(alt,u,(target,value)) for alt in version_set}
                    if len(outcomes)!=1:continue
                    admitted+=1
                    changed_admitted+=value!=obs[u][0 if target=='X' else 1]
                    hard_false+=next(iter(outcomes))!=e.scm(model,u,(target,value))
            self.assertEqual(hard_false,0,key)
            self.assertEqual(admitted,expected_admitted,key)
            self.assertEqual(changed_admitted,expected_changed,key)

    def test_ambiguity_counts_all_changed_queries(self):
        d=e.evaluate()
        self.assertEqual(d['total_model_query_pairs'],4096)
        self.assertEqual(d['intervention_changes_baseline_pairs'],2048)
        self.assertEqual(d['ambiguous_changed_target_pairs'],2048)


if __name__=='__main__':unittest.main()
