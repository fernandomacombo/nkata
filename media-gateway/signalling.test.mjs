import test from "node:test";
import assert from "node:assert/strict";
import {EventEmitter} from "node:events";
import {attachSignalling} from "./signalling.mjs";
const origin="https://staging.example.test";
const flush=()=>new Promise(resolve=>setImmediate(resolve));
class Socket extends EventEmitter{
 readyState=1;messages=[];
 send(s){this.messages.push(JSON.parse(s));}
 close(){if(this.readyState!==1)return;this.readyState=3;this.emit("close");}
 async rpc(op,args={}){this.emit("message",Buffer.from(JSON.stringify({id:"r",op,args})),false);await flush();}
}
function fixture(){
 const wss=new EventEmitter(),created=[],calls=[];
 const server=attachSignalling({wss,origin,admit:async ticket=>({
  a:{sessionId:"s",userId:1,kind:"AUDIO"},b:{sessionId:"s",userId:2,kind:"AUDIO"}
 }[ticket]||null),createRoom:async identity=>{
  const room={peers:new Map(),closed:false,ready:()=>false,async addPeer(i){this.peers.set(i.userId,{producers:new Map()});return {};},
   async createTransport(uid,direction){calls.push([uid,direction]);return {id:"t"};},close(){this.closed=true;}};
  created.push(room);return room;
 },verifyMedia:async()=>false});
 const open=(o=origin)=>{const s=new Socket();wss.emit("connection",s,{headers:{origin:o}});return s;};
 return {server,open,created,calls};
}
test("origin and admission required before any room or transport",async()=>{
 const f=fixture();try{
  const bad=f.open("https://other.example.test");assert.equal(bad.readyState,3);
  const anon=f.open();await anon.rpc("transport",{direction:"send"});assert.equal(anon.readyState,3);
  const unknown=f.open();await unknown.rpc("join",{ticket:"unknown"});assert.equal(unknown.readyState,3);
  assert.equal(f.created.length,0);
 }finally{f.server.close();}
});
test("shared room derives identity from ticket, closes on disconnect",async()=>{
 const f=fixture();try{
  const a=f.open(),b=f.open();await a.rpc("join",{ticket:"a"});await b.rpc("join",{ticket:"b"});
  assert.equal(f.created.length,1);assert.equal(a.messages[0].ok,true);
  await b.rpc("transport",{direction:"send"});assert.deepEqual(f.calls,[[2,"send"]]);
  a.close();assert.equal(b.readyState,3);assert.equal(f.created[0].closed,true);
 }finally{f.server.close();}
});
test("browser cannot inject identity or request paid activation",async()=>{
 const f=fixture();try{
  const a=f.open();await a.rpc("join",{ticket:"a",userId:2});assert.equal(a.readyState,3);
  const b=f.open();await b.rpc("join",{ticket:"b"});await b.rpc("start");assert.equal(b.readyState,3);
  assert.equal(f.calls.length,0);assert.equal(f.created[0].closed,true);
 }finally{f.server.close();}
});
