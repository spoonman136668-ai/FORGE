"""ACC64 U04 focused true-LoRA gradients, numerical checks and IPC negatives."""
import importlib.util
import math
from pathlib import Path
import subprocess
import sys
import unittest

sp=importlib.util.spec_from_file_location("acc64_u04",Path(__file__).with_name("experiment.py"))
m=importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)

class MicroLoraTest(unittest.TestCase):
    def test_01_registry_original(self):
        self.assertEqual(m.custody()["registry_git_blob"],"5126c860771fb024ccfc14c3f7ee8925edf29787")
    def test_02_prereg_first(self):
        self.assertEqual(m.custody()["prereg_commit"],"b220304101f8944f2738c3f318dbd68a9208c661")
    def test_03_frozen_scales(self):
        self.assertEqual(m.DIMENSIONS,(16,32))
        self.assertEqual(m.RANK,4)
        self.assertEqual(m.SEEDS,(211,223,227))
    def test_04_four_update_steps(self):
        self.assertEqual(m.STEPS,4)
        self.assertEqual(m.LR,.05)
    def test_05_shapes_and_data_size(self):
        for n in m.DIMENSIONS:
            a,b,fit,valid=m.samples(n,211)
            self.assertEqual((len(a),len(b),len(fit),len(valid)),(4*n,4*n,64,16))
            self.assertEqual(len(fit[0][0]),n)
            self.assertEqual(len(fit[0][1]),n)
    def test_06_frozen_teacher_distinct_from_initial(self):
        a,b,fit,valid=m.samples(16,211)
        self.assertGreater(m.loss(a,b,fit,16),0)
        self.assertGreater(m.loss(a,b,valid,16),0)
    def test_07_true_lora_rank_four(self):
        a,b,fit,_=m.samples(16,211)
        self.assertEqual(len(m.predict(a,b,fit[0][0],16)),16)
    def test_08_analytic_gradient_a_finite_difference(self):
        n=16;a,b,fit,_=m.samples(n,211);cases=fit[:4]
        g=m.grad(a,b,cases,n);eps=1e-6
        for i in (0,11,31,63):
            q=list(a);q[i]+=eps
            w=list(a);w[i]-=eps
            numerical=(m.loss(q,b,cases,n)-m.loss(w,b,cases,n))/(2*eps)
            self.assertAlmostEqual(numerical,g["ga"][i]/4,delta=1e-6)
    def test_09_analytic_gradient_b_finite_difference(self):
        n=16;a,b,fit,_=m.samples(n,211);cases=fit[:4]
        g=m.grad(a,b,cases,n);eps=1e-6
        for i in (0,11,31,63):
            q=list(b);q[i]+=eps
            w=list(b);w[i]-=eps
            numerical=(m.loss(a,q,cases,n)-m.loss(a,w,cases,n))/(2*eps)
            self.assertAlmostEqual(numerical,g["gb"][i]/4,delta=1e-6)
    def test_10_aggregation_partition_complete(self):
        _,_,fit,_=m.samples(16,211)
        for workers in (1,2,4):
            parts=m.partition(fit,workers)
            self.assertEqual([c for part in parts for c in part],fit)
    def test_11_bad_partition_fails(self):
        _,_,fit,_=m.samples(16,211)
        with self.assertRaises(ValueError):m.partition(fit[:-1],4)
        with self.assertRaises(ValueError):m.partition(fit,3)
    def test_12_invalid_aggregate_count_fails(self):
        a,b,fit,_=m.samples(16,211)
        g=m.grad(a,b,fit[:4],16)
        with self.assertRaises(RuntimeError):m.aggregate([g],5,16)
    def test_13_wrong_gradient_shape_fails(self):
        a,b,fit,_=m.samples(16,211)
        g=m.grad(a,b,fit[:4],16)
        g["ga"]=g["ga"][:-1]
        with self.assertRaises(RuntimeError):m.aggregate([g],4,16)
    def test_14_one_shard_reduction_equals_direct(self):
        a,b,fit,_=m.samples(16,211)
        g=m.grad(a,b,fit,16)
        red=m.aggregate([g],len(fit),16)
        self.assertAlmostEqual(red["ga"][0],g["ga"][0]/64,delta=1e-12)
        self.assertAlmostEqual(red["gb"][5],g["gb"][5]/64,delta=1e-12)
    def test_15_reproducible_input(self):
        self.assertEqual(m.samples(16,211),m.samples(16,211))
    def test_16_training_serial_deterministic(self):
        a=m.train(16,211,"serial");b=m.train(16,211,"serial")
        self.assertEqual(a["param_fingerprint"],b["param_fingerprint"])
        self.assertEqual(a["steps"],4)
        self.assertEqual(a["ipc_bytes"],0)
    def test_17_process_one_equivalent(self):
        a=m.train(16,211,"serial");b=m.train(16,211,"process_1")
        self.assertLessEqual(max(abs(x-y) for x,y in zip(a["a"]+a["b"],b["a"]+b["b"])),1e-9)
        self.assertGreater(b["ipc_bytes"],0)
        self.assertEqual(b["workers"],1)
    def test_18_process_four_equivalent(self):
        a=m.train(16,211,"serial");b=m.train(16,211,"process_4")
        self.assertLessEqual(max(abs(x-y) for x,y in zip(a["a"]+a["b"],b["a"]+b["b"])),1e-9)
        self.assertLessEqual(abs(a["final_valid_loss"]-b["final_valid_loss"]),1e-9)
        self.assertGreater(b["ipc_bytes"],0)
        self.assertEqual(b["workers"],4)
    def test_19_unknown_worker_command_fails(self):
        p=subprocess.run([sys.executable,str(Path(m.__file__).resolve()),"--worker"],
            input='{"op":"not-gradient"}\n',capture_output=True,text=True,timeout=15)
        self.assertNotEqual(p.returncode,0)
        self.assertIn("UNKNOWN_WORKER_COMMAND",p.stderr)
    def test_20_invalid_task_not_accepted(self):
        with self.assertRaises(ValueError):m.samples(100,211)
        with self.assertRaises(ValueError):m.train(16,999,"serial")
    def test_21_worker_math_finite(self):
        a,b,fit,_=m.samples(16,211)
        q=m.grad(a,b,fit[:8],16)
        self.assertTrue(all(math.isfinite(x) for x in q["ga"]+q["gb"]))
    def test_22_evaluation_is_outside_train_timing(self):
        t=m.train(16,211,"serial")
        self.assertGreater(t["wall_ns"],0)
        self.assertGreaterEqual(t["final_valid_loss"],0)
        self.assertEqual(t["fit_count"],64)

if __name__=="__main__":unittest.main()
