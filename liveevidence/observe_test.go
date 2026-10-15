package liveevidence
import(
 "context"
 "encoding/json"
 "io"
 "net/http"
 "strconv"
 "strings"
 "testing"
 "time"
)
type transport func(*http.Request)(*http.Response,error)
func (f transport)RoundTrip(r *http.Request)(*http.Response,error){return f(r)}
func mock(t *testing.T,alter func(string,map[string]any))(*http.Client,*int){
 t.Helper()
 calls:=0
 client:=&http.Client{Transport:transport(func(req *http.Request)(*http.Response,error){
  calls++
  if req.Method!="GET"||req.URL.Host!="api.github.com"||
    req.Header.Get("User-Agent")!="FORGE-F57-read-only"{t.Fatal("unsafe read",req.URL)}
  var p *pin
  for i:=range frozen{
   x:=&frozen[i]
   stem:="/repos/"+x.Repo+"/actions/runs/"+strconv.FormatInt(x.RunID,10)
   if req.URL.Path==stem||req.URL.Path==stem+"/artifacts"{p=x;break}
  }
  if p==nil{t.Fatal("unexpected resource",req.URL)}
  var v map[string]any
  if strings.HasSuffix(req.URL.Path,"/artifacts"){
   if req.URL.RawQuery!="per_page=100"{t.Fatal("missing page bound")}
   v=map[string]any{"total_count":1,"artifacts":[]any{
    map[string]any{"id":p.ArtifactID,"name":p.ArtifactName,"expired":false,
     "digest":p.ArchiveDigest,"workflow_run":map[string]any{"id":p.RunID}},
   }}
  }else{
   stamp:="2026-10-15T22:41:31Z"
   switch p.RunID{
   case 38819060318:stamp="2026-10-15T22:43:41Z"
   case 38819086470:stamp="2026-10-15T22:43:55Z"
   case 38820489117:stamp="2026-10-15T22:56:54Z"
   }
   v=map[string]any{"id":p.RunID,"head_sha":p.Source,"run_attempt":1,
    "status":"completed","conclusion":"success","created_at":stamp,
    "repository":map[string]any{"full_name":p.Repo}}
  }
  if alter!=nil{alter(req.URL.Path,v)}
  b,err:=json.Marshal(v);if err!=nil{t.Fatal(err)}
  return &http.Response{StatusCode:200,Body:io.NopCloser(strings.NewReader(string(b))),
   Request:req,Header:http.Header{}},nil
 })}
 return client,&calls
}
func TestPinnedHistoricalEvidenceNeverBecomesScientificAuthority(t *testing.T){
 c,calls:=mock(t,nil)
 a,err:=Observe(context.Background(),c,"")
 if err!=nil{t.Fatal(err)}
 b,err:=Observe(context.Background(),c,"")
 if err!=nil||a!=b{t.Fatal("non-deterministic result",err)}
 if *calls!=16||!a.PinnedGithubRunMetadataObserved||
   !a.PinnedGithubArtifactMetadataObserved||a.ArchiveContentsAuthenticated||
   a.OriginalStartTerminalSignaturesAuthenticated||a.IndependentOwnerHighWaterVerified||
   a.DistributedFirstUseCASVerified||a.NewProtectedOriginalsExecuted||
   a.UnattendedSuccessorProven||a.ScientificAcceptanceAuthorized||
   a.ResearchDispatchAuthorized||a.OwnerCutoverAuthorized{
  t.Fatalf("false authority: %+v",a)
 }
 if a.Records[0].Lane!="Wingless"||a.Records[3].Lane!="Yggdrasil"||
  a.Records[0].RunMetadataSHA256==""{t.Fatal("missing metadata commitment")}
}
func TestPinnedExternalMetadataDriftFailsClosed(t *testing.T){
 variants:=map[string]func(string,map[string]any){
  "wrong source":func(path string,v map[string]any){if !strings.HasSuffix(path,"/artifacts"){v["head_sha"]=strings.Repeat("f",40)}},
  "rerun":func(path string,v map[string]any){if !strings.HasSuffix(path,"/artifacts"){v["run_attempt"]=2}},
  "failed CI":func(path string,v map[string]any){if !strings.HasSuffix(path,"/artifacts"){v["conclusion"]="failure"}},
  "wrong repo":func(path string,v map[string]any){if !strings.HasSuffix(path,"/artifacts"){v["repository"]=map[string]any{"full_name":"fake/repo"}}},
  "expired ZIP":func(path string,v map[string]any){if strings.HasSuffix(path,"/artifacts"){v["artifacts"].([]any)[0].(map[string]any)["expired"]=true}},
  "changed ZIP digest":func(path string,v map[string]any){if strings.HasSuffix(path,"/artifacts"){v["artifacts"].([]any)[0].(map[string]any)["digest"]="sha256:"+strings.Repeat("0",64)}},
  "wrong associated run":func(path string,v map[string]any){if strings.HasSuffix(path,"/artifacts"){v["artifacts"].([]any)[0].(map[string]any)["workflow_run"]=map[string]any{"id":1}}},
  "missing artifact page":func(path string,v map[string]any){if strings.HasSuffix(path,"/artifacts"){v["total_count"]=3}},
  "reversed lineage clock":func(path string,v map[string]any){if strings.Contains(path,"38819060318")&&!strings.HasSuffix(path,"/artifacts"){v["created_at"]="2026-10-15T20:00:00Z"}},
 }
 for name,edit:=range variants{t.Run(name,func(t *testing.T){
  c,_:=mock(t,edit)
  if _,err:=Observe(context.Background(),c,"");err==nil{t.Fatal("accepted drift")}
 })}
}
func TestUnavailableOrCancelledBlocks(t *testing.T){
 c,_:=mock(t,nil)
 ctx,cancel:=context.WithCancel(context.Background());cancel()
 if _,err:=Observe(ctx,c,"");err==nil{t.Fatal("canceled context accepted")}
 bad:=&http.Client{Timeout:time.Second,Transport:transport(func(r *http.Request)(*http.Response,error){
  return &http.Response{StatusCode:503,Body:io.NopCloser(strings.NewReader("unavailable")),Request:r},nil
 })}
 if _,err:=Observe(context.Background(),bad,"");err==nil{t.Fatal("unavailable service accepted")}
}
