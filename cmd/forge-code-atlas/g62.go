package main

// G62 changes presentation only. It consumes the already-qualified G61
// source index and never changes source identities or invents dependency edges.
import (
 "errors"
 "strings"
)

func renderG62(a Atlas)(map[string][]byte,error){
 out,err:=render(a)
 if err!=nil{return nil,err}
 html:=string(out[htmlFile])
 const start="<script>(()=>{const a=JSON.parse("
 const close="</script></body></html>"
 if strings.Count(html,start)!=1||!strings.HasSuffix(html,close){
  return nil,errors.New("G62_VIEWER_BOUNDARY_DRIFT")
 }
 i:=strings.Index(html,start)
 j:=len(html)-len(close)
 if i<0||j<=i{return nil,errors.New("G62_VIEWER_SCRIPT_MISSING")}
 script:=`<script>(() => {
"use strict";
const a=JSON.parse(document.getElementById("atlas").textContent);
const q=document.getElementById("q");
const list=document.getElementById("matches");
const detail=document.getElementById("detail");
const counter=document.createElement("p");
counter.id="match-count";
list.before(counter);
const more=document.createElement("button");
more.id="load-more";
more.type="button";
more.textContent="Show next 200 results";
list.after(more);
document.getElementById("counts").textContent =
 a.counts.files+" files / "+a.counts.symbols+" provisional symbols";
const entries=[
 ...a.files.map(o=>({name:o.path,o,isFile:true})),
 ...a.symbols.map(o=>({name:o.name+" | "+o.file,o,isFile:false}))
];
let matches=[];
let displayed=0;
function add(kind,content,parent){
 const node=document.createElement(kind);
 node.textContent=content;
 parent.append(node);
 return node;
}
function show(x){
 detail.replaceChildren();
 add("h3",x.name,detail);
 add("p",x.o.evidence_basis||"Exact Git source file; behavior unverified",detail);
 const link=add("a","Open immutable pinned source",detail);
 link.href=x.o.source_url;
 link.target="_blank";
 link.rel="noopener noreferrer";
 if(x.isFile){
  const n=a.symbols.filter(s=>s.file===x.o.path).length;
  add("p",n+" indexed declarations in this file (not dependency edges)",detail);
  if(n){
   const browse=add("button","Browse this file's declarations",detail);
   browse.type="button";
   browse.onclick=()=>{q.value=x.o.path;search();};
  }
 }
}
function appendPage(){
 const end=Math.min(matches.length,displayed+200);
 for(let i=displayed;i<end;i++){
  const row=matches[i];
  const b=add("button",row.name,list);
  b.type="button";
  b.onclick=()=>show(row);
 }
 displayed=end;
 counter.textContent="Showing "+displayed+" of "+matches.length+
  " matching files and provisional declarations";
 more.hidden=displayed>=matches.length;
}
function search(){
 const term=q.value.trim().toLowerCase();
 matches=entries.filter(e=>e.name.toLowerCase().includes(term));
 displayed=0;
 list.replaceChildren();
 detail.replaceChildren();
 appendPage();
}
q.oninput=search;
more.onclick=appendPage;
search();
})();</script>`
 out[htmlFile]=[]byte(html[:i]+script+html[j+len("</script>"):])
 return out,nil
}
