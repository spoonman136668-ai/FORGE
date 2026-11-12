import test from "node:test";
import assert from "node:assert/strict";
import {planSingleReservation,classifyReservationResult} from "./f63_reservation_plan.mjs";

const candidate=()=>({
 original_key_sha256:"a".repeat(64),lane:"Wingless",owner_epoch:8,
 source_commit_sha:"b".repeat(40),frozen_predecision_sha256:"c".repeat(64),
 external_owner_witness_pin_sha256:"d".repeat(64),claimed_sequence:53,
 scientific_authorized:false
});
const pin=(c)=>Object.fromEntries(Object.entries(c).filter(([k])=>k!=="scientific_authorized"));

test("exact immutable candidate produces one parameterized SQL-only plan",()=>{
 const c=candidate();
 const p=planSingleReservation(c,pin(c));
 assert.equal(p.sql.match(/\?/g).length,7);
 assert.ok(p.sql.startsWith("INSERT INTO forge_original_preuse_claims "));
 assert.equal(p.values[0],c.original_key_sha256);
 assert.equal(p.values[6],53);
 assert.ok(Object.isFrozen(p));
 assert.ok(Object.isFrozen(p.values));
 assert.equal(p.worker_permit_issued,false);
 assert.equal(p.science_dispatch_authorized,false);
 assert.equal(p.cloudflare_mutation_performed,false);
 assert.equal(p.permits_retry_after_uncertain_commit,false);
});
test("independent pins and source cannot be substituted",()=>{
 const c=candidate();
 for(const field of Object.keys(pin(c))){
  const forged={...pin(c),[field]:field==="lane"?"Yggdrasil":0};
  assert.throws(()=>planSingleReservation(c,forged),/F63_NO_INDEPENDENT/);
 }
 for(const bad of [
  {...c,scientific_authorized:true},
  {...c,source_commit_sha:"b".repeat(39)},
  {...c,lane:"WingLess"},
  {...c,claimed_sequence:0},
  {...c,owner_epoch:1.1},
  {...c,external_owner_witness_pin_sha256:"x".repeat(64)},
  {...c,scientific_authorized:false,extra:"override"},
  {},
  null
 ]){
  assert.throws(()=>planSingleReservation(bad,pin(c)),/F63_NO_INDEPENDENT/);
 }
});
test("storage commit classification is NEVER a worker execution permit",()=>{
 const c=candidate(),p=planSingleReservation(c,pin(c));
 assert.equal(classifyReservationResult(p,{success:true,meta:{changes:1,changed_db:true}}),
  "R35_R38_STORAGE_CONSUMED_NOT_SCIENTIFIC_RELEASE");
 for(const r of [undefined,{}, {success:true,meta:{changes:0,changed_db:false}},
   {success:false,meta:{changes:1,changed_db:true}}]){
  assert.equal(classifyReservationResult(p,r),"DENY_INDETERMINATE_NO_RETRY");
 }
 assert.equal(classifyReservationResult({schema:"forged"},{success:true,meta:{changes:1,changed_db:true}}),
 "DENY_NO_VERIFIED_PLAN");
});
