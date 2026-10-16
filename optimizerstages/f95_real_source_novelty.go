package optimizerstages

import (
 "crypto/sha256"
 "encoding/hex"
 "errors"
 "fmt"
 "go/ast"
 "go/parser"
 "go/token"
 "strings"

 "github.com/spoonman136668-ai/forge/genenv"
 "github.com/spoonman136668-ai/forge/promptlineage"
)

const F95SourceSchema="forge.optimizer.f95.real-go-source-structural-observation.v1"
var ErrF95=errors.New("FORGE_F95_REAL_SOURCE_AND_STRUCTURAL_IMPLEMENTATION_NOT_VERIFIED")

type F95ArtifactBytes struct {
 Parent []byte
 Candidate []byte
}
// A caller must obtain these bytes from a real immutable repository tree.
// Passing matching in-memory bytes alone cannot prove authentic Git origin.
type F95ThreeSourceArtifacts struct{
 Representation F95ArtifactBytes
 Consumer F95ArtifactBytes
 TestEnvironment F95ArtifactBytes
}
type F95SourceChange struct{
 Role string `json:"role"`
 ParentSHA256 string `json:"parent_sha256"`
 CandidateSHA256 string `json:"candidate_sha256"`
 ParentGoASTSHA256 string `json:"parent_go_ast_sha256"`
 CandidateGoASTSHA256 string `json:"candidate_go_ast_sha256"`
 ASTShapeChanged bool `json:"ast_shape_changed"`
}
type F95SourceReview struct{
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 Generator string `json:"generator"`
 GeneratorCandidateSHA256 string `json:"generator_candidate_sha256"`
 FrozenScreenSHA256 string `json:"frozen_screen_sha256"`
 StructuralClaims []F95SourceChange `json:"structural_claims"`
 SourceBytesMatchClaims bool `json:"source_bytes_match_claims"`
 AllThreeGoASTShapesChanged bool `json:"all_three_go_ast_shapes_changed"`
 VerifiedExternalGitObjectCustody bool `json:"verified_external_git_object_custody"`
 GeneratedCandidateScientificallyNovel bool `json:"generated_candidate_scientifically_novel"`
 RealProspectiveHoldoutQualified bool `json:"real_prospective_holdout_qualified"`
 ScientificCausalGainAccepted bool `json:"scientific_causal_gain_accepted"`
 DreamParetoPromotionAuthorized bool `json:"dream_pareto_promotion_authorized"`
 ThetaEvolveTrainingEnabled bool `json:"theta_evolve_training_enabled"`
 ScientificOriginalDispatchAuthorized bool `json:"scientific_original_dispatch_authorized"`
 AcceptedReferenceMutation bool `json:"accepted_reference_mutation"`
 Status string `json:"status"`
}
func f95SHA(data []byte)string{
 h:=sha256.Sum256(data)
 return hex.EncodeToString(h[:])
}
func f95GoASTSignature(source []byte)(string,int,int,error){
 if len(source)<160||len(source)>100000{return "",0,0,ErrF95}
 file,err:=parser.ParseFile(token.NewFileSet(),"candidate.go",source,parser.AllErrors)
 if err!=nil{return "",0,0,ErrF95}
 var stream strings.Builder
 functions:=0;tests:=0;count:=0
 ast.Inspect(file,func(node ast.Node)bool{
  if node==nil{return true}
  count++
  if count>20000{return false}
  switch x:=node.(type){
  case *ast.FuncDecl:
   functions++
   if strings.HasPrefix(x.Name.Name,"TestF95"){tests++}
  case *ast.BasicLit:
   // Literal values alone do not prove structural novelty.
   stream.WriteString("BasicLit:");stream.WriteString(x.Kind.String())
  case *ast.Ident:
   stream.WriteString("Ident")
  case *ast.BinaryExpr:
   stream.WriteString("BinaryExpr:");stream.WriteString(x.Op.String())
  case *ast.UnaryExpr:
   stream.WriteString("UnaryExpr:");stream.WriteString(x.Op.String())
  case *ast.AssignStmt:
   stream.WriteString("AssignStmt:");stream.WriteString(x.Tok.String())
  case *ast.GenDecl:
   stream.WriteString("GenDecl:");stream.WriteString(x.Tok.String())
  case *ast.BranchStmt:
   stream.WriteString("BranchStmt:");stream.WriteString(x.Tok.String())
  default:
   stream.WriteString(fmt.Sprintf("%T",node))
  }
  stream.WriteByte('\n')
  return true
 })
 if count>20000||functions<1{return "",0,0,ErrF95}
 return f95SHA([]byte(stream.String())),functions,tests,nil
}
// F95 specifically binds this candidate to the actual compiled
// representation, consumer and novel test-condition entrypoints. The generic
// AST fingerprint alone would otherwise accept swapped roles or meaningless
// new filenames containing identical code shapes.
func f95RoleEntrypoints(role string,source []byte)bool{
 file,err:=parser.ParseFile(token.NewFileSet(),"candidate.go",source,parser.AllErrors)
 if err!=nil||file.Name.Name!="noveltymechanisms"{return false}
 needed:=map[string][]string{
  "representation":{"Compile","RelationCount"},
  "consumer":{"Resolve","Verify"},
  "test_environment":{"TestF95NovelRelationshipComposition",
   "TestF95HoldoutStyleRoleSwapAndDistractors","TestF95AmbiguityNoFalsePositive"},
 }[role]
 if len(needed)==0{return false}
 seen:=map[string]bool{}
 for _,decl:=range file.Decls{
  if f,ok:=decl.(*ast.FuncDecl);ok{
   seen[f.Name.Name]=true
  }
 }
 for _,name:=range needed{if !seen[name]{return false}}
 return true
}
// AuditF95SourceBytes rejects fabricated F94 artifact hash assertions by
// comparing claims with actual Go source bytes and Go AST shapes.
// A valid record DOES NOT establish independent git provenance, scientific
// novelty, correctness or true first-use. The CI CLI separately pins real
// Git objects and runs an independent regression.
func AuditF95SourceBytes(f F94Freeze,sourcePin string,
 claim F94ImplementationClaim,artifacts F95ThreeSourceArtifacts)(F95SourceReview,error){
 var zero F95SourceReview
 if !f94FreezeValid(f)||F94FreezeDigest(f)!=sourcePin||
  !exactHex(sourcePin,64)||!exactHex(claim.GeneratorCandidateSHA256,64)||
  (claim.Generator!="Promptbreeder"&&claim.Generator!="DGM/GenEnv"){
  return zero,ErrF95
 }
 changes,ok:=f94Changed(f,claim)
 if !ok||len(changes)!=3{return zero,ErrF95}
 roles:=[]struct{role,oldSHA,newSHA string;files F95ArtifactBytes}{
  {"representation",f.ParentRepresentationSHA256,claim.NewRepresentationSHA256,artifacts.Representation},
  {"consumer",f.ParentConsumerSHA256,claim.NewConsumerSHA256,artifacts.Consumer},
  {"test_environment",f.ParentTestEnvironmentSHA256,claim.NewTestEnvironmentSHA256,artifacts.TestEnvironment},
 }
 out:=F95SourceReview{Schema:F95SourceSchema,Lane:f.Lane,
  Generator:claim.Generator,GeneratorCandidateSHA256:claim.GeneratorCandidateSHA256,
  FrozenScreenSHA256:sourcePin,
  StructuralClaims:make([]F95SourceChange,0,3),
  Status:"ACTUAL_GO_SOURCE_SHAPES_CHANGED_ONLY_NO_INDEPENDENT_SCIENCE_ACCEPTANCE"}
 used:=map[string]bool{}
 for _,r:=range roles{
  if f95SHA(r.files.Parent)!=r.oldSHA||f95SHA(r.files.Candidate)!=r.newSHA||
   r.oldSHA==r.newSHA||used[r.newSHA]{return zero,ErrF95}
  used[r.newSHA]=true
  parentShape,_,_,err:=f95GoASTSignature(r.files.Parent)
  if err!=nil{return zero,ErrF95}
  childShape,fn,testFn,err:=f95GoASTSignature(r.files.Candidate)
  if err!=nil||parentShape==childShape||fn<2||!f95RoleEntrypoints(r.role,r.files.Candidate){return zero,ErrF95}
  if r.role=="test_environment"&&testFn<3{return zero,ErrF95}
  out.StructuralClaims=append(out.StructuralClaims,F95SourceChange{
   Role:r.role,ParentSHA256:r.oldSHA,CandidateSHA256:r.newSHA,
   ParentGoASTSHA256:parentShape,CandidateGoASTSHA256:childShape,
   ASTShapeChanged:true})
 }
 out.SourceBytesMatchClaims=true
 out.AllThreeGoASTShapesChanged=true
 return out,nil
}

