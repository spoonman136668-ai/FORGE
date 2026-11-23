package optimizerstages

import (
 "bytes"
 "os"
 "strings"
 "testing"
)

func f95ReadSource(t *testing.T,path string)[]byte{
 t.Helper()
 raw,err:=os.ReadFile(path)
 if err!=nil{t.Fatal(err)}
 return raw
}
func f95SourceFixture(t *testing.T)(F94Freeze,F94ImplementationClaim,F95ThreeSourceArtifacts){
 t.Helper()
 art:=F95ThreeSourceArtifacts{
  Representation:F95ArtifactBytes{
   Parent:f95ReadSource(t,"../genenv/genenv.go"),
   Candidate:f95ReadSource(t,"../noveltymechanisms/f95_representation.go")},
  Consumer:F95ArtifactBytes{
   Parent:f95ReadSource(t,"../promptlineage/lineage.go"),
   Candidate:f95ReadSource(t,"../noveltymechanisms/f95_consumer.go")},
  TestEnvironment:F95ArtifactBytes{
   Parent:f95ReadSource(t,"../genenv/genenv_test.go"),
   Candidate:f95ReadSource(t,"../noveltymechanisms/f95_environment_test.go")},
 }
 f,_,_,_,links:=f94Base("Wingless")
 f.ParentRepresentationSHA256=f95SHA(art.Representation.Parent)
 f.ParentConsumerSHA256=f95SHA(art.Consumer.Parent)
 f.ParentTestEnvironmentSHA256=f95SHA(art.TestEnvironment.Parent)
 link:=links[0]
 link.NewRepresentationSHA256=f95SHA(art.Representation.Candidate)
 link.NewConsumerSHA256=f95SHA(art.Consumer.Candidate)
 link.NewTestEnvironmentSHA256=f95SHA(art.TestEnvironment.Candidate)
 return f,link,art
}

