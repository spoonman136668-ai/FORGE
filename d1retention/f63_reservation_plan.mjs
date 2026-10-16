// F63: isolated SQL plan for one atomic R35/R38 D1 reservation.
// No Worker handler, no database connection, no remote D1 write, no approval.
// Exporting a valid immutable INSERT plan does not authorize dispatch or a retry.
const H40=/^[0-9a-f]{40}$/;
const H64=/^[0-9a-f]{64}$/;
const validNumber=n=>Number.isSafeInteger(n)&&n>0;
const deny=()=>{throw Error("F63_NO_INDEPENDENT_PROSPECTIVE_OWNER_OR_ATOMIC_RELEASE");};
const SQL="INSERT INTO forge_original_preuse_claims "+
 "(original_key_sha256,lane,owner_epoch,source_commit_sha,"+
 "frozen_predecision_sha256,external_owner_witness_pin_sha256,claimed_sequence) "+
 "VALUES (?,?,?,?,?,?,?)";
const FIELDS=["original_key_sha256","lane","owner_epoch","source_commit_sha",
 "frozen_predecision_sha256","external_owner_witness_pin_sha256","claimed_sequence"];
const own=(obj,key)=>Object.prototype.hasOwnProperty.call(obj,key);

export function planSingleReservation(candidate, pinned) {
 if(!candidate||!pinned||typeof candidate!=="object"||
    typeof pinned!=="object"||
    Object.keys(candidate).sort().join("|")!==
      [...FIELDS,"scientific_authorized"].sort().join("|") ||
    Object.keys(pinned).sort().join("|")!==
      ["original_key_sha256","lane","owner_epoch","source_commit_sha",
       "frozen_predecision_sha256","external_owner_witness_pin_sha256",
       "claimed_sequence"].sort().join("|")) deny();
 for(const key of FIELDS) if(!own(candidate,key)||!own(pinned,key)||
   candidate[key]!==pinned[key])deny();
 for(const key of ["original_key_sha256","frozen_predecision_sha256",
 "external_owner_witness_pin_sha256"]) if(!H64.test(candidate[key]))deny();
 if(!H40.test(candidate.source_commit_sha)||
    !["Wingless","Yggdrasil"].includes(candidate.lane)||
    !validNumber(candidate.owner_epoch)||
    !validNumber(candidate.claimed_sequence)||
    candidate.scientific_authorized!==false)deny();
 const values=FIELDS.map(k=>candidate[k]);
 return Object.freeze({
  schema:"forge.f63.single-original-r35-r38-insert-plan.v1",
  sql:SQL,
  values:Object.freeze(values),
  requires_existing_r35_r38_table_and_triggers:true,
  requires_independently_authenticated_ckb_owner:true,
  requires_external_historical_lease_highwater:true,
  permits_retry_after_uncertain_commit:false,
  science_dispatch_authorized:false,
  worker_permit_issued:false,
  cloudflare_mutation_performed:false
 });
}

export function classifyReservationResult(plan,response) {
 // This readback is intentionally diagnostic only. A committed SQL write
 // remains consumed even on a response timeout; never retry automatically.
 if(!plan||plan.schema!=="forge.f63.single-original-r35-r38-insert-plan.v1")
   return "DENY_NO_VERIFIED_PLAN";
 if(!response ||response.success!==true||
    !response.meta||response.meta.changes!==1 ||
    response.meta.changed_db!==true)
   return "DENY_INDETERMINATE_NO_RETRY";
 return "R35_R38_STORAGE_CONSUMED_NOT_SCIENTIFIC_RELEASE";
}
