// Package genenv generates bounded, deterministic training-only
// candidate environments. Historical distance is NOT a science finding.
package genenv
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
)
const(
 FrozenSchema="forge.genenvironment.frozen.v1"
 HistorySchema="forge.genenvironment.training-history.v1"
 ResultSchema="forge.genenvironment.advisory.v1"
)
var ErrFrozen=errors.New("FORGE_GENENV_FROZEN_NOVELTY_UNQUALIFIED")
type Change struct {Index int `json:"index"`; Delta int64 `json:"delta"`}
type Request struct {ID string `json:"id"`; Changes []Change `json:"changes"`}
type Frozen struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 SourceSHA string `json:"source_sha"`
 Epoch uint64 `json:"epoch"`
 HistorySHA256 string `json:"history_sha256"`
 Base []int64 `json:"base"`
 MaxLevel int64 `json:"max_level"`
 MaxCandidates int `json:"max_candidates"`
 MaxOperations int `json:"max_operations"`
 Requests []Request `json:"requests"`
}
type Record struct {
 Sequence int `json:"sequence"`
 EvidenceSHA256 string `json:"evidence_sha256"`
 TrainingOnly bool `json:"training_only"`
 Classification string `json:"classification"`
 Vector []int64 `json:"vector"`
}
type History struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 SourceSHA string `json:"source_sha"`
 Records []Record `json:"records"`
}
type Candidate struct {
 ID string `json:"id"`
 EnvironmentSHA256 string `json:"environment_sha256"`
 Vector []int64 `json:"vector"`
 HistoricalDistance int64 `json:"historical_distance"`
 Classification string `json:"classification"`
}
type Result struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 FrozenSHA256 string `json:"frozen_sha256"`
 HistorySHA256 string `json:"history_sha256"`
 Candidates []Candidate `json:"candidates"`
 HistoricalCount int `json:"historical_count"`
 NegativeCount int `json:"negative_count"`
 InvalidCount int `json:"invalid_count"`
 MixedCount int `json:"mixed_count"`
 OperationsUsed int `json:"operations_used"`
 ScientificAccepted bool `json:"scientific_accepted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 SealedHoldoutConsumed bool `json:"sealed_holdout_consumed"`
}
func hash(domain string,v any)string{
 b,_:=json.Marshal(v)
 x:=sha256.Sum256(append([]byte(domain+"\n"),b...))
 return hex.EncodeToString(x[:])
}
func FrozenDigest(f Frozen)string{return hash("FORGE-GENENV-FROZEN-V1",f)}
func HistoryDigest(h History)string{return hash("FORGE-GENENV-HISTORY-V1",h)}
func hexLower(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func validID(s string)bool{
 if len(s)<1||len(s)>72{return false}
 for _,c:=range s{if !(c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='_'||c=='-'){return false}}
 return true
}
func validClass(c string)bool{
 switch c{case "SUPPORTED","NEGATIVE","MIXED","INVALID","CONSUMED_INDETERMINATE":return true}
 return false
}
func validVec(v []int64,n int,cap int64)bool{
 if len(v)!=n{return false}
 for _,x:=range v{if x<0||x>cap{return false}}
 return true
}
func abs(a int64)int64{if a<0{return -a};return a}
func distance(a,b []int64)int64{var sum int64;for i,x:=range a{sum+=abs(x-b[i])};return sum}
// Generate creates only deterministic, untested proposals from independently
// pinned training history. Pin equality is not an external provenance witness.
// This package has no network, worker, sealed input or FSA authority.
func Generate(f Frozen,pin string,h History,historyPin string)(Result,error){
 var zero Result
 n:=len(f.Base)
 if f.Schema!=FrozenSchema||(f.Lane!="Wingless"&&f.Lane!="Yggdrasil")||
 !hexLower(f.SourceSHA,40)||f.Epoch==0||!hexLower(f.HistorySHA256,64)||
 !hexLower(pin,64)||pin!=FrozenDigest(f)||!hexLower(historyPin,64)||
 f.HistorySHA256!=historyPin||HistoryDigest(h)!=historyPin||
 h.Schema!=HistorySchema||h.Lane!=f.Lane||h.SourceSHA!=f.SourceSHA||
 n<1||n>16||f.MaxLevel<1||f.MaxLevel>32||!validVec(f.Base,n,f.MaxLevel)||
 f.MaxCandidates<1||f.MaxCandidates>16||f.MaxOperations<1||f.MaxOperations>64||
 len(f.Requests)<1||len(f.Requests)>f.MaxCandidates||
 len(h.Records)<1||len(h.Records)>64{return zero,ErrFrozen}
 historical:=make([][]int64,0,len(h.Records)+1)
 historical=append(historical,f.Base)
 seenEvidence:=map[string]bool{}
 seenVector:=map[string]bool{hash("FORGE-GENENV-VECTOR-V1",f.Base):true}
 out:=Result{Schema:ResultSchema,Lane:f.Lane,FrozenSHA256:pin,HistorySHA256:historyPin,
 Candidates:make([]Candidate,0,len(f.Requests)),HistoricalCount:len(h.Records)}
 for i,r:=range h.Records{
  if r.Sequence!=i+1||!r.TrainingOnly||!hexLower(r.EvidenceSHA256,64)||seenEvidence[r.EvidenceSHA256]||
  !validClass(r.Classification)||!validVec(r.Vector,n,f.MaxLevel){return zero,ErrFrozen}
  sig:=hash("FORGE-GENENV-VECTOR-V1",r.Vector)
  if seenVector[sig]{return zero,ErrFrozen}
  seenVector[sig]=true;seenEvidence[r.EvidenceSHA256]=true;historical=append(historical,r.Vector)
  switch r.Classification{
  case "NEGATIVE":out.NegativeCount++
  case "INVALID":out.InvalidCount++
  case "MIXED":out.MixedCount++
  }
 }
 requests:=map[string]bool{}
 for _,req:=range f.Requests{
  if !validID(req.ID)||requests[req.ID]||len(req.Changes)<1||
   len(req.Changes)>f.MaxOperations-out.OperationsUsed{return zero,ErrFrozen}
  requests[req.ID]=true
  v:=append([]int64(nil),f.Base...)
  for _,op:=range req.Changes{
   if op.Index<0||op.Index>=n||(op.Delta!=1&&op.Delta!= -1)||
   v[op.Index]+op.Delta<0||v[op.Index]+op.Delta>f.MaxLevel{return zero,ErrFrozen}
   v[op.Index]+=op.Delta
  }
  out.OperationsUsed+=len(req.Changes)
  digest:=hash("FORGE-GENENV-VECTOR-V1",v)
  if seenVector[digest]{return zero,ErrFrozen}
  seenVector[digest]=true
  novelty:=int64(1<<62)
  for _,prior:=range historical{d:=distance(v,prior);if d<novelty{novelty=d}}
  if novelty<1{return zero,ErrFrozen}
  out.Candidates=append(out.Candidates,Candidate{ID:req.ID,
   EnvironmentSHA256:hash("FORGE-GENENV-CANDIDATE-V1",struct{Frozen string;History string;ID string;Vector []int64}{pin,historyPin,req.ID,v}),
   Vector:v,HistoricalDistance:novelty,Classification:"UNTESTED_PROPOSAL"})
 }
 return out,nil
}
