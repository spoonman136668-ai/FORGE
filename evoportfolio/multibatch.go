package evoportfolio

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
)

// Batch is a frozen, advisory-only historical screen fragment.
// The independentPin must be sourced outside the untrusted batch collection.
type Batch struct {
 Lane string `json:"lane"`
 FrozenSHA256 string `json:"frozen_sha256"`
 BatchSHA256 string `json:"batch_sha256"`
 Candidates []Candidate `json:"candidates"`
}
func batchDigest(b Batch)string{
 b.BatchSHA256=""
 raw,_:=json.Marshal(b)
 d:=sha256.Sum256(raw)
 return hex.EncodeToString(d[:])
}
// SelectBatches enforces one global frozen screen and sealed budget, regardless
// of how many individual batches are supplied. It never dispatches experiments.
func SelectBatches(f Frozen, independentPin string, batches []Batch)(Decision,error){
 var empty Decision
 if len(batches)==0||len(batches)>20||Digest(f)!=independentPin{return empty,ErrFrozen}
 seenBatches:=map[string]bool{}
 seenIDs:=map[string]bool{}
 combined:=make([]Candidate,0,len(f.Candidates))
 for _,b:=range batches{
  if b.Lane!=f.Lane||b.FrozenSHA256!=independentPin||
   !isHex(b.BatchSHA256,64)||batchDigest(b)!=b.BatchSHA256||
   seenBatches[b.BatchSHA256]||len(b.Candidates)==0{return empty,ErrFrozen}
  seenBatches[b.BatchSHA256]=true
  for _,c:=range b.Candidates{
   if seenIDs[c.ID]||len(combined)>=160{return empty,ErrFrozen}
   seenIDs[c.ID]=true
   combined=append(combined,c)
  }
 }
 if len(combined)!=len(f.Candidates){return empty,ErrFrozen}
 exact:=map[string]Candidate{}
 for _,c:=range f.Candidates{
  if _,ok:=exact[c.ID];ok{return empty,ErrFrozen}
  exact[c.ID]=c
 }
 for _,c:=range combined{
  original,ok:=exact[c.ID]
  if !ok{return empty,ErrFrozen}
  a,_:=json.Marshal(c);b,_:=json.Marshal(original)
  if string(a)!=string(b){return empty,ErrFrozen}
 }
 // Selection runs once against the original frozen candidate set, so a batch
 // cannot independently reset either cap or improve its finalist priority.
 return Select(f,independentPin)
}
