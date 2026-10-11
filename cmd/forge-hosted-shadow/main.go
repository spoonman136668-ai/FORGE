// forge-hosted-shadow runs source-pinned, bounded, NONSCIENTIFIC jobs
// across separate GitHub-hosted Actions jobs. No FSA or science dispatch.
package main
import (
 "bytes"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "runtime"

 "github.com/spoonman136668-ai/forge/hostedcompute"
)
var ErrIO=errors.New("FORGE_HOSTED_SHADOW_INPUT_OR_OUTPUT_BLOCKED")
func readJSON(path string,v any)error{
 if !filepath.IsAbs(path){return ErrIO}
 st,err:=os.Lstat(path)
 if err!=nil||!st.Mode().IsRegular()||st.Size()<1||st.Size()>32768{return ErrIO}
 b,err:=os.ReadFile(path);if err!=nil{return ErrIO}
 d:=json.NewDecoder(bytes.NewReader(b))
 d.DisallowUnknownFields()
 if err=d.Decode(v);err!=nil{return ErrIO}
 var extra any
 if d.Decode(&extra)!=io.EOF{return ErrIO}
 return nil
}
func saveOnce(path string,v any)error{
 if !filepath.IsAbs(path){return ErrIO}
 b,err:=json.MarshalIndent(v,"","  ")
 if err!=nil||len(b)>32768{return ErrIO}
 f,err:=os.OpenFile(path,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return ErrIO}
 if _,err=f.Write(append(b,'\n'));err!=nil{_ =f.Close();return ErrIO}
 if err=f.Sync();err!=nil{_ =f.Close();return ErrIO}
 return f.Close()
}
func execute(args []string)error{
 if len(args)==0{return ErrIO}
 switch args[0]{
 case "prepare":
  f:=flag.NewFlagSet("prepare",flag.ContinueOnError)
  source:=f.String("source","","immutable source Git SHA")
  tree:=f.String("tree","","immutable Git tree SHA")
  run:=f.String("run-id","","GitHub run ID")
  attempt:=f.Int("attempt",0,"GitHub run attempt")
  output:=f.String("output","","exclusive-create manifest")
  if f.Parse(args[1:])!=nil||f.NArg()!=0{return ErrIO}
  manifest,err:=hostedcompute.MakeManifest(*source,*tree,*run,*attempt)
  if err!=nil{return err}
  return saveOnce(*output,manifest)
 case "run":
  f:=flag.NewFlagSet("run",flag.ContinueOnError)
  source:=f.String("source","","checkout source SHA")
  tree:=f.String("tree","","checkout Git tree SHA")
  run:=f.String("run-id","","GitHub run ID")
  attempt:=f.Int("attempt",0,"GitHub run attempt")
  lane:=f.String("lane","","Wingless or Yggdrasil")
  worker:=f.String("worker","","declared lane and OS")
  input:=f.String("manifest","","manifest path")
  output:=f.String("output","","exclusive-create receipt")
  if f.Parse(args[1:])!=nil||f.NArg()!=0{return ErrIO}
  var manifest hostedcompute.Manifest
  if err:=readJSON(*input,&manifest);err!=nil{return err}
  receipt,err:=hostedcompute.RunShadow(manifest,*source,*tree,*run,*attempt,*lane,runtime.GOOS,*worker)
  if err!=nil{return err}
  if err=hostedcompute.VerifyReceipt(manifest,receipt);err!=nil{return err}
  return saveOnce(*output,receipt)
 case "reconcile":
  f:=flag.NewFlagSet("reconcile",flag.ContinueOnError)
  input:=f.String("manifest","","manifest path")
  directory:=f.String("receipts","","four receipts directory")
  output:=f.String("output","","exclusive-create summary")
  if f.Parse(args[1:])!=nil||f.NArg()!=0{return ErrIO}
  if !filepath.IsAbs(*directory){return ErrIO}
  var manifest hostedcompute.Manifest
  if err:=readJSON(*input,&manifest);err!=nil{return err}
  receipts:=make([]hostedcompute.Receipt,0,4)
  for _,name:=range []string{"Wingless-linux","Wingless-windows","Yggdrasil-linux","Yggdrasil-windows"}{
   var r hostedcompute.Receipt
   if err:=readJSON(filepath.Join(*directory,name+".json"),&r);err!=nil{return err}
   receipts=append(receipts,r)
  }
  summary,err:=hostedcompute.Reconcile(manifest,receipts)
  if err!=nil{return err}
  if err=saveOnce(*output,summary);err!=nil{return err}
  fmt.Printf("FORGE_R8_HOSTED_SHADOW_RECONCILED=PASS jobs=%d original_science=%d FSA=false dispatch=false durable_custody=false\n",summary.AcceptedShadowJobs,summary.OriginalExperimentsConsumed)
  return nil
 default:return ErrIO
 }
}
func main(){
 if err:=execute(os.Args[1:]);err!=nil{
  fmt.Fprintln(os.Stderr,"FORGE_HOSTED_SHADOW_FAIL_CLOSED")
  os.Exit(2)
 }
}
