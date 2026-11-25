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

test("admission uses signed HTTPS and only trusts Django identity",async()=>{
 const {createAdmissionClient,joinPath}=await import("./lease-client.mjs");
 const {createHmac}=await import("node:crypto");
 const secret="x".repeat(40),sessionId="12345678-1234-1234-1234-123456789abc";
 const admit=createAdmissionClient({origin:"https://example.test",secret,fetcher:async(url,opts)=>{
  assert.equal(url.pathname,joinPath);assert.equal(opts.redirect,"error");
  assert.deepEqual(JSON.parse(opts.body),{ticket:"opaque-ticket"});
  const h=opts.headers;
  assert.equal(h["X-NKATA-Media-Signature"],createHmac("sha256",secret)
   .update("POST\n"+joinPath+"\n"+h["X-NKATA-Media-Time"]+"\n"+h["X-NKATA-Media-Nonce"]+"\n"+opts.body).digest("hex"));
  return {ok:true,json:async()=>({authorized:true,session_id:sessionId,user_id:7,kind:"AUDIO"})};
 }});
 assert.deepEqual(await admit("opaque-ticket"),{sessionId,userId:7,kind:"AUDIO"});
 assert.equal(await admit({ticket:"opaque-ticket",userId:99}),null);
});
test("admission rejects denied and invalid gateway responses",async()=>{
 const {createAdmissionClient}=await import("./lease-client.mjs");
 const config={origin:"https://example.test",secret:"x".repeat(40)};
 assert.equal(await createAdmissionClient({...config,fetcher:async()=>({ok:false})})("ticket"),null);
 assert.equal(await createAdmissionClient({...config,fetcher:async()=>({ok:true,json:async()=>({authorized:true,session_id:"bad",user_id:7,kind:"AUDIO"})})})("ticket"),null);
 assert.throws(()=>createAdmissionClient({...config,origin:"http://example.test"}));
});


test("independent lease is acknowledged before resume and cleared only after early pause",async()=>{
 let now=1000,events=[],calls=0;
 const consumer={async pause(){events.push("pause");},async resume(){events.push("resume");}};
 const gate=new LeaseGate({sessionId:"lease",userIds:[1,2],clock:()=>now,schedule:()=>1,cancel:()=>{},
  connected:()=>true,consumers:()=>[consumer],closeTransport:()=>events.push("close"),
  authorize:async()=>{calls++;return calls===1?61000:121000;},
  watchdog:{async arm(id,deadline){events.push("arm:"+deadline);},async clear(id,deadline){events.push("clear:"+deadline);}}});
 await gate.tick();
 assert.deepEqual(events,["pause","arm:61000","resume"]);
 now=60250;await gate.tick();
 assert.deepEqual(events.slice(-2),["pause","clear:61000"]);
 assert.equal(calls,1);
 now=61000;await gate.tick();
 assert.equal(calls,2);assert.deepEqual(events.slice(-3),["pause","arm:121000","resume"]);
 await gate.stop();
});
test("missing watchdog acknowledgement prevents resume",async()=>{
 let resumed=0,closed=0;
 const gate=new LeaseGate({sessionId:"lease",userIds:[1,2],clock:()=>1000,schedule:()=>1,cancel:()=>{},
  connected:()=>true,consumers:()=>[{pause:async()=>{},resume:async()=>resumed++}],closeTransport:()=>closed++,
  authorize:async()=>61000,watchdog:{arm:async()=>{throw Error("IPC");}}});
 await gate.tick();assert.equal(resumed,0);assert.equal(closed,1);
});


test("lost authorization reply reconciles only a minute not resumed",async()=>{
 let reports=[],resumed=0;
 const gate=new LeaseGate({sessionId:"s",userIds:[1,2],clock:()=>1000,schedule:()=>1,cancel:()=>{},
  connected:()=>true,consumers:()=>[{pause:async()=>{},resume:async()=>resumed++}],
  closeTransport:()=>{},authorize:async()=>{throw Error("response lost");},
  reconcile:async report=>{reports.push(report);return true;}});
 await gate.tick();await gate.stop();
 assert.equal(resumed,0);assert.deepEqual(reports,[{sessionId:"s",userIds:[1,2],minute:1}]);
});
test("ambiguous failure during resume never triggers automatic refund",async()=>{
 let reports=0;
 const gate=new LeaseGate({sessionId:"s",userIds:[1,2],clock:()=>1000,schedule:()=>1,cancel:()=>{},
  connected:()=>true,consumers:()=>[{pause:async()=>{},resume:async()=>{throw Error("partial resume");}}],
  closeTransport:()=>{},authorize:async()=>61000,reconcile:async()=>{reports++;return true;}});
 await gate.tick();assert.equal(gate.closed,true);assert.equal(reports,0);
});


test("resume evidence is persisted before transmission",async()=>{
 let events=[];
 const gate=new LeaseGate({sessionId:"s",userIds:[1,2],clock:()=>1000,schedule:()=>1,cancel:()=>{},
  connected:()=>true,consumers:()=>[{pause:async()=>{},resume:async()=>events.push("resume")}],
  closeTransport:()=>{},authorize:async()=>61000,
  recordResume:async({phase})=>{events.push(phase);return true;}});
 await gate.tick();assert.deepEqual(events,["INTENT","resume","CONFIRMED"]);await gate.stop();
});
test("missing durable intent acknowledgement prevents transmission",async()=>{
 let resumed=0,refunded=0;
 const gate=new LeaseGate({sessionId:"s",userIds:[1,2],clock:()=>1000,schedule:()=>1,cancel:()=>{},
  connected:()=>true,consumers:()=>[{pause:async()=>{},resume:async()=>resumed++}],
  closeTransport:()=>{},authorize:async()=>61000,reconcile:async()=>{refunded++;return true;},
  recordResume:async()=>false});
 await gate.tick();assert.equal(resumed,0);assert.equal(refunded,0);assert.equal(gate.closed,true);
});


test("early boundary timer waits without revalidating or charging ahead of time",async()=>{
 let now=1000,calls=[],events=[],scheduled;
 const gate=new LeaseGate({sessionId:"s",userIds:[1,2],clock:()=>now,
  schedule:(fn,ms)=>{scheduled=ms;return 1;},cancel:()=>{},
  connected:()=>true,consumers:()=>[{pause:async()=>events.push("pause"),resume:async()=>events.push("resume")}],
  closeTransport:()=>events.push("close"),authorize:async({minute})=>{calls.push(minute);return minute===1?61000:null;}});
 await gate.tick();
 now=60999;await gate.tick();
 assert.deepEqual(calls,[1]);assert.equal(scheduled,1);assert.equal(gate.closed,false);
 now=61000;await gate.tick();
 assert.deepEqual(calls,[1,2]);assert.equal(gate.closed,true);
});
