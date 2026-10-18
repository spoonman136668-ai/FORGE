// F139 development-only Cloudflare Worker runtime (disabled unless explicitly cut over).
// Existing F136/F137 controllers remain authoritative until separately retired.
// This module has no cron trigger, task-seeding API, or public write endpoint.
import {REPO, WORKFLOW, ZERO, Quarantine, need, validateState,
  validateTask, selectNext, claim, sent, observed, finish, jobEvidence,
  signTicket, eventDigest, timestamp} from './core.mjs';

const ENDPOINT = 'https://api.github.com/repos/'+REPO;
const MAX_PAGES = 5;
function qualifiedConfig(env) {
  need(env && env.F139_ACTIVE==='true' && env.F139_LEGACY_SUSPENDED==='true',
    'INACTIVE_OR_LEGACY_CONTROLLER_STILL_AUTHORITATIVE');
  need(env.F139_DB && typeof env.F139_GITHUB_TOKEN==='string'
    && env.F139_GITHUB_TOKEN.length>=20 && typeof env.F139_HMAC_KEY==='string'
    && env.F139_HMAC_KEY.length>=32 && /^[a-f0-9]{40}$/.test(env.F139_MAIN_SHA||''),
    'RUNTIME_CREDENTIALS_OR_FROZEN_MAIN_MISSING');
}
export class D1Authority {
  constructor(db) { this.db=db; }
  async read() {
    const row=await this.db.prepare('SELECT revision, state_json, event_hash FROM f139_controller WHERE id=1').first();
    need(row && Number.isSafeInteger(row.revision) && typeof row.state_json==='string', 'DURABLE_CONTROLLER_NOT_INITIALIZED');
    const state=validateState(JSON.parse(row.state_json));
    need(state.version===row.revision && state.last_hash===row.event_hash, 'DURABLE_STATE_OR_HASH_DRIFT');
    const last=await this.db.prepare('SELECT revision,event_hash,state_json,event_kind,previous_hash FROM f139_events ORDER BY revision DESC LIMIT 1').first();
    if (state.version===0) need(!last && state.last_hash===ZERO, 'INITIAL_LEDGER_MISMATCH');
    else {
      need(last && last.revision===state.version && last.event_hash===state.last_hash
        && last.state_json===row.state_json && typeof last.event_kind==='string'
        && /^[A-Z_]+$/.test(last.event_kind) && /^[a-f0-9]{64}$/.test(last.previous_hash),
        'EVENT_CHAIN_MISSING');
      const independent=await eventDigest(last.previous_hash,state,last.event_kind);
      need(independent===last.event_hash,'DURABLE_EVENT_DIGEST_INVALID');
    }
    return state;
  }
  async tasks() {
    const rows=await this.db.prepare('SELECT ticket,lane,source_sha FROM f139_tasks ORDER BY priority DESC,ticket ASC LIMIT 101').all();
    need(Array.isArray(rows?.results) && rows.results.length<=100,'QUEUE_CAP_EXCEEDED');
    return rows.results;
  }
  async completed() {
    const rows=await this.db.prepare('SELECT ticket FROM f139_completed LIMIT 101').all();
    need(Array.isArray(rows?.results)&&rows.results.length<=100,'COMPLETED_CUSTODY_OVERFLOW');
    return new Set(rows.results.map(x=>x.ticket));
  }
  async commit(old,next,kind) {
    validateState(old);validateState(next);
    need(next.version===old.version+1 && next.epoch===old.epoch && next.last_hash===old.last_hash,
      'NONMONOTONIC_CAS');
    const digest=await eventDigest(old.last_hash,next,kind);
    const fresh={...next,last_hash:digest};
    // f139_append_event trigger writes matching append-only journal atomically.
    const result=await this.db.prepare('UPDATE f139_controller SET revision=?,state_json=?,event_hash=?,event_kind=?,previous_hash=? WHERE id=1 AND revision=? AND event_hash=?')
      .bind(fresh.version,JSON.stringify(fresh),digest,kind,old.last_hash,old.version,old.last_hash).run();
    need(result?.meta?.changes===1,'D1_CONCURRENT_OWNER_OR_SOURCE_DRIFT');
    return fresh;
  }
  async complete(ticket,runId,sourceSHA) {
    need(typeof ticket==='string'&&Number.isSafeInteger(runId)&&runId>0&&/^[a-f0-9]{40}$/.test(sourceSHA),
      'COMPLETION_IDENTITY');
    // Repeating this exact write is safe; it never re-dispatches a worker.
    await this.db.prepare('INSERT OR IGNORE INTO f139_completed(ticket,run_id,source_sha) VALUES(?,?,?)')
      .bind(ticket,runId,sourceSHA).run();
    const row=await this.db.prepare('SELECT run_id,source_sha FROM f139_completed WHERE ticket=?').bind(ticket).first();
    need(row?.run_id===runId && row?.source_sha===sourceSHA,'CONFLICTING_COMPLETION');
  }
}
export class GitHubDevelopmentProvider {
  constructor(token,transport=fetch) { this.token=token;this.transport=transport; }
  async api(path, method='GET', payload) {
    need(typeof path==='string'&&path.startsWith('/')&&!path.includes('..')
      && (method==='GET'||method==='POST'),'UNTRUSTED_GITHUB_ROUTE');
    const resp=await this.transport(ENDPOINT+path,{method,headers:{
      'Accept':'application/vnd.github+json',
      'Authorization':'Bearer '+this.token,
      'X-GitHub-Api-Version':'2022-11-28',
      ...(payload?{'Content-Type':'application/json'}:{})},
      ...(payload?{body:JSON.stringify(payload)}:{})});
    need(resp.status===(method==='POST'?204:200),'GITHUB_PROVIDER_UNAVAILABLE_OR_REJECTED');
    return method==='POST'?null:resp.json();
  }
  async source() {const v=await this.api('/branches/main');return v?.commit?.sha;}
  async launch(task,epoch,signature) {
    need(task&&typeof signature==='string'&&/^[a-f0-9]{64}$/.test(signature),'BAD_DISPATCH_SIGNATURE');
    await this.api('/actions/workflows/'+WORKFLOW+'/dispatches','POST',{
      ref:'main',inputs:{ticket:task.ticket,lane:task.lane,
        source_sha:task.source_sha,epoch:String(epoch),signature}});
  }
  async locate(task,startedAt) {
    let found=[];let complete=false;
    for(let page=1;page<=MAX_PAGES;page++){
      const idx=await this.api('/actions/workflows/'+WORKFLOW+'/runs?branch=main&event=workflow_dispatch&per_page=100&page='+page);
      need(Array.isArray(idx?.workflow_runs) && Number.isSafeInteger(idx?.total_count), 'HISTORY_UNTRUSTED');
      for(const item of idx.workflow_runs) {
        if(item.display_title==='F139 '+task.ticket) found.push(item);
      }
      if(idx.workflow_runs.length===0 || idx.workflow_runs.length<100){complete=true;break;}
      const oldest=idx.workflow_runs[idx.workflow_runs.length-1];
      if(oldest?.created_at && timestamp(oldest.created_at)<timestamp(startedAt)){complete=true;break;}
    }
    need(complete,'GITHUB_HISTORY_TOO_BUSY_OR_TRUNCATED');
    need(found.length<=1,'DUPLICATE_PROVIDER_START_RISK');
    if(!found.length)return {verdict:'PENDING',reason:'RUN_NOT_VISIBLE_NO_REDISPATCH'};
    const run=found[0];
    if(run.status!=='completed')return jobEvidence(run,null,null,task.ticket,task.source_sha,startedAt);
    const [jobs,arts]=await Promise.all([
      this.api('/actions/runs/'+run.id+'/jobs?per_page=100'),
      this.api('/actions/runs/'+run.id+'/artifacts?per_page=100')]);
    need(Number.isSafeInteger(jobs.total_count) && jobs.total_count===jobs.jobs?.length
      && Number.isSafeInteger(arts.total_count) && arts.total_count===arts.artifacts?.length,
      'PROVIDER_JOBS_OR_ARTIFACTS_TRUNCATED');
    return jobEvidence(run,jobs.jobs,arts.artifacts,task.ticket,task.source_sha,startedAt);
  }
}
export async function runOnce({store,provider,nowISO,sourceSHA,secret,epoch}) {
  // Only an independently enabled host can call this; never from public requests.
  const main=await provider.source();
  need(main===sourceSHA,'MAIN_SOURCE_DRIFT');
  let state=await store.read();
  need(state.epoch===epoch,'CONTROLLER_EPOCH_CHANGED');
  if(state.stage==='QUARANTINED')throw new Quarantine('STICKY_QUARANTINE');
  if(state.stage==='IDLE'){
    const selected=selectNext(state,await store.tasks(),await store.completed(),sourceSHA,nowISO);
    if(!selected)return {phase:'EMPTY_AUTHORIZED_QUEUE',science_authorized:false};
    const intent=await store.commit(state,claim(state,selected,nowISO),'START_RISK');
    // No retries on an ambiguous 204, crash, timeout, or interrupted call.
    const signature=await signTicket(secret,selected,intent.epoch);
    await provider.launch(selected,intent.epoch,signature);
    await store.commit(intent,sent(intent),'PROVIDER_POST_OBSERVED');
    return {phase:'DISPATCHED_ONCE_WAITING_PROVIDER',ticket:selected.ticket,science_authorized:false};
  }
  if(state.stage==='START_RISK'||state.stage==='WAIT_PROVIDER'){
    const result=await provider.locate(state.active,state.started_at);
    if(result.verdict==='PENDING')return {phase:'PENDING_NO_REDISPATCH',reason:result.reason,
      ticket:state.active.ticket,science_authorized:false};
    state=await store.commit(state,observed(state,result),'PROVIDER_VERIFIED');
    // Read-only verified terminal; no scientific original can be activated.
  }
  if(state.stage==='VERIFIED'){
    const ticket=state.active.ticket;
    await store.complete(ticket,state.run_id,state.active.source_sha);
    const idle=await store.commit(state,finish(state),'DEV_TERMINAL_RETAINED');
    // Launch at most one new task after a verified terminal in one tick.
    const next=selectNext(idle,await store.tasks(),await store.completed(),sourceSHA,nowISO);
    if(!next)return {phase:'DEVELOPMENT_TERMINAL_RETAINED_QUEUE_EMPTY',ticket,science_authorized:false};
    const intent=await store.commit(idle,claim(idle,next,nowISO),'START_RISK');
    const signature=await signTicket(secret,next,intent.epoch);
    await provider.launch(next,intent.epoch,signature);
    await store.commit(intent,sent(intent),'PROVIDER_POST_OBSERVED');
    return {phase:'AUTOMATIC_DEVELOPMENT_SUCCESSION',previous_ticket:ticket,
      ticket:next.ticket,science_authorized:false};
  }
  throw new Quarantine('UNSUPPORTED_PHASE');
}
export default {
  async fetch() { return new Response('Not Found',{status:404}); },
  async scheduled(_event,env,ctx){
    if(env?.F139_ACTIVE!=='true')return; // inert before explicit cutover
    ctx.waitUntil((async()=>{
      qualifiedConfig(env);
      const store=new D1Authority(env.F139_DB);
      const provider=new GitHubDevelopmentProvider(env.F139_GITHUB_TOKEN);
      return runOnce({store,provider,nowISO:new Date().toISOString(),
        sourceSHA:env.F139_MAIN_SHA,secret:env.F139_HMAC_KEY,
        epoch:Number(env.F139_OWNER_EPOCH)});
    })());
  }
};
