// Disposable Matrix server interoperability trial, synthetic accounts only.
// Not the application trust/browser qualification. No raw tokens, keys or bodies logged.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHmac,randomBytes,randomUUID} from 'node:crypto';
import {createClient} from 'matrix-js-sdk';
import {OnlySignedDevicesIsolationMode} from 'matrix-js-sdk/lib/crypto-api/index.js';
import {VerificationPhase} from 'matrix-js-sdk/lib/crypto-api/verification.js';
import {createPartnerSender} from './crypto-policy.mjs';
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

const wait=async(label,fn)=>{
  step=label;
  const end=Date.now()+45000;
  while(Date.now()<end){
    const v=await fn();
    if(v)return v;
    await new Promise(resolve=>setTimeout(resolve,200));
  }
  throw Error('bounded wait expired');
};
function localFetch(input,init){
  const u=new URL(input);
  assert.equal(u.origin,base);
  assert(!u.username&&!u.password&&!u.hash&&!u.searchParams.has('access_token'));
  assert(u.pathname.startsWith('/_matrix/client/'));
  const parts=u.pathname.split('/').map(decodeURIComponent);
  if(parts[4]==='rooms'&&parts[6]==='send'){
    assert.equal(parts.length,9);assert.equal(parts[7],'m.room.encrypted');
    assert.equal(init?.method?.toUpperCase(),'PUT');
    const content=JSON.parse(init.body);
    assert.equal(content.algorithm,'m.megolm.v1.aes-sha2');
    assert.equal(typeof content.ciphertext,'string');
    sends++;
  }
  return fetch(u.href,{...init,redirect:'error',credentials:'omit',cache:'no-store'});
}
async function start(a){
  const c=createClient({baseUrl:base,userId:a.user,deviceId:a.device,accessToken:a.token,
    fetchFn:localFetch,useAuthorizationHeader:true,disableVoip:true,verificationMethods:['m.sas.v1']});
  clients.push(c);
  a.c=c;
  await c.initRustCrypto({useIndexedDB:false});
  a.crypto=c.getCrypto();assert(a.crypto);
  await c.startClient({initialSyncLimit:20,pollTimeout:1000});
  await wait('sync',()=>c.getSyncState()==='SYNCING');
}
async function bootstrap(a){
  step='bootstrap';
  // First-time synthetic identities only. Never reset or accept a changed identity.
  assert.equal(await a.crypto.userHasCrossSigningKeys(a.user,true),false);
  await a.crypto.bootstrapCrossSigning({authUploadDeviceSigningKeys:makeRequest=>makeRequest().then(()=>undefined)});
  await wait('crosssignready',async()=>await a.crypto.isCrossSigningReady());
  await wait('ownsign',async()=>{
    const d=await a.crypto.getDeviceVerificationStatus(a.user,a.device);
    return d?.signedByOwner===true&&d.crossSigningVerified===true&&d.blocked===false;
  });
}
async function verify(a,b){
  await wait('knowdevice',async()=>{
    const d=await a.crypto.getUserDeviceInfo([b.user],true);
    return d.get(b.user)?.has(b.device);
  });
  step='request';
  const req=await a.crypto.requestDeviceVerification(b.user,b.device);
  const incoming=await wait('incoming',()=>b.crypto.getVerificationRequestsToDeviceInProgress(a.user).find(r=>r.transactionId===req.transactionId&&r.otherUserId===a.user));
  assert.equal(req.otherUserId,b.user);
  assert.equal(incoming.initiatedByMe,false);
  await incoming.accept();
  await wait('ready',()=>req.phase===VerificationPhase.Ready);
  step='sasstart';
  const va=await req.startVerification('m.sas.v1');
  const vb=await wait('peerstart',()=>incoming.verifier);
  const pa=va.verify(),pb=vb.verify();
  // Register rejection handlers immediately; completion still asserted below.
  pa.catch(()=>{});pb.catch(()=>{});
  const sa=await wait('localsas',()=>va.getShowSasCallbacks());
  const sb=await wait('peersas',()=>vb.getShowSasCallbacks());
  step='sascompare';
  // In-process comparison is permitted ONLY for the explicitly synthetic
  // fixture. No auto-trust API, locally marking devices verified, or reset.
  assert.equal(sa.sas.decimal?.length,3);assert.equal(sa.sas.emoji?.length,7);
  assert.deepEqual(sa.sas.decimal,sb.sas.decimal);assert.deepEqual(sa.sas.emoji,sb.sas.emoji);
  await Promise.all([sa.confirm(),sb.confirm()]);
  await Promise.race([Promise.all([pa,pb]),new Promise((_,reject)=>{const t=setTimeout(()=>reject(Error('verification timeout')),45000);t.unref();})]);
  await wait('mutualtrust',async()=>{
    const aa=await a.crypto.getUserVerificationStatus(b.user),bb=await b.crypto.getUserVerificationStatus(a.user);
    return aa.isCrossSigningVerified()&&bb.isCrossSigningVerified()&&!aa.needsUserApproval&&!bb.needsUserApproval;
  });
}
async function exchange(a,b,e,room){
  step='send';
  const before=sends,marker='KM_SYNTHETIC_'+randomUUID();
  const sent=await a.policy.sendText(room,marker);
  assert(sent?.event_id);assert.equal(sends,before+1);
  step='readback';
  const raw=await req('GET',p+'/rooms/'+enc(room)+'/event/'+enc(sent.event_id),a.token);
  assert.equal(raw.type,'m.room.encrypted');assert(!JSON.stringify(raw).includes(marker));
  step='outsider';
  const denied=await req('GET',p+'/rooms/'+enc(room)+'/event/'+enc(sent.event_id),e.token,undefined,404);
  assert.equal(denied.errcode,'M_NOT_FOUND');assert.deepEqual(Object.keys(denied).sort(),['errcode','error']);
  await wait('verifiedhistory',async()=>{
    const rows=await b.policy.readTextHistory(room);
    const row=rows.find(r=>r.id===sent.event_id);
    if(!row)return false;
    assert.equal(row.body,marker);assert.equal(row.sender,a.user);return true;
  });
}
const watchdog=setTimeout(()=>{console.error('KM_SDK_FAILURE stage='+stage+' kind=Timeout step='+step+' line=0 http='+lastHttp+' expected='+expectedHttp);process.exit(1);},240000);
try{
  stage='accounts';
  const a=await account('alice','ALICE'),b=await account('bob','BOB'),e=await account('eve','EVE');
  stage='rooms';
  const room=(await req('POST',p+'/createRoom',a.token,{visibility:'private',preset:'private_chat',invite:[b.user],initial_state:[{type:'m.room.encryption',state_key:'',content:{algorithm:'m.megolm.v1.aes-sha2'}}]})).room_id;
  const plain=(await req('POST',p+'/createRoom',a.token,{visibility:'private',preset:'private_chat',invite:[b.user]})).room_id;
  assert(room&&plain&&room!==plain);
  await req('POST',p+'/join/'+enc(room),b.token,{});
  await req('POST',p+'/join/'+enc(plain),b.token,{});
  await req('POST',p+'/join/'+enc(room),e.token,{},403);
  stage='clients';await start(a);await start(b);await bootstrap(a);await bootstrap(b);
  for(const [x,y] of [[a,b],[b,a]]){
    await wait('roomready',async()=>x.c.getRoom(room)?.getMyMembership()==='join'&&x.c.getRoom(plain)?.getMyMembership()==='join'&&await x.crypto.isEncryptionEnabledInRoom(room));
    x.policy=createPartnerSender({client:x.c,OnlySignedDevicesIsolationMode,rooms:[{roomId:room,partners:[y.user]},{roomId:plain,partners:[y.user]}]});
  }
  console.log('KM_SDK_OWN_IDENTITIES=PASS count=2');
  stage='unverified';step='denial';
  const before=sends;
  await assert.rejects(()=>a.policy.sendText(room,'synthetic pre-verification denial'),/partner not verified/);
  await assert.rejects(()=>a.policy.sendText(plain,'synthetic plaintext denial'),/encryption required/);
  assert.equal(sends,before);
  console.log('KM_SDK_PREVERIFICATION_AND_PLAINTEXT_DENIED=PASS');
  stage='verify';await verify(a,b);console.log('KM_SDK_MUTUAL_SAS=PASS');
  stage='forward';await exchange(a,b,e,room);console.log('KM_SDK_FORWARD=PASS');
  stage='reverse';await exchange(b,a,e,room);console.log('KM_SDK_REVERSE=PASS');
  console.log('KM_SDK_POLICY=PASS directions=2 denied=2 outsider_http_denied=2');
}catch(error){
  const loc=String(error?.stack??'').match(/sdk-trust\.mjs:(\d+):(\d+)/);
  const kind=String(error?.name??'Error').replace(/[^A-Za-z0-9_]/g,'').slice(0,40);
  console.error('KM_SDK_FAILURE stage='+stage+' kind='+kind+' step='+step+' line='+(loc?.[1]??'0')+' http='+lastHttp+' expected='+expectedHttp);
  process.exitCode=1;
}finally{
  clearTimeout(watchdog);
  for(const c of clients)c.stopClient();
}
