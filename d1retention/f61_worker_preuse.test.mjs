import test from "node:test";
import assert from "node:assert/strict";
import {generateKeyPairSync,sign,webcrypto} from "node:crypto";
import {Blocked,verifyIssuer,inspectExistingBoundary} from "./f61_worker_preuse.mjs";

const ISSUER="https://token.actions.githubusercontent.com";
const KEYSET=ISSUER+"/.well-known/jwks";
const AUD="forge-f61-ckb-preuse-observation-only";
const WORKFLOW="spoonman136668-ai/ckb-plane/.github/workflows/research-loop-headless-wake-v2.yml@refs/heads/main";
const SHA="a".repeat(40);
const now=Date.parse("2026-10-16T00:00:00.000Z");
const enc=o=>Buffer.from(JSON.stringify(o)).toString("base64url");

function fixture() {
 const {privateKey,publicKey}=generateKeyPairSync("rsa",{modulusLength:2048,
  publicExponent:65537});
 const jwk=publicKey.export({format:"jwk"});
 Object.assign(jwk,{kid:"f61-synthetic-test-key",use:"sig",alg:"RS256"});
 const trust={
  schema:"forge.f61.external-ckb-prospective-pins.v1",
  exact_repository:"spoonman136668-ai/ckb-plane",
  protected_workflow_ref:WORKFLOW,
  expected_event:"workflow_dispatch",
  expected_audience:AUD,
  pinned_subject:"repo:spoonman136668-ai/ckb-plane:ref:refs/heads/main",
  approved_source_sha:SHA,approved_run_id:38899999999,
  owner_epoch:7, decision_sequence:52,authorized_lane:"Wingless",
  complete_consumed_active_uncertain_history_sha256:"a".repeat(64),
  external_authority_custody_sha256:"b".repeat(64),
  authorized_original_key_sha256:"c".repeat(64),
  authorized_predecision_sha256:"d".repeat(64),
  authorized_owner_witness_pin_sha256:"e".repeat(64)
 };
 const c={
  iss:ISSUER,aud:AUD,
  repository:"spoonman136668-ai/ckb-plane",
  repository_owner:"spoonman136668-ai",
  ref:"refs/heads/main",workflow_ref:WORKFLOW,
  event_name:"workflow_dispatch",run_attempt:"1",
  sub:trust.pinned_subject,sha:SHA,run_id:String(trust.approved_run_id),
  iat:Math.floor(now/1000)-10,nbf:Math.floor(now/1000)-10,
  exp:Math.floor(now/1000)+300
 };
 const candidate={
  original_key_sha256:trust.authorized_original_key_sha256,
  lane:"Wingless",owner_epoch:7,claimed_sequence:52,
  source_commit_sha:SHA,
  frozen_predecision_sha256:trust.authorized_predecision_sha256,
  external_owner_witness_pin_sha256:trust.authorized_owner_witness_pin_sha256,
  scientific_authorized:false
 };
 function jwt(mod={}, signer=privateKey) {
  const b=enc({alg:"RS256",typ:"JWT",kid:jwk.kid})+"."+
   enc({...c,...mod});
  return b+"."+sign("RSA-SHA256",Buffer.from(b),signer).toString("base64url");
 }
 return {trust,c,candidate,jwk,jwks:{keys:[jwk]},jwt};
}
function database({missing=false,duplicate=0,sequence=9,epoch=7}={}) {
 const queries=[];
 const db={
  prepare(q){
   assert.match(q,/^SELECT /);
   queries.push(q);
   return {bind(...args){
    return {async all(){
     if(q.includes("sqlite_master"))
      return {success:true,results:missing?[]:[
       {name:"forge_original_preuse_claims"},
       {name:"forge_original_preuse_claims_update_immutable"},
       {name:"forge_original_preuse_claims_delete_immutable"},
       {name:"forge_original_preuse_claims_insert_monotonic"}]};
     if(q.includes("COUNT(*)")){
      assert.deepEqual(args,["c".repeat(64)]);
      return {success:true,results:[{n:duplicate}]};
     }
     if(q.includes("MAX(claimed_sequence)"))
      return {success:true,results:[{sequence,epoch}]};
     throw Error("Unexpected SQL query");
    }};
   }};
  }
 };
 return {db,queries};
}
function github(jwks){
 return async function(url,opts){
  assert.equal(url,KEYSET);assert.equal(opts.method,"GET");
  return {url,ok:true,status:200,async text(){return JSON.stringify(jwks)}};
 };
}
async function inspect(f,opts={}){
 const x=database(opts.db);
 const outcome=await inspectExistingBoundary({
  jwt:opts.jwt||f.jwt(),trust:opts.trust||f.trust,
  candidate:opts.candidate||f.candidate,db:x.db,
  now,fetcher:opts.fetcher||github(f.jwks),subtle:webcrypto.subtle
 });
 return {outcome,queries:x.queries};
}
test("exact signed protected-main owner origin is verified, but never permits science",async()=>{
 const f=fixture(),{outcome,queries}=await inspect(f);
 assert.equal(outcome.github_issuer_verified,true);
 assert.equal(outcome.existing_claim_table_and_immutability_observed,true);
 assert.equal(outcome.disposition,"READ_ONLY_PREUSE_CANDIDATE_MATCH_NO_PERMIT");
 assert.equal(queries.length,3);
 assert.ok(queries.every(x=>x.startsWith("SELECT ")));
 for(const key of ["independently_authenticated_current_owner",
  "all_lane_lease_history_authenticated","first_use_atomic_claim_consumed",
  "worker_dispatch_permit_issued","scientific_execution_authorized",
  "forge_owner_cutover_authorized"]){assert.equal(outcome[key],false,key)}
});
test("signature tampering, modified GitHub identity, stale token all fail",async()=>{
 const f=fixture(),valid=f.jwt();
 const cases=[
  valid.slice(0,-2)+"aa",
  f.jwt({repository:"foreign/attacker"}),
  f.jwt({workflow_ref:"foreign/workflow.yml"}),
  f.jwt({sha:"f".repeat(40)}),
  f.jwt({run_attempt:"2"}),f.jwt({run_id:"39000000000"}),
  f.jwt({aud:"forged-audience"}),f.jwt({sub:"untrusted"}),
  f.jwt({ref:"refs/heads/feature"}),f.jwt({event_name:"push"}),
  f.jwt({exp:Math.floor(now/1000)-5})
 ];
 for(const jwt of cases){
  await assert.rejects(
   verifyIssuer(jwt,f.jwks,f.trust,now,webcrypto.subtle),Blocked);
  const {outcome,queries}=await inspect(f,{jwt});
  assert.equal(outcome.worker_dispatch_permit_issued,false);
  assert.equal(outcome.existing_claim_table_and_immutability_observed,false);
  assert.equal(queries.length,0);
 }
});
test("separate RSA signing key cannot substitute for GitHub OIDC JWKS",async()=>{
 const f=fixture();
 const {privateKey}=generateKeyPairSync("rsa",{modulusLength:2048});
 await assert.rejects(verifyIssuer(f.jwt({},privateKey),f.jwks,
  f.trust,now,webcrypto.subtle),Blocked);
});
test("caller input cannot supply its own trust roots, source, permissions or cohort hash",async()=>{
 const f=fixture();
 const malformed=[
  {pinned_subject:"different-sub"},
  {approved_source_sha:"f".repeat(40)},
  {approved_run_id:38899999998},
  {complete_consumed_active_uncertain_history_sha256:""},
  {external_authority_custody_sha256:""},
  {owner_epoch:0},{expected_audience:"forged"},{protected_workflow_ref:"other"}
 ];
 for(const change of malformed){
  const {outcome,queries}=await inspect(f,{trust:{...f.trust,...change}});
  assert.equal(outcome.worker_dispatch_permit_issued,false);
  assert.equal(queries.length,0);
 }
 const drift=[
  {original_key_sha256:"f".repeat(64)},{owner_epoch:8},
  {claimed_sequence:53},{scientific_authorized:true},{lane:"Yggdrasil"},
  {source_commit_sha:"f".repeat(40)}
 ];
 for(const change of drift){
  const {outcome,queries}=await inspect(f,{candidate:{...f.candidate,...change}});
  assert.equal(outcome.worker_dispatch_permit_issued,false);
  assert.equal(queries.length,0);
 }
});
test("missing real D1 claim table blocks; consumed first-use and stale highwater block",async()=>{
 const f=fixture();
 for(const db of [{missing:true},{duplicate:1},{sequence:52},{epoch:8}]){
  const {outcome,queries}=await inspect(f,{db});
  assert.equal(outcome.scientific_execution_authorized,false);
  assert.equal(outcome.worker_dispatch_permit_issued,false);
  assert.ok(queries.length>=1);
 }
});
test("unavailable issuer/JWKS or D1 cannot grant any worker permit",async()=>{
 const f=fixture();
 const brokenIssuer=async()=>{throw Error("issuer down");};
 const {outcome,queries}=await inspect(f,{fetcher:brokenIssuer});
 assert.equal(outcome.github_issuer_verified,false);
 assert.equal(outcome.worker_dispatch_permit_issued,false);
 assert.equal(queries.length,0);
 const x=await inspectExistingBoundary({jwt:f.jwt(),trust:f.trust,
  candidate:f.candidate,db:null,now,fetcher:github(f.jwks),
  subtle:webcrypto.subtle});
 assert.equal(x.worker_dispatch_permit_issued,false);
});
