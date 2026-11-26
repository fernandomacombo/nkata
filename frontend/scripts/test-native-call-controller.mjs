import test from "node:test";
import assert from "node:assert/strict";
import {createNativeCallController} from "../src/services/nativeCallController.js";
const flush=()=>new Promise(r=>setImmediate(r));
function fixture(){
 let state="CHAMANDO",payer=false,mediaCreated=0,closed=0,updates=[],actions=[],active;
 const server=()=>({id:"s",conversation_id:1,kind:"AUDIO",state,payer,rate:3,balance:payer?9:null,max_minutes:3,paid_minutes:state==="ATIVA"?1:0,server_time:"2026-11-25T12:00:00Z",paid_until:state==="ATIVA"?"2026-11-25T12:01:00Z":null});
 const request=async(path,{body}={})=>{
  if(path.endsWith("/actual/"))return {call:server()};
  if(path.endsWith("/ice/"))return {ice_servers:[]};
  if(path.endsWith("/ticket/"))return {ticket:"t"};
  if(body?.action){actions.push(body.action);state=body.action==="accept"?"ACEITE":body.action==="decline"?"RECUSADA":"TERMINADA";}
  return server();
 };
 const controller=createNativeCallController({request,signalUrl:"wss://example.test/signal",onChange:s=>updates.push(s),createMedia:opts=>{
  mediaCreated++;active=opts.onActive;
  return {connect:async()=>{},close:()=>closed++,toggleMic:()=>false,toggleCamera:()=>false};
 }});
 return {controller,actions,updates,get created(){return mediaCreated;},get closed(){return closed;},activate(){state="ATIVA";active();},setState(s){state=s;},setPayer(p){payer=p;}};
}
test("incoming call requires explicit acceptance; only server and gateway activate media",async()=>{
 const f=fixture(),c=f.controller;
 await c.refresh();assert.equal(c.call.phase,"incoming");assert.equal(f.created,0);
 await c.accept();await flush();assert.equal(f.created,1);assert.equal(c.call.phase,"connecting");
 f.activate();await flush();await c.refresh();assert.equal(c.call.phase,"active");
 c.toggleMic();assert.equal(c.call.micEnabled,false);
 c.end();assert.equal(f.closed,1);assert.equal(c.call.phase,"ended");await flush();assert.deepEqual(f.actions,["accept","end"]);
 c.dispose();
});
test("a reloaded tab cannot silently join or end another tab's accepted call",async()=>{
 const f=fixture();f.setState("ACEITE");await f.controller.refresh();
 assert.equal(f.created,0);assert.equal(f.controller.call,null);assert.deepEqual(f.actions,[]);
 f.controller.dispose();
});
test("declining does not open media",async()=>{
 const f=fixture();await f.controller.refresh();await f.controller.decline();
 assert.equal(f.controller.call.phase,"declined");assert.equal(f.created,0);f.controller.dispose();
});
