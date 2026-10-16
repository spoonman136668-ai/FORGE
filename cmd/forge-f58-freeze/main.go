// forge-f58-freeze publishes the concrete *current* four control-policy
// identities per research lane before any new prospective owner decision.
// A generated JSON/hash is NOT external policy custody or real randomization.
package main

import (
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "github.com/spoonman136668-ai/forge/optimizerbridge"
)
func write(path string,v interface{})error {
 data,err:=json.MarshalIndent(v,"","  ")
 if err!=nil{return err}
 data=append(data,'\n')
 return os.WriteFile(path,data,0644)
}
func main(){
 f:=flag.String("frozen","", "output frozen control-policy identities JSON")
 r:=flag.String("readiness","", "output non-promoting prospective eligibility JSON")
 flag.Parse()
 if *f==""||*r==""||*f==*r{fmt.Fprintln(os.Stderr,"separate frozen and readiness output files are required");os.Exit(2)}
 frozen,err:=optimizerbridge.FreezeF58()
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 readiness,err:=optimizerbridge.ReadinessF58(frozen)
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 if err:=write(*f,frozen);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 if err:=write(*r,readiness);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
}
