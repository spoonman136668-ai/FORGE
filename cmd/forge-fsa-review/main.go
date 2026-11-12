// forge-fsa-review reads an already-collected native GitHub snapshot.
// It does not perform network calls, mutations, or source merges.
package main

import (
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/fsamergeattest"
)

func verify(path string, out io.Writer) error {
 if !filepath.IsAbs(path) {return errors.New("ABSOLUTE_SNAPSHOT_REQUIRED")}
 info,err:=os.Lstat(path)
 if err!=nil{return err}
 if !info.Mode().IsRegular() || info.Size()==0 || info.Size()>2<<20 {
  return errors.New("INVALID_SNAPSHOT_FILE")
 }
 f,err:=os.Open(path)
 if err!=nil{return err}
 defer f.Close()
 dec:=json.NewDecoder(io.LimitReader(f,(2<<20)+1))
 dec.DisallowUnknownFields()
 var snapshot fsamergeattest.Snapshot
 if err:=dec.Decode(&snapshot);err!=nil{return err}
 var additional any
 if err:=dec.Decode(&additional);err!=io.EOF{return errors.New("TRAILING_JSON")}
 result:=fsamergeattest.Check(snapshot)
 if result.MergeAuthorized{return errors.New("UNEXPECTED_MERGE_AUTHORITY")}
 raw,err:=json.Marshal(result)
 if err!=nil{return err}
 _,err=fmt.Fprintln(out,string(raw))
 return err
}

func main(){
 f:=flag.NewFlagSet("forge-fsa-review",flag.ExitOnError)
 path:=f.String("snapshot","","absolute read-only GitHub evidence file")
 f.Parse(os.Args[1:])
 if *path==""||f.NArg()!=0 {fmt.Fprintln(os.Stderr,"SNAPSHOT_REQUIRED");os.Exit(2)}
 if err:=verify(*path,os.Stdout);err!=nil {
  fmt.Fprintln(os.Stderr,"SOURCE_REVIEW_NOT_QUALIFIED:",err)
  os.Exit(1)
 }
}
