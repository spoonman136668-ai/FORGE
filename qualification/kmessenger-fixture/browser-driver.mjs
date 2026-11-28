// Disposable Matrix server interoperability trial, synthetic accounts only.
// Not the application trust/browser qualification. No raw tokens, keys or bodies logged.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHmac,randomBytes,randomUUID} from 'node:crypto';
import {spawn,spawnSync} from 'node:child_process';
import {existsSync,unlinkSync} from 'node:fs';
import {join} from 'node:path';
import {once} from 'node:events';
const port=Number(process.env.KM_FIXTURE_PORT);
assert(Number.isInteger(port)&&port>1024&&port<65536);
const base='http://127.0.0.1:'+port;
const secret=readFileSync(process.env.KM_FIXTURE_SECRET,'utf8').trim();
assert(/^[a-f0-9]{64}$/.test(secret));
const clients=[];
let sends=0;
let stage='boot',step='entry',lastHttp=0,expectedHttp=0;
async function req(method,path,token,body,expected=200){
  lastHttp=0;expectedHttp=expected;
  assert(path.startsWith('/')&&!path.startsWith('//'));
  const url=new URL(path,base);
  assert.equal(url.origin,base);
  const res=await fetch(url,{method,redirect:'error',signal:AbortSignal.timeout(20000),
    headers:{...(token?{authorization:'Bearer '+token}:{}),...(body!==undefined?{'content-type':'application/json'}:{})},
    ...(body!==undefined?{body:JSON.stringify(body)}:{})});
  lastHttp=res.status;
  const json=await res.json();
  assert.equal(res.status,expected,'unexpected HTTP status '+res.status);
  return json;
}
const p='/_matrix/client/v3';
const enc=encodeURIComponent;
async function account(name,device){
  const password=randomBytes(24).toString('hex');
  const register='/_synapse/admin/v1/register';
  const {nonce}=await req('GET',register);
  assert(typeof nonce==='string'&&nonce.length);
  const mac=createHmac('sha1',secret).update([nonce,name,password,'notadmin'].join('\0')).digest('hex');
  await req('POST',register,null,{nonce,username:name,password,admin:false,mac});
  const login=await req('POST',p+'/login',null,{type:'m.login.password',identifier:{type:'m.id.user',user:name},password,device_id:device});
  assert.equal(login.user_id,'@'+name+':km-fixture.invalid');
  assert.equal(login.device_id,device);assert(login.access_token);
  const who=await req('GET',p+'/account/whoami',login.access_token);
  assert.equal(who.user_id,login.user_id);assert.equal(who.device_id,device);
  return {user:login.user_id,device,token:login.access_token,password};
}


