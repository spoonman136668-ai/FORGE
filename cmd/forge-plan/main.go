// Command forge-plan inspects a frozen portfolio. It never schedules,
// executes, promotes, opens a network connection or writes a CKB database.
package main

import (
 "bytes"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"

 "github.com/spoonman136668-ai/forge/planner"
)

func run(args []string,output io.Writer)error {
 flags:=flag.NewFlagSet("forge-plan",flag.ContinueOnError)
 file:=flags.String("frozen","","exact canonical frozen portfolio JSON file")
 pin:=flags.String("pin","","independently pinned canonical frozen portfolio SHA-256")
 if err:=flags.Parse(args);err!=nil{return err}
 if flags.NArg()!=0||*file==""||*pin==""{return errors.New("FORGE_REQUIRES_FROZEN_FILE_AND_INDEPENDENT_SHA256")}
 f,err:=os.Open(*file);if err!=nil{return err};defer f.Close()
 raw,err:=io.ReadAll(io.LimitReader(f,1024*1024+1));if err!=nil{return err}
 if len(raw)==0||len(raw)>1024*1024{return errors.New("FORGE_INPUT_SIZE_LIMIT")}
 var frozen planner.FrozenPortfolio
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if err:=d.Decode(&frozen);err!=nil{return err}
 var trailing any
 if err:=d.Decode(&trailing);err!=io.EOF{return errors.New("FORGE_JSON_TRAILING_OR_DUPLICATE_STRUCTURE")}
 canonical,err:=json.Marshal(frozen);if err!=nil{return err}
 if !bytes.Equal(bytes.TrimSpace(raw),canonical){return errors.New("FORGE_REJECT_NONCANONICAL_JSON_OR_DUPLICATE_KEYS")}
 result,err:=planner.Build(frozen,*pin);if err!=nil{return err}
 out,err:=json.Marshal(result);if err!=nil{return err}
 _,err=fmt.Fprintln(output,string(out));return err
}
func main(){if e:=run(os.Args[1:],os.Stdout);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}}
