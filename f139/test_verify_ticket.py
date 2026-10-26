import json
import unittest
from verify_ticket import signature,admit,receipt,diagnostic_receipt,Untrusted,REPO
SHA='e1b16d0a4097e9fd3d61c9ee635486a72395cf4b'
SECRET='f139-test-hmac-secret-never-deploy-00000000000000000000'
def inputs():
    i=dict(key=SECRET,ticket='f139-wingless-dev-001',lane='Wingless',
           source_sha=SHA,epoch='1',repository=REPO,ref='refs/heads/main',
           event='workflow_dispatch',head_sha=SHA,run_attempt='1',
           run_id='12345',os='ubuntu-latest')
    i['signature']=signature(i['key'],i['ticket'],i['lane'],i['source_sha'],i['epoch'])
    return i
def advisory():
    return (json.dumps(dict(schema='forge.model-free.two-lane-untested-advisory.v1',
        source_commit_sha=SHA,scientific_first_use_authorized=False,
        real_research_progress_established=False,policy_promotion_authorized=False,
        accepted_ref_mutations=0,new_scientific_originals=0,model_invocations=0,
        codex_invocations=0,lanes=[{'lane':'Wingless'},{'lane':'Yggdrasil'}]))+'\n').encode()
class F139WorkerTests(unittest.TestCase):
    def test_signed_development_ticket(self):
        item=inputs()
        self.assertTrue(admit(item))
        report=receipt(item,advisory())
        self.assertEqual(report['lane'],'Wingless')
        self.assertTrue(report['development_only'])
        self.assertFalse(report['scientific_first_use_authorized'])
    def test_exact_release_branch_accepted_without_relaxing_sha(self):
        item=inputs()
        item["ref"]="refs/heads/f139-owner-release-"+SHA
        self.assertTrue(admit(item))
        item["ref"]="refs/heads/f139-owner-release-"+"0"*40
        with self.assertRaises(Untrusted):
            admit(item)

    def test_all_tamper_cases_rejected(self):
        changes=[('source_sha','0'*40),('head_sha','0'*40),('ticket','f139-other-ticket'),
                 ('lane','Yggdrasil'),('epoch','2'),('signature','0'*64),
                 ('event','schedule'),('ref','refs/pull/1/merge'),('run_attempt','2'),
                 ('repository','other/forge'),('os','macos')]
        for key,value in changes:
            i=inputs();i[key]=value
            with self.subTest(key=key),self.assertRaises(Untrusted):
                admit(i)
    def test_unauthorized_missing_signer_denied(self):
        i=inputs();i['key']=''
        with self.assertRaises(Untrusted):admit(i)
    def test_false_science_and_accepted_mutations_rejected(self):
        for name,value in [('scientific_first_use_authorized',True),
                           ('new_scientific_originals',1),
                           ('accepted_ref_mutations',1),
                           ('codex_invocations',1),
                           ('source_commit_sha','0'*40)]:
            data=json.loads(advisory());data[name]=value
            with self.subTest(name=name),self.assertRaises(Untrusted):
                receipt(inputs(),json.dumps(data).encode())
class D2KWorkerTests(unittest.TestCase):
    def request(self):
        i=inputs();digest='a'*64
        i.update(ticket='f139-d2k-i1401-'+SHA[:12]+'-'+digest[:8],
                 lane='Qualification',issue_number='1401',issue_id='91401',
                 body_sha256=digest,target_package='./planner')
        i['signature']=signature(i['key'],i['ticket'],i['lane'],i['source_sha'],
            i['epoch'],issue_number=i['issue_number'],issue_id=i['issue_id'],
            body_sha256=i['body_sha256'],target_package=i['target_package'])
        return i

    def diagnostic(self,i):
        return (json.dumps(dict(
            schema='forge.f139.d2k.package-diagnostic.v1',source_sha=i['source_sha'],
            issue_number=int(i['issue_number']),issue_id=int(i['issue_id']),
            body_sha256=i['body_sha256'],target_package=i['target_package'],
            run_id=int(i['run_id']),os=i['os'],outcome='PASS',returncode=0,
            duration_ms=15,output_sha256='b'*64,output_excerpt='PASS',
            output_bytes=4,scientific_first_use=False,paid_model_calls=0))+'\n').encode()

    def test_signed_d2k_diagnostic_receipt(self):
        i=self.request();self.assertTrue(admit(i))
        result=diagnostic_receipt(i,self.diagnostic(i))
        self.assertEqual(result['outcome'],'PASS')
        self.assertEqual(result['issue_number'],1401)
        self.assertEqual(result['target_package'],'./planner')
        with self.assertRaisesRegex(Untrusted,'D2K_DIAGNOSTIC_REQUIRED'):
            receipt(i,advisory())

    def test_issue_identity_tamper_rejected(self):
        for field,value in [('issue_number','1402'),('issue_id','91402'),
            ('body_sha256','b'*64),('target_package','./dreamrsi'),
            ('target_package','../secret'),('ticket','f139-d2k-i1402-'+SHA[:12]+'-'+'a'*8)]:
            item=self.request();item[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(Untrusted):
                admit(item)

    def test_mismatched_diagnostic_and_false_positive_rejected(self):
        i=self.request()
        for field,value in [('source_sha','0'*40),('issue_id',1),
            ('outcome','TEST_FAILURE'),('returncode',1),('paid_model_calls',1),
            ('scientific_first_use',True),('target_package','./dreamrsi')]:
            diag=json.loads(self.diagnostic(i));diag[field]=value
            with self.subTest(field=field),self.assertRaises(Untrusted):
                diagnostic_receipt(i,json.dumps(diag).encode())
        diag=json.loads(self.diagnostic(i));diag.update(outcome='TEST_FAILURE',returncode=1)
        self.assertEqual(diagnostic_receipt(i,json.dumps(diag).encode())['outcome'],'TEST_FAILURE')

if __name__=='__main__':unittest.main()
