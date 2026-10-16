"""Read-only Cloudflare existing R2 private backup destination census.

Never emit bucket names, IDs, credentials, or object paths. A listable R2
bucket does NOT establish backup restore qualifications or storage permissions.
"""
import json,os,urllib.request,urllib.error,re,sys
class Blocked(RuntimeError):pass
def observe(account,token,opener=urllib.request.urlopen):
 if not re.fullmatch(r"[0-9a-f]{32}",account or "") or not token:raise Blocked("CLOUDFLARE_ACCOUNT_OR_TOKEN_MISSING")
 url="https://api.cloudflare.com/client/v4/accounts/"+account+"/r2/buckets?per_page=100"
 req=urllib.request.Request(url,headers={"Authorization":"Bearer "+token,"Accept":"application/json"},method="GET")
 try:
  with opener(req,timeout=20) as resp:raw=resp.read(131073)
 except urllib.error.HTTPError as exc:
  if exc.code in (401,403):return {"schema":"forge.native.r2.readonly-census.v1","r2_list_permission":"DENIED","private_backup_destination_verified":False,"live_backup_exported":False,"restoration_qualified":False}
  raise Blocked("R2_HTTP_FAILURE") from None
 except Exception as exc:raise Blocked("R2_TRANSPORT_ERROR") from exc
 if len(raw)>131072:raise Blocked("R2_RESPONSE_TOO_LARGE")
 try:v=json.loads(raw)
 except (ValueError,UnicodeError) as exc:raise Blocked("R2_BAD_RESPONSE") from exc
 if not isinstance(v,dict) or v.get("success") is not True:raise Blocked("R2_API_UNEXPECTED")
 arr=v.get("result")
 if not isinstance(arr,dict) or not isinstance(arr.get("buckets"),list):raise Blocked("R2_BUCKET_RESPONSE_INVALID")
 buckets=arr["buckets"]
 if len(buckets)>100:raise Blocked("R2_BUCKET_RESPONSE_OVERFLOW")
 info=v.get("result_info")
 if isinstance(info,dict) and info.get("total_count",0)>len(buckets):
  return {"schema":"forge.native.r2.readonly-census.v1","r2_list_permission":"PARTIAL","private_backup_destination_verified":False,"live_backup_exported":False,"restoration_qualified":False}
 return {"schema":"forge.native.r2.readonly-census.v1","r2_list_permission":"GRANTED","existing_bucket_count_bounded":len(buckets),"private_backup_destination_verified":False,"live_backup_exported":False,"restoration_qualified":False}
if __name__=="__main__":
 try:
  print(json.dumps(observe(os.getenv("CLOUDFLARE_ACCOUNT_ID"),os.getenv("CLOUDFLARE_API_TOKEN")),sort_keys=True))
  print("FORGE_R2_LIVE_BACKUP_RESTORE=NOT_QUALIFIED")
 except Blocked as exc:
  print("FORGE_R2_READONLY_BLOCKED="+str(exc),file=sys.stderr)
  raise SystemExit(1)
