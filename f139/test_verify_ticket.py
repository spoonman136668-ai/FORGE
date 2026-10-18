import json
import unittest
from verify_ticket import signature,admit,receipt,Untrusted,REPO
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
if __name__=='__main__':unittest.main()
