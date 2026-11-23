package main

import (
 "bytes"
 "strings"
 "testing"
)

// The G29 source snapshot, JSON and ICE evidence must be bit-identical.
// G62 changes only the runner-private offline HTML interaction layer.
func TestG62PresentationOnly(t *testing.T){
 a:=Atlas{Schema:schema,Repository:repository,SourceCommit:g61Target,Authority:"public-source-navigation-only",
  Files:[]File{{Path:"f139/local_controller.py",Kind:"python",URL:"https://github.com/"+repository+"/blob/"+g61Target+"/f139/local_controller.py"}},
  Symbols:[]Symbol{{File:"f139/local_controller.py",Name:"loop",Evidence:"lexical-locator-only",URL:"https://github.com/"+repository+"/blob/"+g61Target+"/f139/local_controller.py#L8"}}}
 a.Counts.Files=len(a.Files);a.Counts.Symbols=len(a.Symbols)
 previous,e:=render(a);if e!=nil{t.Fatal(e)}
 current,e:=renderG62(a);if e!=nil{t.Fatal(e)}
 for _,name:=range []string{jsonFile,iceFile}{
  if !bytes.Equal(previous[name],current[name]){t.Fatalf("evidence drift %s",name)}
 }
 html:=string(current[htmlFile])
 for _,term:=range []string{
  "Show next 200 results",
  "function appendPage()",
  "Browse this file's declarations",
  "indexed declarations in this file (not dependency edges)",
  "Open immutable pinned source",
  "lexical-locator-only",
 } {
  if !strings.Contains(html,term){t.Fatalf("missing G62 navigation contract %q",term)}
 }
 if strings.Contains(html,"fetch(")||strings.Contains(html,"XMLHttpRequest")||strings.Contains(html,"localStorage"){
  t.Fatal("G62 viewer attempted external or stored state")
 }
}