func TestF95ObservedRealGoSourceChangesCannotGrantScience(t *testing.T){
 f,link,art:=f95SourceFixture(t)
 audit,err:=AuditF95SourceBytes(f,F94FreezeDigest(f),link,art)
 if err!=nil{t.Fatal(err)}
 if !audit.SourceBytesMatchClaims||!audit.AllThreeGoASTShapesChanged||
  len(audit.StructuralClaims)!=3||audit.VerifiedExternalGitObjectCustody||
  audit.GeneratedCandidateScientificallyNovel||
  audit.RealProspectiveHoldoutQualified||
  audit.ScientificCausalGainAccepted||audit.DreamParetoPromotionAuthorized||
  audit.ThetaEvolveTrainingEnabled||audit.ScientificOriginalDispatchAuthorized||
  audit.AcceptedReferenceMutation{
  t.Fatalf("implementation source promoted as science: %+v",audit)
 }
 for _,r:=range audit.StructuralClaims{
  if !r.ASTShapeChanged||r.ParentGoASTSHA256==r.CandidateGoASTSHA256||
   !exactHex(r.CandidateSHA256,64)||!exactHex(r.ParentSHA256,64){
   t.Fatalf("not a verifiable implementation change: %+v",r)
  }
 }
}
func TestF95CompleteF94PopulationRecomputedBeforeSourceIntake(t *testing.T){
 f,p,e,h,links:=f94Base("Wingless")
 realFreeze,realLink,art:=f95SourceFixture(t)
 f.ParentRepresentationSHA256=realFreeze.ParentRepresentationSHA256
 f.ParentConsumerSHA256=realFreeze.ParentConsumerSHA256
 f.ParentTestEnvironmentSHA256=realFreeze.ParentTestEnvironmentSHA256
 links[0]=realLink
 links[1].NewTestEnvironmentSHA256=f.ParentTestEnvironmentSHA256
 links[2].NewRepresentationSHA256=f.ParentRepresentationSHA256
 links[3].NewConsumerSHA256=f.ParentConsumerSHA256
 good,err:=AuditF95LinkedGeneratorSource(f,F94FreezeDigest(f),p,e,h,links,0,art)
 if err!=nil||!good.AllThreeGoASTShapesChanged||
  good.VerifiedExternalGitObjectCustody||good.ScientificCausalGainAccepted{
  t.Fatalf("real generator linkage failed or claimed science %+v %v",good,err)
 }
 missing:=append([]F94ImplementationClaim(nil),links[:3]...)
 if _,err:=AuditF95LinkedGeneratorSource(f,F94FreezeDigest(f),p,e,h,missing,0,art);err==nil{
  t.Fatal("cherry-picked candidate population was accepted")
 }
 altered:=append([]F94ImplementationClaim(nil),links...)
 altered[0].GeneratorCandidateSHA256=strings.Repeat("0",64)
 if _,err:=AuditF95LinkedGeneratorSource(f,F94FreezeDigest(f),p,e,h,altered,0,art);err==nil{
  t.Fatal("candidate without actual generator lineage accepted")
 }
}
func TestF95HashOnlyAndCosmeticGoChangesDoNotQualify(t *testing.T){
 cases:=map[string]func(*F94Freeze,*F94ImplementationClaim,*F95ThreeSourceArtifacts){
  "manifest fabrication":func(_ *F94Freeze,l *F94ImplementationClaim,_ *F95ThreeSourceArtifacts){
   l.NewRepresentationSHA256=strings.Repeat("0",64)},
  "altered candidate without rehash":func(_ *F94Freeze,_ *F94ImplementationClaim,a *F95ThreeSourceArtifacts){
   a.Consumer.Candidate=append(append([]byte(nil),a.Consumer.Candidate...),[]byte("\n// forged\n")...)},
  "not a new source artifact":func(_ *F94Freeze,l *F94ImplementationClaim,a *F95ThreeSourceArtifacts){
   a.Representation.Candidate=append([]byte(nil),a.Representation.Parent...)
   l.NewRepresentationSHA256=f95SHA(a.Representation.Candidate)},
  "swapped semantic roles":func(_ *F94Freeze,l *F94ImplementationClaim,a *F95ThreeSourceArtifacts){
   a.Consumer.Candidate,a.Representation.Candidate=a.Representation.Candidate,a.Consumer.Candidate
   l.NewConsumerSHA256=f95SHA(a.Consumer.Candidate)
   l.NewRepresentationSHA256=f95SHA(a.Representation.Candidate)},
  "changed parent blob":func(_ *F94Freeze,_ *F94ImplementationClaim,a *F95ThreeSourceArtifacts){
   a.TestEnvironment.Parent=append(append([]byte(nil),a.TestEnvironment.Parent...),[]byte("\n")...)},
  "invalid Go syntax":func(_ *F94Freeze,l *F94ImplementationClaim,a *F95ThreeSourceArtifacts){
   a.Representation.Candidate=[]byte(strings.Repeat("not-a-go-file",20))
   l.NewRepresentationSHA256=f95SHA(a.Representation.Candidate)},
  "no test conditions":func(_ *F94Freeze,l *F94ImplementationClaim,a *F95ThreeSourceArtifacts){
   a.TestEnvironment.Candidate=a.Consumer.Candidate
   l.NewTestEnvironmentSHA256=f95SHA(a.TestEnvironment.Candidate)},
 }
 for name,mutate:=range cases{
  t.Run(name,func(t *testing.T){
   f1,l1,ar:=f95SourceFixture(t)
   mutate(&f1,&l1,&ar)
   if _,err:=AuditF95SourceBytes(f1,F94FreezeDigest(f1),l1,ar);err==nil{
    t.Fatalf("unqualified source substitution %s accepted",name)
   }
  })
 }
 // Comments, whitespace and renamed identifiers are deliberately ignored by
 // the AST shape fingerprint even though the SHA256 of the source changes.
 source:=[]byte("package test\n func BuildThing(a int)int{b:=a+1;return b}\n"+
  strings.Repeat("// enough input characters for syntax parser\n",6))
 renamed:=bytes.ReplaceAll(source,[]byte("BuildThing"),[]byte("RenamedXxx"))
 renamed=bytes.ReplaceAll(renamed,[]byte("b:=a+1"),[]byte("c:=a+1"))
 s1,_,_,e1:=f95GoASTSignature(source)
 s2,_,_,e2:=f95GoASTSignature(renamed)
 if e1!=nil||e2!=nil||s1!=s2||f95SHA(source)==f95SHA(renamed){
  t.Fatalf("cosmetic-only edits incorrectly counted as AST novelty %v %v",e1,e2)
 }
}
