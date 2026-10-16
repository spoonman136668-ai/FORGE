// F70: an UNDEPLOYED Cloudflare D1 first-use transaction boundary.
// This is not a Worker fetch handler and cannot start a science worker.
// R41's canonical original owner/witness predecision is reused verbatim;
// no new signer, new signature domain, controller, or scheduler is created.
//
// Only an independently controlled existing Worker deployment may supply
// trusted pins, and ONLY after authentic CKB owner+full seed-lease reconciliation.
// No live trusted pins or Worker integration exist at this engineering gate.
export class Denied extends Error {
 constructor() { super("F70_PROTECTED_ORIGINAL_OWNER_FIRSTUSE_NOT_AUTHENTICATED"); }
}
const denied = ok => {if (!ok) throw new Denied();};
const h64 = /^[0-9a-f]{64}$/;
const h40 = /^[0-9a-f]{40}$/;
const DOMAIN="FORGE-ORIGINAL-OWNER-PREDECISION-V1\n";
const object=x=>x!==null&&typeof x==="object"&&!Array.isArray(x);
const pos=n=>Number.isSafeInteger(n)&&n>0;
const ascii = s=>typeof s==="string"&&s.length>0&&s.length<=256;
const inputHex=(s,n)=> {
 denied(typeof s==="string"&&s.length===n&&/^[0-9a-f]+$/.test(s));
 return Uint8Array.from(s.match(/../g),v=>Number.parseInt(v,16));
};
const encode=new TextEncoder();
async function hexdigest(subtle,raw){
 const bytes=new Uint8Array(await subtle.digest("SHA-256",raw));
 return Array.from(bytes,v=>v.toString(16).padStart(2,"0")).join("");
}
async function edCheck(subtle,pubHex,sigHex,msg){
 const pub=await subtle.importKey("raw",inputHex(pubHex,64),
   {name:"Ed25519"},false,["verify"]);
 return subtle.verify({name:"Ed25519"},pub,inputHex(sigHex,128),msg);
}
function validatedPins(p){
 denied(object(p)&&p.schema==="forge.f70.existing-owner-protected-pins.v1"&&
  p.release_policy==="CKB_OWNER_REQUIRES_INDEPENDENT_PROVENANCE"&&
  p.owner_id==="ckb-plane"&&pos(p.owner_epoch)&&
  h40.test(p.approved_source_commit)&&
  h64.test(p.approved_original_key_sha256)&&
  h64.test(p.approved_predecision_sha256)&&
  h64.test(p.wingless_cohort_sha256)&&h64.test(p.yggdrasil_cohort_sha256)&&
  h64.test(p.complete_scientific_history_sha256)&&
  pos(p.approved_decision_sequence)&&pos(p.approved_run_id)&&
  ascii(p.pinned_worker_id)&&ascii(p.approved_experiment_id)&&
  ["Wingless","Yggdrasil"].includes(p.approved_lane)&&
  /^[0-9a-f]{64}$/.test(p.owner_public_key_hex)&&
  /^[0-9a-f]{64}$/.test(p.witness_public_key_hex)&&
  p.owner_public_key_hex!==p.witness_public_key_hex);
}
function exactCandidate(c,p){
 denied(object(c)&&c.scientific_authorized===false&&
  c.lane===p.approved_lane&&
  c.original_key_sha256===p.approved_original_key_sha256&&
  c.owner_epoch===p.owner_epoch&&
  c.claimed_sequence===p.approved_decision_sequence&&
  c.source_commit_sha===p.approved_source_commit&&
  c.frozen_predecision_sha256===p.approved_predecision_sha256&&
  h64.test(c.external_owner_witness_pin_sha256)&&
  c.external_owner_witness_pin_sha256===p.expected_owner_witness_pin_sha256);
}
async function signedCanonicalOwnerDecision(proof,p,subtle){
 denied(object(proof)&&typeof proof.canonical_event_json==="string"&&
  proof.canonical_event_json.length<=4095&&
  /^[0-9a-f]{128}$/.test(proof.owner_signature_hex)&&
  /^[0-9a-f]{128}$/.test(proof.witness_signature_hex));
 const event=JSON.parse(proof.canonical_event_json);
 denied(object(event)&&JSON.stringify(event)===proof.canonical_event_json&&
  event.schema==="forge.original.owner-predecision.v1"&&
  event.lane===p.approved_lane&&event.experiment_id===p.approved_experiment_id&&
  event.owner_epoch===p.owner_epoch&&
  event.source_commit_sha===p.approved_source_commit&&
  event.worker_id===p.pinned_worker_id&&
  event.decision_sequence===p.approved_decision_sequence&&
  event.before_outcome_declared===true);
 const message=encode.encode(DOMAIN+proof.canonical_event_json);
 denied(await hexdigest(subtle,message)===p.approved_predecision_sha256);
 denied(await edCheck(subtle,p.owner_public_key_hex,proof.owner_signature_hex,message));
 denied(await edCheck(subtle,p.witness_public_key_hex,proof.witness_signature_hex,message));
 return event;
}
const TABLES=[
  "forge_original_preuse_claims",
  "forge_original_preuse_claims_update_immutable",
  "forge_original_preuse_claims_delete_immutable",
  "forge_original_preuse_claims_insert_monotonic"
];
const SQL_TABLE="SELECT name FROM sqlite_master WHERE name IN "+
  "('forge_original_preuse_claims','forge_original_preuse_claims_update_immutable',"+
  "'forge_original_preuse_claims_delete_immutable',"+
  "'forge_original_preuse_claims_insert_monotonic') ORDER BY name";
