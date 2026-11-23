package researcharchive

import(
 "archive/zip"
 "bytes"
 "encoding/json"
 "errors"
 "strings"
 "testing"
)
func archive(t *testing.T,n string)[]byte{
 t.Helper()
 var dst bytes.Buffer
 z:=zip.NewWriter(&dst)
 f,err:=z.Create(n);if err!=nil{t.Fatal(err)}
 if _,err=f.Write([]byte("{\"classification\":\"NO_BENEFIT\"}\n"));err!=nil{t.Fatal(err)}
 if err=z.Close();err!=nil{t.Fatal(err)}
 return dst.Bytes()
}
func synthetic(t *testing.T)([]byte,[]byte,[]byte,[]byte,Entry,Entry){
 t.Helper()
 blob:=archive(t,"original.json")
 w:=Entry{Lane:"Wingless",Experiment:"W-R26",Repository:"spoonman136668-ai/Wingless",
  RunID:38403931613,HeadSHA:strings.Repeat("a",40),WorkflowPath:".github/workflows/qualify-w-r26-raw-next-prediction.yml",
  ArtifactID:11815709362,ArtifactName:"W-R26-original-causal-next-step",ArchiveSHA256:SHA(blob)}
 y:=Entry{Lane:"Yggdrasil",Experiment:"Y039",Repository:"spoonman136668-ai/Yggdrasil",
  RunID:38403937698,HeadSHA:strings.Repeat("b",40),WorkflowPath:".github/workflows/qualify-y039-interruption.yml",
  ArtifactID:11815774175,ArtifactName:"Y039-original-interrupted-memory",ArchiveSHA256:SHA(blob)}
 // Batch identity must not allow duplicate byte identities being silently
 // substituted for a distinct original evidence object.
 y.ArchiveSHA256=SHA(blob)
 m:=Manifest{Schema:ManifestSchema,Entries:[]Entry{w,y}}
 raw,err:=json.Marshal(m);if err!=nil{t.Fatal(err)}
 raw=append(raw,'\n')
 sourceRun:=map[string]any{"id":w.RunID,"run_attempt":1,"head_sha":w.HeadSHA,
  "path":w.WorkflowPath,"status":"completed","conclusion":"success",
  "repository":map[string]any{"full_name":w.Repository},
  "head_repository":map[string]any{"full_name":w.Repository}}
 run,_:=json.Marshal(sourceRun)
 sourceArtifact:=map[string]any{"id":w.ArtifactID,"name":w.ArtifactName,
  "expired":false,"digest":"sha256:"+w.ArchiveSHA256,
  "size_in_bytes":len(blob),
  "workflow_run":map[string]any{"id":w.RunID,"head_sha":w.HeadSHA}}
 meta,_:=json.Marshal(sourceArtifact)
 return raw,run,meta,blob,w,y
}
func TestExactOriginalArchiveVerificationIsReadOnly(t *testing.T){
 raw,run,meta,blob,w,_:=synthetic(t)
 if _,err:=LoadManifest(raw);err!=nil{t.Fatal(err)}
 got,err:=Verify(w,run,meta,blob)
 if err!=nil{t.Fatal(err)}
 if !got.ArchivalIntegrityVerified||got.ScientificAccepted||
  got.FirstUseReconciled||got.PreregistrationVerified||
  got.ScientificClassification!="UNQUALIFIED_ORIGINAL_EVIDENCE_PRESERVED"||
  len(got.Files)!=1||got.Files[0]!="original.json"{
  t.Fatal("invalid science boundary",got)
 }
}
func TestTamperedSourceAndArchiveFailClosed(t *testing.T){
 _,run,meta,blob,w,_:=synthetic(t)
 mutations:=[]struct{name string;change func(*Entry,*[]byte,*[]byte,*[]byte)}{
  {"run head",func(e *Entry,r,m,z *[]byte){*r=bytes.Replace(*r,[]byte(strings.Repeat("a",40)),[]byte(strings.Repeat("f",40)),1)}},
  {"wrong GitHub run",func(e *Entry,r,m,z *[]byte){e.RunID++}},
  {"untrusted artifact",func(e *Entry,r,m,z *[]byte){e.ArtifactID++}},
  {"changed ZIP",func(e *Entry,r,m,z *[]byte){(*z)[0]^=1}},
  {"artifact digest",func(e *Entry,r,m,z *[]byte){*m=bytes.Replace(*m,[]byte(e.ArchiveSHA256),[]byte(strings.Repeat("f",64)),1)}},
  {"changed frozen original",func(e *Entry,r,m,z *[]byte){e.WorkflowPath=".github/workflows/other.yml"}},
  {"foreign lane",func(e *Entry,r,m,z *[]byte){e.Lane="CKB-plane"}},
  {"expired archive",func(e *Entry,r,m,z *[]byte){*m=bytes.Replace(*m,[]byte(`"expired":false`),[]byte(`"expired":true`),1)}},
  {"redirected original",func(e *Entry,r,m,z *[]byte){*r=bytes.Replace(*r,[]byte("spoonman136668-ai/Wingless"),[]byte("foreign/Wingless"),1)}},
 }
 for _,tt:=range mutations{t.Run(tt.name,func(t *testing.T){
  e:=w;r:=append([]byte(nil),run...);m:=append([]byte(nil),meta...);z:=append([]byte(nil),blob...)
  tt.change(&e,&r,&m,&z)
  if _,err:=Verify(e,r,m,z);!errors.Is(err,ErrBlocked){t.Fatal("unsafe archive accepted",err)}
 })}
}
func TestFrozenMultiLaneManifestIsCanonicalAndImmutable(t *testing.T){
 raw,_,_,_,w,y:=synthetic(t)
 for name,source:=range map[string][]byte{
  "duplicate":bytes.Replace(raw,[]byte(`"schema":"forge.research-archive.frozen-cohort.v1"`),
   []byte(`"schema":"forge.research-archive.frozen-cohort.v1","schema":"forge.research-archive.frozen-cohort.v1"`),1),
  "trailing":append(append([]byte(nil),raw...),[]byte("{}")...),
  "missing lane":func()[]byte{b,_:=json.Marshal(Manifest{Schema:ManifestSchema,Entries:[]Entry{w}});return append(b,'\n')}(),
  "reversed":func()[]byte{b,_:=json.Marshal(Manifest{Schema:ManifestSchema,Entries:[]Entry{y,w}});return append(b,'\n')}(),
  "extra key":bytes.Replace(raw,[]byte(`"lane":"Wingless"`),[]byte(`"lane":"Wingless","execution_authorized":true`),1),
 }{
  t.Run(name,func(t *testing.T){
   if _,err:=LoadManifest(source);!errors.Is(err,ErrBlocked){t.Fatal("untrusted manifest accepted",err)}
  })
 }
}
func TestNoScienceInferenceEvenWhenAllArchiveBytesPass(t *testing.T){
 raw,run,meta,blob,w,y:=synthetic(t)
 report,err:=Collect(raw,func(e Entry)([]byte,[]byte,[]byte,error){
  if e.Lane=="Wingless"{return run,meta,blob,nil}
  otherRun:=map[string]any{"id":y.RunID,"run_attempt":1,
   "head_sha":y.HeadSHA,"path":y.WorkflowPath,"status":"completed","conclusion":"success",
   "repository":map[string]any{"full_name":y.Repository},
   "head_repository":map[string]any{"full_name":y.Repository}}
  r,_:=json.Marshal(otherRun)
  otherMeta:=map[string]any{"id":y.ArtifactID,"name":y.ArtifactName,"expired":false,
   "digest":"sha256:"+y.ArchiveSHA256,"size_in_bytes":len(blob),
   "workflow_run":map[string]any{"id":y.RunID,"head_sha":y.HeadSHA}}
  m,_:=json.Marshal(otherMeta)
  return r,m,blob,nil
 })
 if err!=nil{t.Fatal(err)}
 if report.ArchiveCount!=2||report.WinglessCount!=1||report.YggdrasilCount!=1||
  report.OriginalExecutionAuthorized||report.ScientificAccepted||
  report.CompleteCKBCustody||report.AcceptedRefMutation||
  report.Observations[0].ScientificAccepted||report.Observations[1].ScientificAccepted||
  report.ManifestSHA256!=SHA(raw){t.Fatalf("qualified source falsely activated science: %+v",report)}
 _,_,_,_,_=run,meta,blob,w,y
}
func TestZipTraversalCannotBeHiddenBehindExpectedDigest(t *testing.T){
 _,run,meta,_,w,_:=synthetic(t)
 bad:=archive(t,"../escape.json")
 w.ArchiveSHA256=SHA(bad)
 meta=bytes.Replace(meta,[]byte(strings.Repeat("a",64)),[]byte(strings.Repeat("b",64)),1)
 var a map[string]any
 if err:=json.Unmarshal(meta,&a);err!=nil{t.Fatal(err)}
 a["digest"]="sha256:"+w.ArchiveSHA256
 a["size_in_bytes"]=len(bad)
 meta,_=json.Marshal(a)
 if _,err:=Verify(w,run,meta,bad);!errors.Is(err,ErrBlocked){
  t.Fatal("path traversal archive accepted",err)
 }
}

