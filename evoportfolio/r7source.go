package evoportfolio
// R7SourceReceipt is strictly read-only historical evidence; never creates readiness.
type R7SourceReceipt struct {
 Schema string
 Lane string
 CandidateSHA256 string
 ParentSHA string
 Status string
 FocusedGoTestInvocations int
 VerifiedSourceFiles int
 FullHistoricalDisjointnessProven bool
 ProspectiveSourceVerificationCount int
 SealedOutcomesSeen bool
 ScientificClassification string
 SourceQualificationAuthority bool
 ReadyResearchAuthority bool
 DispatchAuthority bool
 AcceptedRefMutation bool
 ProductionAuthority bool
 BrokerAccess bool
 KTRADEAccess bool
 ModelCalls int
 PredecessorReceiptSHA256 string
}
func ValidateR7ArchivedSource(r R7SourceReceipt)error{
 if r.Schema!="ckb-plane.research-source-qualification.r168"||
  !isHex(r.CandidateSHA256,64)||!isHex(r.ParentSHA,40)||
  !isHex(r.PredecessorReceiptSHA256,64)||
  r.FullHistoricalDisjointnessProven||r.ProspectiveSourceVerificationCount!=0||
  r.SealedOutcomesSeen||r.ScientificClassification!="NOT_EVALUATED"||
  r.SourceQualificationAuthority||r.ReadyResearchAuthority||
  r.DispatchAuthority||r.AcceptedRefMutation||r.ProductionAuthority||
  r.BrokerAccess||r.KTRADEAccess||r.ModelCalls!=0{return ErrFrozen}
 switch r.Lane{
 case "Wingless":
  if r.CandidateSHA256!="60a421d4ed786b92cd8d0e8a4b58988dd5d89229277ad2b91e5b11ca47f6cf8a"||
   r.ParentSHA!="b6716df4d94bdac07fde526de4e3a37c5b4f23ee"||
   r.Status!="PINNED_IMPLEMENTATION_COMPILES_SCIENCE_STILL_BLOCKED"||
   r.FocusedGoTestInvocations!=2||r.VerifiedSourceFiles!=2{return ErrFrozen}
 case "Yggdrasil":
  if r.CandidateSHA256!="ead6681782763de8b953a705783bb3babd5858da30f94257545a394bad928f88"||
   r.ParentSHA!="d5e3715c7124e1fd0fc91da5efbef850ec1d9254"||
   r.Status!="BLOCKED_REQUIRE_FULL_PARENT_SOURCE"||
   r.FocusedGoTestInvocations!=0||r.VerifiedSourceFiles!=0{return ErrFrozen}
 default:return ErrFrozen
 }
 return nil
}
