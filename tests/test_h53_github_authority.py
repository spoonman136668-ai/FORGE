import unittest
from f139 import h53_github_authority as a
from f139 import h53_audit_guards as g

class AuthorityTests(unittest.TestCase):
    def test_bounded_readback_and_negative_controls(self):
        sha="a"*40
        rule={"id":17,"enforcement":"active"}
        detail={"enforcement":"active","target":"branch",
                "conditions":{"ref_name":{"include":[g.REF],"exclude":[]}},
                "bypass_actors":[],"rules":[{"type":"update"},{"type":"deletion"}]}
        comment={"body":"F139-H53-ORIGINAL-READONLY-ONCE "+sha,
                 "user":{"login":g.OWNER},"author_association":"OWNER"}
        def reader(url):
            if "/rulesets?" in url: return [rule]
            if "/rulesets/17" in url: return detail
            if "page=1" in url: return [comment]
            raise AssertionError(url)
        self.assertEqual(a.verify_authority(sha,reader)["approval_count"],1)
        with self.assertRaisesRegex(RuntimeError,"AUDIT_SHA"):
            a.verify_authority("bad",reader)
        for bad in ([{**detail,"bypass_actors":[{"actor_id":1}]}],
                    [{**detail,"rules":[{"type":"deletion"}]}]):
            def read_bad(url):
                if "/rulesets?" in url: return [rule]
                if "/rulesets/17" in url: return bad[0]
                return [comment]
            with self.assertRaisesRegex(RuntimeError,"IMMUTABLE_RULESET"):
                a.verify_authority(sha,read_bad)
        def missing(url):
            if "/rulesets?" in url: return [rule]
            if "/rulesets/17" in url: return detail
            return []
        with self.assertRaisesRegex(RuntimeError,"EXACT_OWNER_APPROVAL"):
            a.verify_authority(sha,missing)
        def duplicated(url):
            if "/rulesets?" in url: return [rule]
            if "/rulesets/17" in url: return detail
            return [comment,comment]
        with self.assertRaisesRegex(RuntimeError,"EXACT_OWNER_APPROVAL"):
            a.verify_authority(sha,duplicated)
        with self.assertRaisesRegex(RuntimeError,"RULESET_INVENTORY"):
            a.verify_authority(sha,lambda url:[rule]*100)
if __name__=="__main__":
    unittest.main()
