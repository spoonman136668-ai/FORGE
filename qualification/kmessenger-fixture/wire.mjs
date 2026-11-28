// Disposable Matrix server interoperability trial, synthetic accounts only.
// Not the application trust/browser qualification. No raw tokens, keys or bodies logged.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHmac,randomBytes,randomUUID} from 'node:crypto';
import {OlmMachine,UserId,DeviceId,DeviceLists,RoomId,RequestType,EncryptionSettings,DecryptionSettings,TrustRequirement,MegolmDecryptionError,DecryptionErrorCode} from '@matrix-org/matrix-sdk-crypto-wasm';
const port=Number(process.env.KM_FIXTURE_PORT);
assert(Number.isInteger(port)&&port>1024&&port<65536);
const base='http://127.0.0.1:'+port;
const secret=readFileSync(process.env.KM_FIXTURE_SECRET,'utf8').trim();
assert(/^[a-f0-9]{64}$/.test(secret));
const machines=[];
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
  const m=await OlmMachine.initialize(new UserId(login.user_id),new DeviceId(device));
  machines.push(m);
  return {user:login.user_id,device,token:login.access_token,m,since:null};
}
async function sync(a,timeout=1000){
  const s=await req('GET',p+'/sync?timeout='+timeout+(a.since?'&since='+enc(a.since):''),a.token);
  assert(s.next_batch);a.since=s.next_batch;
  const ev=s.to_device?.events??[];
  await a.m.receiveSyncChanges(JSON.stringify(ev),new DeviceLists(),new Map(Object.entries(s.device_one_time_keys_count??{})),undefined);
  return s;
}
async function upload(a){
  await sync(a,0);
  const r=(await a.m.outgoingRequests()).find(x=>x.type===RequestType.KeysUpload);
  assert(r?.id);
  const result=await req('POST',p+'/keys/upload',a.token,JSON.parse(r.body));
  assert.equal(await a.m.markRequestAsSent(r.id,r.type,JSON.stringify(result)),true);
}
async function learn(a,b){
  await a.m.updateTrackedUsers([new UserId(b.user)]);
  const requests=(await a.m.outgoingRequests()).filter(x=>x.type===RequestType.KeysQuery);
  assert(requests.length);
  for(const r of requests){
    const result=await req('POST',p+'/keys/query',a.token,JSON.parse(r.body));
    assert.equal(await a.m.markRequestAsSent(r.id,r.type,JSON.stringify(result)),true);
  }
}
async function exchange(a,b,eve,room){
  step='learn';
  await learn(a,b);
  step='claim';
  const claim=await a.m.getMissingSessions([new UserId(b.user)]);
  if(claim){
    step='claimresponse';
    const result=await req('POST',p+'/keys/claim',a.token,JSON.parse(claim.body));
    assert.equal(await a.m.markRequestAsSent(claim.id,RequestType.KeysClaim,JSON.stringify(result)),true);
  }
  step='share';
  const shares=await a.m.shareRoomKey(new RoomId(room),[new UserId(b.user)],new EncryptionSettings());
  assert(shares.length>0);
  for(const share of shares){
    step='sharetype';
    assert.equal(share.event_type,'m.room.encrypted');
    const payload=JSON.parse(share.body);
    step='sharerecipient';
    assert.deepEqual(Object.keys(payload.messages),[b.user]);
    step='sharedevice';
    assert.deepEqual(Object.keys(payload.messages[b.user]),[b.device]);
    step='shareupload';
    await req('PUT',p+'/sendToDevice/'+enc(share.event_type)+'/'+enc(share.txn_id),a.token,payload);
    step='shareack';
    assert.equal(await a.m.markRequestAsSent(share.id,RequestType.ToDevice,'{}'),true);
  }
  const marker='KM_SYNTHETIC_'+randomUUID();
  step='encrypt';
  const ciphertext=JSON.parse(await a.m.encryptRoomEvent(new RoomId(room),'m.room.message',JSON.stringify({msgtype:'m.text',body:marker})));
  assert.equal(ciphertext.algorithm,'m.megolm.v1.aes-sha2');assert(!JSON.stringify(ciphertext).includes(marker));
  // No receiver sync during send: recover through subsequent server sync.
  step='send';
  const sent=await req('PUT',p+'/rooms/'+enc(room)+'/send/m.room.encrypted/'+randomUUID(),a.token,ciphertext);
  assert(sent.event_id);
  step='readback';
  const raw=await req('GET',p+'/rooms/'+enc(room)+'/event/'+enc(sent.event_id),a.token);
  assert.equal(raw.type,'m.room.encrypted');assert(!JSON.stringify(raw).includes(marker));
  step='outsiderhttp';
  // Pinned Dendrite GetEvent intentionally conceals unauthorized events with M_NOT_FOUND.
  const denied=await req('GET',p+'/rooms/'+enc(room)+'/event/'+enc(sent.event_id),eve.token,undefined,404);
  assert.equal(denied.errcode,'M_NOT_FOUND');
  assert.deepEqual(Object.keys(denied).sort(),['errcode','error']);
  assert(!JSON.stringify(denied).includes(marker));
  step='receiversync';
  let event;
  for(let i=0;i<8&&!event;i++){
    const s=await sync(b);
    event=s.rooms?.join?.[room]?.timeline?.events?.find(e=>e.event_id===sent.event_id);
  }
  step='receiveevent';
  assert(event,'recipient event absent');
  assert.equal(event.type,'m.room.encrypted');assert(!JSON.stringify(event).includes(marker));
  // A synthetic primitive fixture intentionally uses unverified identities.
  // This never substitutes for K-Messenger's signed-device application policy.
  step='decrypt';
  const decrypted=await b.m.decryptRoomEvent(JSON.stringify(event),new RoomId(room),new DecryptionSettings(TrustRequirement.Untrusted));
  step='plaintextmatch';
  assert.equal(JSON.parse(decrypted.event).content.body,marker);
  step='outsiderdecrypt';
  await assert.rejects(()=>eve.m.decryptRoomEvent(JSON.stringify(event),new RoomId(room),new DecryptionSettings(TrustRequirement.Untrusted)),err=>err instanceof MegolmDecryptionError&&err.code===DecryptionErrorCode.MissingRoomKey);
}
try{
  const versions=await req('GET','/_matrix/client/versions');assert(versions.versions.length);
  await req('POST',p+'/register',null,{username:'publicattempt',password:randomBytes(24).toString('hex'),auth:{type:'m.login.dummy'}},403);
  console.log('KM_FIXTURE_PUBLIC_REGISTRATION_DENIED=PASS');
  stage='accounts';
  const a=await account('alice','ALICE'),b=await account('bob','BOB'),e=await account('eve','EVE');
  console.log('KM_FIXTURE_ACCOUNTS=PASS count=3');
  stage='room';
  const {room_id:room}=await req('POST',p+'/createRoom',a.token,{visibility:'private',preset:'private_chat',invite:[b.user],initial_state:[{type:'m.room.encryption',state_key:'',content:{algorithm:'m.megolm.v1.aes-sha2'}}]});
  assert(room);await req('POST',p+'/join/'+enc(room),b.token,{});
  await req('POST',p+'/join/'+enc(room),e.token,{},403);
  console.log('KM_FIXTURE_PRIVATE_ROOM=PASS');
  stage='keys';await upload(a);await upload(b);
  stage='forward';await exchange(a,b,e,room);console.log('KM_FIXTURE_FORWARD=PASS');
  stage='reverse';await exchange(b,a,e,room);console.log('KM_FIXTURE_REVERSE=PASS');
  console.log('KM_FIXTURE_WIRE_PRIMITIVES=PASS directions=2 outsider_denied=2 receiver_offline_during_send=2');
 }catch(error){
  const loc=String(error?.stack??'').match(/wire\.mjs:(\d+):(\d+)/);
  const kind=String(error?.name??'Error').replace(/[^A-Za-z0-9_]/g,'').slice(0,40);
  console.error('KM_FIXTURE_FAILURE stage='+stage+' kind='+kind+' step='+step+' line='+(loc?.[1]??'0')+' http='+lastHttp+' expected='+expectedHttp);
  process.exitCode=1;
}
finally{for(const m of machines)m.close();}
