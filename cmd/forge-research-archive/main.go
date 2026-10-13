// forge-research-archive verifies exact real original research ZIP bytes
// against immutable GitHub source/run/archive metadata. No scientific execution.
package main
import(
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"
 "strconv"

 "github.com/spoonman136668-ai/forge/researcharchive"
)
var ErrBlocked=errors.New("FORGE_RESEARCH_ARCHIVE_INPUT_BLOCKED")
func read(path string,max int64)([]byte,error){
 if !filepath.IsAbs(path){return nil,ErrBlocked}
 st,err:=os.Lstat(path)
 if err!=nil||!st.Mode().IsRegular()||st.Size()<=0||st.Size()>max{return nil,ErrBlocked}
 raw,err:=os.ReadFile(path)
 if err!=nil||int64(len(raw))!=st.Size(){return nil,ErrBlocked}
 return raw,nil
}
func run(args []string)(researcharchive.Report,error){
 var empty researcharchive.Report
 f:=flag.NewFlagSet("forge-research-archive",flag.ContinueOnError)
 manifestPath:=f.String("manifest","","absolute frozen artifact cohort manifest")
 evidenceDir:=f.String("evidence-dir","","absolute directory with independently fetched immutable archive files")
 if err:=f.Parse(args);err!=nil{return empty,err}
 if f.NArg()!=0||!filepath.IsAbs(*manifestPath)||!filepath.IsAbs(*evidenceDir){
  return empty,ErrBlocked
 }
 m,err:=read(*manifestPath,16384);if err!=nil{return empty,err}
 report,err:=researcharchive.Collect(m,func(e researcharchive.Entry)([]byte,[]byte,[]byte,error){
  prefix:=filepath.Join(*evidenceDir,strconv.FormatUint(e.RunID,10))
  r,err:=read(prefix+".run.json",2<<20);if err!=nil{return nil,nil,nil,err}
  a,err:=read(prefix+".artifact.json",2<<20);if err!=nil{return nil,nil,nil,err}
  z,err:=read(prefix+".zip",researcharchive.MaxZipBytes);if err!=nil{return nil,nil,nil,err}
  return r,a,z,nil
 })
 if err!=nil{return empty,ErrBlocked}
 return report,nil
}
func main(){
 report,err:=run(os.Args[1:])
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 if err=json.NewEncoder(os.Stdout).Encode(report);err!=nil{
  fmt.Fprintln(os.Stderr,err);os.Exit(1)
 }
}
