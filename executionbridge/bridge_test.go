package executionbridge
import(
 "context"
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/shadowoutbox"
)
type witness struct{approved bool}
func(w witness)VerifyAuthority(context.Context,AuthorityProof)(bool,error){return w.approved,nil}
func(w witness)VerifyWorker(context.Context,WorkerProof)(bool,error){return w.approved,nil}
func permit()ExecutionPermit{return ExecutionPermit{
 Candidate:shadowoutbox.Entry{Schema:shadowoutbox.Schema,Lane:"Wingless",OriginalID:"existing",RequiresRequalification:true},
 Authority:AuthorityProof{Owner:"future-forge",Epoch:17,CutoverAuthorized:true,OldOwnerRevoked:true,IndependentlyAuthenticated:true},
 Worker:WorkerProof{WorkerID:"old-existing-worker",EnforcesEpoch:17,BinarySHA256:strings.Repeat("a",64),IndependentlyAuthenticated:true},
}}
func TestExecutionBoundaryDenyByDefault(t *testing.T){
 p:=permit()
 if _,err:=Admit(context.Background(),witness{approved:false},p);err==nil{t.Fatal("untrusted witness accepted")}
 if _,err:=Admit(context.Background(),witness{approved:true},p);err!=nil{t.Fatal(err)}
 p.Authority.OldOwnerRevoked=false
 if _,err:=Admit(context.Background(),witness{approved:true},p);err==nil{t.Fatal("overlapping controllers accepted")}
 p=permit();p.Worker.EnforcesEpoch=16
 if _,err:=Admit(context.Background(),witness{approved:true},p);err==nil{t.Fatal("stale worker epoch accepted")}
 p=permit();p.Candidate.FirstUseRisk=true
 if _,err:=Admit(context.Background(),witness{approved:true},p);err==nil{t.Fatal("consumed first-use accepted")}
}
