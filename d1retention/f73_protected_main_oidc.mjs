// F73: authenticate the REAL GitHub-hosted protected-main origin without scientific release.
// Observation ONLY. No new signer, controller, D1 write, or scientific permit.
// A signed engineering branch run must never be promoted into scientific owner.
import {createPublicKey, verify as rsaVerify} from "node:crypto";
const ISSUER="https://token.actions.githubusercontent.com";
const WELLKNOWN=ISSUER+"/.well-known/openid-configuration";
const AUD="forge-f73-observe-protected-main-no-science";
const REPO="spoonman136668-ai/FORGE";
const GITHUB="https://api.github.com";
const MAX=60000;
const MAXJWT=16000;
const hex40=/^[0-9a-f]{40}$/;
const isObj=x=>x!==null&&typeof x==="object"&&!Array.isArray(x);
const eligibleText=(s,max=300)=>typeof s==="string"&&s.length>0&&s.length<=max;
export class Denied extends Error{
 constructor(){super("F73_GITHUB_ISSUER_OR_AUTHORITY_NOT_AUTHENTICATED");}
}
const requireTrue=v=>{if(!v)throw new Denied();};
function decodePart(s){
 requireTrue(eligibleText(s,MAXJWT)&&/^[A-Za-z0-9_-]+$/.test(s));
 const v=Buffer.from(s,"base64url");
 requireTrue(v.length>0&&v.length<=MAX);
 return v;
}
const parsePart=s=>{
 const d=JSON.parse(decodePart(s).toString("utf8"));
 requireTrue(isObj(d));
 return d;
};
function originPins(env){
 requireTrue(isObj(env)&&env.GITHUB_REPOSITORY===REPO&&
  hex40.test(env.GITHUB_SHA)&&eligibleText(env.GITHUB_REF,180)&&
  env.GITHUB_REF.startsWith("refs/heads/")&&
  eligibleText(env.GITHUB_WORKFLOW_REF,500)&&
  eligibleText(env.GITHUB_RUN_ID,20)&&
  /^[1-9][0-9]{7,15}$/.test(env.GITHUB_RUN_ID)&&
  env.GITHUB_RUN_ATTEMPT==="1"&&env.GITHUB_EVENT_NAME==="push");
 const workflow=REPO+"/.github/workflows/forge-f73-protected-main-identity.yml@"+env.GITHUB_REF;
 requireTrue(env.GITHUB_WORKFLOW_REF===workflow);
 return {
  repository:REPO,ref:env.GITHUB_REF,workflow_ref:workflow,
  sha:env.GITHUB_SHA,run_id:env.GITHUB_RUN_ID,
  run_attempt:"1",event_name:"push",
 };
}
export function verifyJWT(jwt,jwks,pins,timeMillis){
 requireTrue(eligibleText(jwt,MAXJWT)&&isObj(jwks)&&Array.isArray(jwks.keys)&&
   jwks.keys.length>0&&jwks.keys.length<=25&&isObj(pins));
 const chunks=jwt.split(".");
 requireTrue(chunks.length===3);
 const head=parsePart(chunks[0]);
 const claims=parsePart(chunks[1]);
 requireTrue(head.alg==="RS256"&&head.typ==="JWT"&&
   eligibleText(head.kid,256));
 const matches=jwks.keys.filter(x=>x.kid===head.kid);
 requireTrue(matches.length===1);
 const key=matches[0];
 requireTrue(key.kty==="RSA"&&key.use==="sig"&&
   (!key.alg||key.alg==="RS256"));
 requireTrue(rsaVerify("RSA-SHA256",
   Buffer.from(chunks[0]+"."+chunks[1]),
   createPublicKey({key,format:"jwk"}),decodePart(chunks[2])));
 const want={
  iss:ISSUER,aud:AUD,repository:REPO,
  repository_owner:"spoonman136668-ai",...pins,
 };
 for(const [name,value] of Object.entries(want))
  requireTrue(typeof claims[name]==="string"&&claims[name]===value);
 const now=Math.floor(timeMillis/1000);
 requireTrue(Number.isSafeInteger(timeMillis)&&
  ["iat","nbf","exp"].every(k=>Number.isSafeInteger(claims[k]))&&
  claims.iat<=now+60&&claims.iat>=now-600&&
  claims.nbf<=now+60&&claims.nbf>=now-600&&
  claims.exp>now&&claims.exp<=now+600);
 requireTrue(eligibleText(claims.repository_id,24)&&/^[1-9][0-9]*$/.test(claims.repository_id));
 return {repository_id:Number(claims.repository_id)};
}
async function getJSON(url,fetcher,headers={}){
 requireTrue(typeof fetcher==="function"&&eligibleText(url,1500));
 const r=await fetcher(url,{method:"GET",redirect:"error",
  headers:{"Accept":"application/json",...headers}});
 requireTrue(r&&r.ok&&r.status===200&&r.url===url);
 const raw=await r.text();
 requireTrue(eligibleText(raw,MAX));
 const json=JSON.parse(raw);
 requireTrue(isObj(json));
 return json;
}
export async function observeRealOrigin({
 env=process.env,fetcher=fetch,now=Date.now()
}={}){
 const pins=originPins(env);
 requireTrue(eligibleText(env.ACTIONS_ID_TOKEN_REQUEST_TOKEN,16384)&&
  eligibleText(env.ACTIONS_ID_TOKEN_REQUEST_URL,2048));
 const request=new URL(env.ACTIONS_ID_TOKEN_REQUEST_URL);
 requireTrue(request.protocol==="https:"&&
  request.searchParams.get("audience")===null);
 request.searchParams.set("audience",AUD);
 // Only GitHub-hosted Actions supplies the OIDC URL and short-lived token.
 const result=await getJSON(request.href,fetcher,{
  Authorization:"Bearer "+env.ACTIONS_ID_TOKEN_REQUEST_TOKEN
 });
 requireTrue(eligibleText(result.value,MAXJWT));
 const config=await getJSON(WELLKNOWN,fetcher);
 requireTrue(config.issuer===ISSUER&&
  config.jwks_uri===ISSUER+"/.well-known/jwks");
 const jwks=await getJSON(config.jwks_uri,fetcher);
 const verified=verifyJWT(result.value,jwks,pins,now);
 const repo=await getJSON(GITHUB+"/repos/"+REPO,fetcher);
 requireTrue(repo.full_name===REPO&&repo.id===verified.repository_id);
 const run=await getJSON(GITHUB+"/repos/"+REPO+"/actions/runs/"+pins.run_id,fetcher);
 requireTrue(String(run.id)===pins.run_id&&
  run.head_sha===pins.sha&&run.head_branch===pins.ref.slice(11)&&
  run.event==="push"&&run.run_attempt===1&&
  run.path===".github/workflows/forge-f73-real-oidc-readonly.yml");
 const main=await getJSON(GITHUB+"/repos/"+REPO+"/branches/main",fetcher);
 requireTrue(isObj(main.commit)&&hex40.test(main.commit.sha)&&
  typeof main.protected==="boolean");
 // Authenticated policy observation independently joins real protected-main
 // rules, required Linux+Windows checks and exact current run commit. Even a
 // protected-main GitHub identity cannot mint scientific first-use authority.
 requireTrue(eligibleText(env.GITHUB_TOKEN,2048));
 const rules=await getJSON(GITHUB+"/repos/"+REPO+"/rulesets/25031517",fetcher,
  {Authorization:"Bearer "+env.GITHUB_TOKEN});
 const status=rules.rules?.find(x=>x.type==="required_status_checks");
 const contexts=status?.parameters?.required_status_checks;
 requireTrue(rules.id===25031517&&rules.enforcement==="active"&&
  rules.target==="branch"&&
  Array.isArray(rules.conditions?.ref_name?.include)&&
  rules.conditions.ref_name.include.includes("refs/heads/main")&&
  Array.isArray(contexts)&&
  ["linux","windows"].every(name=>contexts.some(c=>c.context===name)));
 requireTrue(main.protected===true);
 const onMain=pins.ref==="refs/heads/main";
 if(onMain)requireTrue(main.commit.sha===pins.sha);
 return {
  schema:"forge.f73.protected-main-github-oidc-readonly.v1",
  repository:REPO,
  oidc_signature_and_live_jwks_verified:true,
  signed_run_source_and_repository_identity_joined:true,
  github_repository_id:repo.id,
  run_id:Number(pins.run_id),
  source_sha:pins.sha,
  run_attempt:1,
  workflow_ref:pins.workflow_ref,
  on_protected_main_workflow: onMain,
  on_protected_main_science_issuer:false,
  protected_main_ruleset_enforced:true,
  required_linux_and_windows_checks_observed:true,
  main_branch_protected_observed:main.protected,
  independently_accepted_current_scientific_owner:false,
  complete_two_lane_original_firstuse_attested:false,
  private_restorable_d1_backup_verified:false,
  live_cloudflare_firstuse_schema_installed:false,
  worker_execution_permit_issued:false,
  scientific_originals_dispatched:0,
  disposition:onMain
   ? "REAL_PROTECTED_MAIN_GITHUB_OIDC_VERIFIED_NO_SCIENCE_OWNER"
   : "REAL_ENGINEERING_GITHUB_OIDC_VERIFIED_NO_SCIENCE_OWNER",
 };
}
if(process.argv[1]?.endsWith("f73_real_oidc_readonly.mjs")){
 try{
  const r=await observeRealOrigin();
  process.stdout.write(JSON.stringify(r)+"\n");
  process.stdout.write("F73_PROTECTED_ORIGINAL_SCIENCE=DENIED\n");
 }catch(e){
  process.stderr.write("F73_REAL_OIDC_READONLY_CHECK=BLOCKED\n");
  process.exitCode=1;
 }
}
