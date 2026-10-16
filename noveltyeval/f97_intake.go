package noveltyeval

// F97 validates separately supplied, signed, REVEALED source-only candidate
// tests against F96's frozen source population. Caller-provided signer pins
// and a signature cannot establish that a source was independent or sealed.
import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "sort"
 "strings"
)

const F97Schema="forge.optimizer.f97.revealed-external-candidate-v1"
const F97ReviewSchema="forge.optimizer.f97.source-only-contamination-review-v1"
const F97SigningDomain="FORGE-F97-REVEALED-SOURCE-ONLY-V1\n"
const F97Disposition="REVEALED_SOURCE_ONLY_INDEPENDENT_PREOUTCOME_CUSTODY_UNVERIFIED"
var ErrF97=errors.New("FORGE_F97_INDEPENDENT_NOVEL_TEST_ORIGINAL_NOT_VERIFIED")

// A bundle containing any still-sealed/unrevealed scientific holdout MUST NOT
// be passed to this source-only inspector.
type F97CandidateBundle struct{
 Schema string `json:"schema"`
 SourceGitSHA string `json:"source_git_sha"`
 Origin string `json:"origin"`
 RevealedForSourceInspection bool `json:"revealed_for_source_inspection"`
 IndependentlyAcceptedScience bool `json:"independently_accepted_science"`
 Cases []Case `json:"cases"`
}
type F97SuppliedPins struct{
 FrozenF96BytesSHA256 string `json:"frozen_f96_bytes_sha256"`
 CandidateBundleSHA256 string `json:"candidate_bundle_sha256"`
 ClaimedExternalSignerPublicKeyHex string `json:"claimed_external_signer_public_key_hex"`
 ClaimedPredecisionRegistrationSHA256 string `json:"claimed_predecision_registration_sha256"`
 ClaimedExternalArchiveSHA256 string `json:"claimed_external_archive_sha256"`
}
type F97IntakeReview struct{
 Schema string `json:"schema"`
 CandidateSourceGitSHA string `json:"candidate_source_git_sha"`
 F96SourceSHA256 string `json:"f96_source_sha256"`
 CandidateBytesSHA256 string `json:"candidate_bytes_sha256"`
 SuppliedSignatureMatchesClaimedKey bool `json:"supplied_signature_matches_claimed_key"`
 AllProposedCasesRetained bool `json:"all_proposed_cases_retained"`
 ProposedCaseCount int `json:"proposed_case_count"`
 F96PopulationCount int `json:"f96_population_count"`
 RenamingInvariantOverlapCount int `json:"renaming_invariant_overlap_count"`
 DistinctProposedTopologyCount int `json:"distinct_proposed_topology_count"`
 SuppliedSignerIdentityExternallyQualified bool `json:"supplied_signer_identity_externally_qualified"`
 IndependentPreOutcomeRegistrationVerified bool `json:"independent_pre_outcome_registration_verified"`
 SealedNovelHoldoutQualified bool `json:"sealed_novel_holdout_qualified"`
 AuthenticOriginalFirstUseVerified bool `json:"authentic_original_first_use_verified"`
 ScientificGeneralizationEstablished bool `json:"scientific_generalization_established"`
 DreamParetoPromotionAuthorized bool `json:"dream_pareto_promotion_authorized"`
 ThetaEvolveAcceptedTrainingAllowed bool `json:"theta_evolve_accepted_training_allowed"`
 AcceptedScientificReferenceMutation bool `json:"accepted_scientific_reference_mutation"`
 ScientificDispatchAuthorized bool `json:"scientific_dispatch_authorized"`
 Status string `json:"status"`
}
func f97Hex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !strings.ContainsRune("0123456789abcdef",c){return false}}
 return true
}
func f97Parse(raw []byte)(F97CandidateBundle,error){
 var zero F97CandidateBundle
 if len(raw)<300||len(raw)>200000{return zero,ErrF97}
 dec:=json.NewDecoder(bytes.NewReader(raw));dec.DisallowUnknownFields()
 var b F97CandidateBundle
 if dec.Decode(&b)!=nil{return zero,ErrF97}
 var tail any
 if dec.Decode(&tail)!=io.EOF{return zero,ErrF97}
 if b.Schema!=F97Schema||!f97Hex(b.SourceGitSHA,40)||
  b.SourceGitSHA==BaseF95Commit||
  b.Origin!="UNQUALIFIED_SEPARATE_PRODUCER_CLAIM"||
  !b.RevealedForSourceInspection||b.IndependentlyAcceptedScience||
  len(b.Cases)<4||len(b.Cases)>128{return zero,ErrF97}
 return b,nil
}
func f97Topology(c Case)(string,error){
 if !nameOK(c.Root)||len(c.Roles)<1||len(c.Roles)>8||
  len(c.Relations)<1||len(c.Relations)>128{return "",ErrF97}
 nodes:=map[string]bool{c.Root:true}
 for _,r:=range c.Relations{
  if !nameOK(r.From)||!nameOK(r.To)||!nameOK(r.Role)||r.From==r.To{
   return "",ErrF97
  }
  nodes[r.From]=true;nodes[r.To]=true
 }
 // Deterministic directed edge-colored Weisfeiler-Lehman refinement.
 // Node labels are deliberately excluded; renaming entities and changing
 // JSON edge order cannot create an apparently independent condition.
 // Equal fingerprints do NOT imply full graph isomorphism; conservative
 // rejection of some truly new cases is preferable to training leakage.
 colors:=map[string]string{}
 for node:=range nodes{
  in,out:=[]string{},[]string{}
  for _,r:=range c.Relations{
   if r.From==node{out=append(out,r.Role)}
   if r.To==node{in=append(in,r.Role)}
  }
  sort.Strings(in);sort.Strings(out)
  colors[node]=f93Hash("F97-BASE-ROLE-IN-OUT",[]any{in,out,node==c.Root})
 }
 for step:=0;step<9;step++{
  next:=map[string]string{}
  for node:=range nodes{
   paths:=[]string{}
   for _,r:=range c.Relations{
    if r.From==node{paths=append(paths,"out:"+r.Role+":"+colors[r.To])}
    if r.To==node{paths=append(paths,"in:"+r.Role+":"+colors[r.From])}
   }
   sort.Strings(paths)
   next[node]=f93Hash("F97-DIRECTED-TYPED-REFINEMENT",[]any{colors[node],paths})
  }
  colors=next
 }
 values:=make([]string,0,len(nodes))
 for _,v:=range colors{values=append(values,v)}
 sort.Strings(values)
 roles:=append([]string(nil),c.Roles...)
 return f93Hash("F97-RENAMING-INVARIANT-TOPOLOGY",[]any{
  colors[c.Root],values,roles,len(c.Relations),len(c.ExpectedTargets),
 }),nil
}
func f97CheckCase(c Case)error{
 if !nameOK(c.ID)||!nameOK(c.Category)||
  len(c.Relations)<1||len(c.Relations)>128||
  len(c.Roles)<1||len(c.Roles)>8{return ErrF97}
 for _,s:=range c.Roles{if !nameOK(s){return ErrF97}}
 expected,err:=uniqueSorted(c.ExpectedTargets)
 if err!=nil||!same(expected,c.ExpectedTargets){return ErrF97}
 if _,err:=exactReference(c);err!=nil{return ErrF97}
 return nil
}

