"""G106 dual-cache exact service, shared-DMA and frozen controls."""
import unittest

from g106_dual_staging import (
    COMPUTE_TIME, EVAL, KV_BYTES, KV_CAPACITY, KV_PAGES, KV_TRANSFER,
    POLICIES, PREDICTOR_TIME, REGIMES, SCHEMA, SEEDS,
    SPEEDUP_FLOOR, TRAFFIC_CEILING, TRAIN, WEIGHT_BYTES,
    WEIGHT_CAPACITY, WEIGHT_PAGES, WEIGHT_TRANSFER,
    digest,fit_bigram,make_requests,predict,screen,simulate,
)


class G106Guards(unittest.TestCase):
    def test_frozen_specifications(self):
        self.assertEqual(SEEDS,(10601,10602,10603))
        self.assertEqual(REGIMES,("iid","coupled_cycle"))
        self.assertEqual(POLICIES,("bigram","last_page"))
        self.assertEqual((WEIGHT_PAGES,KV_PAGES,WEIGHT_CAPACITY,KV_CAPACITY),
                         (32,64,4,8))
        self.assertEqual((WEIGHT_BYTES,KV_BYTES),(16384,4096))
        self.assertEqual((WEIGHT_TRANSFER,KV_TRANSFER,COMPUTE_TIME,PREDICTOR_TIME),
                         (.20,.30,1.,.02))
        self.assertEqual((TRAIN,EVAL,SPEEDUP_FLOOR,TRAFFIC_CEILING),
                         (128,384,1.15,1.20))

    def test_training_only_prediction_is_not_future_oracle(self):
        training=[(1,3),(2,4),(1,3),(2,4),(1,3)]
        learned_weight=fit_bigram(training,0)
        learned_kv=fit_bigram(training,1)
        self.assertEqual(predict("bigram",1,learned_weight),2)
        self.assertEqual(predict("bigram",3,learned_kv),4)
        self.assertEqual(predict("bigram",9,learned_kv),9)
        self.assertEqual(predict("last_page",1,learned_weight),1)

    def test_dual_cache_exact_service_and_transfer_accounting(self):
        for seed in SEEDS:
            for regime in REGIMES:
                stream=make_requests(seed,regime)
                self.assertEqual(len(stream),TRAIN+EVAL)
                if regime=="coupled_cycle":
                    self.assertEqual(len(set(w for w,_ in stream)),8)
                    self.assertEqual(len(set(k for _,k in stream)),16)
                training,heldout=stream[:TRAIN],stream[TRAIN:]
                base=simulate(heldout,training)
                self.assertTrue(base["exact_service"])
                self.assertEqual(base["weight_prefetches"],0)
                self.assertEqual(base["kv_prefetches"],0)
                self.assertEqual(base["events"],EVAL)
                self.assertEqual(base["weight_transfer_bytes"],
                                 base["weight_demand_misses"]*WEIGHT_BYTES)
                self.assertEqual(base["kv_transfer_bytes"],
                                 base["kv_demand_misses"]*KV_BYTES)
                self.assertAlmostEqual(base["model_time_units"],
                    EVAL*COMPUTE_TIME+base["weight_demand_misses"]*WEIGHT_TRANSFER+
                    base["kv_demand_misses"]*KV_TRANSFER)
                for policy in POLICIES:
                    result=simulate(heldout,training,policy)
                    self.assertTrue(result["exact_service"])
                    self.assertEqual(result["events"],EVAL)
                    self.assertEqual(result["weight_transfer_bytes"],
                        (result["weight_demand_misses"]+result["weight_prefetches"])*WEIGHT_BYTES)
                    self.assertEqual(result["kv_transfer_bytes"],
                        (result["kv_demand_misses"]+result["kv_prefetches"])*KV_BYTES)
                    self.assertAlmostEqual(result["model_time_units"],
                        EVAL*(COMPUTE_TIME+PREDICTOR_TIME)+
                        result["weight_demand_misses"]*WEIGHT_TRANSFER+
                        result["kv_demand_misses"]*KV_TRANSFER)

    def test_complete_12_case_cost_model_no_gpu_claim(self):
        data=screen()
        self.assertEqual(data["schema"],SCHEMA)
        self.assertEqual(len(data["cases"]),12)
        self.assertEqual(len(data["digests"]),6)
        self.assertTrue(all(c["exact_service_parity"] for c in data["cases"]))
        self.assertTrue(all(len(c["heldout_sha256"])==64 for c in data["cases"]))
        self.assertEqual(data["authentic_model"],"NOT_RUN")
        self.assertEqual(data["gpu_dma_timing"],"NOT_MEASURED")
        self.assertEqual(data["scientific_acceptance"],"NOT_GRANTED")
        self.assertIn(data["decision"],("NO_GO_ANALYTICAL",
                                       "CONDITIONAL_ANALYTIC_FEASIBILITY_ONLY"))


if __name__=="__main__":
    unittest.main()
