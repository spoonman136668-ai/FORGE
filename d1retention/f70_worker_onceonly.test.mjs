import test from "node:test";
import assert from "node:assert/strict";
import {generateKeyPairSync,sign,createHash,webcrypto} from "node:crypto";
import {onceOnlyClaimAtWorkerStart,Denied} from "./f70_worker_onceonly.mjs";
const digest=s=>createHash("sha256").update(s).digest("hex");
const bytes=x=>Buffer.from(x,"base64url");
function fixture(){
 const o=generateKeyPairSync("ed25519"),w=generateKeyPairSync("ed25519");
 const pub=k=>bytes(k.publicKey.export({format:"jwk"}).x).toString("hex");
 const owner=pub(o),witness=pub(w);
 const predecision={
  schema:"forge.original.owner-predecision.v1",
  lane:"Wingless",experiment_id:"SYNTHETIC_F70_NEXT_ONLY",
  frozen_sha256:digest("synthetic-frozen"),
  intent_sha256:digest("synthetic-intent"),
  source_commit_sha:"a".repeat(40),
  original_run_id:"SYNTHETIC_NEXT_F70",
  owner_epoch:7,worker_id:"synthetic-worker",
  policy_sha256:digest("policy"),
  candidate_set_sha256:digest("set"),
  selected_candidate_sha256:digest("candidate"),
  baseline_policy_sha256:[0,1,2,3].map(n=>digest("baseline"+n)),
  logged_action_probability_bp:5000,
  randomization_proof_sha256:digest("synthetic-fairness"),
  decision_sequence:47,before_outcome_declared:true
 };
 const raw=JSON.stringify(predecision);
 const signed=Buffer.from("FORGE-ORIGINAL-OWNER-PREDECISION-V1\n"+raw);
 const pin=digest(signed);
 const ownersDigest=digest(owner+"\x00"+witness);
 const key=digest("Wingless\x00"+predecision.experiment_id);
 const trust={
  schema:"forge.f70.existing-owner-protected-pins.v1",
  release_policy:"CKB_OWNER_REQUIRES_INDEPENDENT_PROVENANCE",
  owner_id:"ckb-plane",owner_epoch:7,
  approved_source_commit:"a".repeat(40),
  approved_original_key_sha256:key,
  approved_predecision_sha256:pin,
  wingless_cohort_sha256:digest("synthetic-Wingless"),
  yggdrasil_cohort_sha256:digest("synthetic-Yggdrasil"),
  complete_scientific_history_sha256:digest("synthetic-complete-history"),
  approved_decision_sequence:47,approved_run_id:38900000000,
  pinned_worker_id:"synthetic-worker",
  approved_experiment_id:predecision.experiment_id,
  approved_lane:"Wingless",
  owner_public_key_hex:owner,witness_public_key_hex:witness,
  expected_owner_witness_pin_sha256:ownersDigest
 };
 const claim={
  original_key_sha256:key,lane:"Wingless",owner_epoch:7,
  source_commit_sha:"a".repeat(40),
  frozen_predecision_sha256:pin,
  external_owner_witness_pin_sha256:ownersDigest,
  claimed_sequence:47,scientific_authorized:false
 };
 const proof={
  canonical_event_json:raw,
  owner_signature_hex:sign(null,signed,o.privateKey).toString("hex"),
  witness_signature_hex:sign(null,signed,w.privateKey).toString("hex")
 };
 return {pins:trust,claim,ownerPredecision:proof,subtle:webcrypto.subtle};
}
function database({missing=false,failure=false,ambiguous=false}={}){
 const touched={schema:0,writes:0,consumed:new Set(),seq:0};
 const db={prepare(sql){
  if(sql.startsWith("SELECT name FROM sqlite_master")){
   return {async all(){
    touched.schema++;
    return {success:true,results:missing?[]:[
     "forge_original_preuse_claims",
     "forge_original_preuse_claims_update_immutable",
     "forge_original_preuse_claims_delete_immutable",
     "forge_original_preuse_claims_insert_monotonic"
    ].map(name=>({name}))};
   }};
  }
  assert.match(sql,/^INSERT INTO forge_original_preuse_claims/);
  return {bind(key,lane,epoch,source,predecision,witness,sequence){
   return {async run(){
    touched.writes++;
    if(ambiguous)throw Error("simulated uncertain D1 response");
    if(failure)return {success:false,meta:{changes:0}};
    if(touched.consumed.has(key)||sequence<=touched.seq)
      throw Error("sqlite UNIQUE or R38 monotonic first-use");
    touched.consumed.add(key);touched.seq=sequence;
    return {success:true,meta:{changes:1}};
   }};
  }};
 }};
 return {db,touched};
}
const admission={
 ownerAndCohortIndependentlyAttested:true,
 currentWorkerIndependentlyAuthenticated:true,
 privateRestorableRecoveryVerified:true,
 authorizedProtectedWorkflow:true
};
function call(f,db,extra={}){
 return onceOnlyClaimAtWorkerStart({
   ...f,db,...admission,...extra
 });
}
test("all real external custody prerequisites are absent by default; no D1 request",async()=>{
 const f=fixture(),d=database();
 await assert.rejects(onceOnlyClaimAtWorkerStart({...f,db:d.db}),Denied);
 assert.equal(d.touched.schema,0);assert.equal(d.touched.writes,0);
 for(const k of Object.keys(admission)){
  const a={...admission,[k]:false};
  await assert.rejects(onceOnlyClaimAtWorkerStart({...f,...a,db:d.db}),Denied);
 }
 assert.equal(d.touched.writes,0);
});
test("synthetic signed R41 owner record admits one DB intent only; NO bearer permit or science",async()=>{
 const f=fixture(),d=database();
 const result=await call(f,d.db);
 assert.equal(result.claimed_once_in_bound_database,true);
 assert.equal(result.reusable_bearer_permit_issued,false);
 assert.equal(result.external_worker_invoked,false);
 assert.equal(result.scientific_result_accepted,false);
 assert.equal(result.owner_cutover_authorized,false);
 assert.equal(d.touched.writes,1);
 await assert.rejects(call(f,d.db));
 assert.equal(d.touched.writes,2);
 assert.equal(d.touched.consumed.size,1);
});
test("forged owner/witness, source, epoch, cohort pins, and decision refused before D1",async()=>{
 const variants=[
  x=>x.ownerPredecision.owner_signature_hex="0".repeat(128),
  x=>x.ownerPredecision.witness_signature_hex="0".repeat(128),
  x=>x.pins.owner_public_key_hex=x.pins.witness_public_key_hex,
  x=>x.claim.owner_epoch=8,
  x=>x.claim.source_commit_sha="b".repeat(40),
  x=>x.claim.claimed_sequence=48,
  x=>x.claim.external_owner_witness_pin_sha256="b".repeat(64),
  x=>x.pins.approved_predecision_sha256="c".repeat(64),
  x=>x.pins.wingless_cohort_sha256="",
  x=>x.pins.yggdrasil_cohort_sha256="",
  x=>x.pins.complete_scientific_history_sha256="",
  x=>x.ownerPredecision.canonical_event_json+=" ",
  x=>x.claim.scientific_authorized=true,
  x=>x.pins.release_policy="SIGNED_BY_LOCAL_WORKER"
 ];
 for(const edit of variants){
  const f=fixture(),d=database();edit(f);
  await assert.rejects(call(f,d.db),Denied);
  assert.equal(d.touched.writes,0);
 }
});
test("missing live D1 table, failure, uncertain database outcome never yields permit",async()=>{
 for(const fopts of [{missing:true},{failure:true},{ambiguous:true}]){
  const f=fixture(),d=database(fopts);
  await assert.rejects(call(f,d.db));
  assert.equal(d.touched.consumed.size,0);
 }
});
test("different experimental intent with stale global sequence is rejected by R38 at start",async()=>{
 const f=fixture(),d=database();
 await call(f,d.db);
 const other=fixture();
 // Distinct synthetic signer and experiment context, but same sequence.
 await assert.rejects(call(other,d.db));
 assert.equal(d.touched.consumed.size,1);
});
