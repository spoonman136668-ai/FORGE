// forge-f104o-shadow-audit: frozen public TRAIN-only nonreflexive shadow.
// Immutable original Git objects only; no saved rows, predictions or labels.
package main

import (
 "crypto/sha1"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "strconv"

 "github.com/spoonman136668-ai/forge/noveltymechanisms/nonreflexive"
 "github.com/spoonman136668-ai/forge/noveltymechanisms/largegraph"
)

const (
 originalRepo="tiantiangao7/kalm-qa"
 originalCommit="826ee617e4da5b087584b0e03c70fe76642c6188"
 kbID="a43fa7ca5e6894236556f2984764070c4ca5562b"
 twoID="d2ce0a9f3670769f4239baa4eb6bf7bdc91d9468"
 threeID="77409d56af8d1fde7a4bec23cf5e1df1e0a08e59"
 kbSHA="9b4d3b3066266075ad1577b4beed68e6e112e76e1a29ed2cb00a2896d2b792af"
)

type PinnedSource struct {
 GitBlob string `json:"git_blob"`
 SHA256 string `json:"sha256"`
}
type Report struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 SourceRepository string `json:"source_repository"`
 SourceCommit string `json:"source_commit"`
 FrozenPolicy string `json:"frozen_policy"`
 KnowledgeGraph PinnedSource `json:"knowledge_graph"`
 TwoTraining PinnedSource `json:"two_hop_training"`
 ThreeTraining PinnedSource `json:"three_hop_training"`
 WholeTrainingDenominator int `json:"whole_training_denominator"`
 Two nonreflexive.Comparison `json:"two_hop"`
 Three nonreflexive.Comparison `json:"three_hop"`
 PublicTestRead bool `json:"public_test_read"`
 AnswerInputToPolicy bool `json:"answer_input_to_policy"`
 PerRowDataPublished bool `json:"per_row_data_published"`
 ScientificFirstUse bool `json:"independent_scientific_firstuse"`
 AcceptedScience bool `json:"accepted_science"`
 DreamParetoPromotion bool `json:"dream_pareto_promotion"`
 ThetaEvolveAcceptedTraining bool `json:"thetaevolve_accepted_training"`
 ScientificDispatch bool `json:"scientific_dispatch"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
 ModelCalls int `json:"model_calls"`
 CodexCalls int `json:"codex_calls"`
 CloudflareWrites int `json:"cloudflare_writes"`
}

func source(path,want string,budget int)([]byte,PinnedSource,error){
 var empty PinnedSource
 st,err:=os.Lstat(path)
 if err!=nil||!st.Mode().IsRegular()||st.Size()<=0||st.Size()>int64(budget){
  return nil,empty,fmt.Errorf("F104O_SOURCE_FILE_NOT_REGULAR_OR_BOUNDED")
 }
 raw,err:=os.ReadFile(path)
 if err!=nil{return nil,empty,fmt.Errorf("F104O_SOURCE_NOT_READABLE")}
 h:=sha1.New()
 _,_=h.Write([]byte("blob "+strconv.Itoa(len(raw))))
 _,_=h.Write([]byte{0})
 _,_=h.Write(raw)
 if hex.EncodeToString(h.Sum(nil))!=want{
  return nil,empty,fmt.Errorf("F104O_SOURCE_IMMUTABLE_GIT_BLOB_MISMATCH")
 }
 digest:=sha256.Sum256(raw)
 return raw,PinnedSource{GitBlob:want,SHA256:hex.EncodeToString(digest[:])},nil
}

func audit(kb,two,three []byte)(Report,error){
 var denied Report
 graph,err:=largegraph.Compile(kb)
 if err!=nil{return denied,err}
 stats:=graph.Statistics()
 if stats.SourceRows!=134741||stats.DistinctTriples!=133582||
  stats.DuplicateRows!=1159||stats.SelfRelations!=11||
  stats.DistinctEntities!=43234||stats.DistinctRoles!=9 {
  return denied,fmt.Errorf("F104O_PINNED_SOURCE_GRAPH_COUNT_DRIFT")
 }
 c2,err:=nonreflexive.Compare(graph,two,2,118980)
 if err!=nil{return denied,fmt.Errorf("F104O_2HOP_TRAIN_DENIED: %w",err)}
 c3,err:=nonreflexive.Compare(graph,three,3,114196)
 if err!=nil{return denied,fmt.Errorf("F104O_3HOP_TRAIN_DENIED: %w",err)}
 // Immutable F103-O baseline MUST match its independently qualified evidence;
 // shadow cannot rewrite or silently alter the antecedent.
 b2,b3:=c2.Baseline,c3.Baseline
 if b2.Parsed!=21609||b2.ParserAbstained!=97371||
  b2.GraphResolvedExactSet!=1561||b2.GraphResolvedPartialOverlap!=20048||
  b2.GraphResolvedDisjoint!=0||b2.GraphBudgetRefused!=0||
  b2.GraphMissingOrNoTargets!=0||b2.GraphResolvedAmbiguous!=20734||
  b2.GoldAnswerMembers!=739782||
  b3.Parsed!=26442||b3.ParserAbstained!=87754||
  b3.GraphResolvedExactSet!=13937||b3.GraphResolvedPartialOverlap!=12505||
  b3.GraphResolvedDisjoint!=0||b3.GraphBudgetRefused!=0||
  b3.GraphMissingOrNoTargets!=0||b3.GraphResolvedAmbiguous!=25506||
  b3.GoldAnswerMembers!=1521495 {
  return denied,fmt.Errorf("F104O_REFERENCE_F103O_BASELINE_COUNTERS_DRIFT")
 }
 k,t,u:=sha256.Sum256(kb),sha256.Sum256(two),sha256.Sum256(three)
 if hex.EncodeToString(k[:])!=kbSHA{return denied,fmt.Errorf("F104O_ORIGINAL_KB_SHA256_DRIFT")}
 return Report{
  Schema:"forge.optimizer.f104o.train-only-nonreflexive-shadow.v1",
  Status:"PUBLIC_TRAIN_ONLY_NONREFLEXIVE_SHADOW_DIAGNOSTIC",
  SourceRepository:originalRepo,SourceCommit:originalCommit,
  FrozenPolicy:"inverse-two-hop-exact-root-only-removal.v1",
  KnowledgeGraph:PinnedSource{kbID,hex.EncodeToString(k[:])},
  TwoTraining:PinnedSource{twoID,hex.EncodeToString(t[:])},
  ThreeTraining:PinnedSource{threeID,hex.EncodeToString(u[:])},
  WholeTrainingDenominator:c2.OriginalRows+c3.OriginalRows,
  Two:c2,Three:c3,
 },nil
}
func main(){
 kbPath:=flag.String("kb","","immutable KB original Git object materialization")
 twoPath:=flag.String("two-hop-train","","immutable original two-hop TRAIN Git object")
 threePath:=flag.String("three-hop-train","","immutable original three-hop TRAIN Git object")
 outPath:=flag.String("out","","new aggregate-only evidence path")
 flag.Parse()
 if *kbPath==""||*twoPath==""||*threePath==""||*outPath==""||len(flag.Args())!=0{
  fmt.Fprintln(os.Stderr,"F104O_REQUIRES_THREE_ORIGINAL_SOURCE_FILES_AND_NEW_OUTPUT")
  os.Exit(2)
 }
 kb,kbRec,err:=source(*kbPath,kbID,largegraph.MaxSourceBytes)
 var train2,train3 []byte
 var source2,source3 PinnedSource
 if err==nil{train2,source2,err=source(*twoPath,twoID,30*1024*1024)}
 if err==nil{train3,source3,err=source(*threePath,threeID,30*1024*1024)}
 if err==nil {
  var result Report
  result,err=audit(kb,train2,train3)
  if err==nil {
   if result.KnowledgeGraph!=kbRec||result.TwoTraining!=source2||result.ThreeTraining!=source3{
    err=fmt.Errorf("F104O_SOURCE_RECORD_DRIFT")
   }else{
    var payload []byte
    payload,err=json.MarshalIndent(result,"","  ")
    if err==nil{
     var f *os.File
     f,err=os.OpenFile(*outPath,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
     if err==nil {
      _,err=f.Write(append(payload,byte(10)))
      e:=f.Close()
      if err==nil{err=e}
     }
    }
   }
  }
 }
 if err!=nil {fmt.Fprintln(os.Stderr,"F104O_PUBLIC_TRAIN_SHADOW_DENIED:",err);os.Exit(1)}
 fmt.Println("F104O_WHOLE_TRAIN_DENOMINATOR=233176")
 fmt.Println("F104O_PARENT_F103O_EXACT_BASELINE_RECONCILED=TRUE")
 fmt.Println("F104O_CKB_CODEX_PAID_MODEL_AND_PROTECTED_SCIENCE=ZERO")
}
