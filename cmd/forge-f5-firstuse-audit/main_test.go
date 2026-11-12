package main

import (
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/f5custody"
)

type fileExample struct {Field string `json:"field"`}

func TestCanonicalIntakeRejectsUnknownAndDuplicateKeys(t *testing.T){
 cases:=[]struct{name,contents string;valid bool}{
  {"canonical","{\"field\":\"value\"}\n",true},
  {"duplicate","{\"field\":\"value\",\"field\":\"replacement\"}\n",false},
  {"unknown","{\"field\":\"value\",\"secret\":\"ignored\"}\n",false},
  {"not canonical","{ \"field\":\"value\" }\n",false},
  {"trailing","{\"field\":\"value\"}\n{}\n",false},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   path:=filepath.Join(t.TempDir(),"input.json")
   if e:=os.WriteFile(path,[]byte(tc.contents),0600);e!=nil{t.Fatal(e)}
   v,err:=canonicalRead[fileExample](path)
   if tc.valid&&(err!=nil||v.Field!="value"){t.Fatalf("reject valid %v",err)}
   if !tc.valid&&err==nil{t.Fatal("accepted untrusted input")}
  })
 }
}
func TestMissingExternalAuthorityAlwaysDenies(t *testing.T){
 out,err:=audit("","",f5custody.Pins{})
 if err==nil||out.Disposition!="BLOCKED"{t.Fatalf("unsafe authority %+v %v",out,err)}
 path:=filepath.Join(t.TempDir(),"fake.json")
 if e:=os.WriteFile(path,[]byte("{}\n"),0600);e!=nil{t.Fatal(e)}
 out,err=audit(path,path,f5custody.Pins{})
 if err==nil||out.Disposition!="BLOCKED"{t.Fatalf("unsafe forged bundle %+v %v",out,err)}
}
func TestSymlinkInputIsRefused(t *testing.T){
 dir:=t.TempDir()
 file:=filepath.Join(dir,"real")
 link:=filepath.Join(dir,"link")
 if e:=os.WriteFile(file,[]byte("{\"field\":\"value\"}\n"),0600);e!=nil{t.Fatal(e)}
 if err:=os.Symlink(file,link);err!=nil{
  if strings.Contains(strings.ToLower(err.Error()),"privilege"){t.Skip("Windows symlink privilege unavailable")}
  t.Skipf("symlink unavailable: %v",err)
 }
 _,err:=canonicalRead[fileExample](link)
 if err==nil{t.Fatal("symlink allowed")}
}
