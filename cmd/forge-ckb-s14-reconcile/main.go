// forge-ckb-s14-reconcile executes a READ-ONLY two-source reconciliation
// of original CKB S14 first-use without a scientific launch or replay.
package main
import(
 "bytes"
 "context"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "time"

 "github.com/spoonman136668-ai/forge/ckbhistory"
 "github.com/spoonman136668-ai/forge/ckbreconcile"
)
const pinsSchema="forge.ckb.pinned-firstuse-hashes.v1"
type pinsFile struct{
 Schema string `json:"schema"`
 SHA256 map[string]string `json:"sha256"`
}
func readPins(path string)(map[string]string,error){
 if path==""||!filepath.IsAbs(path){return nil,ckbreconcile.ErrBlocked}
 info,err:=os.Lstat(path)
 if err!=nil||!info.Mode().IsRegular()||info.Size()<=0||info.Size()>4096{return nil,ckbreconcile.ErrBlocked}
 raw,err:=os.ReadFile(path)
 if err!=nil||len(raw)>4096{return nil,ckbreconcile.ErrBlocked}
 dec:=json.NewDecoder(bytes.NewReader(raw));dec.DisallowUnknownFields()
 var p pinsFile
 if err:=dec.Decode(&p);err!=nil||p.Schema!=pinsSchema||len(p.SHA256)!=6{
  return nil,ckbreconcile.ErrBlocked
 }
 var extra any
 if !errors.Is(dec.Decode(&extra),io.EOF){return nil,ckbreconcile.ErrBlocked}
 normalized,err:=json.Marshal(p)
 if err!=nil||!bytes.Equal(raw,append(normalized,'\n')){return nil,ckbreconcile.ErrBlocked}
 return p.SHA256,nil
}
func run(ctx context.Context,args []string,out io.Writer,token string)error{
 flags:=flag.NewFlagSet("forge-ckb-s14-reconcile",flag.ContinueOnError)
 flags.SetOutput(io.Discard)
 state:=flags.String("state","","absolute existing CKB private research state path")
 pinPath:=flags.String("pinned","","absolute path to independently witnessed six-gen SHA256 hashes")
 if err:=flags.Parse(args);err!=nil||flags.NArg()!=0{return ckbreconcile.ErrBlocked}
 pins,err:=readPins(*pinPath)
 if err!=nil{return err}
 client,err:=ckbhistory.New(token)
 if err!=nil{return err}
 report,err:=ckbreconcile.ReconcileWake(ctx,client,*state,pins)
 if err!=nil{return err}
 return json.NewEncoder(out).Encode(report)
}
func main(){
 ctx,cancel:=context.WithTimeout(context.Background(),60*time.Second)
 defer cancel()
 if err:=run(ctx,os.Args[1:],os.Stdout,os.Getenv("GH_TOKEN"));err!=nil{
  fmt.Fprintln(os.Stderr,"FORGE_CKB_S14_DUAL_SOURCE_RECONCILIATION_BLOCKED_NO_RETRY")
  os.Exit(1)
 }
}