const scratch=process.env.KM_SCRATCH,edge=process.env.KM_EDGE;
assert(scratch&&edge&&existsSync(edge));
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const profile=join(scratch,'edge-profile');
const infoPath=join(scratch,'tls-fixture.json');
let proxy,browser;
function custody(mode,port=0){
 const r=spawnSync('pwsh.exe',['-NoProfile','-NonInteractive','-File',join(process.cwd(),'browser-custody.ps1'),'-Mode',mode,'-Port',String(port)],{encoding:'utf8',timeout:90000,windowsHide:true});
 assert.equal(r.status,0,'native browser custody failed');return r.stdout.trim();
}
async function profileClosed(){
 for(let i=0;i<20;i++){if(custody('count')==='0')return;await wait(500);}
 throw Error('browser profile did not close gracefully');
}
async function stop(p){
 if(!p||p.exitCode!==null||p.signalCode!==null)return;
 const ended=once(p,'exit');
 spawnSync('taskkill.exe',['/PID',String(p.pid),'/T','/F'],{stdio:'ignore',timeout:10000});
 await Promise.race([ended,wait(10000)]);
 assert(p.exitCode!==null||p.signalCode!==null,'process cleanup failed');
}
async function startBrowser(origin,pin){
 const portFile=join(profile,'DevToolsActivePort');
 assert(!browser,'previous browser still owned');
 assert.equal(custody('count'),'0','profile still owned');
 if(existsSync(portFile))unlinkSync(portFile);
 const args=['--headless=new','--remote-debugging-port=0','--remote-debugging-address=127.0.0.1','--user-data-dir='+profile,'--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-component-update','--disable-sync','--disable-extensions','--ignore-certificate-errors-spki-list='+pin,'--no-proxy-server','about:blank'];
 const p=spawn(edge,args,{stdio:['ignore','ignore','pipe'],windowsHide:true});
 browser=p;
 let diagnostics='',launchError=false;
 p.stderr.on('data',data=>{diagnostics=(diagnostics+data.toString('utf8')).slice(-16384);});
 p.on('error',()=>{launchError=true;});
 function startupFailure(){
  let kind='UNKNOWN';
  if(/remote debugging|devtools/i.test(diagnostics))kind='DEVTOOLS';
  else if(/sandbox/i.test(diagnostics))kind='SANDBOX';
  else if(/user.data.dir|profile|singleton/i.test(diagnostics))kind='PROFILE';
  else if(/access.denied|permission/i.test(diagnostics))kind='PERMISSION';
  else if(/gpu|graphics/i.test(diagnostics))kind='GRAPHICS';
  console.error('KM_BROWSER_LAUNCH_FAILURE kind='+kind+' exit='+(Number.isInteger(p.exitCode)?p.exitCode:-1));
  throw Error('browser launch readiness failed');
 }
 let discovery;
 for(let i=0;i<150;i++){
  if(launchError||(p.exitCode!==null&&p.exitCode!==0)||p.signalCode!==null)startupFailure();
  // A successful launcher exit may hand off to the actual browser. Only the
  // exact profile-bound listener's native owner is allowed to establish CDP.
  if(existsSync(portFile)){
   const parts=readFileSync(portFile,'utf8').trim().split(/\r?\n/);
   const port=Number(parts[0]);
   if(parts.length===2&&Number.isInteger(port)&&port>1024&&port<65536&&/^\/devtools\/browser\/[0-9a-f-]+$/i.test(parts[1])){
    discovery={port,path:parts[1]};break;
   }
  }
  await wait(200);
 }
 if(!discovery)startupFailure();
 // Validate native process ownership before sending synthetic credentials.
 const actualPid=Number(custody('probe',discovery.port));
 assert(Number.isSafeInteger(actualPid)&&actualPid>0);
 console.log('KM_BROWSER_NATIVE_OWNER=PASS');
 console.log('KM_BROWSER_DEBUG_LOOPBACK=PASS');
 const ws=new WebSocket('ws://127.0.0.1:'+discovery.port+discovery.path);
 await new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>reject(Error('CDP websocket timeout')),15000);
  ws.addEventListener('open',()=>{clearTimeout(timer);resolve();},{once:true});
  ws.addEventListener('error',()=>{clearTimeout(timer);reject(Error('CDP websocket error'));},{once:true});
 });
 let id=0;const pending=new Map();
 ws.addEventListener('message',event=>{
  const m=JSON.parse(event.data);
  const h=pending.get(m.id);
  if(h){pending.delete(m.id);clearTimeout(h.timer);m.error?h.reject(Error('CDP error')):h.resolve(m.result);}
 });
 const ended=()=>{for(const h of pending.values()){clearTimeout(h.timer);h.reject(Error('browser disconnected'));}pending.clear();};
 ws.addEventListener('close',ended);
 const call=(method,params={},sessionId,timeout=15000)=>new Promise((resolve,reject)=>{
  const n=++id,timer=setTimeout(()=>{pending.delete(n);reject(Error('CDP timeout'));},timeout);
  pending.set(n,{resolve,reject,timer});
  try{ws.send(JSON.stringify({id:n,method,params,...(sessionId?{sessionId}:{})}));}catch{clearTimeout(timer);pending.delete(n);reject(Error('CDP send failed'));}
 });
 async function page(){
  const {targetId}=await call('Target.createTarget',{url:'about:blank'});
  const {sessionId}=await call('Target.attachToTarget',{targetId,flatten:true});
  await call('Page.enable',{},sessionId);
  await call('Runtime.enable',{},sessionId);
  const nav=await call('Page.navigate',{url:origin+'/'},sessionId);
  assert(!nav.errorText,'navigation failed');
  async function evaluate(expression,timeout=150000){
   const r=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true},sessionId,timeout);
   assert(!r.exceptionDetails,'browser evaluation failed');return r.result.value;
  }
  for(let i=0;i<100;i++){if(await evaluate('Boolean(window.km)',15000))return {evaluate,close:()=>call('Target.closeTarget',{targetId})};await wait(150);}
  throw Error('browser bundle not ready');
 }
 return {p,page,async close(){
   try{await call('Browser.close',{},undefined,10000);}catch{}
   if(p.exitCode===null&&p.signalCode===null)await Promise.race([once(p,'exit'),wait(10000)]);
   await profileClosed();
   ws.close();browser=null;
 }};
}
const evaluate=(page,name,...args)=>page.evaluate('window.km.'+name+'('+args.map(a=>JSON.stringify(a)).join(',')+')');
try{
 stage='accounts';
 const a=await account('alice','ALICE'),b=await account('bob','BOB');
 const room=(await req('POST',p+'/createRoom',a.token,{visibility:'private',preset:'private_chat',invite:[b.user],initial_state:[{type:'m.room.encryption',state_key:'',content:{algorithm:'m.megolm.v1.aes-sha2'}}]})).room_id;
 assert(room);await req('POST',p+'/join/'+enc(room),b.token,{});
 const key=[...randomBytes(32)];
 const input={userId:a.user,deviceId:a.device,accessToken:a.token,storageKey:key,rooms:[{roomId:room,partners:[b.user]}]};
 const wrong={...input,storageKey:[...key]};wrong.storageKey[0]^=1;
 stage='tls';
 proxy=spawn(join(scratch,'fixture-tls.exe'),[String(port),join(process.cwd(),'public'),infoPath],{stdio:'ignore',windowsHide:true});
 for(let i=0;i<100&&!existsSync(infoPath);i++){assert.equal(proxy.exitCode,null);await wait(100);}
 const info=JSON.parse(readFileSync(infoPath,'utf8'));
 assert(/^https:\/\/127\.0\.0\.1:\d+$/.test(info.origin)&&/^[A-Za-z0-9+/]{43}=$/.test(info.pin));
 stage='browser';step='first';
 let br=await startBrowser(info.origin,info.pin),tab=await br.page();
 assert.deepEqual(await evaluate(tab,'capabilities'),{secure:true,https:true,locks:true,idb:true});
 console.log('KM_BROWSER_HTTPS_CONTEXT=PASS');
 step='firststore';
 const initial=await evaluate(tab,'open',input,true);
 assert(initial?.master&&initial?.device?.ed25519&&initial?.device?.curve25519&&initial.db.length);
 console.log('KM_BROWSER_STORE_INITIAL=PASS');
 step='unverified';
 assert.equal(await evaluate(tab,'unverified',room),true);
 console.log('KM_BROWSER_UNVERIFIED_DENIED=PASS');
 step='lock';
 const second=await br.page();
 assert.equal(await evaluate(second,'deny',input,'crypto store already owned'),true);
 assert.equal(await evaluate(tab,'close'),true);
 const third=await br.page();
 assert.equal(await evaluate(third,'deny',input,'crypto store already owned'),true);
 console.log('KM_BROWSER_LOCK=PASS contention=2');
 await br.close();
 step='wrongkey';
 br=await startBrowser(info.origin,info.pin);tab=await br.page();
 assert.equal(await evaluate(tab,'deny',wrong,'secure session initialization failed'),true);
 await br.close();
 console.log('KM_BROWSER_WRONG_KEY=PASS');
 step='coldreopen';
 br=await startBrowser(info.origin,info.pin);tab=await br.page();
 const after=await evaluate(tab,'open',input,false);
 assert.deepEqual(after,initial);
 assert.equal(await evaluate(tab,'unverified',room),true);
 assert.equal(await evaluate(tab,'close'),true);
 await br.close();
 console.log('KM_BROWSER_COLD_REOPEN=PASS identity_unchanged=1');
 console.log('KM_BROWSER_CUSTODY=PASS');
}catch(error){
 const loc=String(error?.stack??'').match(/browser-driver\.mjs:(\d+):(\d+)/);
 console.error('KM_BROWSER_FAILURE stage='+stage+' step='+step+' line='+(loc?.[1]??'0')+' kind='+String(error?.name??'Error').replace(/[^A-Za-z0-9_]/g,'').slice(0,40));
 process.exitCode=1;
}finally{
 try{custody('cleanup');assert.equal(custody('count'),'0');await stop(proxy);console.log('KM_BROWSER_PROCESSES_STOPPED=PASS');}catch{process.exitCode=1;console.error('KM_BROWSER_CLEANUP_FAIL');}
}