// AuditF95LinkedGeneratorSource ALSO recomputes the complete F94 frozen
// candidate population. No caller-picked subset can masquerade as a real
// generated lineage. The selected candidate's actual implementation is
// checked against the real source bytes, but independent scientific novelty
// and prospective source custody still remain unqualified.
func AuditF95LinkedGeneratorSource(f F94Freeze,sourcePin string,
 pf promptlineage.Frozen,ef genenv.Frozen,h genenv.History,
 links []F94ImplementationClaim,selected int,
 artifacts F95ThreeSourceArtifacts)(F95SourceReview,error){
 var zero F95SourceReview
 review,err:=ScreenF94(f,sourcePin,pf,ef,h,links)
 if err!=nil||selected<0||selected>=len(links)||
  selected>=len(review.CandidateScreens)||selected>=len(review.StageProposals){
  return zero,ErrF95
 }
 chosen:=links[selected]
 if review.CandidateScreens[selected].Generator!=chosen.Generator||
  review.CandidateScreens[selected].GeneratorCandidateSHA256!=chosen.GeneratorCandidateSHA256||
  review.StageProposals[selected].CandidateSHA256!=review.CandidateScreens[selected].ProposedMechanismSHA256{
  return zero,ErrF95
 }
 return AuditF95SourceBytes(f,sourcePin,chosen,artifacts)
}
