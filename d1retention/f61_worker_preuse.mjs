// F61: source-only Cloudflare Worker release-boundary preflight.
//
// THIS FILE DOES NOT EXPORT A FETCH HANDLER, DOES NOT INSERT INTO D1, AND
// CANNOT ISSUE A WORKER PERMIT. A caller must NEVER treat advisory facts
// or a valid GitHub OIDC identity as independent science authorization.
const DENIED = "F61_EXISTING_OWNER_OR_DURABLE_FIRSTUSE_NOT_AUTHENTICATED";
const ISSUER = "https://token.actions.githubusercontent.com";
const AUD = "forge-f61-ckb-preuse-observation-only";
const REPO = "spoonman136668-ai/ckb-plane";
const WORKFLOW = REPO + "/.github/workflows/research-loop-headless-wake-v2.yml@refs/heads/main";
const KEYSET = ISSUER + "/.well-known/jwks";
const HEX40 = /^[0-9a-f]{40}$/;
const HEX64 = /^[0-9a-f]{64}$/;
const MAX_JWT = 16000;
const tableNames = [
 "forge_original_preuse_claims",
 "forge_original_preuse_claims_update_immutable",
 "forge_original_preuse_claims_delete_immutable",
 "forge_original_preuse_claims_insert_monotonic"
];

export class Blocked extends Error {
 constructor(){ super(DENIED); this.name = "F61Denied"; }
}
const requireTrue = c => { if (!c) throw new Blocked(); };
const str = (x, length = 256) => typeof x === "string" && x.length > 0 && x.length <= length;
const isInt = x => Number.isSafeInteger(x) && x > 0;
const decode64 = s => {
 requireTrue(str(s, 20000) && /^[A-Za-z0-9_-]+$/.test(s));
 const b64 = s.replace(/-/g, "+").replace(/_/g, "/");
 const bytes = Uint8Array.from(atob(b64.padEnd(Math.ceil(b64.length/4)*4,"=")), c=>c.charCodeAt(0));
 requireTrue(bytes.length > 0 && bytes.length < 12000);
 return bytes;
};
const json = s => {
 const val = JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(decode64(s)));
 requireTrue(val && typeof val === "object" && !Array.isArray(val));
 return val;
};
const exact = (actual, expected) => requireTrue(str(actual,2048) && actual === expected);

export async function verifyIssuer(jwt, jwks, trust, currentMillis, subtle = crypto.subtle) {
 requireTrue(str(jwt, MAX_JWT) && trust && typeof trust === "object");
 // An independently configured, exact subject is REQUIRED. The GitHub
 // organization's OIDC "sub" is customized; guessing its template is unsafe.
 requireTrue(trust.schema === "forge.f61.external-ckb-prospective-pins.v1" &&
  HEX40.test(trust.approved_source_sha) && str(trust.pinned_subject,1024) &&
  str(trust.protected_workflow_ref,512) && trust.protected_workflow_ref === WORKFLOW &&
  trust.exact_repository === REPO && trust.expected_event === "workflow_dispatch" &&
  trust.expected_audience === AUD && isInt(trust.approved_run_id) &&
  isInt(trust.owner_epoch) && isInt(trust.decision_sequence) &&
  HEX64.test(trust.complete_consumed_active_uncertain_history_sha256) &&
  HEX64.test(trust.external_authority_custody_sha256) &&
  HEX64.test(trust.authorized_original_key_sha256) &&
  HEX64.test(trust.authorized_predecision_sha256) &&
  HEX64.test(trust.authorized_owner_witness_pin_sha256) &&
  str(trust.authorized_lane,32) &&
  ["Wingless","Yggdrasil"].includes(trust.authorized_lane));
 requireTrue(Number.isSafeInteger(currentMillis));
 const pieces = jwt.split(".");
 requireTrue(pieces.length === 3);
 const header = json(pieces[0]);
 const claims = json(pieces[1]);
 requireTrue(header.alg === "RS256" && header.typ === "JWT" &&
  str(header.kid) && jwks && Array.isArray(jwks.keys) &&
  jwks.keys.length > 0 && jwks.keys.length <= 25);
 const keys = jwks.keys.filter(k=>k.kid === header.kid);
 requireTrue(keys.length === 1 && keys[0].kty === "RSA" &&
  keys[0].use === "sig" && (!keys[0].alg || keys[0].alg === "RS256"));
 const key = await subtle.importKey("jwk", keys[0],
  {name:"RSASSA-PKCS1-v1_5",hash:"SHA-256"},false,["verify"]);
 const signed = new TextEncoder().encode(pieces[0]+"."+pieces[1]);
 requireTrue(await subtle.verify("RSASSA-PKCS1-v1_5",key,decode64(pieces[2]),signed));
 const now = Math.floor(currentMillis / 1000);
 requireTrue([claims.iat,claims.nbf,claims.exp].every(Number.isSafeInteger) &&
  claims.iat >= now - 600 && claims.iat <= now + 60 &&
  claims.nbf >= now - 600 && claims.nbf <= now + 60 &&
  claims.exp > now && claims.exp <= now + 600);
 const expected = {
  iss: ISSUER, aud: AUD, repository:REPO, repository_owner:"spoonman136668-ai",
  ref:"refs/heads/main", workflow_ref:WORKFLOW,
  event_name:"workflow_dispatch", run_attempt:"1",
  sub:trust.pinned_subject, sha:trust.approved_source_sha,
  run_id:String(trust.approved_run_id)
 };
 for (const [name,want] of Object.entries(expected)) exact(claims[name],want);
 return { verified_github_identity:true, run_id:trust.approved_run_id };
}

