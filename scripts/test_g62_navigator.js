// G62: exercise the unmodified generated navigator JS with a hermetic DOM shim.
// This is script-interaction acceptance, not Chromium or runtime-call evidence.
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");

const source=fs.readFileSync(process.argv[2],"utf8");
const payload=source.match(/<script id="atlas" type="application\/json">([\s\S]*?)<\/script>/);
assert(payload,"G62_EMBEDDED_ATLAS_MISSING");
const atlas=JSON.parse(payload[1]);
const script=source.match(/<script>\(\(\) => \{([\s\S]*?)\}\)\(\);<\/script>/);
assert(script,"G62_NAV_SCRIPT_MISSING");
const nodes={};
function element(tag){
 return {
  tag,children:[],textContent:"",value:"",hidden:false,onclick:null,oninput:null,
  append(child){this.children.push(child);},
  replaceChildren(...children){this.children=[...children];},
  before(node){if(this.tag==="div"&&this===nodes.matches)nodes.counter=node;},
  after(node){if(this.tag==="div"&&this===nodes.matches)nodes.more=node;}
 };
}
const document={
 getElementById(id){return nodes[id]??null;},
 createElement:element
};
for(const id of ["atlas","q","matches","detail","counts"])nodes[id]=element("div");
nodes.atlas.textContent=payload[1];
vm.runInNewContext(script[0].slice("<script>".length,-"</script>".length),{document},{timeout:5000});
assert(atlas.files.length===783,"G62_SOURCE_SIZE_DRIFT");
const total=atlas.files.length+atlas.symbols.length;
assert(total>200);
assert.equal(nodes.matches.children.length,200,"first page must be bounded");
assert.equal(nodes.more.hidden,false);
while(!nodes.more.hidden)nodes.more.onclick();
assert.equal(nodes.matches.children.length,total,"all entries must become accessible");
assert.match(nodes.counter.textContent,new RegExp("Showing "+total+" of "+total));
const candidate=atlas.files.find(f=>atlas.symbols.some(s=>s.file===f.path));
assert(candidate,"no file with indexed declarations");
nodes.q.value=candidate.path;
nodes.q.oninput();
assert(nodes.matches.children.length>0);
const row=nodes.matches.children.find(n=>n.textContent===candidate.path);
assert(row,"file not found by exact path search");
row.onclick();
const sourceLink=nodes.detail.children.find(n=>n.tag==="a");
assert(sourceLink,"immutable source action absent");
assert.equal(sourceLink.href,candidate.source_url,"pinned source identity changed");
assert.match(sourceLink.href,/\/blob\/[0-9a-f]{40}\//);
const declarationAction=nodes.detail.children.find(n=>n.tag==="button"&&n.textContent==="Browse this file's declarations");
assert(declarationAction,"file->declaration navigation absent");
declarationAction.onclick();
assert.equal(nodes.q.value,candidate.path);
assert(nodes.matches.children.some(n=>n.textContent.includes(" | "+candidate.path)),"symbol not found from file navigation");
const cs=atlas.files.find(f=>f.path==="scripts/F139WindowsJobSupervisor.cs");
assert(cs,"G61 C# source absent");
nodes.q.value=cs.path;
nodes.q.oninput();
assert(nodes.matches.children.some(n=>n.textContent.includes("F139WindowsJobSupervisor")),"C# declaration unreachable");
nodes.q.value="__g62_no_matching_name__";
nodes.q.oninput();
assert.equal(nodes.matches.children.length,0);
assert.equal(nodes.more.hidden,true);
assert.match(nodes.counter.textContent,/Showing 0 of 0/);
console.log("FORGE_G62_OFFLINE_NAVIGATION_PASS files="+atlas.files.length+" entries="+total);
