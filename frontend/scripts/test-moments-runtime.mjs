import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const source = (await readFile(new URL('../src/services/momentsApi.js', import.meta.url), 'utf8')).replace('import { API_BASE_URL } from "./api.js";', 'const API_BASE_URL = "";');
const api = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
test('Moment request sends caption and persisted appearance; returns server moment', async () => {
  const oldFetch = globalThis.fetch;
  const oldDocument = globalThis.document;
  globalThis.document = { cookie: 'csrftoken=test' };
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/momentos/');
    assert.equal(options.body.get('caption'), 'DIA_TRANQUILO');
    assert.equal(options.body.get('theme'), 'sand');
    assert.equal(options.body.get('font'), 'italic');
    assert.equal(options.body.get('visibilidade'), 'MATCHES');
    return new Response(JSON.stringify({ id: 1, text: 'Um dia tranquilo por aqui.', theme: 'sand', font: 'italic' }), { status: 201, headers: { 'content-type': 'application/json' } });
  };
  try {
    const moment = await api.createMoment({ caption: 'DIA_TRANQUILO', theme: 'sand', font: 'italic', visibility: 'MATCHES' });
    assert.equal(moment.id, 1);
    assert.equal(moment.text, 'Um dia tranquilo por aqui.');
  } finally { globalThis.fetch = oldFetch; globalThis.document = oldDocument; }
});

const seenApi = await import('../src/services/seenMoments.js');
test('Moment viewing memory is isolated, expires, and stores no content',()=>{
 const now=1700000000000, data=new Map(), storage={getItem:k=>data.get(k),setItem:(k,v)=>data.set(k,v)};
 const a=seenApi.seenStorageKey(1),b=seenApi.seenStorageKey(2);
 assert.equal(seenApi.seenStorageKey(null),null);
 seenApi.writeSeenMoments(storage,a,{"10":now+1000,"11":now-1,"bad":now+1000,"12":now+86400001},now);
 assert.deepEqual(seenApi.readSeenMoments(storage,a,now),{"10":now+1000});
 assert.deepEqual(seenApi.readSeenMoments(storage,b,now),{});
 seenApi.writeSeenMoments(storage,a,{"13":now+2000},now);
 assert.deepEqual(seenApi.readSeenMoments(storage,a,now+1001),{"13":now+2000});
 assert.deepEqual(seenApi.readSeenMoments({getItem:()=>"{broken"},a,now),{});
 assert.deepEqual(seenApi.writeSeenMoments(null,a,{"10":now+1000},now),{"10":now+1000});
 assert.equal(Object.keys(seenApi.pruneSeenMoments(Object.fromEntries(Array.from({length:600},(_,i)=>[i,now+1000+i])),now)).length,500);
});

test('credit Moment sends a stable idempotency key and explicit zero price',async()=>{const oldFetch=globalThis.fetch,oldDocument=globalThis.document;globalThis.document={cookie:""};globalThis.fetch=async(url,options)=>{assert.equal(options.body.get("expected_cost"),"0");assert.equal(options.body.get("key"),"11111111-1111-4111-8111-111111111111");return new Response(JSON.stringify({moment:{id:1},charged:0}),{status:202,headers:{"content-type":"application/json"}});};try{const result=await api.createMoment({media:new Blob(["image"],{type:"image/png"}),key:"11111111-1111-4111-8111-111111111111",expectedCost:0});assert.equal(result.charged,0);}finally{globalThis.fetch=oldFetch;globalThis.document=oldDocument;}});