function candidateCheck(c,trust) {
 requireTrue(c && typeof c === "object" && c.scientific_authorized === false &&
  c.lane === trust.authorized_lane &&
  HEX64.test(c.original_key_sha256) &&
  c.original_key_sha256 === trust.authorized_original_key_sha256 &&
  c.owner_epoch === trust.owner_epoch &&
  c.claimed_sequence === trust.decision_sequence &&
  c.source_commit_sha === trust.approved_source_sha &&
  c.frozen_predecision_sha256 === trust.authorized_predecision_sha256 &&
  c.external_owner_witness_pin_sha256 === trust.authorized_owner_witness_pin_sha256);
}
async function select(db, sql, args=[]) {
 requireTrue(db && typeof db.prepare==="function" && typeof sql==="string");
 const stmt = db.prepare(sql);
 requireTrue(stmt && typeof stmt.bind==="function");
 const response = await stmt.bind(...args).all();
 requireTrue(response && response.success === true && Array.isArray(response.results));
 return response.results;
}

// The only code path in F61 is read-only and NON-AUTHORIZING.
// SQLite/D1 SELECT observations are not an atomic permission to dispatch;
// that must be a later Worker transaction plus owner worker-side fencing.
export async function inspectExistingBoundary({ jwt, trust, candidate, db,
  now = Date.now(), fetcher = fetch, subtle = crypto.subtle }) {
 const failed = {
  schema:"forge.f61.readonly-existing-worker-preuse-boundary.v1",
  disposition:"BLOCKED_UNTIL_PROTECTED_MAIN_AUTHORITY_AND_WORKER_CAS",
  github_issuer_verified:false,
  existing_claim_table_and_immutability_observed:false,
  prior_duplicate_observed:false,
  independently_authenticated_current_owner:false,
  all_lane_lease_history_authenticated:false,
  first_use_atomic_claim_consumed:false,
  worker_dispatch_permit_issued:false,
  scientific_execution_authorized:false,
  forge_owner_cutover_authorized:false
 };
 try {
  requireTrue(typeof fetcher==="function");
  const response=await fetcher(KEYSET, {redirect:"error",method:"GET",
   headers:{"Accept":"application/json"}});
  requireTrue(response && response.ok && response.status === 200 &&
   response.url === KEYSET);
  const raw=await response.text();
  requireTrue(str(raw,65536));
  const jwks=JSON.parse(raw);
  await verifyIssuer(jwt,jwks,trust,now,subtle);
  failed.github_issuer_verified=true;
  candidateCheck(candidate,trust);
  const table=await select(db,
   "SELECT name FROM sqlite_master WHERE name IN ('forge_original_preuse_claims','forge_original_preuse_claims_update_immutable','forge_original_preuse_claims_delete_immutable','forge_original_preuse_claims_insert_monotonic') ORDER BY name");
  const names=table.map(x=>x.name);
  requireTrue(names.length===tableNames.length &&
   tableNames.every(n=>names.filter(x=>x===n).length===1));
  failed.existing_claim_table_and_immutability_observed=true;
  const previous=await select(db,
   "SELECT COUNT(*) AS n FROM forge_original_preuse_claims WHERE original_key_sha256=?",
   [candidate.original_key_sha256]);
  requireTrue(previous.length===1 && isIntOrZero(previous[0].n));
  failed.prior_duplicate_observed=previous[0].n>0;
  requireTrue(previous[0].n===0);
  const floor=await select(db,
   "SELECT MAX(claimed_sequence) AS sequence, MAX(owner_epoch) AS epoch FROM forge_original_preuse_claims");
  requireTrue(floor.length===1 &&
   (floor[0].sequence===null || Number.isSafeInteger(floor[0].sequence)) &&
   (floor[0].epoch===null || Number.isSafeInteger(floor[0].epoch)));
  requireTrue(floor[0].sequence===null ||
   candidate.claimed_sequence>floor[0].sequence);
  requireTrue(floor[0].epoch===null ||
   candidate.owner_epoch>=floor[0].epoch);
  // Success HERE is still a preflight; no transaction or release was made.
  failed.disposition="READ_ONLY_PREUSE_CANDIDATE_MATCH_NO_PERMIT";
  return failed;
 } catch {
  return failed;
 }
}
const isIntOrZero = x=> Number.isSafeInteger(x) && x >= 0;
