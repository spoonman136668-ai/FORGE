package mindcontext

import (
 "context"
 "encoding/json"
 "errors"
 "strings"
 "testing"
)

type fixtureSource struct{
 pin string
 blobs map[string][]byte
 resolved int
 reads []string
}
func (s *fixtureSource)ResolveMain(context.Context)(string,error){
 s.resolved++
 return s.pin,nil
}
func (s *fixtureSource)ReadAt(_ context.Context,pin,path string)([]byte,error){
 if pin!=s.pin{return nil,errors.New("unpinned")}
 s.reads=append(s.reads,pin+":"+path)
 b,ok:=s.blobs[path]
 if !ok{return nil,errors.New("fixture document missing")}
 return b,nil
}
func fixture(t *testing.T)*fixtureSource{
 t.Helper()
 pin:=strings.Repeat("a",40)
 source:=strings.Repeat("b",64)
 record:=func(id,project string)string{
  var projectValue *string
  if project!="__global__"{projectValue=&project}
  b,e:=json.Marshal(Record{ID:id,Project:projectValue,Kind:"decision",Status:"current",Importance:"hot",Statement:"Synthetic "+id,SourceRefs:[]recordSource{{Type:"repo",Ref:"fixture:immutable"}}})
  if e!=nil{t.Fatal(e)}
  return string(b)
 }
 index:=strings.Join([]string{record("global-1","__global__"),record("global-2","__global__"),record("W-1","Wingless"),record("W-2","Wingless"),record("Y-1","Yggdrasil"),record("Y-2","Yggdrasil"),record("R-1","Research")},"\n")+"\n"
 bootstrap:=map[string]any{
  "schema":BootstrapSchema,
  "source":map[string]string{"records_sha256":source},
  "retrieval_transport":"direct-repository-read",
  "remote_catalog":CatalogPath,"remote_index":IndexPath,
 }
 catalog:=map[string]any{
  "schema":CatalogSchema,
  "source":map[string]string{"records_sha256":source},
  "index":IndexPath,"active_record_count":7,
  "retrieval_transport":"direct-repository-read","control_plane_required":false,
  "projects":map[string]any{
   "__global__":Range{1,2,2},"Wingless":Range{3,4,2},
   "Yggdrasil":Range{5,6,2},"Research":Range{7,7,1},
  },
 }
 b,_:=json.Marshal(bootstrap);c,_:=json.Marshal(catalog)
 return &fixtureSource{pin:pin,blobs:map[string][]byte{BootstrapPath:b,CatalogPath:c,IndexPath:[]byte(index)}}
}
func TestPinnedDirectResearchRetrievalAndFairness(t *testing.T){
 src:=fixture(t)
 out,err:=(Reader{Source:src}).Read(context.Background(),[]string{"Wingless","Yggdrasil"},4)
 if err!=nil{t.Fatal(err)}
 if !out.AdvisoryOnly||out.PinnedCommit!=src.pin||len(out.Entries)!=4||!out.Truncated{t.Fatal("missing advisory isolation")}
 if out.Entries[0].Project!="__global__"||out.Entries[1].Project!="__global__"||out.Entries[2].Project!="Wingless"||out.Entries[3].Project!="Yggdrasil"{t.Fatal("governance or lane fairness lost")}
 if len(out.ContextSHA256)!=64||out.ContextSHA256==out.RecordsSHA256{t.Fatal("context identity invalid")}
 if src.resolved!=1||len(src.reads)!=3{t.Fatal("unbounded reads")}
 for _,read:=range src.reads{if !strings.HasPrefix(read,src.pin+":"){t.Fatal("un-pinned read")}}
}
func TestNoKTRADERetrievalOrUnlistedProjects(t *testing.T){
 src:=fixture(t)
 for _,p:=range []string{"KTRADE","CKB-plane","Mind-Palace","unknown","Wingless/../KTRADE"} {
  if _,err:=(Reader{Source:src}).Read(context.Background(),[]string{p},10);err==nil{t.Fatalf("unsafe project %s permitted",p)}
 }
 if src.resolved!=0{t.Fatal("unsafe query caused upstream reads")}
}
func TestMalformedPrivateMetadataFailsClosed(t *testing.T){
 changes:=[]func(*fixtureSource){
  func(s *fixtureSource){s.pin="main"},
  func(s *fixtureSource){s.blobs[BootstrapPath]=[]byte("{}")},
  func(s *fixtureSource){s.blobs[CatalogPath]=[]byte("{}")},
  func(s *fixtureSource){s.blobs[IndexPath]=[]byte("{}")},
  func(s *fixtureSource){s.blobs[IndexPath]=append(s.blobs[IndexPath],[]byte("{}\n")...)},
  func(s *fixtureSource){s.blobs[IndexPath]=[]byte(strings.Replace(string(s.blobs[IndexPath]),"fixture:immutable","",1))},
 }
 for i,f:=range changes{
  src:=fixture(t);f(src)
  if _,err:=(Reader{Source:src}).Read(context.Background(),[]string{"Wingless"},8);err==nil{t.Fatalf("malformed index case %d accepted",i)}
 }
}
func TestProvenanceAndRecordProjectSeparation(t *testing.T){
 src:=fixture(t)
 src.blobs[IndexPath]=[]byte(strings.Replace(string(src.blobs[IndexPath]),"Wingless","KTRADE",1))
 if _,err:=(Reader{Source:src}).Read(context.Background(),[]string{"Wingless"},8);err==nil{t.Fatal("cross-project context leaked")}
 src=fixture(t)
 src.blobs[IndexPath]=[]byte(strings.Replace(string(src.blobs[IndexPath]),"fixture:immutable","",1))
 if _,err:=(Reader{Source:src}).Read(context.Background(),[]string{"Wingless"},8);err==nil{t.Fatal("missing original source ref accepted")}
 src=fixture(t)
 src.blobs[IndexPath]=[]byte(strings.Replace(string(src.blobs[IndexPath]),"\"current\"","\"superseded\"",1))
 if _,err:=(Reader{Source:src}).Read(context.Background(),[]string{"Wingless"},8);err==nil{t.Fatal("superseded context accepted")}
}
func TestGovernanceBudgetMustNeverBeSilentlyDropped(t *testing.T){
 src:=fixture(t)
 if _,err:=(Reader{Source:src}).Read(context.Background(),[]string{"Wingless"},1);err==nil{t.Fatal("governance silently truncated")}
}
