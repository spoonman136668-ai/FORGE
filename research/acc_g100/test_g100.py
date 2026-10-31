"""G100 controls: source training only, no oracle, strict byte/time accounting."""
import unittest

from g100_kv_staging import (
    CACHE_CAPACITY, COMPUTE_TIME, EVAL, PAGE_BYTES, PAGES,
    POLICIES, PREDICTOR_COST, REGIMES, SCHEMA, SEEDS, SPEEDUP_FLOOR,
    TRAIN, TRANSFER_CEILING, TRANSFER_TIME, digest, fit_bigram,
    make_requests, predict, screen, simulate,
)


class G100Guards(unittest.TestCase):
    def test_frozen_pre_registered_contract(self):
        self.assertEqual(SEEDS,(10001,10002,10003))
        self.assertEqual(REGIMES,("iid","cycle16"))
        self.assertEqual(POLICIES,("bigram","last_page"))
        self.assertEqual((PAGES,PAGE_BYTES,CACHE_CAPACITY,TRAIN,EVAL),
                         (64,4096,8,128,384))
        self.assertEqual((COMPUTE_TIME,TRANSFER_TIME,PREDICTOR_COST),
                         (1.,.30,.01))
        self.assertEqual((SPEEDUP_FLOOR,TRANSFER_CEILING),(1.15,1.20))

    def test_train_only_bigram_does_not_use_heldout(self):
        training=[4,5,4,5,4,5,4,5]
        learned=fit_bigram(training)
        self.assertEqual(predict("bigram",4,learned),5)
        self.assertEqual(predict("bigram",5,learned),4)
        self.assertEqual(predict("bigram",17,learned),17)
        self.assertEqual(predict("last_page",4,learned),4)
        self.assertEqual(learned,fit_bigram(training))

    def test_exact_page_service_and_transfer_bytes(self):
        for seed in SEEDS:
            for regime in REGIMES:
                events=make_requests(seed,regime)
                self.assertEqual(len(events),TRAIN+EVAL)
                if regime=="cycle16":
                    self.assertEqual(len(set(events)),16)
                training,test=events[:TRAIN],events[TRAIN:]
                base=simulate(test,training)
                self.assertTrue(base["served_exactly"])
                self.assertEqual(base["prefetch_transfers"],0)
                self.assertEqual(base["transfer_bytes"],
                                 base["demand_misses"]*PAGE_BYTES)
                self.assertAlmostEqual(base["model_time_units"],
                                       EVAL*COMPUTE_TIME+base["demand_misses"]*TRANSFER_TIME)
                for policy in POLICIES:
                    candidate=simulate(test,training,policy)
                    self.assertTrue(candidate["served_exactly"])
                    self.assertEqual(candidate["events"],EVAL)
                    self.assertEqual(candidate["transfer_pages"],
                                     candidate["demand_misses"]+candidate["prefetch_transfers"])
                    self.assertEqual(candidate["transfer_bytes"],
                                     PAGE_BYTES*candidate["transfer_pages"])
                    self.assertAlmostEqual(candidate["model_time_units"],
                        EVAL*(COMPUTE_TIME+PREDICTOR_COST) +
                        candidate["demand_misses"]*TRANSFER_TIME)

    def test_all_12_heldout_sequence_cases(self):
        result=screen()
        self.assertEqual(result["schema"],SCHEMA)
        self.assertEqual(len(result["digests"]),6)
        self.assertEqual(len(result["cases"]),12)
        self.assertTrue(all(c["exact_service_parity"] for c in result["cases"]))
        self.assertTrue(all(len(c["heldout_sha256"])==64 for c in result["cases"]))
        self.assertEqual(result["genuine_gpu_transfer"],"NOT_MEASURED")
        self.assertEqual(result["authentic_model"],"NOT_RUN")
        self.assertEqual(result["scientific_acceptance"],"NOT_GRANTED")
        self.assertIn(result["decision"],("NO_GO_ANALYTICAL",
                                         "CONDITIONAL_ANALYTIC_FEASIBILITY_ONLY"))


if __name__=="__main__":
    unittest.main()