// InspectF97SignedIntake checks cryptographic consistency and topology
// contamination ONLY. The public key, preregistration and archive hashes
// are caller-supplied, not an external trust root. No sealed science is read.
func InspectF97SignedIntake(f96Raw,candidateRaw []byte,
 pin F97SuppliedPins,signatureHex string)(F97IntakeReview,error){
 var zero F97IntakeReview
 original,err:=decodeStrict(f96Raw);if err!=nil{return zero,ErrF97}
 proposed,err:=f97Parse(candidateRaw);if err!=nil{return zero,ErrF97}
 if !f97Hex(pin.FrozenF96BytesSHA256,64)||
  !f97Hex(pin.CandidateBundleSHA256,64)||
  !f97Hex(pin.ClaimedExternalSignerPublicKeyHex,64)||
  !f97Hex(pin.ClaimedPredecisionRegistrationSHA256,64)||
  !f97Hex(pin.ClaimedExternalArchiveSHA256,64)||
  !f97Hex(signatureHex,128)||
  pin.FrozenF96BytesSHA256!=digest(f96Raw)||
  pin.CandidateBundleSHA256!=digest(candidateRaw){return zero,ErrF97}
 values:=[]string{pin.FrozenF96BytesSHA256,pin.CandidateBundleSHA256,
  pin.ClaimedPredecisionRegistrationSHA256,pin.ClaimedExternalArchiveSHA256}
 usedPins:=map[string]bool{}
 for _,v:=range values{if usedPins[v]{return zero,ErrF97};usedPins[v]=true}
 pub,_:=hex.DecodeString(pin.ClaimedExternalSignerPublicKeyHex)
 sig,_:=hex.DecodeString(signatureHex)
 if !ed25519.Verify(ed25519.PublicKey(pub),
  append([]byte(F97SigningDomain),candidateRaw...),sig){return zero,ErrF97}
 seen:=map[string]bool{}
 for _,c:=range original.Cases{
  key,err:=f97Topology(c);if err!=nil{return zero,ErrF97}
  seen[key]=true
 }
 candidateSeen:=map[string]bool{};ids:=map[string]bool{}
 categories:=map[string]bool{}
 for _,c:=range proposed.Cases{
  if f97CheckCase(c)!=nil||ids[c.ID]{return zero,ErrF97}
  ids[c.ID]=true;categories[c.Category]=true
  key,err:=f97Topology(c);if err!=nil||seen[key]||candidateSeen[key]{
   return zero,ErrF97
  }
  candidateSeen[key]=true
 }
 if len(categories)<3{return zero,ErrF97}
 return F97IntakeReview{
  Schema:F97ReviewSchema,CandidateSourceGitSHA:proposed.SourceGitSHA,
  F96SourceSHA256:digest(f96Raw),CandidateBytesSHA256:digest(candidateRaw),
  SuppliedSignatureMatchesClaimedKey:true,AllProposedCasesRetained:true,
  ProposedCaseCount:len(proposed.Cases),F96PopulationCount:len(original.Cases),
  RenamingInvariantOverlapCount:0,
  DistinctProposedTopologyCount:len(candidateSeen),
  Status:F97Disposition,
 },nil
}

