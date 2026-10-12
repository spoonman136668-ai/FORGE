package watchdog

import (
 "bytes"
 "encoding/json"
 "errors"
 "io"
 "os"
 "path/filepath"
)

// ImportIncidentChain verifies a complete, canonical, immutable shadow
// incident history. Unknown JSON fields, trailing bytes and changed hashes
// fail closed. This is evidence intake, NEVER authority or work dispatch.
func ImportIncidentChain(directory string)([]DurableIncident,string,error){
 if directory==""||!filepath.IsAbs(directory){return nil,"",ErrPersistentLedger}
 path:=filepath.Join(directory,"shadow-chain.v1.json")
 f,err:=os.Open(path)
 if err!=nil{return nil,"",errors.Join(ErrPersistentLedger,err)}
 defer f.Close()
 st,err:=f.Stat()
 if err!=nil||!st.Mode().IsRegular()||st.Size()<3||st.Size()>16<<20{return nil,"",ErrPersistentLedger}
 raw,err:=io.ReadAll(io.LimitReader(f,(16<<20)+1))
 if err!=nil||len(raw)>16<<20{return nil,"",ErrPersistentLedger}
 var chain []DurableIncident
 decoder:=json.NewDecoder(bytes.NewReader(raw))
 decoder.DisallowUnknownFields()
 if err:=decoder.Decode(&chain);err!=nil{return nil,"",ErrPersistentLedger}
 var trailing any
 if err:=decoder.Decode(&trailing);!errors.Is(err,io.EOF){return nil,"",ErrPersistentLedger}
 if chain==nil{return nil,"",ErrPersistentLedger}
 canonical,err:=json.Marshal(chain)
 if err!=nil||!bytes.Equal(raw,append(canonical,'\n')){return nil,"",ErrPersistentLedger}
 seen:=map[string]bool{}
 for _,entry:=range chain{
  key:=IncidentKey(entry.Incident)
  if seen[key]{return nil,"",ErrPersistentLedger}
  seen[key]=true
 }
 head,err:=VerifyIncidentChain(chain)
 if err!=nil{return nil,"",err}
 return chain,head,nil
}
