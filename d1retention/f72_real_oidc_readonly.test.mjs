import test from "node:test";
import assert from "node:assert/strict";
import {generateKeyPairSync,sign} from "node:crypto";
import {verifyJWT,observeRealOrigin,Denied} from "./f72_real_oidc_readonly.mjs";
const ISS="https://token.actions.githubusercontent.com";
const REPO="spoonman136668-ai/FORGE";
const SHA="a".repeat(40);
const BRANCH="engineering/f72-real-forge-oidc-origin-science-denial-20261016-r1";
const REF="refs/heads/"+BRANCH;
const WFLOW=REPO+"/.github/workflows/forge-f72-real-oidc-readonly.yml@"+REF;
const AUD="forge-f72-observe-genuine-run-not-science";
const clock=Date.parse("2026-10-16T13:00:00Z");
const repoID=1413298198;
const enc=v=>Buffer.from(JSON.stringify(v)).toString("base64url");
function fixture(){
 const {privateKey,publicKey}=generateKeyPairSync("rsa",{modulusLength:2048});
 const key={...publicKey.export({format:"jwk"}),kid:"f72-synthetic-only",use:"sig",alg:"RS256"};
 const pins={repository:REPO,ref:REF,workflow_ref:WFLOW,sha:SHA,
             run_id:"38888000001",run_attempt:"1",event_name:"push"};
 const claims={iss:ISS,aud:AUD,repository_owner:"spoonman136668-ai",
  ...pins,repository_id:String(repoID),sub:"repo:"+REPO+":ref:"+REF,
  iat:Math.floor(clock/1000)-8,nbf:Math.floor(clock/1000)-8,
  exp:Math.floor(clock/1000)+300};
 const jwt=(patch={},signer=privateKey)=>{
   const data=enc({alg:"RS256",typ:"JWT",kid:key.kid})+"."+
     enc({...claims,...patch});
   return data+"."+sign("RSA-SHA256",Buffer.from(data),signer).toString("base64url");
 };
 const env={GITHUB_REPOSITORY:REPO,GITHUB_SHA:SHA,GITHUB_REF:REF,
  GITHUB_WORKFLOW_REF:WFLOW,GITHUB_RUN_ID:pins.run_id,
  GITHUB_RUN_ATTEMPT:"1",GITHUB_EVENT_NAME:"push",
  ACTIONS_ID_TOKEN_REQUEST_URL:"https://oidc.github.example/test?api-version=2.0",
  ACTIONS_ID_TOKEN_REQUEST_TOKEN:"synthetic-scope"};
 const actionURL=env.ACTIONS_ID_TOKEN_REQUEST_URL+"&audience="+encodeURIComponent(AUD);
 const endpoints={
   [actionURL]:{value:jwt()},
   [ISS+"/.well-known/openid-configuration"]:{
     issuer:ISS,jwks_uri:ISS+"/.well-known/jwks"},
   [ISS+"/.well-known/jwks"]:{keys:[key]},
   ["https://api.github.com/repos/"+REPO]:{full_name:REPO,id:repoID},
   ["https://api.github.com/repos/"+REPO+"/actions/runs/"+pins.run_id]:{
     id:Number(pins.run_id),head_sha:SHA,head_branch:BRANCH,
     event:"push",run_attempt:1,
     path:".github/workflows/forge-f72-real-oidc-readonly.yml"},
   ["https://api.github.com/repos/"+REPO+"/branches/main"]:{
     name:"main",protected:false,commit:{sha:"d".repeat(40)}},
 };
 const requested=[];
 const fetcher=async(url,opts)=>{
  requested.push({url,method:opts.method});
  assert.equal(opts.method,"GET");
  assert.equal(opts.redirect,"error");
  if(!(url in endpoints))throw new Error("F72_MOCK_UNEXPECTED_ENDPOINT");
  return {url,ok:true,status:200,async text(){return JSON.stringify(endpoints[url])}};
 };
 return {key,claims,pins,env,endpoints,actionURL,fetcher,requested,jwt};
}
test("valid synthetic issuer authenticity remains non-authorizing on engineering branch",async()=>{
 const f=fixture();
 const r=await observeRealOrigin({env:f.env,fetcher:f.fetcher,now:clock});
 assert.equal(r.oidc_signature_and_live_jwks_verified,true);
 assert.equal(r.signed_run_source_and_repository_identity_joined,true);
 assert.equal(r.on_protected_main_science_issuer,false);
 assert.equal(r.independently_accepted_current_scientific_owner,false);
 assert.equal(r.complete_two_lane_original_firstuse_attested,false);
 assert.equal(r.worker_execution_permit_issued,false);
 assert.equal(r.scientific_originals_dispatched,0);
 assert.equal(r.run_attempt,1);
 assert.equal(f.requested.length,6);
});
test("forged signed JWT, wrong repository, ref, run attempt, OIDC audience or stale expiry refused",async()=>{
 for(const change of [
   {sha:"f".repeat(40)},{repository:"attacker/forge"},
   {repository_id:"99999"},{ref:"refs/heads/main"},
   {workflow_ref:"attacker/original.yml"},{run_attempt:"2"},
   {aud:"cloudflare-owner-release"},{iss:"https://attacker.example"},
   {sub:"foo",exp:Math.floor(clock/1000)-2},
   {run_id:"38888000002"}
 ]){
  const f=fixture();
  assert.throws(()=>verifyJWT(f.jwt(change),{keys:[f.key]},
      f.pins,clock),Denied);
 }
 const f=fixture(),fakeKey=generateKeyPairSync("rsa",{modulusLength:2048}).privateKey;
 assert.throws(()=>verifyJWT(f.jwt({},fakeKey),{keys:[f.key]},f.pins,clock),Denied);
});
test("moving source/run/repository identity from live GitHub read is never admitted",async()=>{
 for(const which of ["sha","branch","run","repo"]){
  const f=fixture();
  if(which==="sha")
   f.endpoints["https://api.github.com/repos/"+REPO+"/actions/runs/"+f.pins.run_id].head_sha="f".repeat(40);
  if(which==="branch")
   f.endpoints["https://api.github.com/repos/"+REPO+"/actions/runs/"+f.pins.run_id].head_branch="main";
  if(which==="run")
   f.endpoints["https://api.github.com/repos/"+REPO+"/actions/runs/"+f.pins.run_id].run_attempt=2;
  if(which==="repo")
   f.endpoints["https://api.github.com/repos/"+REPO].id=3;
  await assert.rejects(observeRealOrigin({env:f.env,fetcher:f.fetcher,now:clock}),Denied);
 }
});
test("main or foreign workflow is NOT an independently authorized science workflow",async()=>{
 for(const mutate of [
  env=>{env.GITHUB_REF="refs/heads/main";env.GITHUB_WORKFLOW_REF=WFLOW.replace(REF,"refs/heads/main");},
  env=>{env.GITHUB_WORKFLOW_REF="attacker/project@refs/heads/main";},
  env=>{env.GITHUB_EVENT_NAME="workflow_dispatch";},
  env=>{env.GITHUB_RUN_ATTEMPT="2";},
  env=>{env.GITHUB_REPOSITORY="other/repo";}
 ]){
  const f=fixture();mutate(f.env);
  await assert.rejects(observeRealOrigin({env:f.env,fetcher:f.fetcher,now:clock}),Denied);
 }
});
test("issuer discovery, JWKS, request URL and OIDC identity tampering fail",async()=>{
 const failures=[
  f=>{f.endpoints[ISS+"/.well-known/openid-configuration"].jwks_uri="https://other/jwks";},
  f=>{f.endpoints[ISS+"/.well-known/jwks"].keys=[];},
  f=>{f.env.ACTIONS_ID_TOKEN_REQUEST_TOKEN="";},
  f=>{f.env.ACTIONS_ID_TOKEN_REQUEST_URL="http://insecure.example";},
  f=>{f.endpoints[f.actionURL].value="not.jwt";}
 ];
 for(const fn of failures){
  const f=fixture();fn(f);
  await assert.rejects(observeRealOrigin({env:f.env,fetcher:f.fetcher,now:clock}));
 }
});
test("private OIDC token and bearer are never part of nonsecret report",async()=>{
 const f=fixture();
 const r=await observeRealOrigin({env:f.env,fetcher:f.fetcher,now:clock});
 const body=JSON.stringify(r);
 assert.equal(body.includes(f.env.ACTIONS_ID_TOKEN_REQUEST_TOKEN),false);
 assert.equal(body.includes(f.endpoints[f.actionURL].value),false);
 assert.equal(body.includes("owner_signature"),false);
 assert.equal(r.disposition,"REAL_GITHUB_OIDC_VERIFIED_ENGINEERING_ONLY_NO_SCIENCE_AUTHORITY");
});