// EvaluateF97RevealedSourceOnly executes *revealed* tests with F96's exact
// controls. This is an engineering diagnostic; it cannot certify an unseen
// holdout, owner first-use, model generalization or optimizer learning.
func EvaluateF97RevealedSourceOnly(f96Raw,candidateRaw []byte,
 pin F97SuppliedPins,signatureHex string)(Report,F97IntakeReview,error){
 var empty Report
 r,err:=InspectF97SignedIntake(f96Raw,candidateRaw,pin,signatureHex)
 if err!=nil{return empty,F97IntakeReview{},err}
 b,err:=f97Parse(candidateRaw)
 if err!=nil{return empty,F97IntakeReview{},ErrF97}
 result:=Report{Schema:ReportSchema,BaselineSourceSHA:b.SourceGitSHA,
  FixtureFreezeCommit:"EXTERNAL_PREOUTCOME_GIT_FREEZE_UNVERIFIED",
  FixtureBytesSHA256:digest(candidateRaw),
  FixtureCaseCount:len(b.Cases),EveryCaseRetained:true,
  EquivalentReferenceIsRequiredControl:true,
  Status:"REVEALED_SIGNED_SOURCE_ONLY_NO_INDEPENDENT_SCIENTIFIC_GENERALIZATION",
 }
 names:=[]string{"f95_typed_composition","direct_typed_onehop_control",
  "role_blind_multihop_control","independent_typed_reference_control"}
 for _,name:=range names{result.Totals=append(result.Totals,
  Totals{Model:name,Cases:len(b.Cases)})}
 for _,c:=range b.Cases{
  expected,err:=exactReference(c)
  if err!=nil||!same(expected,c.ExpectedTargets){
   return empty,F97IntakeReview{},fmt.Errorf("%w:reference_disagreement",ErrF97)
  }
  mem,err:=noveltymechanisms.Compile(c.Relations)
  if err!=nil{return empty,F97IntakeReview{},ErrF97}
  got,err:=noveltymechanisms.Resolve(mem,c.Root,c.Roles)
  if err!=nil{return empty,F97IntakeReview{},ErrF97}
  direct,_:=oneHop(c);blind,_:=blindHop(c)
  rows:=[][]string{got.Targets,direct,blind,expected}
  cr:=CaseResult{ID:c.ID,Category:c.Category,ExpectedTargets:c.ExpectedTargets}
  for i,targets:=range rows{
   if targets==nil{targets=[]string{}}
   yes:=same(targets,c.ExpectedTargets)
   if yes{result.Totals[i].Correct++}else{result.Totals[i].Errors++}
   cr.Models=append(cr.Models,ModelResult{
    Name:names[i],ActualTargets:targets,Correct:yes,
    ErrorClass:class(targets,c.ExpectedTargets)})
  }
  result.Results=append(result.Results,cr)
 }
 return result,r,nil
}

func F97RawDigest(raw []byte)string{
 h:=sha256.Sum256(raw);return hex.EncodeToString(h[:])
}
