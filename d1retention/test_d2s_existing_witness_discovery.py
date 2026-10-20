"""D2S: fail-closed resource metadata, unknown access, and zero authority."""
import unittest

import d2s_existing_witness_discovery as d2s
import install_remote as cf

class Fake:
    account="a"*32
    def __init__(self, overrides=None):
        self.calls=[]
        self.overrides=overrides or {}
    def call(self, path, method=None):
        self.calls.append((path,method))
        category=path.split("/")[2].split("?")[0]
        if category=="workers":
            category="workers" if "scripts?" in path else "durable"
        elif category=="storage":
            category="kv"
        result=self.overrides.get(category, [])
        if isinstance(result,Exception):
            raise result
        return result

class Tests(unittest.TestCase):
    def test_empty_provider_inventory_never_grants_science(self):
        api=Fake()
        d=d2s.inspect(api)
        self.assertEqual(len(api.calls),3)
        self.assertTrue(all(method=="GET" for _,method in api.calls))
        self.assertEqual({k:v["resource_count_observed"] for k,v in d["checks"].items()},
                         {k:0 for k in ("worker_scripts","durable_object_namespaces","kv_namespaces")})
        for name in ("separate_witness_key_possession_authenticated",
                     "independently_pinned_monotonic_firstuse_highwater",
                     "complete_two_lane_original_firstuse_ledger_verified",
                     "deployment_independence_verified","fsa_witness_qualified",
                     "scientific_execution_authorized"):
            self.assertIs(d[name],False)
        self.assertEqual(d["new_origins_dispatched"],0)
        self.assertEqual(d["cloudflare_mutations"],0)

    def test_matching_names_do_not_establish_signer_custody(self):
        api=Fake({"workers":[{"id":"forge-fsa-witness"}],
                  "durable":[{"name":"fsa-highwater","class":"Holder"}],
                  "kv":[{"title":"scientific-ledger"}]})
        d=d2s.inspect(api)
        self.assertEqual([v["candidate_names_observed"] for v in d["checks"].values()],[1,1,1])
        self.assertFalse(d["fsa_witness_qualified"])
        self.assertFalse(d["deployment_independence_verified"])

    def test_permission_denied_is_not_resource_absence(self):
        api=Fake({"workers":cf.InstallBlocked("CLOUDFLARE_HTTP_403")})
        d=d2s.inspect(api)
        self.assertEqual(d["checks"]["worker_scripts"]["status"],"UNREADABLE_NOT_ABSENT")
        self.assertIsNone(d["checks"]["worker_scripts"]["candidate_names_observed"])
        self.assertFalse(d["fsa_witness_qualified"])

    def test_unexpected_provider_errors_fail_closed(self):
        for value in ({"hello":"world"}, [42], [{"id":""}], cf.InstallBlocked("CLOUDFLARE_HTTP_500")):
            with self.subTest(value=repr(value)):
                api=Fake({"workers":value})
                with self.assertRaises((d2s.Denied,cf.InstallBlocked)):
                    d2s.inspect(api)

    def test_hundred_results_cannot_be_called_exhaustive(self):
        api=Fake({"workers":[{"id":"worker-"+str(n)} for n in range(100)]})
        d=d2s.inspect(api)
        self.assertEqual(d["checks"]["worker_scripts"]["status"],"BOUNDED_NONEXHAUSTIVE")
        self.assertFalse(d["fsa_witness_qualified"])

    def test_unauthenticated_account_rejected_before_network(self):
        api=Fake()
        api.account="unverified"
        with self.assertRaisesRegex(d2s.Denied,"D2S_ACCOUNT_IDENTITY_NOT_PINNED"):
            d2s.inspect(api)

if __name__ == "__main__":
    unittest.main()
