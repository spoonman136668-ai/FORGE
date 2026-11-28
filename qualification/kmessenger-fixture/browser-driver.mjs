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
const profiles=['edge-profile','edge-profile-b','edge-profile-replacement'];
const infoPath=join(scratch,'tls-fixture.json');
let proxy;
const browsers=new Map();
function custody(mode,port=0,name='edge-profile'){
 const r=spawnSync('pwsh.exe',['-NoProfile','-NonInteractive','-File',join(process.cwd(),'browser-custody.ps1'),'-Mode',mode,'-Port',String(port),'-ProfileName',name],{encoding:'utf8',timeout:90000,windowsHide:true});
 assert.equal(r.status,0,'native browser custody failed');return r.stdout.trim();
}
async function profileClosed(name){
 for(let i=0;i<20;i++){if(custody('count',0,name)==='0')return;await wait(500);}
 throw Error('browser profile did not close gracefully');
}
async function stop(p){
 if(!p||p.exitCode!==null||p.signalCode!==null)return;
 const ended=once(p,'exit');
 spawnSync('taskkill.exe',['/PID',String(p.pid),'/T','/F'],{stdio:'ignore',timeout:10000});
 await Promise.race([ended,wait(10000)]);
 assert(p.exitCode!==null||p.signalCode!==null,'process cleanup failed');
}
async function startBrowser(origin,pin,name){
 assert(profiles.includes(name));const profile=join(scratch,name);
 const portFile=join(profile,'DevToolsActivePort');
 assert(!browsers.has(name),'previous browser still owned');
 assert.equal(custody('count',0,name),'0','profile still owned');
 if(existsSync(portFile))unlinkSync(portFile);
 const args=['--headless=new','--remote-debugging-port=0','--remote-debugging-address=127.0.0.1','--user-data-dir='+profile,'--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-component-update','--disable-sync','--disable-extensions','--ignore-certificate-errors-spki-list='+pin,'--no-proxy-server','about:blank'];
 const p=spawn(edge,args,{stdio:['ignore','ignore','pipe'],windowsHide:true});
 browsers.set(name,p);
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
 const actualPid=Number(custody('probe',discovery.port,name));
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
   await profileClosed(name);
   ws.close();browsers.delete(name);
 }};
}
const evaluate=(page,name,...args)=>page.evaluate('window.km.'+name+'('+args.map(a=>JSON.stringify(a)).join(',')+')');
async function until(label,fn){
 step=label;const end=Date.now()+60000;
 while(Date.now()<end){const v=await fn();if(v)return v;await wait(250);}
 throw Error('bounded condition expired');
}
async function verify(at,bt,a,b){
 step='request';
 const tx=await evaluate(at,'request',b.user,b.device);
 assert(typeof tx==='string'&&tx.length);
 await evaluate(bt,'accept',a.user,tx);
 await evaluate(at,'startSas');
 await Promise.all([evaluate(at,'prepareSas'),evaluate(bt,'prepareSas')]);
 step='sascompare';
 const [sa,sb]=await Promise.all([evaluate(at,'sas'),evaluate(bt,'sas')]);
 assert.equal(sa.decimal?.length,3);assert.equal(sa.emoji?.length,7);
 assert.deepEqual(sa,sb);
 // Synthetic independent endpoints only; never a production auto-trust path.
 await Promise.all([evaluate(at,'confirmSas'),evaluate(bt,'confirmSas')]);
 await Promise.all([evaluate(at,'trusted',b.user),evaluate(bt,'trusted',a.user)]);
}
async function exchange(at,bt,a,b,e,room,marker){
 step='submit';
 await evaluate(at,'uiSubmit',marker);
 const row=await until('senderhistory',async()=>{
  const rows=await evaluate(at,'history',room);
  return rows.find(r=>r.body===marker&&r.sender===a.user);
 });
 step='serverevent';
 const raw=await req('GET',p+'/rooms/'+enc(room)+'/event/'+enc(row.id),a.token);
 assert.equal(raw.type,'m.room.encrypted');assert(!JSON.stringify(raw).includes(marker));
 const denied=await req('GET',p+'/rooms/'+enc(room)+'/event/'+enc(row.id),e.token,undefined,404);
 assert.equal(denied.errcode,'M_NOT_FOUND');assert.deepEqual(Object.keys(denied).sort(),['errcode','error']);
 if(bt){
  step='receiverui';
  await until('receiverui',()=>evaluate(bt,'uiHas',marker,a.user));
 }
 return row.id;
}
try{
 stage='accounts';
 const a=await account('alice','ALICE'),b=await account('bob','BOB'),e=await account('eve','EVE');
 const room=(await req('POST',p+'/createRoom',a.token,{visibility:'private',preset:'private_chat',invite:[b.user],initial_state:[{type:'m.room.encryption',state_key:'',content:{algorithm:'m.megolm.v1.aes-sha2'}}]})).room_id;
 const plain=(await req('POST',p+'/createRoom',a.token,{visibility:'private',preset:'private_chat',invite:[b.user]})).room_id;
 assert(room&&plain&&room!==plain);
 await req('POST',p+'/join/'+enc(room),b.token,{});await req('POST',p+'/join/'+enc(plain),b.token,{});
 await req('POST',p+'/join/'+enc(room),e.token,{},403);
 const input=(x,y)=>({userId:x.user,deviceId:x.device,accessToken:x.token,storageKey:[...randomBytes(32)],rooms:[{roomId:room,partners:[y.user]},{roomId:plain,partners:[y.user]}]});
 const ai=input(a,b),bi=input(b,a);
 stage='tls';
 proxy=spawn(join(scratch,'fixture-tls.exe'),[String(port),join(process.cwd(),'public'),infoPath],{stdio:'ignore',windowsHide:true});
 for(let i=0;i<100&&!existsSync(infoPath);i++){assert.equal(proxy.exitCode,null);await wait(100);}
 const info=JSON.parse(readFileSync(infoPath,'utf8'));
 assert(/^https:\/\/127\.0\.0\.1:\d+$/.test(info.origin)&&/^[A-Za-z0-9+/]{43}=$/.test(info.pin));
 stage='browser';step='launch';
 let ab=await startBrowser(info.origin,info.pin,profiles[0]),at=await ab.page();
 let bb=await startBrowser(info.origin,info.pin,profiles[1]),bt=await bb.page();
 for(const tab of [at,bt])assert.deepEqual(await evaluate(tab,'capabilities'),{secure:true,https:true,locks:true,idb:true});
 step='identity';
 const aa=await evaluate(at,'open',ai,true),ba=await evaluate(bt,'open',bi,true);
 assert(aa.master&&ba.master&&aa.master!==ba.master&&aa.device.ed25519!==ba.device.ed25519);
 console.log('KM_UI_INDEPENDENT_IDENTITIES=PASS count=2');
 stage='negative';step='unverified';
 assert.equal(await evaluate(at,'unverified',room),true);
 assert.equal(await evaluate(bt,'unverified',room),true);
 assert.equal(await evaluate(at,'plainDenied',plain),true);
 console.log('KM_UI_UNVERIFIED_AND_PLAINTEXT_DENIED=PASS');
 stage='verify';await verify(at,bt,a,b);console.log('KM_UI_MUTUAL_SAS=PASS');
 stage='ui';step='mount';
 await Promise.all([evaluate(at,'mount',room),evaluate(bt,'mount',room)]);
 const marker='KM_REVOKE_BASELINE_'+randomUUID();
 stage='baseline';const baseline=await exchange(at,bt,a,b,e,room,marker);
 console.log('KM_REVOKE_BASELINE=PASS');
 const oldKeys=await req('POST',p+'/keys/query',a.token,{device_keys:{[b.user]:[]}});
 assert(oldKeys.device_keys?.[b.user]?.[b.device]);
 const master=oldKeys.master_keys?.[b.user];assert(master&&Object.keys(master.keys).length===1);
 stage='revoke';step='close';
 assert.equal(await evaluate(bt,'closeUI'),true);await bb.close();bt=null;
 step='logout';await req('POST',p+'/logout',b.token,{});
 step='oldtoken';
 for(const path of [p+'/account/whoami',p+'/sync?timeout=0',p+'/rooms/'+enc(room)+'/event/'+enc(baseline),p+'/devices']){
  const denied=await req('GET',path,b.token,undefined,401);assert.equal(denied.errcode,'M_UNKNOWN_TOKEN');
 }
 const oldAfter=await req('POST',p+'/keys/query',a.token,{device_keys:{[b.user]:[]}});
 assert(!oldAfter.device_keys?.[b.user]?.[b.device]);assert.deepEqual(oldAfter.master_keys?.[b.user]?.keys,master.keys);
 console.log('KM_REVOKE_TOKEN_AND_KEYS=PASS routes=4');
 step='oldbrowser';
 bb=await startBrowser(info.origin,info.pin,profiles[1]);bt=await bb.page();
 assert.equal(await evaluate(bt,'deny',bi,'secure session initialization failed'),true);
 await bb.close();bt=null;
 console.log('KM_REVOKE_OLD_BROWSER_DENIED=PASS');
 stage='replacement';step='login';
 const replacementDevice='BOB_REPLACEMENT';
 const login=await req('POST',p+'/login',null,{type:'m.login.password',identifier:{type:'m.id.user',user:'bob'},password:b.password,device_id:replacementDevice});
 assert.equal(login.user_id,b.user);assert.equal(login.device_id,replacementDevice);assert(login.access_token&&login.access_token!==b.token);
 const replacement={user:b.user,device:replacementDevice,token:login.access_token};
 const ri=input(replacement,a);
 const rb=await startBrowser(info.origin,info.pin,profiles[2]),rt=await rb.page();
 step='untrusted';
 const newDevice=await evaluate(rt,'openUntrusted',ri,room);
 assert(newDevice.ed25519&&newDevice.curve25519&&newDevice.ed25519!==ba.device.ed25519&&newDevice.curve25519!==ba.device.curve25519);
 const keyState=await req('POST',p+'/keys/query',a.token,{device_keys:{[b.user]:[]}});
 assert(!keyState.device_keys?.[b.user]?.[b.device]);assert(keyState.device_keys?.[b.user]?.[replacementDevice]);
 assert.deepEqual(keyState.master_keys?.[b.user]?.keys,master.keys);
 await evaluate(at,'replacementUnsigned',b.user,replacementDevice,b.device);
 assert.equal(await evaluate(rt,'ownUntrusted',room),true);
 console.log('KM_REVOKE_REPLACEMENT_UNTRUSTED=PASS');
 step='history';
 const cipher=await req('GET',p+'/rooms/'+enc(room)+'/event/'+enc(baseline),replacement.token);
 assert.equal(cipher.type,'m.room.encrypted');assert(!JSON.stringify(cipher).includes(marker));
 assert.equal(await evaluate(rt,'cannotDecrypt',room,baseline,marker),true);
 console.log('KM_REVOKE_REPLACEMENT_OLD_CIPHERTEXT_DENIED=PASS');
 stage='membership';step='leave';
 await req('POST',p+'/rooms/'+enc(room)+'/leave',replacement.token,{});
 assert.equal(await evaluate(at,'membershipDenied',room,b.user),true);
 console.log('KM_REVOKE_ROSTER_DENIED=PASS');
 stage='close';step='wipe';
 assert.equal(await evaluate(at,'closeUI'),true);assert.equal(await evaluate(rt,'close'),true);
 await ab.close();await rb.close();
 console.log('KM_REVOKE_POLICY=PASS routes=4 replacement_denied=1 old_cipher_denied=1 roster_denied=1');
}catch(error){
 const loc=String(error?.stack??'').match(/browser-driver\.mjs:(\d+):(\d+)/);
 console.error('KM_BROWSER_FAILURE stage='+stage+' step='+step+' line='+(loc?.[1]??'0')+' kind='+String(error?.name??'Error').replace(/[^A-Za-z0-9_]/g,'').slice(0,40));
 process.exitCode=1;
}finally{
 try{for(const name of profiles){custody('cleanup',0,name);assert.equal(custody('count',0,name),'0');}await stop(proxy);console.log('KM_BROWSER_PROCESSES_STOPPED=PASS');}catch{process.exitCode=1;console.error('KM_BROWSER_CLEANUP_FAIL');}
}
