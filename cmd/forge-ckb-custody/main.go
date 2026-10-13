// forge-ckb-custody is a READ-ONLY inspector of original CKB-plane
// S09-S14 first-use ledgers. It never grants or retries original research.
package main
import(
 "bytes"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/ckbcustody"
)
const PinsSchema="forge.ckb.pinned-firstuse-hashes.v1"
type pinsDocument struct{
 Schema string `json:"schema"`
 SHA256 map[string]string `json:"sha256"`
}
type output struct{
 Mode string `json:"mode"`
 PinnedHashesMatch bool `json:"pinned_hashes_match"`
 Snapshot ckbcustody.Snapshot `json:"snapshot"`
}
func readPins(path string)(map[string]string,error){
 if path==""||!filepath.IsAbs(path){return nil,ckbcustody.ErrUnsafe}
 st,err:=os.Lstat(path)
 if err!=nil||!st.Mode().IsRegular()||st.Size()<=0||st.Size()>4096{return nil,ckbcustody.ErrUnsafe}
 raw,err:=os.ReadFile(path)
 if err!=nil||len(raw)>4096{return nil,ckbcustody.ErrUnsafe}
 decoder:=json.NewDecoder(bytes.NewReader(raw));decoder.DisallowUnknownFields()
 var p pinsDocument
 if err=decoder.Decode(&p);err!=nil||p.Schema!=PinsSchema{return nil,ckbcustody.ErrUnsafe}
 var trailing any
 if !errors.Is(decoder.Decode(&trailing),io.EOF){return nil,ckbcustody.ErrUnsafe}
 canonical,err:=json.Marshal(p)
 if err!=nil||!bytes.Equal(raw,append(canonical,'\n'))||len(p.SHA256)<5||len(p.SHA256)>6{return nil,ckbcustody.ErrUnsafe}
 return p.SHA256,nil
}
func run(args []string,out io.Writer)error{
 f:=flag.NewFlagSet("forge-ckb-custody",flag.ContinueOnError);f.SetOutput(io.Discard)
 state:=f.String("state","","absolute path to installed existing CKB research state")
 pinsPath:=f.String("pinned","","absolute external authenticated SHA256 pins file")
 if err:=f.Parse(args);err!=nil||f.NArg()!=0{return ckbcustody.ErrUnsafe}
 pins,err:=readPins(*pinsPath);if err!=nil{return err}
 s,err:=ckbcustody.Inspect(*state);if err!=nil{return err}
 if err:=ckbcustody.VerifyPins(s,pins);err!=nil{return err}
 return json.NewEncoder(out).Encode(output{
  Mode:"READ_ONLY_PIN_MATCH_NOT_AUTHORITY",
  PinnedHashesMatch:true,
  Snapshot:s,
 })
}
func main(){
 if err:=run(os.Args[1:],os.Stdout);err!=nil{
  fmt.Fprintln(os.Stderr,"FORGE_CKB_CUSTODY_IMPORT_BLOCKED_NO_REPLAY")
  os.Exit(1)
 }
}
