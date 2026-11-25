import test from "node:test";
import assert from "node:assert/strict";
import {readConfig,verifyInboundMedia} from "./runtime.mjs";
const env={NKATA_MEDIA_RUNTIME:"isolated-staging",NKATA_STAGING_WEB_ORIGIN:"https://stage.example.test",NKATA_STAGING_API_ORIGIN:"https://api-stage.example.test",NKATA_MEDIA_GATEWAY_SECRET:"x".repeat(40),NKATA_MEDIA_ANNOUNCED_IP:"192.0.2.10"};
test("runtime refuses production, unsafe origin and missing explicit staging flag",()=>{
 assert.equal(readConfig(env).mediaPort,44444);
 assert.throws(()=>readConfig({...env,NKATA_MEDIA_RUNTIME:"production"}));
 assert.throws(()=>readConfig({...env,NKATA_STAGING_API_ORIGIN:"https://nkata.date"}));
 assert.throws(()=>readConfig({...env,NKATA_STAGING_WEB_ORIGIN:"http://stage.example.test"}));
 assert.throws(()=>readConfig({...env,NKATA_MEDIA_ANNOUNCED_IP:"127.0.0.1"}));
});
test("each producer needs increasing inbound RTP counters",async()=>{
 const p=(increment)=>{let n=0;return {getStats:async()=>[{type:"inbound-rtp",packetCount:n+=increment}]};};
 const room=(a,b)=>({ready:()=>true,peers:new Map([[1,{producers:new Map([["audio",a]])}],[2,{producers:new Map([["audio",b]])}]])});
 const options={sleep:async()=>{}};
 assert.equal(await verifyInboundMedia(room(p(5),p(4)),options),true);
 assert.equal(await verifyInboundMedia(room(p(5),p(0)),options),false);
});
