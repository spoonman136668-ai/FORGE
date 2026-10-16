import io,json,unittest,urllib.error
from r2_destination_census import observe,Blocked
class Fake:
 def __init__(self,b):self.b=b
 def __enter__(self):return self
 def __exit__(self,*a):return False
 def read(self,n):return self.b
class Test(unittest.TestCase):
 def test_existing_not_backup(self):
  doc={"success":True,"result":{"buckets":[{"name":"sensitive"}]},"result_info":{"total_count":1}}
  r=observe("a"*32,"secret",lambda req,timeout:Fake(json.dumps(doc).encode()))
  self.assertEqual(r["existing_bucket_count_bounded"],1)
  self.assertFalse(r["private_backup_destination_verified"] or r["restoration_qualified"])
  self.assertNotIn("sensitive",json.dumps(r))
 def test_no_permission(self):
  def deny(req,timeout):raise urllib.error.HTTPError("x",403,"Forbidden",None,None)
  self.assertEqual(observe("a"*32,"secret",deny)["r2_list_permission"],"DENIED")
 def test_invalid_response(self):
  with self.assertRaises(Blocked):observe("a"*32,"secret",lambda req,timeout:Fake(b'{}'))
 def test_no_token(self):
  with self.assertRaises(Blocked):observe("a"*32,"")
