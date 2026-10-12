package classification
import (
 "github.com/spoonman136668-ai/forge/researchstate"
)
// Apply proposes classification only after an independent reviewer attests
// to the precise sealed original. It is NOT an accepted-ref update.
func Apply(j researchstate.Journal,a Attestation,e Expected)(researchstate.Journal,error){
 hash,err:=Verify(a,e);if err!=nil{return researchstate.Journal{},err}
 phase,found,err:=researchstate.Status(j,e.Lane,e.ExperimentID)
 if err!=nil||!found||phase!=researchstate.EvidenceSealed{return researchstate.Journal{},ErrBlocked}
 // Link attestation identity to scientific state; this does NOT verify
 // that the original evidence bytes remain available. The caller must do so.
 head,err:=researchstate.Head(j);if err!=nil{return researchstate.Journal{},err}
 next,err:=researchstate.Append(j,researchstate.Event{Lane:e.Lane,ExperimentID:e.ExperimentID,
  FrozenSHA256:e.FrozenSHA256,From:researchstate.EvidenceSealed,
  To:researchstate.Classified,EvidenceSHA256:hash},head)
 if err!=nil{return researchstate.Journal{},ErrBlocked}
 return next,nil
}
