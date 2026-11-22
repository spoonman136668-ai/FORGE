package main

import (
 "bytes"
 "encoding/json"
 "errors"
 "io"
 "os"
 "path/filepath"
 "strings"
 "testing"
)

// Captures the source-authenticated pre-R13 decoder behavior in a test only.
// It is never used for production parsing or used as acceptance authority.
func r13LegacyDecoder(in io.Reader,target any)error{
 dec:=json.NewDecoder(io.LimitReader(in,65537))
 dec.DisallowUnknownFields()
 if err:=dec.Decode(target);err!=nil{return err}
 var extra any
 if !errors.Is(dec.Decode(&extra),io.EOF){return errors.New("trailing witness input rejected")}
 return nil
}

func TestR13OriginalDecoderSilentlyAcceptsTruncatedTail(t *testing.T){
 prefix:=append([]byte("{}"),bytes.Repeat([]byte(" "),65535)...)
 if len(prefix)!=65537{t.Fatal(len(prefix))}
 input:=append(prefix,[]byte("{}\n")...)
 var legacy map[string]any
 if err:=r13LegacyDecoder(bytes.NewReader(input),&legacy);err!=nil{
  t.Fatalf("legacy negative mechanism not reproduced: %v",err)
 }
 var target=map[string]any{"unchanged":true}
 if err:=decodeBoundedWitness(bytes.NewReader(input),&target);err==nil{
  t.Fatal("source candidate accepted truncated tail")
 }
 if len(target)!=1||target["unchanged"]!=true{t.Fatal("oversized reader mutated target")}
}

func TestR13ExactBoundaryAndTrailingJSON(t *testing.T){
 exact:=append([]byte("{}"),bytes.Repeat([]byte(" "),65534)...)
 if len(exact)!=65536{t.Fatal(len(exact))}
 var target map[string]any
 if err:=decodeBoundedWitness(bytes.NewReader(exact),&target);err!=nil{t.Fatal(err)}
 if target==nil||len(target)!=0{t.Fatal("exact valid boundary not decoded")}
 for _,data:=range [][]byte{
  []byte("{}\n{}"), // distinct in-bound extra JSON record
  append(append([]byte{},exact...),byte(' ')), // first byte over cap
  []byte("  "), // invalid JSON
 }{
  var x map[string]any
  if err:=decodeBoundedWitness(bytes.NewReader(data),&x);err==nil{
   t.Fatal("trailing, oversize or invalid JSON accepted")
  }
 }
}

type r13ReaderFailure struct{once bool}
func(r *r13ReaderFailure)Read(p []byte)(int,error){
 if !r.once{r.once=true;return copy(p,[]byte("{}")),nil}
 return 0,errors.New("injected original I/O failure")
}
func TestR13InputReadFailureAndNoTargetMutation(t *testing.T){
 original:=map[string]any{"safe":"retained"}
 if err:=decodeBoundedWitness(&r13ReaderFailure{},&original);err==nil||
    !strings.Contains(err.Error(),"changed size"){
  t.Fatalf("read error not rejected: %v",err)
 }
 if len(original)!=1||original["safe"]!="retained"{t.Fatal("input read error changed target")}
}

func TestR13FilesystemContractPreserved(t *testing.T){
 dir:=t.TempDir()
 path:=filepath.Join(dir,"witness.json")
 if err:=os.WriteFile(path,[]byte("{}\n"),0600);err!=nil{t.Fatal(err)}
 var valid map[string]any
 if err:=readBounded(path,&valid);err!=nil{t.Fatal(err)}
 if valid==nil{t.Fatal("valid original witness rejected")}
 if err:=os.WriteFile(path,bytes.Repeat([]byte(" "),65537),0600);err!=nil{t.Fatal(err)}
 if err:=readBounded(path,&valid);err==nil{t.Fatal("oversized original file admitted")}
 symlink:=filepath.Join(dir,"link.json")
 if err:=os.Symlink(path,symlink);err==nil {
  if err:=readBounded(symlink,&valid);err==nil{t.Fatal("symlink admitted")}
 }
 if err:=readBounded("relative.json",&valid);err==nil{t.Fatal("relative path admitted")}
}


func TestR13OpenedFileIdentityRejectsReplacedPath(t *testing.T){
 dir:=t.TempDir()
 path:=filepath.Join(dir,"witness.json")
 if err:=os.WriteFile(path,[]byte(`{"source":"original"}`),0600);err!=nil{t.Fatal(err)}
 original,err:=os.Lstat(path);if err!=nil{t.Fatal(err)}
 if err:=os.Rename(path,path+".old");err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(path,[]byte(`{"source":"swapped"}`),0600);err!=nil{t.Fatal(err)}
 opened,err:=os.Open(path);if err!=nil{t.Fatal(err)};defer opened.Close()
 // Original decoder would accept the different regular file.
 var legacy map[string]any
 if err:=r13LegacyDecoder(opened,&legacy);err!=nil{t.Fatal(err)}
 if legacy["source"]!="swapped"{t.Fatal("legacy path replacement not reproduced")}
 if err:=verifyOpenedWitness(original,opened);err==nil{
  t.Fatal("replaced path accepted as original opened witness")
 }
 // A stable file at the same path remains acceptable on a fresh read.
 var stable map[string]any
 if err:=readBounded(path,&stable);err!=nil{t.Fatal(err)}
 if stable["source"]!="swapped"{t.Fatal("stable file rejected or changed")}
}

func TestR13OpenedFileRejectsSameInodeSizeDrift(t *testing.T){
 path:=filepath.Join(t.TempDir(),"witness.json")
 if err:=os.WriteFile(path,[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 original,err:=os.Lstat(path);if err!=nil{t.Fatal(err)}
 opened,err:=os.Open(path);if err!=nil{t.Fatal(err)};defer opened.Close()
 if err:=os.WriteFile(path,[]byte(`{"value":1}`),0600);err!=nil{t.Fatal(err)}
 // os.SameFile still matches: size comparison must independently deny.
 changed,err:=opened.Stat();if err!=nil{t.Fatal(err)}
 if !os.SameFile(original,changed){t.Fatal("size-change fixture replaced inode")}
 if err:=verifyOpenedWitness(original,opened);err==nil{
  t.Fatal("same-inode size drift accepted")
 }
}
