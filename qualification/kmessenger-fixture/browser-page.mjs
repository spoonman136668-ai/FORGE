// Test-only instrumentation of the unchanged browser session factory.
import {createClient} from 'matrix-js-sdk';
import {OnlySignedDevicesIsolationMode} from 'matrix-js-sdk/lib/crypto-api/index.js';
import {createBrowserSessionFactory} from './client-lifecycle.mjs';
import {preparePartnerClient} from './matrix-entry.mjs';
let client,session;
const make=()=>createBrowserSessionFactory({
 createClient:opts=>{client=createClient(opts);return client;},
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
 async close(){session.close();return session.state()==='CLOSED';}
});
