// Real native worker, no live network or Django, no real credits.
import test from "node:test";
import assert from "node:assert/strict";
import {setTimeout as sleep} from "node:timers/promises";
import {createWorker} from "mediasoup";
import {Device} from "mediasoup-client";
import {LeaseGate} from "../lease-gate.mjs";
import {verifyInboundMedia} from "../runtime.mjs";

test("native SFU blocks actual RTP before lease and after denied renewal",{timeout:30000},async()=>{
 assert.equal(typeof Device,"function");
 const worker=await createWorker({logLevel:"warn"});
 let gate,interval;
 try{
  const webRtcServer=await worker.createWebRtcServer({listenInfos:[
   {protocol:"udp",ip:"127.0.0.1",portRange:{min:45000,max:45100}},
   {protocol:"tcp",ip:"127.0.0.1",portRange:{min:45101,max:45200}}
  ]});
  const router=await worker.createRouter({mediaCodecs:[{kind:"audio",mimeType:"audio/opus",clockRate:48000,channels:2}]});
  const transport=await router.createWebRtcTransport({webRtcServer,enableUdp:true,enableTcp:true});
  assert.ok(transport.iceCandidates.length>0);
  transport.close();
  // Direct transports exercise the actual C++ RTP forwarding path without
  // claiming browser, ICE, TURN, or mobile-network validation.
  const a=await router.createDirectTransport(),b=await router.createDirectTransport();
  const params=ssrc=>({codecs:[{mimeType:"audio/opus",payloadType:111,clockRate:48000,channels:2}],encodings:[{ssrc}],rtcp:{cname:"test-"+ssrc}});
  const pa=await a.produce({kind:"audio",rtpParameters:params(11111)});
  const pb=await b.produce({kind:"audio",rtpParameters:params(22222)});
  const ca=await a.consume({producerId:pb.id,rtpCapabilities:router.rtpCapabilities,paused:true});
  const cb=await b.consume({producerId:pa.id,rtpCapabilities:router.rtpCapabilities,paused:true});
  let receivedA=0,receivedB=0,sequence=0,now=1000;
  ca.on("rtp",()=>receivedA++);cb.on("rtp",()=>receivedB++);
  const sendPackets=()=>{
   sequence++;
   for(const [producer,ssrc] of [[pa,11111],[pb,22222]]){
    const packet=Buffer.alloc(15);packet[0]=0x80;packet[1]=111;
    packet.writeUInt16BE(sequence%65536,2);packet.writeUInt32BE((sequence*960)>>>0,4);packet.writeUInt32BE(ssrc,8);
    // Synthetic Opus silence payload, never user audio.
    packet.set([0xf8,0xff,0xfe],12);producer.send(packet);
   }
  };
  interval=setInterval(sendPackets,20);
  const room={ready:()=>!router.closed,peers:new Map([[1,{producers:new Map([["audio",pa]])}],[2,{producers:new Map([["audio",pb]])}]])};
  await sleep(250);
  assert.equal(await verifyInboundMedia(room),true,"worker sees RTP from both peers");
  assert.equal(receivedA+receivedB,0,"no packets forwarded before billing");
  let attempts=[];
  gate=new LeaseGate({sessionId:"test",userIds:[1,2],clock:()=>now,schedule:()=>1,cancel:()=>{},
   connected:()=>!router.closed,consumers:()=>[ca,cb],closeTransport:()=>router.close(),
   authorize:async({minute})=>{attempts.push(minute);assert.ok(ca.paused&&cb.paused);return minute===1?61000:null;}});
  await gate.tick();
  assert.equal(gate.closed,false);
  for(let n=0;n<30&&(!receivedA||!receivedB);n++)await sleep(50);
  assert.ok(receivedA>0&&receivedB>0,"RTP flows in both directions only after authorization");
  now=61000;
  // Stop the producer timer once the real worker is closed.
  clearInterval(interval);interval=null;
  await gate.tick();
  assert.equal(gate.closed,true);assert.equal(router.closed,true);
  assert.equal(ca.closed,true);assert.equal(cb.closed,true);
  assert.deepEqual(attempts,[1,2]);
 }finally{if(interval)clearInterval(interval);await gate?.stop();worker.close();}
});
