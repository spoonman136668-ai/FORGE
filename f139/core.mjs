// F139: source-pinned, development-only FORGE controller kernel.
// No direct network or persistent-storage access. No original science rights.
export const REPO = 'spoonman136668-ai/FORGE';
export const WORKFLOW = 'forge-f139-development-worker.yml';
export const SCHEMA = 'forge.f139.unified-development-controller.v1';
export const ZERO = '0'.repeat(64);
export const MAX_DAILY_STARTS = 48;
const SHA = /^[a-f0-9]{40}$/;
const TICKET = /^f139-[a-z0-9][a-z0-9-]{2,47}$/;
const LANES = new Set(['Wingless', 'Yggdrasil', 'Qualification']);
const STAGES = new Set(['IDLE', 'START_RISK', 'WAIT_PROVIDER', 'VERIFIED', 'QUARANTINED']);
export class Quarantine extends Error { constructor(message) { super('F139_'+message); this.name='Quarantine'; } }
export function need(cond, reason) { if (!cond) throw new Quarantine(reason); }
const validSHA = value => typeof value === 'string' && SHA.test(value);
const validTicket = value => typeof value === 'string' && TICKET.test(value);
const nonnegative = value => Number.isSafeInteger(value) && value >= 0;
export function timestamp(value) {
  need(typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(value)
    && /(Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value)),
    'PROVIDER_TIME_INVALID');
  return Date.parse(value);
}
export function validateTask(task, expectedSource) {
  need(task && typeof task === 'object' && Object.keys(task).sort().join(',') ===
    'lane,source_sha,ticket', 'TASK_FIELDS_UNTRUSTED');
  need(validTicket(task.ticket) && LANES.has(task.lane) && validSHA(task.source_sha)
    && task.source_sha === expectedSource, 'TASK_UNQUALIFIED_OR_SOURCE_DRIFT');
  return task;
}
export function validateState(state) {
  need(state && state.schema === SCHEMA && Number.isSafeInteger(state.version) && state.version >= 0
    && Number.isSafeInteger(state.epoch) && state.epoch > 0
    && STAGES.has(state.stage) && nonnegative(state.daily_starts)
    && typeof state.utc_day === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(state.utc_day)
    && typeof state.last_hash === 'string' && /^[a-f0-9]{64}$/.test(state.last_hash), 'STATE_IDENTITY_INVALID');
  if (state.stage !== 'IDLE') validateTask(state.active, state.active?.source_sha);
  else need(state.active === null, 'IDLE_HAS_ACTIVE_INTENT');
  if (state.stage === 'START_RISK' || state.stage === 'WAIT_PROVIDER') {
    need(state.active !== null && Number.isSafeInteger(state.epoch)
      && typeof state.started_at === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(state.started_at), 'UNFENCED_START_RISK');
  }
  return state;
}
export function makeInitial(day, epoch = 1) {
  need(/^\d{4}-\d{2}-\d{2}$/.test(day) && Number.isSafeInteger(epoch) && epoch>0, 'INITIAL_IDENTITY');
  return {schema:SCHEMA, version:0, epoch, stage:'IDLE', active:null,
    run_id:null, started_at:null, daily_starts:0, utc_day:day, last_hash:ZERO};
}
export function selectNext(state, tasks, completedTickets, mainSHA, nowISO) {
  validateState(state);
  need(state.stage === 'IDLE' && validSHA(mainSHA) && typeof nowISO==='string'
    && /^\d{4}-\d{2}-\d{2}T/.test(nowISO), 'SELECTION_NOT_ALLOWED');
  need(Array.isArray(tasks) && tasks.length <= 100 && completedTickets instanceof Set,
    'QUEUE_UNTRUSTED');
  const unique = new Set();
  for (const t of tasks) {
    validateTask(t, mainSHA);
    need(!unique.has(t.ticket), 'DUPLICATE_TICKET'); unique.add(t.ticket);
  }
  const today = nowISO.slice(0,10);
  const count = state.utc_day === today ? state.daily_starts : 0;
  need(count < MAX_DAILY_STARTS, 'DAILY_BUDGET_EXHAUSTED');
  return tasks.find(t => !completedTickets.has(t.ticket)) ?? null;
}
export function claim(state, task, nowISO) {
  validateState(state); validateTask(task, task.source_sha);
  need(state.stage === 'IDLE', 'CONCURRENT_CLAIM');
  const day=nowISO.slice(0,10), count=state.utc_day===day?state.daily_starts:0;
  need(count < MAX_DAILY_STARTS, 'DAILY_START_LIMIT');
  // START_RISK is durable BEFORE any provider POST. Never dispatch again on restart.
  return {...state,version:state.version+1,stage:'START_RISK',active:{...task},
    run_id:null,started_at:nowISO,utc_day:day,daily_starts:count+1};
}
export function sent(state) {
  validateState(state); need(state.stage==='START_RISK','INVALID_POST_TRANSITION');
  return {...state,version:state.version+1,stage:'WAIT_PROVIDER'};
}
export function observed(state, metadata) {
  validateState(state);
  need(state.stage==='START_RISK'||state.stage==='WAIT_PROVIDER','OBSERVATION_PHASE_INVALID');
  if (metadata?.verdict==='PENDING') return state;
  need(metadata?.verdict==='VERIFIED' && Number.isSafeInteger(metadata.run_id) && metadata.run_id>0,
    'UNVERIFIED_PROVIDER_RESULT');
  return {...state,version:state.version+1,stage:'VERIFIED',run_id:metadata.run_id};
}
export function finish(state) {
  validateState(state); need(state.stage==='VERIFIED' && state.run_id>0,'TERMINAL_NOT_VERIFIED');
  return {...state,version:state.version+1,stage:'IDLE',active:null,run_id:null,started_at:null};
}
export function jobEvidence(run, jobs, artifacts, ticket, sourceSHA, createdAfter) {
  need(validTicket(ticket) && validSHA(sourceSHA), 'WITNESS_INPUT_INVALID');
  if (!run) return {verdict:'PENDING',reason:'RUN_NOT_VISIBLE_NO_REDISPATCH'};
  const expectedName='F139 '+ticket;
  need(run.display_title===expectedName && run.name==='FORGE F139 development worker'
    && run.path==='.github/workflows/'+WORKFLOW && run.head_branch==='main'
    && run.event==='workflow_dispatch' && run.head_sha===sourceSHA
    && run.run_attempt===1 && Number.isSafeInteger(run.id) && run.id>0
    && timestamp(run.created_at)>=timestamp(createdAfter),
    'PROVIDER_IDENTITY_MISMATCH');
  if (run.status !== 'completed') {
    need(['queued','requested','in_progress','waiting','pending'].includes(run.status), 'UNKNOWN_RUN_STATUS');
    return {verdict:'PENDING',reason:'RUN_UNFINISHED_NO_REDISPATCH'};
  }
  need(run.conclusion==='success','WORKER_FAILED_NO_REPLAY');
  need(Array.isArray(jobs) && Array.isArray(artifacts), 'PROVIDER_JOBS_OR_ARTIFACTS_ABSENT');
  for(const os of ['ubuntu-latest','windows-latest']) {
    const name='execute ('+os+')';
    need(jobs.filter(j=>j.name===name).length===1 && jobs.some(j=>j.name===name
      && j.status==='completed' && j.conclusion==='success'), 'HOSTED_EXECUTION_UNQUALIFIED_'+os);
    const artifactName='forge-f139-dev-receipt-'+os;
    need(artifacts.filter(a=>a.name===artifactName).length===1
      && artifacts.some(a=>a.name===artifactName && a.expired===false
        && a.workflow_run?.id===run.id && a.workflow_run?.head_sha===sourceSHA
        && typeof a.digest==='string' && /^sha256:[a-f0-9]{64}$/.test(a.digest)),
        'ARTIFACT_CUSTODY_UNQUALIFIED_'+os);
  }
  return {verdict:'VERIFIED',run_id:run.id,
    status:'PROVIDER_VERIFIED_DEVELOPMENT_ONLY_NOT_ORIGINAL_SCIENCE',
    source_sha:sourceSHA, ticket,scientific_first_use_authorized:false,
    accepted_ref_mutations:0};
}
export async function signTicket(secret, task, epoch) {
  validateTask(task,task.source_sha);
  need(typeof secret==='string' && secret.length>=32 && Number.isSafeInteger(epoch) && epoch>0,
    'DISPATCH_SECRET_OR_EPOCH_NOT_CONFIGURED');
  const payload=['F139-DISPATCH-V1',REPO,WORKFLOW,task.ticket,task.lane,task.source_sha,String(epoch)].join('\n')+'\n';
  const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(secret),
    {name:'HMAC',hash:'SHA-256'},false,['sign']);
  const signed=new Uint8Array(await crypto.subtle.sign('HMAC',key,new TextEncoder().encode(payload)));
  return [...signed].map(x=>x.toString(16).padStart(2,'0')).join('');
}
export async function eventDigest(last_hash, next, kind) {
  need(typeof last_hash==='string'&&/^[a-f0-9]{64}$/.test(last_hash)
    && /^[A-Z_]+$/.test(kind),'EVENT_CHAIN_INVALID');
  const e=JSON.stringify({kind,previous_sha256:last_hash,version:next.version,
    stage:next.stage,ticket:next.active?.ticket??null,run_id:next.run_id,
    daily_starts:next.daily_starts,utc_day:next.utc_day,epoch:next.epoch});
  const digest=new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(e)));
  return [...digest].map(x=>x.toString(16).padStart(2,'0')).join('');
}
