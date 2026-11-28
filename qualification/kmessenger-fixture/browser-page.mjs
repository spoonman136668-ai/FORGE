// Test-only instrumentation of the unchanged browser session factory.
import {createClient} from 'matrix-js-sdk';
import {OnlySignedDevicesIsolationMode} from 'matrix-js-sdk/lib/crypto-api/index.js';
import {createBrowserSessionFactory} from './client-lifecycle.mjs';
import {VerificationPhase} from 'matrix-js-sdk/lib/crypto-api/verification.js';
import {mountConversation} from './conversation-view.mjs';
import {preparePartnerClient} from './matrix-entry.mjs';
let client,session,request,verifier,verification,view;
const make=()=>createBrowserSessionFactory({
 createClient:opts=>{client=createClient({...opts,verificationMethods:['m.sas.v1']});return client;},
 OnlySignedDevicesIsolationMode,
 environment:{origin:location.origin,secureContext:isSecureContext,locks:navigator.locks,indexedDB,fetchFn:fetch.bind(window)}
});
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn){for(let i=0;i<300;i++){const r=await fn();if(r)return r;await delay(200);}throw Error('bounded wait');}
function argumentsFor(a){return {...a,storageKey:new Uint8Array(a.storageKey)};}
const open=async(a,bootstrap)=>{
 session=await make()(argumentsFor(a));
 await until(()=>session.state()==='SYNCING');
 const crypto=client.getCrypto();
 if(bootstrap){
  if(await crypto.userHasCrossSigningKeys(a.userId,true))throw Error('existing identity');
  await crypto.bootstrapCrossSigning({authUploadDeviceSigningKeys:makeRequest=>makeRequest().then(()=>undefined)});
 }
 await until(()=>crypto.isCrossSigningReady());
 await until(async()=>{const s=await crypto.getDeviceVerificationStatus(a.userId,a.deviceId);return s?.signedByOwner===true&&s.crossSigningVerified===true&&s.blocked===false;});
 const master=await crypto.getCrossSigningKeyId();
 if(!master)throw Error('missing master');
 const device=await crypto.getOwnDeviceKeys();
 const db=(await indexedDB.databases()).map(x=>x.name).filter(n=>n?.startsWith('k-messenger-v1')).sort();
 if(!db.length)throw Error('missing database');
 return {master,device,db};
};
window.km=Object.freeze({
 capabilities:()=>({secure:isSecureContext,https:location.protocol==='https:',locks:!!navigator.locks,idb:!!indexedDB}),
 open,
 async deny(a,expected){
   try{const s=await preparePartnerClient()(argumentsFor(a));s.close();return false;}
   catch(e){return e?.message===expected;}
 },
 async unverified(room){
  try{await session.sendText(room,'synthetic unverified denial');return false;}catch(e){return e?.message==='partner not verified';}
 },
 async plainDenied(room){
  try{await session.sendText(room,'synthetic plaintext denial');return false;}catch(e){return e?.message==='encryption required';}
 },
 async request(user,device){
  const c=client.getCrypto();await until(async()=>(await c.getUserDeviceInfo([user],true)).get(user)?.has(device));
  request=await c.requestDeviceVerification(user,device);
  if(request.otherUserId!==user)throw Error('peer mismatch');
  return request.transactionId;
 },
 async accept(user,tx){
  request=await until(()=>client.getCrypto().getVerificationRequestsToDeviceInProgress(user).find(r=>r.transactionId===tx&&r.otherUserId===user&&!r.initiatedByMe));
  await request.accept();return true;
 },
 async startSas(){await until(()=>request.phase===VerificationPhase.Ready);verifier=await request.startVerification('m.sas.v1');return true;},
 async prepareSas(){verifier=verifier??await until(()=>request.verifier);verification=verifier.verify();verification.catch(()=>{});return true;},
 async sas(){return (await until(()=>verifier.getShowSasCallbacks())).sas;},
 async confirmSas(){await verifier.getShowSasCallbacks().confirm();await verification;return true;},
 async trusted(user){await until(async()=>{const s=await client.getCrypto().getUserVerificationStatus(user);return s.isCrossSigningVerified()&&!s.needsUserApproval;});return true;},
 async history(room){return session.readTextHistory(room,50);},
 async mount(room){
  view=mountConversation(document.body,{session,rooms:[{roomId:room,label:'Synthetic partner'}]});
  const select=document.querySelector('.km-select');select.value=room;select.dispatchEvent(new Event('change'));
  await until(()=>document.querySelector('.km-primary')?.disabled===false);return true;
 },
 async uiSubmit(marker){
  const draft=document.querySelector('.km-draft'),send=document.querySelector('.km-primary');
  if(!draft||send?.disabled)throw Error('UI not ready');
  draft.value=marker;send.click();
  await until(()=>document.querySelector('.km-status')?.textContent==='Submitted to server; delivery not confirmed');
  if(draft.value!=='')throw Error('draft not cleared');return true;
 },
 async uiHas(marker,sender){
  const refresh=[...document.querySelectorAll('.km-actions button')].find(b=>b.textContent==='Refresh');
  if(!refresh||refresh.disabled)return false;
  refresh.click();await until(()=>!refresh.disabled);
  if(document.querySelector('.km-timeline img'))throw Error('unsafe HTML rendering');
  return [...document.querySelectorAll('.km-message')].some(n=>n.querySelector('strong')?.textContent===sender&&n.querySelector('p')?.textContent===marker);
 },
 async closeUI(){
  const close=[...document.querySelectorAll('.km-actions button')].find(b=>b.textContent==='Close session');
  if(!close||close.disabled)throw Error('close unavailable');close.click();
  return session.state()==='CLOSED'&&document.querySelector('.km-draft').value===''&&!document.querySelector('.km-message');
 },
 async close(){session.close();return session.state()==='CLOSED';}
});