func TestExternalGitHubMetadataRejectsAmbiguousKeysAtEveryDepth(t *testing.T){
 _,run,meta,blob,entry,_:=synthetic(t)
 sameRepo:=[]byte(`"full_name":"`+entry.Repository+`"`)
 cases:=[]struct{name string;run []byte;meta []byte}{
  {"run nested duplicate",bytes.Replace(run,sameRepo,append(append([]byte{},sameRepo...),[]byte(`,"full_name":"`+entry.Repository+`"`)...),1),meta},
  {"run nested casefold alias",bytes.Replace(run,sameRepo,append(append([]byte{},sameRepo...),[]byte(`,"FULL_NAME":"`+entry.Repository+`"`)...),1),meta},
  {"run top-level duplicate",bytes.Replace(run,[]byte(`"run_attempt":1`),[]byte(`"run_attempt":1,"run_attempt":1`),1),meta},
  {"artifact nested duplicate",run,bytes.Replace(meta,[]byte(`"head_sha":"`+entry.HeadSHA+`"`),[]byte(`"head_sha":"`+entry.HeadSHA+`","head_sha":"`+entry.HeadSHA+`"`),1)},
  {"artifact nested casefold alias",run,bytes.Replace(meta,[]byte(`"head_sha":"`+entry.HeadSHA+`"`),[]byte(`"head_sha":"`+entry.HeadSHA+`","HEAD_SHA":"`+entry.HeadSHA+`"`),1)},
  {"artifact top-level duplicate",run,bytes.Replace(meta,[]byte(`"expired":false`),[]byte(`"expired":false,"expired":false`),1)},
  {"run trailing second JSON",append(append([]byte{},run...),[]byte("{}")...),meta},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   if bytes.Equal(tc.run,run)&&bytes.Equal(tc.meta,meta){t.Fatal("test did not mutate metadata")}
   if _,err:=Verify(entry,tc.run,tc.meta,blob);!errors.Is(err,ErrBlocked){
    t.Fatalf("accepted ambiguous GitHub provenance: %v",err)
   }
  })
 }
}
func TestGitHubMetadataRejectsDeeplyNestedUnknownObject(t *testing.T){
 _,run,meta,blob,entry,_:=synthetic(t)
 // An otherwise valid GitHub payload with an irrelevant malicious nested
 // field must not force recursion beyond the bounded trust parser.
 extra:=`"extraneous":`+strings.Repeat(`{"layer":`,50)+`0`+strings.Repeat(`}`,50)
 changed:=append(append([]byte{},run[:len(run)-1]...),[]byte(","+extra+"}")...)
 if _,err:=Verify(entry,changed,meta,blob);!errors.Is(err,ErrBlocked){
  t.Fatal("accepted unbounded nested GitHub payload",err)
 }
}
