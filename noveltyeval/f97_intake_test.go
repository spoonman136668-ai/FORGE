package noveltyeval

import (
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"
 "os"
 "reflect"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/noveltymechanisms"
)
func f97Relation(from,role,to string)noveltymechanisms.Relation{
 return noveltymechanisms.Relation{From:from,Role:role,To:to}
}
func f97Tests()[]Case{
 return []Case{
  {ID:"candidate-a",Category:"branched-roles",
   Root:"u",Roles:[]string{"owns","located","contains"},
   Relations:[]noveltymechanisms.Relation{
    f97Relation("u","owns","a"),f97Relation("u","mentors","b"),
    f97Relation("a","located","c"),f97Relation("b","located","d"),
    f97Relation("c","contains","e"),f97Relation("d","contains","f"),
    f97Relation("a","owns","b"),
   },ExpectedTargets:[]string{"e"}},
  {ID:"candidate-b",Category:"many-bindings",
   Root:"hub",Roles:[]string{"sends","assigned"},
   Relations:[]noveltymechanisms.Relation{
    f97Relation("hub","sends","x"),f97Relation("hub","sends","y"),
    f97Relation("hub","sends","z"),f97Relation("x","assigned","token1"),
    f97Relation("y","assigned","token2"),f97Relation("z","assigned","token3"),
   },ExpectedTargets:[]string{"token1","token2","token3"}},
  {ID:"candidate-c",Category:"deep-dependencies",
   Root:"s0",Roles:[]string{"r1","r2","r3","r4","r5","r6","r7"},
   Relations:[]noveltymechanisms.Relation{
    f97Relation("s0","r1","s1"),f97Relation("s1","r2","s2"),
    f97Relation("s2","r3","s3"),f97Relation("s3","r4","s4"),
    f97Relation("s4","r5","s5"),f97Relation("s5","r6","s6"),
    f97Relation("s6","r7","s7"),f97Relation("s0","r2","trap1"),
    f97Relation("trap1","r3","trap2"),f97Relation("s4","r7","trap3"),
    f97Relation("trap3","r6","trap4"),
   },ExpectedTargets:[]string{"s7"}},
  {ID:"candidate-d",Category:"missing-tail",
   Root:"root",Roles:[]string{"links","handles","unknown","finishes"},
   Relations:[]noveltymechanisms.Relation{
    f97Relation("root","links","b"),f97Relation("b","handles","c"),
    f97Relation("root","owns","e"),f97Relation("e","belongs","f"),
    f97Relation("f","has","g"),f97Relation("b","handles","d"),
    f97Relation("d","finishes","marker"),
   },ExpectedTargets:[]string{}},
  {ID:"candidate-e",Category:"cycles-with-bindings",
   Root:"a",Roles:[]string{"refers","knows","refers","lists"},
   Relations:[]noveltymechanisms.Relation{
    f97Relation("a","refers","b"),f97Relation("b","knows","c"),
    f97Relation("c","refers","b"),f97Relation("b","lists","token"),
    f97Relation("a","knows","decoy"),f97Relation("decoy","lists","fake"),
   },ExpectedTargets:[]string{"token"}},
 }
}
func f97Fixture(t *testing.T)([]byte,[]byte,F97SuppliedPins,string){
 t.Helper()
 baseline,err:=os.ReadFile("f96_cases.json")
 if err!=nil{t.Fatal(err)}
 bundle:=F97CandidateBundle{
  Schema:F97Schema,SourceGitSHA:strings.Repeat("a",40),
  Origin:"UNQUALIFIED_SEPARATE_PRODUCER_CLAIM",
  RevealedForSourceInspection:true,Cases:f97Tests(),
 }
 raw,err:=json.Marshal(bundle);if err!=nil{t.Fatal(err)}
 key:=ed25519.NewKeyFromSeed([]byte(strings.Repeat("k",32)))
 pub:=key.Public().(ed25519.PublicKey)
 pin:=F97SuppliedPins{
  FrozenF96BytesSHA256:digest(baseline),
  CandidateBundleSHA256:digest(raw),
  ClaimedExternalSignerPublicKeyHex:hex.EncodeToString(pub),
  ClaimedPredecisionRegistrationSHA256:strings.Repeat("d",64),
  ClaimedExternalArchiveSHA256:strings.Repeat("e",64),
 }
 signature:=ed25519.Sign(key,append([]byte(F97SigningDomain),raw...))
 return baseline,raw,pin,hex.EncodeToString(signature)
}
func TestF97RevealedSourceCohortStrongParityAndNoScientificRelease(t *testing.T){
 original,raw,pin,sig:=f97Fixture(t)
 proof,err:=InspectF97SignedIntake(original,raw,pin,sig)
 if err!=nil{t.Fatal(err)}
 if proof.Schema!=F97ReviewSchema||!proof.SuppliedSignatureMatchesClaimedKey||
  proof.F96PopulationCount!=16||proof.ProposedCaseCount!=5||
  proof.DistinctProposedTopologyCount!=5||proof.RenamingInvariantOverlapCount!=0||
  !proof.AllProposedCasesRetained||proof.Status!=F97Disposition||
  proof.SuppliedSignerIdentityExternallyQualified||
  proof.IndependentPreOutcomeRegistrationVerified||proof.SealedNovelHoldoutQualified||
  proof.AuthenticOriginalFirstUseVerified||proof.ScientificGeneralizationEstablished||
  proof.DreamParetoPromotionAuthorized||proof.ThetaEvolveAcceptedTrainingAllowed||
  proof.AcceptedScientificReferenceMutation||proof.ScientificDispatchAuthorized{
  t.Fatalf("caller signature became scientific trust: %+v",proof)
 }
 report,again,err:=EvaluateF97RevealedSourceOnly(original,raw,pin,sig)
 if err!=nil||!reflect.DeepEqual(proof,again){t.Fatalf("source report error %v",err)}
 if report.FixtureCaseCount!=5||!report.EveryCaseRetained||
  len(report.Results)!=5||len(report.Totals)!=4||
  !report.EquivalentReferenceIsRequiredControl||
  report.AnyScientificSuperiorityEstablished||report.ScientificDispatchAuthorized||
  report.ThetaEvolveAcceptedTrainingEnabled||report.AuthenticOriginalFirstUse{
  t.Fatalf("source comparison claimed science %+v",report)
 }
 if report.Totals[0].Correct!=5||report.Totals[3].Correct!=5||
  report.Totals[1].Errors==0||report.Totals[2].Errors==0{
  t.Fatalf("missing parity/negative controls %+v",report.Totals)
 }
 for _,row:=range report.Results{
  if len(row.Models)!=4||!row.Models[0].Correct||!row.Models[3].Correct||
   !reflect.DeepEqual(row.Models[0].ActualTargets,row.Models[3].ActualTargets){
   t.Fatalf("incomplete source control %+v",row)
  }
 }
}
func TestF97RenamingAndRelationOrderCannotLaunderF96Cases(t *testing.T){
 base,raw,pin,sig:=f97Fixture(t)
 var first Suite
 if err:=json.Unmarshal(base,&first);err!=nil{t.Fatal(err)}
 // A pure relabeling of an F96 source-visible graph must be quarantined.
 old:=first.Cases[0]
 old.ID="renamed-f96-test"
 for i:=range old.Relations{
  old.Relations[i].From="rename-"+old.Relations[i].From
  old.Relations[i].To="rename-"+old.Relations[i].To
 }
 old.Root="rename-"+old.Root
 for i:=range old.ExpectedTargets{old.ExpectedTargets[i]="rename-"+old.ExpectedTargets[i]}
 for i,j:=0,len(old.Relations)-1;i<j;i,j=i+1,j-1{
  old.Relations[i],old.Relations[j]=old.Relations[j],old.Relations[i]
 }
 k1,err:=f97Topology(first.Cases[0])
 if err!=nil{t.Fatal(err)}
 k2,err:=f97Topology(old)
 if err!=nil||k1!=k2{t.Fatalf("renaming/original ordering changed topology %v",err)}
 var b F97CandidateBundle
 if err:=json.Unmarshal(raw,&b);err!=nil{t.Fatal(err)}
 b.Cases[0]=old
 modified,_:=json.Marshal(b)
 pin.CandidateBundleSHA256=digest(modified)
 // Re-sign changed bytes: valid signature cannot make a contaminated case new.
 key:=ed25519.NewKeyFromSeed([]byte(strings.Repeat("k",32)))
 sig=hex.EncodeToString(ed25519.Sign(key,append([]byte(F97SigningDomain),modified...)))
 if _,err:=InspectF97SignedIntake(base,modified,pin,sig);!errors.Is(err,ErrF97){
  t.Fatalf("re-signed F96 contamination was admitted: %v",err)
 }
}
func TestF97TamperReplayAndMissingPopulationFailClosed(t *testing.T){
 base,raw,pin,sig:=f97Fixture(t)
 altered:=append([]byte(nil),raw...)
 altered[len(altered)-3]^=1
 if _,err:=InspectF97SignedIntake(base,altered,pin,sig);!errors.Is(err,ErrF97){
  t.Fatal("unsigned modified source accepted")
 }
 mutations:=map[string]func(*F97CandidateBundle){
  "partial population":func(b *F97CandidateBundle){b.Cases=b.Cases[:3]},
  "duplicate case":func(b *F97CandidateBundle){b.Cases[1]=b.Cases[0]},
  "duplicate names":func(b *F97CandidateBundle){b.Cases[1].ID=b.Cases[0].ID},
  "made-up independently accepted science":func(b *F97CandidateBundle){b.IndependentlyAcceptedScience=true},
  "still sealed":func(b *F97CandidateBundle){b.RevealedForSourceInspection=false},
  "source owner mislabeled":func(b *F97CandidateBundle){b.Origin="independent_verified"},
  "malformed expected":func(b *F97CandidateBundle){b.Cases[0].ExpectedTargets=[]string{"z"}},
  "invalid relation":func(b *F97CandidateBundle){b.Cases[0].Relations[0].From="INVALID"},
  "invalid source commit":func(b *F97CandidateBundle){b.SourceGitSHA="bad"},
 }
 key:=ed25519.NewKeyFromSeed([]byte(strings.Repeat("k",32)))
 for name,mutate:=range mutations{
  t.Run(name,func(t *testing.T){
   var b F97CandidateBundle
   if err:=json.Unmarshal(raw,&b);err!=nil{t.Fatal(err)}
   mutate(&b)
   changed,_:=json.Marshal(b)
   p:=pin;p.CandidateBundleSHA256=digest(changed)
   signature:=hex.EncodeToString(ed25519.Sign(key,append([]byte(F97SigningDomain),changed...)))
   _,err:=InspectF97SignedIntake(base,changed,p,signature)
   if name=="malformed expected"{
    // Intake is provenance/topology validation, not outcome scoring.
    // Scoring MUST separately verify the expected answer vs strong reference.
    if err==nil{
     if _,_,e:=EvaluateF97RevealedSourceOnly(base,changed,p,signature);!errors.Is(e,ErrF97){
      t.Fatalf("incorrect supplied answer passed reference %v",e)
     }
    }
   }else if !errors.Is(err,ErrF97){
    t.Fatalf("malformed source re-signed and admitted: %s %v",name,err)
   }
  })
 }
 bad:=pin;bad.ClaimedExternalSignerPublicKeyHex=strings.Repeat("f",64)
 if _,err:=InspectF97SignedIntake(base,raw,bad,sig);!errors.Is(err,ErrF97){
  t.Fatal("signer pin mismatch admitted")
 }
 bad=pin;bad.ClaimedPredecisionRegistrationSHA256=bad.CandidateBundleSHA256
 if _,err:=InspectF97SignedIntake(base,raw,bad,sig);!errors.Is(err,ErrF97){
  t.Fatal("same registration and cohort digest admitted")
 }
 if _,err:=InspectF97SignedIntake(base,raw,pin,strings.Repeat("0",128));!errors.Is(err,ErrF97){
  t.Fatal("invalid signature admitted")
 }
}
