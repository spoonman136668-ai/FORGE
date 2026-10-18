import test from 'node:test';
import assert from 'node:assert/strict';
import {Quarantine,makeInitial,claim,selectNext,validateTask,jobEvidence,
        signTicket,eventDigest} from './core.mjs';
import {runOnce,GitHubDevelopmentProvider} from './cloudflare.mjs';
const SHA='e1b16d0a4097e9fd3d61c9ee635486a72395cf4b';
const OLD='e2fca32e0d4439aed801dac6b697ecea28855017';
const SECRET='f139-test-hmac-secret-never-deploy-00000000000000000000';
const DATE='2026-10-18T14:10:00.000Z';
const tasks=[
  {ticket:'f139-wingless-dev-001',lane:'Wingless',source_sha:SHA},
  {ticket:'f139-yggdrasil-dev-002',lane:'Yggdrasil',source_sha:SHA}
];
class Store {
  constructor(){this.state=makeInitial('2026-10-18');this.queue=structuredClone(tasks);this.done=new Map();this.events=[];}
  async read(){return structuredClone(this.state);}
  async tasks(){return structuredClone(this.queue);}
  async completed(){return new Set(this.done.keys());}
  async commit(old,next,kind){
    assert.equal(old.version,this.state.version,'stale owner');
    assert.equal(old.last_hash,this.state.last_hash);
    assert.equal(next.version,old.version+1);
    const hash=await eventDigest(old.last_hash,next,kind);
    this.state={...structuredClone(next),last_hash:hash};
    this.events.push({kind,hash,version:next.version});
    return structuredClone(this.state);
  }
  async complete(ticket,runId,sha){
    if(this.done.has(ticket))assert.deepEqual(this.done.get(ticket),{runId,sha});
    else this.done.set(ticket,{runId,sha});
  }
}
class Provider {
  constructor(){this.started=[];this.outcome={verdict:'PENDING',reason:'WAIT'};this.main=SHA;}
  async source(){return this.main;}
  async launch(task,epoch,signature){this.started.push({task,epoch,signature});}
  async locate(task){this.lastLookup=task.ticket;return this.outcome;}
}
const run=(store,provider)=>runOnce({store,provider,nowISO:DATE,sourceSHA:SHA,secret:SECRET,epoch:1});
const reject=fn=>assert.rejects(fn,Quarantine);
test('two tasks automatically succeed, advance, and never duplicate',async()=>{
  const db=new Store(),gh=new Provider();
  assert.equal((await run(db,gh)).phase,'DISPATCHED_ONCE_WAITING_PROVIDER');
  assert.equal(db.state.stage,'WAIT_PROVIDER');
  assert.equal(db.state.daily_starts,1);
  assert.equal((await run(db,gh)).phase,'PENDING_NO_REDISPATCH');
  assert.equal(gh.started.length,1);
  gh.outcome={verdict:'VERIFIED',run_id:9876543};
  const next=await run(db,gh);
  assert.equal(next.phase,'AUTOMATIC_DEVELOPMENT_SUCCESSION');
  assert.equal(next.previous_ticket,tasks[0].ticket);
  assert.equal(next.ticket,tasks[1].ticket);
  assert.equal(gh.started.length,2);
  assert.equal(db.done.get(tasks[0].ticket).runId,9876543);
  gh.outcome={verdict:'VERIFIED',run_id:9876544};
  assert.equal((await run(db,gh)).phase,'DEVELOPMENT_TERMINAL_RETAINED_QUEUE_EMPTY');
  assert.equal(gh.started.length,2);
  assert.equal(db.state.stage,'IDLE');
  assert.equal(db.done.size,2);
  assert.equal(db.events.length,8);
});
test('crash after durable START_RISK never redispatches',async()=>{
  const db=new Store(),gh=new Provider();
  const prior=await db.read();
  await db.commit(prior,claim(prior,tasks[0],DATE),'START_RISK');
  for(let i=0;i<5;i++) assert.equal((await run(db,gh)).phase,'PENDING_NO_REDISPATCH');
  assert.equal(gh.started.length,0);
  assert.equal(db.state.daily_starts,1);
});
test('provider POST timeout remains fenced',async()=>{
  const db=new Store(),gh=new Provider();
  gh.launch=async()=>{gh.started.push('once');throw Error('network acknowledgment lost');};
  await assert.rejects(()=>run(db,gh));
  assert.equal(db.state.stage,'START_RISK');
  for(let i=0;i<3;i++)assert.equal((await run(db,gh)).phase,'PENDING_NO_REDISPATCH');
  assert.equal(gh.started.length,1);
});
test('source drift and untrusted backlog block without POST',async()=>{
  const db=new Store(),gh=new Provider();
  gh.main=OLD;
  await reject(()=>run(db,gh));
  gh.main=SHA;db.queue=[{...tasks[0],source_sha:OLD}];
  await reject(()=>run(db,gh));
  assert.equal(gh.started.length,0);
});
test('daily budget, command injection, duplicate tickets and quarantine fail closed',()=>{
  const s=makeInitial('2026-10-18');s.daily_starts=48;
  assert.throws(()=>selectNext(s,tasks,new Set(),SHA,DATE),Quarantine);
  assert.throws(()=>validateTask({...tasks[0],command:'arbitrary execution'},SHA),Quarantine);
  assert.throws(()=>selectNext(makeInitial('2026-10-18'),[tasks[0],tasks[0]],new Set(),SHA,DATE),Quarantine);
  const q=makeInitial('2026-10-18');q.stage='QUARANTINED';
  assert.throws(()=>selectNext(q,tasks,new Set(),SHA,DATE),Quarantine);
});
test('provider rejects forged runs, failed OS, missing artifacts, reruns',()=>{
 const witness={id:9876543,display_title:'F139 '+tasks[0].ticket,
  name:'FORGE F139 development worker',path:'.github/workflows/forge-f139-development-worker.yml',
  head_branch:'main',event:'workflow_dispatch',head_sha:SHA,run_attempt:1,
  created_at:'2026-10-18T14:11:00Z',status:'completed',conclusion:'success'};
 const jobs=['ubuntu-latest','windows-latest'].map((os,i)=>({id:i+1,name:'execute ('+os+')',status:'completed',conclusion:'success'}));
 const arts=['ubuntu-latest','windows-latest'].map((os,i)=>({id:i+1,name:'forge-f139-dev-receipt-'+os,
  expired:false,workflow_run:{id:witness.id,head_sha:SHA},digest:'sha256:'+'a'.repeat(64)}));
 assert.equal(jobEvidence(witness,jobs,arts,tasks[0].ticket,SHA,DATE).verdict,'VERIFIED');
 for(const changed of [{...witness,run_attempt:2},{...witness,event:'schedule'},
   {...witness,head_sha:OLD},{...witness,conclusion:'failure'},
   {...witness,display_title:'F139 impersonated'}]){
   assert.throws(()=>jobEvidence(changed,jobs,arts,tasks[0].ticket,SHA,DATE),Quarantine);
 }
 assert.throws(()=>jobEvidence(witness,[jobs[0]],arts,tasks[0].ticket,SHA,DATE),Quarantine);
 assert.throws(()=>jobEvidence(witness,jobs,[arts[0]],tasks[0].ticket,SHA,DATE),Quarantine);
 assert.equal(jobEvidence({...witness,status:'in_progress',conclusion:null},null,null,tasks[0].ticket,SHA,DATE).verdict,'PENDING');
});
test('HMAC binds source, ticket, lane, epoch and denies missing key',async()=>{
 const s=await signTicket(SECRET,tasks[0],1);
 assert.match(s,/^[a-f0-9]{64}$/);
 assert.notEqual(s,await signTicket(SECRET,tasks[1],1));
 assert.notEqual(s,await signTicket(SECRET,tasks[0],2));
 assert.notEqual(s,await signTicket(SECRET,{...tasks[0],source_sha:OLD},1));
 await reject(()=>signTicket('short',tasks[0],1));
});
test('provider invokes only explicit development workflow and no science',async()=>{
 const calls=[],reply=(status,data)=>({status,async json(){return data;}});
 const network=async(url,options)=>{
   calls.push({url,options});
   if(url.endsWith('/branches/main'))return reply(200,{commit:{sha:SHA}});
   if(url.endsWith('/dispatches'))return reply(204,null);
   if(url.includes('/runs?'))return reply(200,{total_count:0,workflow_runs:[]});
   return reply(404,null);
 };
 const api=new GitHubDevelopmentProvider('synthetic-credential',network);
 assert.equal(await api.source(),SHA);
 await api.launch(tasks[0],1,'a'.repeat(64));
 assert.equal((await api.locate(tasks[0],DATE)).verdict,'PENDING');
 assert.equal(calls.filter(x=>x.options.method==='POST').length,1);
 assert.match(calls[1].url,/forge-f139-development-worker\.yml\/dispatches$/);
 assert.deepEqual(JSON.parse(calls[1].options.body).inputs,
   {ticket:tasks[0].ticket,lane:'Wingless',source_sha:SHA,epoch:'1',signature:'a'.repeat(64)});
});
