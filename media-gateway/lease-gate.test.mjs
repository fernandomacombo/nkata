import test from "node:test";
import assert from "node:assert/strict";
import {LeaseGate} from "./lease-gate.mjs";

test("pause before billing, no media after exhausted balance",async()=>{
 let now=1000,events=[],connected=true;
 const consumer={pause:async()=>events.push("pause"),resume:async()=>events.push("resume")};
 const gate=new LeaseGate({sessionId:"session",userIds:[1,2],clock:()=>now,
  connected:()=>connected,consumers:()=>[consumer],closeTransport:async()=>events.push("close"),
  schedule:()=>1,cancel:()=>{},authorize:async({minute})=>{events.push("minute:"+minute);return minute===1?61000:null;}});
 await gate.tick();assert.deepEqual(events,["pause","minute:1","resume"]);
 now=6000;await gate.tick();assert.equal(gate.minute,1);
 now=61000;await gate.tick();assert.deepEqual(events.slice(-3),["pause","minute:2","close"]);
 assert.equal(gate.closed,true);
});
test("gateway error closes transport without resuming",async()=>{
 let resumed=false,closed=false;
 const gate=new LeaseGate({sessionId:"s",userIds:[1,2],connected:()=>true,
  consumers:()=>[{pause:async()=>{},resume:async()=>{resumed=true;}}],
  closeTransport:async()=>{closed=true;},authorize:async()=>{throw Error("offline");}});
 await gate.tick();assert.equal(resumed,false);assert.equal(closed,true);
});
test("disconnected peer cannot trigger billing",async()=>{
 let calls=0,closed=false;
 const gate=new LeaseGate({sessionId:"s",userIds:[1,2],connected:()=>false,consumers:()=>[],
  closeTransport:async()=>{closed=true;},authorize:async()=>{calls++;}});
 await gate.tick();assert.equal(calls,0);assert.equal(closed,true);
});

test("peer disconnecting while media pauses cannot trigger billing",async()=>{
 let connected=true,charged=0,closed=0;
 const gate=new LeaseGate({sessionId:"s",userIds:[1,2],connected:()=>connected,
  consumers:()=>[{pause:async()=>{connected=false;},resume:async()=>{throw Error("unexpected resume");}}],
  closeTransport:async()=>{closed++;},authorize:async()=>{charged++;},
  schedule:()=>1,cancel:()=>{}});
 await gate.tick();assert.equal(charged,0);assert.equal(closed,1);
});
test("pause watchdog closes transport and late acknowledgement cannot charge",async()=>{
 let acknowledge,watchdog,charged=0,closed=0;
 const gate=new LeaseGate({sessionId:"s",userIds:[1,2],connected:()=>true,
  consumers:()=>[{pause:()=>new Promise(resolve=>{acknowledge=resolve;}),resume:async()=>{throw Error("unexpected resume");}}],
  closeTransport:async()=>{closed++;},authorize:async()=>{charged++;},
  schedule:(fn,ms)=>{if(ms===500)watchdog=fn;return 1;},cancel:()=>{}});
 const pending=gate.tick();
 assert.equal(typeof watchdog,"function");
 watchdog();acknowledge();await pending;
 assert.equal(charged,0);assert.equal(closed,1);assert.equal(gate.closed,true);
});
