// Package originals imports two actual, already-consumed FORGE synthetic
// research generations. No historical policy choices or propensities exist in
// these archives; they MUST NOT be converted into Dream-RSI decision replay.
package originals

import (
 "archive/zip"
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "math"
 "sort"
)
const Schema="forge.dreamrsi.authenticated-original-intake.v1"
const MaxZipBytes=1<<20
const MaxJSONBytes=1<<18
var ErrEvidence=errors.New("FORGE_DREAMRSI_ORIGINAL_INTAKE_FAIL_CLOSED")
var ErrNoCounterfactual=errors.New("FORGE_DREAMRSI_NO_LOGGED_POLICY_OR_PROPENSITY")
type Pin struct {
 Generation string
 RunID int64
 SourceSHA string
 FrozenBlob string
 ArchiveSHA [5]string // W started, Y started, W raw, Y raw, postraw
 RawSHA [2]string
 DispositionSHA string
}
var Pins=[]Pin{
 {"F1",38128621982,"8dd2672f015f734761c09b2ef441edb4d6feac5f",
  "be0d5b1eafbbd65573bbdabdfcc42c88c807f7c1",
  [5]string{
   "7824451726a65c553ee65d164e2f84a33d5810cb02e37e9f091c47963888d110",
   "9a9579c41c28a5ce985b5c4129624efb77275f6f4814053d2ed3b16f73e6afd3",
   "289ba83b79f217a051b413e34cc2170a51cdb6c982bde4fe71fda2387c3a3273",
   "137d35c53dc7cfb0f2c7e253dbcde83c9a0b58687a0bff44a9a69823d3652b27",
   "0d57e3f942eda2a08c31f75d6f66dfb56f0cd81074447176969c8cee27ebb0c3",
  },
  [2]string{
   "84a7a7e6eb3dcf3fc25ebf06f91bfd128804d25457afd005c30454b5430034fe",
   "33ed9111b5583930ac953a655370f5f0cc3295e9b949b479e0e0a548cfcdc140",
  },
  "6f7b367463a3aca2acae8fda9112240de4da53f7fe31c1b4c76e130cfa19541b",
 },
 {"F2",38129536058,"e1503dbc040854161f33ae13da935741018a0386",
  "54bccd2f42854f000baccbcb5692faae7aa66057",
  [5]string{
   "4773b01a9dbbf84d0667e7280f4de8092f9ba62cf35379cf81ebe94ecc0083ff",
   "9e0a4e8c242961eb9483f14e11f278c8b1c77eb34d50ba5ee89f3d95fadac648",
   "f7c453452b12704ab25293c92b179ec99905c36496202ca9323c0fed7269012a",
   "60d392c31409104a9c8c9235db42f21d1cc49ee4b7a3745d12d84251ea9fc57c",
   "c071edb57a15ed55078ed47ade6b1594fc6b38110b874d6858aad84f3bd7aee2",
  },
  [2]string{
   "dfe38b0bf0771a8cc8005a7bf20c651baa2e3f0b25f4b11afda0d347c64eb3c0",
   "cf9517b8efcff437e2b1cbb2bbee2061f82a37ecaf74fc12d964990e998c8c1e",
  },
  "9f1027db392b8db9a65ef0ef283d69082c4ed7e48b2a7827927dea5811ba6b82",
 },
}
type Bundle struct {
 RunAPI []byte
 Archives [5][]byte
}
type Run struct {
 ID int64 `json:"id"`
 HeadSHA string `json:"head_sha"`
 HeadBranch string `json:"head_branch"`
 Event string `json:"event"`
 Status string `json:"status"`
 Conclusion string `json:"conclusion"`
 RunAttempt int `json:"run_attempt"`
 Repository struct{FullName string `json:"full_name"`} `json:"repository"`
}
type Started struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 Generation string `json:"generation"`
 RunID string `json:"run_id"`
 Attempt int `json:"attempt"`
 SourceSHA string `json:"source_sha"`
 FrozenBlob string `json:"frozen_blob"`
 ReplayAuthorized bool `json:"replay_authorized"`
 ScientificAccepted bool `json:"scientific_accepted"`
}
type Raw struct {
 Schema string
 Generation string
 Lane string
 FreezeBlob string
 SourceSHA string
 RunID string
 SyntheticOnly bool
 ScientificAccepted bool
 ExternalSourceAdmitted bool
 ModelCalls int
 Wingless json.RawMessage
 Yggdrasil json.RawMessage
}
type Outcome struct {
 Lane string
 Disposition string
 FrozenClauses []bool
 Clauses []bool
 Metrics map[string]float64
 Cases int
 RawSHA256 string
}
type Postraw struct {
 Schema string
 Generation string
 RunID string
 SourceSHA string
 SyntheticOnly bool
 ScientificAccepted bool
 ExternalSourceAdmitted bool
 ExecutionAuthority bool
 AcceptedRefMutation bool
 Outcomes []Outcome
 NextStep string
}
type EvidenceRecord struct {
 Generation string `json:"generation"`
 Lane string `json:"lane"`
 RunID int64 `json:"run_id"`
 SourceSHA string `json:"source_sha"`
 FrozenBlob string `json:"frozen_blob"`
 StartedSHA256 string `json:"started_sha256"`
 RawSHA256 string `json:"raw_sha256"`
 PostrawSHA256 string `json:"postraw_sha256"`
 OriginalDisposition string `json:"original_disposition"`
 OriginalClauses [4]bool `json:"original_clauses"`
 OriginalMetrics map[string]float64 `json:"original_metrics"`
 Cases int `json:"cases"`
 DataClass string `json:"data_class"`
 PolicyDecisionMenuRecorded bool `json:"policy_decision_menu_recorded"`
 LoggedActionPropensityRecorded bool `json:"logged_action_propensity_recorded"`
 ScientificComputeCostRecorded bool `json:"scientific_compute_cost_recorded"`
 CounterfactualReplayEligible bool `json:"counterfactual_replay_eligible"`
 ScientificAccepted bool `json:"scientific_accepted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 RecordSHA256 string `json:"record_sha256"`
}
type Catalog struct {
 Schema string `json:"schema"`
 ProvenanceLevel string `json:"provenance_level"`
 ScientificIssuerIndependentlyAttested bool `json:"scientific_issuer_independently_attested"`
 ExecutablePolicyReplay bool `json:"executable_policy_replay"`
 ScientificAccepted bool `json:"scientific_accepted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 OriginalRuns []int64 `json:"original_runs"`
 Records []EvidenceRecord `json:"records"`
 CatalogSHA256 string `json:"catalog_sha256"`
}
func digest(b []byte)string{d:=sha256.Sum256(b);return hex.EncodeToString(d[:])}
func parse(b []byte,v any)error{
 if len(b)==0||len(b)>MaxJSONBytes{return ErrEvidence}
 d:=json.NewDecoder(bytes.NewReader(b));d.DisallowUnknownFields()
 if err:=d.Decode(v);err!=nil{return ErrEvidence}
 var tail any
 if err:=d.Decode(&tail);err!=io.EOF{return ErrEvidence}
 return nil
}
func oneZip(raw []byte,pin,name string)([]byte,error){
 if len(raw)==0||len(raw)>MaxZipBytes||digest(raw)!=pin{return nil,ErrEvidence}
 z,err:=zip.NewReader(bytes.NewReader(raw),int64(len(raw)))
 if err!=nil||len(z.File)!=1||z.File[0].Name!=name||
  z.File[0].UncompressedSize64>MaxJSONBytes||z.File[0].FileInfo().IsDir(){
  return nil,ErrEvidence
 }
 f,err:=z.File[0].Open();if err!=nil{return nil,ErrEvidence}
 defer f.Close()
 b,err:=io.ReadAll(io.LimitReader(f,MaxJSONBytes+1))
 if err!=nil||len(b)>MaxJSONBytes{return nil,ErrEvidence}
 return b,nil
}
func pinFor(g string)(Pin,error){
 for _,p:=range Pins{if p.Generation==g{return p,nil}}
 return Pin{},ErrEvidence
}
func actualBool(r []bool,keys ...bool)([4]bool,error){
 var b [4]bool
 if len(r)!=4||len(keys)!=4{return b,ErrEvidence}
 for i:=range keys {b[i]=r[i];if b[i]!=keys[i]{return b,ErrEvidence}}
 return b,nil
}
func actualDisposition(bits [4]bool)string {
 n:=0;for _,b:=range bits{if b{n++}}
 if n==4{return "SUPPORTED"}
 if n==0{return "NEGATIVE"}
 return "MIXED"
}
func metricsMatch(received,expected map[string]float64)bool{
 if len(received)!=len(expected){return false}
 for k,v:=range expected{
  if _,ok:=received[k];!ok||math.IsNaN(received[k])||math.Abs(received[k]-v)>1e-10{return false}
 }
 return true
}
func verifyMetrics(g,lane string,r Raw,o Outcome)([4]bool,error){
 var invalid [4]bool
 var expected map[string]float64
 var frozen [4]bool
 cases:=0
 if lane=="Wingless"{
  var rows []struct{
   Cases int
   OrderedCorrect int
   ReversedCorrect int
   SortedCorrect int
   Correct int
   FixedRoleControl int
   ReversedControl int
  }
  if err:=json.Unmarshal(r.Wingless,&rows);err!=nil||len(rows)!=4{return invalid,ErrEvidence}
  a,b,c:=0,0,0
  for _,row:=range rows{
   if row.Cases!=192{return invalid,ErrEvidence}
   cases+=row.Cases
   if g=="F1" {a+=row.OrderedCorrect;b+=row.ReversedCorrect;c+=row.SortedCorrect
   }else{a+=row.Correct;b+=row.FixedRoleControl;c+=row.ReversedControl}
  }
  aa:=float64(a)/float64(cases)
  bb:=float64(a-b)/float64(cases)
  cc:=float64(a-c)/float64(cases)
  if g=="F1"{
   expected=map[string]float64{"ordered_accuracy":aa,"reversed_gap":bb,"sorted_gap":cc,"resource_bound":1}
   frozen=[4]bool{aa>=.9,bb>=.2,cc>=.15,cases==768}
   // F1 third gap threshold is actually 0.15 for the frozen prereg.
  }else{
   expected=map[string]float64{"correct_accuracy":aa,"gain_over_static_mapping":bb,"gain_over_reversed_order":cc,"resource_and_split_integrity":1}
   frozen=[4]bool{aa>=.90,bb>=.35,cc>=.20,cases==768}
  }
 }else{
  var rows []struct{
   HotKeys int
   ColdKeys int
   ProtectedColdCorrect int
   LRUSlotColdCorrect int
   ProtectedHotCorrect int
   ProtectedCold int
   LRUCold int
   ProtectedHot int
   LRUHot int
   Cases int
  }
  if err:=json.Unmarshal(r.Yggdrasil,&rows);err!=nil||len(rows)!=8{
   return invalid,ErrEvidence
  }
  a,b,c,d:=0,0,0,0
  for _,row:=range rows{
   if g=="F1"{
    if row.HotKeys!=9||row.ColdKeys!=3{return invalid,ErrEvidence}
    cases+=row.HotKeys+row.ColdKeys
    a+=row.ProtectedColdCorrect;b+=row.LRUSlotColdCorrect;c+=row.ProtectedHotCorrect
   }else{
    if row.Cases!=15{return invalid,ErrEvidence}
    cases+=row.Cases
    a+=row.ProtectedCold;b+=row.LRUCold;c+=row.ProtectedHot;d+=row.LRUHot
   }
  }
  if g=="F1"{
   cold:=float64(a)/24;gain:=float64(a-b)/24;hot:=float64(c)/72
   expected=map[string]float64{"cold_recall_protected":cold,"cold_gain_over_lru":gain,"hot_recall_protected":hot,"resource_bound":1}
   frozen=[4]bool{cold>=.3,gain>=.25,hot>=.55,cases==96}
  }else{
   cold:=float64(a)/40;gain:=float64(a-b)/40
   hot:=float64(c)/80;deficit:=float64(d-c)/80
   expected=map[string]float64{"dormant_cold_recall":cold,"cold_gain_over_equal_capacity_lru":gain,"final_hot_recall":hot,"final_hot_deficit_vs_lru":deficit}
   frozen=[4]bool{cold>=.25,gain>=.20,hot>=.60,deficit<=.40}
  }
 }
 if o.Cases!=cases||!metricsMatch(o.Metrics,expected){return invalid,ErrEvidence}
 clauses:=o.FrozenClauses
 if g=="F2"{clauses=o.Clauses}
 got,err:=actualBool(clauses,frozen[:]...)
 if err!=nil||o.Disposition!=actualDisposition(got){return invalid,ErrEvidence}
 return got,nil
}
// Import accepts actual GitHub API run JSON and the ten pre-pinned ZIP files
// for F1/F2. Its result is observational SCIENCE history, NOT exploration
// decision history. The external caller must independently obtain GitHub API
// responses over trusted TLS: static bytes alone aren't FSA issuer authority.
func Import(bundles map[string]Bundle)(Catalog,error){
 var empty Catalog
 if len(bundles)!=2{return empty,ErrEvidence}
 catalog:=Catalog{Schema:Schema,ProvenanceLevel:"PINNED_GITHUB_ACTIONS_ARTIFACT_AND_API_NOT_INDEPENDENT_FSA_SIGNATURE"}
 for _,pin:=range Pins{
  b,ok:=bundles[pin.Generation];if !ok{return empty,ErrEvidence}
  var run Run
  if len(b.RunAPI)==0||len(b.RunAPI)>MaxJSONBytes||json.Unmarshal(b.RunAPI,&run)!=nil||
   run.ID!=pin.RunID||run.HeadSHA!=pin.SourceSHA||
   run.Status!="completed"||run.Conclusion!="success"||run.RunAttempt!=1||
   run.Event!="push"||run.Repository.FullName!="spoonman136668-ai/FORGE"||
   run.HeadBranch!="experiment/forge-"+lower(pin.Generation)+"-original-20261011"{
   return empty,ErrEvidence
  }
  raw:=make([][]byte,5)
  for i,filename:=range []string{"started.json","started.json","raw.json","raw.json","disposition.json"}{
   var err error
   raw[i],err=oneZip(b.Archives[i],pin.ArchiveSHA[i],filename)
   if err!=nil{return empty,ErrEvidence}
  }
  var post Postraw
  if err:=parse(raw[4],&post);err!=nil||digest(raw[4])!=pin.DispositionSHA||
   post.Schema!="forge."+lower(pin.Generation)+".postraw-disposition.v1"||
   post.Generation!=pin.Generation||post.RunID!=intToString(pin.RunID)||
   post.SourceSHA!=pin.SourceSHA||!post.SyntheticOnly||
   post.ScientificAccepted||post.ExternalSourceAdmitted||
   post.ExecutionAuthority||post.AcceptedRefMutation||len(post.Outcomes)!=2{
   return empty,ErrEvidence
  }
  for laneIdx,lane:=range []string{"Wingless","Yggdrasil"}{
   var started Started
   if err:=parse(raw[laneIdx],&started);err!=nil||
    started.Schema!=map[string]string{"F1":"forge.f1.original-started.v1","F2":"forge.f2.original-started.v1"}[pin.Generation]||
    started.Lane!=lane||started.Generation!=pin.Generation||
    started.SourceSHA!=pin.SourceSHA||started.FrozenBlob!=pin.FrozenBlob||
    started.RunID!=intToString(pin.RunID)||started.Attempt!=1||
    started.ReplayAuthorized||started.ScientificAccepted{
    return empty,ErrEvidence
   }
   var science Raw
   original:=raw[2+laneIdx]
   if err:=parse(original,&science);err!=nil||
    digest(original)!=pin.RawSHA[laneIdx]||
    science.Schema!="forge."+lower(pin.Generation)+".original-raw.v1"||
    science.Generation!=pin.Generation||science.Lane!=lane||
    science.FreezeBlob!=pin.FrozenBlob||science.SourceSHA!=pin.SourceSHA||
    science.RunID!=started.RunID||!science.SyntheticOnly||
    science.ScientificAccepted||science.ExternalSourceAdmitted||science.ModelCalls!=0{
    return empty,ErrEvidence
   }
   o:=post.Outcomes[laneIdx]
   if o.Lane!=lane||o.RawSHA256!=digest(original){return empty,ErrEvidence}
   bits,err:=verifyMetrics(pin.Generation,lane,science,o)
   if err!=nil{return empty,err}
   rec:=EvidenceRecord{
    Generation:pin.Generation,Lane:lane,RunID:pin.RunID,
    SourceSHA:pin.SourceSHA,FrozenBlob:pin.FrozenBlob,
    StartedSHA256:digest(raw[laneIdx]),RawSHA256:digest(original),
    PostrawSHA256:digest(raw[4]),
    OriginalDisposition:o.Disposition,OriginalClauses:bits,
    OriginalMetrics:o.Metrics,Cases:o.Cases,DataClass:"SYNTHETIC_ONLY",
   }
   r,err:=json.Marshal(rec);if err!=nil{return empty,ErrEvidence}
   rec.RecordSHA256=digest(r)
   catalog.Records=append(catalog.Records,rec)
  }
  catalog.OriginalRuns=append(catalog.OriginalRuns,pin.RunID)
 }
 if len(catalog.Records)!=4{return empty,ErrEvidence}
 sort.Slice(catalog.Records,func(i,j int)bool{
  if catalog.Records[i].RunID==catalog.Records[j].RunID{return catalog.Records[i].Lane<catalog.Records[j].Lane}
  return catalog.Records[i].RunID<catalog.Records[j].RunID
 })
 raw,err:=json.Marshal(catalog);if err!=nil{return empty,ErrEvidence}
 catalog.CatalogSHA256=digest(raw)
 return catalog,nil
}
func lower(s string)string{
 switch s{case "F1":return "f1";case "F2":return "f2"}
 return ""
}
func intToString(n int64)string{
 // Run IDs are fixed 11-digit decimal, not arithmetic seed data.
 if n==38128621982{return "38128621982"}
 if n==38129536058{return "38129536058"}
 return ""
}
// ToPolicyReplay deliberately never emits a fabricated Decision with
// invented menu, propensity, historical cost or counterfactual outcomes.
func ToPolicyReplay(_ Catalog)error{return ErrNoCounterfactual}
