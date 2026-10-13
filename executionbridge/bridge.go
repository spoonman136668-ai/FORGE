// Package executionbridge stages recovery actions behind an independently
// authenticated authority fence. This is a non-executing qualification seam.
package executionbridge
import (
 "context"
 "errors"
 "github.com/spoonman136668-ai/forge/shadowoutbox"
)
var ErrBlocked=errors.New("FORGE_EXECUTION_BRIDGE_BLOCKED")
type AuthorityProof struct{
 Owner string
 Epoch uint64
 CutoverAuthorized bool
 OldOwnerRevoked bool
 IndependentlyAuthenticated bool
}
type WorkerProof struct{
 WorkerID string
 EnforcesEpoch uint64
 BinarySHA256 string
 IndependentlyAuthenticated bool
}
type ExecutionPermit struct{
 Candidate shadowoutbox.Entry
 Authority AuthorityProof
 Worker WorkerProof
}
type Witness interface{
 VerifyAuthority(context.Context,AuthorityProof)(bool,error)
 VerifyWorker(context.Context,WorkerProof)(bool,error)
}
// Admit verifies all conditions and returns a non-executing permit. A permit
// cannot itself start a scientific original. No execute method is exposed.
func validDigest(s string)bool{if len(s)!=64{return false};for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}};return true}
func Admit(ctx context.Context,w Witness,p ExecutionPermit)(ExecutionPermit,error){
 if ctx==nil||ctx.Err()!=nil||w==nil||!p.Authority.CutoverAuthorized||
 !p.Authority.OldOwnerRevoked||!p.Authority.IndependentlyAuthenticated||
 p.Authority.Owner==""||p.Authority.Epoch==0||
 !p.Worker.IndependentlyAuthenticated||p.Worker.WorkerID==""||
 p.Worker.EnforcesEpoch!=p.Authority.Epoch||
 p.Candidate.Schema!=shadowoutbox.Schema||
 (p.Candidate.Lane!="Wingless"&&p.Candidate.Lane!="Yggdrasil")||
 p.Candidate.OriginalID==""||p.Candidate.Scope==""||
 !validDigest(p.Candidate.IncidentSHA256)||!validDigest(p.Candidate.RecoveryManifestSHA256)||
 p.Candidate.FirstUseRisk||
 !p.Candidate.RequiresRequalification{return ExecutionPermit{},ErrBlocked}
 if len(p.Worker.BinarySHA256)!=64{return ExecutionPermit{},ErrBlocked}
 for _,c:=range p.Worker.BinarySHA256{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return ExecutionPermit{},ErrBlocked}}
 a,err:=w.VerifyAuthority(ctx,p.Authority);if err!=nil||!a{return ExecutionPermit{},ErrBlocked}
 b,err:=w.VerifyWorker(ctx,p.Worker);if err!=nil||!b{return ExecutionPermit{},ErrBlocked}
 return p,nil
}
