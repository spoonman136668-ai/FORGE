// forge-retention-verify verifies externally pinned trust, signed receipts
// and physically recovered bytes. Offline only; no automatic backup or promotion.
package main
import (
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "path/filepath"
 "time"
 "github.com/spoonman136668-ai/forge/retentiongate"
)
func main(){
 f:=flag.NewFlagSet("forge-retention-verify",flag.ExitOnError)
 anchor:=f.String("external-trust","","independently controlled public-key anchor file")
 receipt:=f.String("receipt","","dual-signed external custody receipt")
 original:=f.String("original","","original GitHub downloaded byte archive")
 recovered:=f.String("restored","","separately restored offline backup bytes")
 date:=f.String("as-of","","YYYY-MM-DD qualification observation date")
 if err:=f.Parse(os.Args[1:]);err!=nil||f.NArg()!=0{fmt.Fprintln(os.Stderr,retentiongate.ErrBlocked);os.Exit(2)}
 read:=func(name string,cap int64)([]byte,error){
  if !filepath.IsAbs(name){return nil,retentiongate.ErrBlocked}
  st,err:=os.Lstat(name);if err!=nil||!st.Mode().IsRegular()||st.Size()<1||st.Size()>cap{return nil,retentiongate.ErrBlocked}
  return os.ReadFile(name)
 }
 t,err:=read(*anchor,4096);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 r,err:=read(*receipt,4096);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 o,err:=read(*original,8<<20);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 b,err:=read(*recovered,8<<20);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 asOf,err:=time.Parse("2006-01-02",*date);if err!=nil{fmt.Fprintln(os.Stderr,retentiongate.ErrBlocked);os.Exit(2)}
 report,err:=retentiongate.Verify(t,r,o,b,asOf)
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 if err=json.NewEncoder(os.Stdout).Encode(report);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
}
