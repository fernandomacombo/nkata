import test from "node:test";
import assert from "node:assert/strict";
import {EventEmitter} from "node:events";
import {SfuRoom} from "./sfu-room.mjs";
function fixture(kind="AUDIO"){
 let next=0,charged=0;
 const events=[],producers=new Map();
 const router={rtpCapabilities:{},closed:false,canConsume:()=>true,close(){this.closed=true;events.push("close");},
  async createWebRtcTransport(){
   const t=new EventEmitter();Object.assign(t,{id:String(++next),dtlsState:"new",iceState:"new",closed:false,
    close(){this.closed=true;},async connect(){},
    async produce({kind}){const p=Object.assign(new EventEmitter(),{id:String(++next),kind,closed:false,close(){this.closed=true;}});producers.set(p.id,p);return p;},
    async consume({producerId,paused}){assert.equal(paused,true);return Object.assign(new EventEmitter(),{id:String(++next),kind:producers.get(producerId).kind,paused,closed:false,
     async pause(){this.paused=true;events.push("pause");},async resume(){this.paused=false;events.push("resume");},close(){this.closed=true;}});}
   });return t;
  }};
 const room=new SfuRoom({router,sessionId:"s",kind,transportOptions:{},authorize:async()=>{charged++;events.push("authorize");return Date.now()+60000;}});
 const admit=id=>room.addPeer({sessionId:"s",userId:id,kind});
 const setup=async()=>{
  await admit(1);await admit(2);
  for(const id of [1,2])for(const d of ["send","recv"])await room.createTransport(id,d);
  const a=await room.produce(1,"audio",{}),b=await room.produce(2,"audio",{});
  await room.consume(1,b.id,{});await room.consume(2,a.id,{});
 };
 const connect=()=>{for(const p of room.peers.values())for(const t of p.transports.values()){t.dtlsState="connected";t.iceState="completed";}};
 return {room,router,admit,setup,connect,events,charges:()=>charged};
}
test("admission and media topology are limited to two peers and call type",async()=>{
 const f=fixture();try{
  await f.admit(1);await f.admit(2);
  await assert.rejects(f.admit(3));await assert.rejects(f.admit(1));
  await f.room.createTransport(1,"send");
  await assert.rejects(f.room.createTransport(1,"send"));
  await assert.rejects(f.room.produce(1,"video",{}));
  await assert.rejects(f.room.consume(1,"unknown",{}));
  assert.equal(f.charges(),0);
 }finally{f.room.close();}
});
test("both connected transports and paused consumers precede authorization",async()=>{
 const f=fixture();try{
  await f.setup();
  await assert.rejects(f.room.start());assert.equal(f.charges(),0);
  f.connect();await f.room.start();
  assert.deepEqual(f.events,["pause","pause","authorize","resume","resume"]);
  await assert.rejects(f.room.createTransport(1,"send"));
  const t=f.room.peers.get(1).transports.get("send");
  t.emit("dtlsstatechange","failed");assert.equal(f.router.closed,true);
 }finally{f.room.close();}
});
test("video call requires video tracks as well as audio",async()=>{
 const f=fixture("VIDEO");try{await f.setup();f.connect();await assert.rejects(f.room.start());assert.equal(f.charges(),0);}finally{f.room.close();}
});
