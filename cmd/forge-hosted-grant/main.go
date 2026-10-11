// forge-hosted-grant checks an independently signed and pinned FSA
// authorization against exact GitHub Actions context. It NEVER dispatches.
package main

import (
 "bytes"
 "encoding/json"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/dreamrsi/fsagate"
 "github.com/spoonman136668-ai/forge/hostedgrant"
)

func readFile(path string,target any)error{
 if !filepath.IsAbs(path){return hostedgrant.ErrDenied}
 stat,err:=os.Lstat(path)
 if err!=nil||!stat.Mode().IsRegular()||stat.Size()<1||stat.Size()>16384{
  return hostedgrant.ErrDenied
 }
 raw,err:=os.ReadFile(path);if err!=nil{return hostedgrant.ErrDenied}
 decoder:=json.NewDecoder(bytes.NewReader(raw));decoder.DisallowUnknownFields()
 if decoder.Decode(target)!=nil{return hostedgrant.ErrDenied}
 var trailing any
 if decoder.Decode(&trailing)!=io.EOF{return hostedgrant.ErrDenied}
 return nil
}
func run(args []string)error{
 f:=flag.NewFlagSet("verify",flag.ContinueOnError)
 grant:=f.String("grant","","independently signed FSA grant input")
 scope:=f.String("scope","","independently frozen FSA scope input")
 proof:=f.String("proof","","independently confirmed FSA first-use proof")
 grantHash:=f.String("grant-sha","","external grant digest")
 grantKey:=f.String("grant-public-key","","externally pinned FSA grant key")
 headKey:=f.String("head-public-key","","independent FSA checkpoint key")
 output:=f.String("output","","new review-only output file")
 if f.Parse(args)!=nil||f.NArg()!=0{return hostedgrant.ErrDenied}
 var e hostedgrant.Envelope
 if err:=readFile(*grant,&e);err!=nil{return err}
 var s fsagate.Scope
 if err:=readFile(*scope,&s);err!=nil{return err}
 var p fsagate.FirstUseProof
 if err:=readFile(*proof,&p);err!=nil{return err}
 ctx:=hostedgrant.Context{
  Repository:os.Getenv("GITHUB_REPOSITORY"),
  Workflow:os.Getenv("FORGE_FSA_WORKFLOW"),
  RunID:os.Getenv("GITHUB_RUN_ID"),
  SourceSHA:os.Getenv("GITHUB_SHA"),
  TreeSHA:os.Getenv("FORGE_SOURCE_TREE"),
  Lane:os.Getenv("FORGE_SCIENCE_LANE"),
 }
 attempt:=os.Getenv("GITHUB_RUN_ATTEMPT")
 if attempt=="1"{ctx.Attempt=1}
 review,err:=hostedgrant.ReviewGrant(e,hostedgrant.Pin{
  GrantSHA256:*grantHash,GrantKeyHex:*grantKey,
  IndependentFSAHeadKeyHex:*headKey},ctx,s,p)
 if err!=nil{return err}
 // A positive review is still NOT execution permission. FSA must
 // independently consume a separate atomic dispatch lease.
 if !filepath.IsAbs(*output){return hostedgrant.ErrDenied}
 raw,err:=json.MarshalIndent(review,"","  ")
 if err!=nil{return hostedgrant.ErrDenied}
 file,err:=os.OpenFile(*output,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return hostedgrant.ErrDenied}
 if _,err=file.Write(append(raw,'\n'));err!=nil{_ =file.Close();return hostedgrant.ErrDenied}
 if file.Sync()!=nil{_ =file.Close();return hostedgrant.ErrDenied}
 if file.Close()!=nil{return hostedgrant.ErrDenied}
 fmt.Println("FORGE_HOSTED_GRANT_CRYPTOGRAPHIC_REVIEW=PASS science_not_executed=true first_use_lock_not_acquired=true")
 return nil
}
func main(){
 if err:=run(os.Args[1:]);err!=nil{
  fmt.Fprintln(os.Stderr,"FORGE_HOSTED_ORIGINAL=DENIED_NO_INDEPENDENT_FSA_DISPATCH")
  os.Exit(2)
 }
}
