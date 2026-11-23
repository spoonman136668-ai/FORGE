package shadowcore

import (
 "errors"
 "github.com/spoonman136668-ai/forge/researchstate"
)

// ReadinessEvidence binds externally witnessed cutover facts to one exact
// historical journal head. Caller-supplied booleans alone are not custody.
type ReadinessEvidence struct {
 JournalHeadSHA256 string
 WinglessCustodySHA256 string
 YggdrasilCustodySHA256 string
 CKBRevocationSHA256 string
 IndependentAuthoritySHA256 string
 ConsumedLedgerSHA256 string
 QualificationSHA256 string
 OperatorAuthorizationSHA256 string
}
var ErrUnwitnessed=errors.New("FORGE_CUTOVER_EVIDENCE_INCOMPLETE")
func valid64(s string)bool{
 if len(s)!=64{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
// VerifyReadinessEvidence prevents a stale synthetic run from being reused
// for a different current scientific journal. No activation is performed.
func VerifyReadinessEvidence(j researchstate.Journal,r CutoverReadiness,e ReadinessEvidence)error{
 if err:=CheckCutover(j,r);err!=nil{return err}
 h,err:=researchstate.Head(j)
 if err!=nil||h!=e.JournalHeadSHA256||!valid64(h)||
 !valid64(e.WinglessCustodySHA256)||!valid64(e.YggdrasilCustodySHA256)||
 e.WinglessCustodySHA256==e.YggdrasilCustodySHA256||
 !valid64(e.CKBRevocationSHA256)||!valid64(e.IndependentAuthoritySHA256)||
 !valid64(e.ConsumedLedgerSHA256)||!valid64(e.QualificationSHA256)||
 !valid64(e.OperatorAuthorizationSHA256){return ErrUnwitnessed}
 // These digests must be verified with separate trust anchors by the
 // eventual deployed cutover executor. This function validates shape/identity
 // only and never claims that signatures have been verified.
 return nil
}