const SQL_INSERT="INSERT INTO forge_original_preuse_claims "+
  "(original_key_sha256,lane,owner_epoch,source_commit_sha,"+
  "frozen_predecision_sha256,external_owner_witness_pin_sha256,"+
  "claimed_sequence,scientific_authorized) VALUES (?,?,?,?,?,?,?,0)";
async function rows(db,query){
 denied(db&&typeof db.prepare==="function");
 const stmt=db.prepare(query);
 denied(stmt&&typeof stmt.all==="function");
 const result=await stmt.all();
 denied(result?.success===true&&Array.isArray(result.results));
 return result.results;
}

// This function is not currently connected to a deployed Worker or an existing
// scientific executor. A successful synthetic unit test is only a transaction
// contract. Never call from a public request without authenticating the real
// CKB owner principal and worker start identity at that deployment boundary.
export async function onceOnlyClaimAtWorkerStart({
 db,pins,claim,ownerPredecision,
 ownerAndCohortIndependentlyAttested=false,
 currentWorkerIndependentlyAuthenticated=false,
 privateRestorableRecoveryVerified=false,
 authorizedProtectedWorkflow=false,
 subtle=crypto.subtle,
}={}){
 // Four external conditions are NOT derivable from GitHub user-supplied
 // claims, local synthetic records or existing Cloudflare read-only API.
 // In deployment they must be derived from independently controlled custody.
 denied(ownerAndCohortIndependentlyAttested===true&&
  currentWorkerIndependentlyAuthenticated===true&&
  privateRestorableRecoveryVerified===true&&
  authorizedProtectedWorkflow===true);
 validatedPins(pins);
 denied(h64.test(pins.expected_owner_witness_pin_sha256));
 // The canonical R41 D1 key and signer pin MUST derive from the signed
 // experiment identity and the already-pinned existing signer public keys.
 denied(await hexdigest(subtle,encode.encode(
  pins.approved_lane+"\x00"+pins.approved_experiment_id))===
  pins.approved_original_key_sha256);
 denied(await hexdigest(subtle,encode.encode(
  pins.owner_public_key_hex+"\x00"+pins.witness_public_key_hex))===
  pins.expected_owner_witness_pin_sha256);
 exactCandidate(claim,pins);
 await signedCanonicalOwnerDecision(ownerPredecision,pins,subtle);
 const schema=await rows(db,SQL_TABLE);
 const names=schema.map(x=>x.name);
 denied(names.length===TABLES.length&&TABLES.every(
  name=>names.filter(x=>x===name).length===1));
 // The R35/R38 UNIQUE, immutable and monotonic trigger protects the one
 // irrevocable original attempt. Deliberately no SELECT-then-INSERT TOCTOU.
 // NEVER retry after a remote timeout/unknown commit outcome.
 const statement=db.prepare(SQL_INSERT);
 denied(statement&&typeof statement.bind==="function");
 const value=statement.bind(claim.original_key_sha256,claim.lane,
  claim.owner_epoch,claim.source_commit_sha,
  claim.frozen_predecision_sha256,
  claim.external_owner_witness_pin_sha256,
  claim.claimed_sequence);
 denied(value&&typeof value.run==="function");
 const result=await value.run();
 denied(result?.success===true&&result?.meta?.changes===1);
 // Local contract result, NOT a serializable bearer token: reusing a response
 // as an execution permit bypasses the first-use transaction.
 return Object.freeze({
  schema:"forge.f70.at-execution-onceonly-claim.v1",
  claimed_once_in_bound_database:true,
  reusable_bearer_permit_issued:false,
  external_worker_invoked:false,
  scientific_result_accepted:false,
  owner_cutover_authorized:false,
  disposition:"ATOMIC_INTENT_CONSUMED_NO_EXTERNAL_SCIENCE_START_IMPLEMENTED",
 });
}
