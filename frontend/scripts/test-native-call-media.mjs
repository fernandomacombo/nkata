import test from "node:test";
import assert from "node:assert/strict";
import {createBrowserMedia} from "../src/services/nativeCallMedia.js";
class Socket extends EventTarget{
 readyState=0;
 constructor(url){super();this.url=url;queueMicrotask(()=>{this.readyState=1;this.dispatchEvent(new Event("open"));});}
 send(raw){const {id,op,args}=JSON.parse(raw);
 const result=op==="join"?{kind:"AUDIO",rtpCapabilities:{}}:op==="producers"?[{kind:"audio",id:"peer"}]:op==="consume"?{id:"c",producerId:"peer",kind:"audio",rtpParameters:{}}:{id:"t"};
 queueMicrotask(()=>this.dispatchEvent(new MessageEvent("message",{data:JSON.stringify({id,ok:true,result})})));
 }
 close(){this.readyState=3;this.dispatchEvent(new Event("close"));}
}
class Track{enabled=true;stopped=false;stop(){this.stopped=true;}}
class Stream{
 constructor(tracks=[]){this.tracks=tracks;}
 getTracks(){return this.tracks;}
 getAudioTracks(){return this.tracks;}
 getVideoTracks(){return [];}
 addTrack(t){this.tracks.push(t);}
}
const transports=[];
class Device{
 async load(){}
 createSendTransport(options){const t={options,on(){},async produce(){},closed:false,close(){this.closed=true;}};transports.push(t);return t;}
 createRecvTransport(options){const t={options,on(){},async consume(){return {track:new Track()};},closed:false,close(){this.closed=true;}};transports.push(t);return t;}
 get rtpCapabilities(){return {};}
}
const config={kind:"AUDIO",ticket:"ticket",iceServers:[{urls:["turns:example.test"],username:"u",credential:"p"}],signalUrl:"wss://example.test/signal"};
test("adapter uses relay, controls microphone and releases all resources",async()=>{
 const track=new Track();let streams;
 const media=createBrowserMedia({Device,WebSocketClass:Socket,Stream,mediaDevices:{getUserMedia:async()=>new Stream([track])},onStreams:s=>{streams=s;}});
 await media.connect(config);
 assert.equal(transports.at(-1).options.iceTransportPolicy,"relay");
 assert.equal(media.toggleMic(),false);assert.equal(track.enabled,false);
 assert.equal(media.toggleMic(),true);assert.equal(track.enabled,true);
 assert.equal(streams.remoteStream.getTracks().length,1);
 media.close();media.close();
 assert.equal(track.stopped,true);assert.equal(streams.remoteStream.getTracks()[0].stopped,true);
 assert.ok(transports.every(t=>t.closed));
});
test("permission resolved after cancellation does not leave microphone open",async()=>{
 let grant;const track=new Track();
 const media=createBrowserMedia({Device,WebSocketClass:Socket,Stream,mediaDevices:{getUserMedia:()=>new Promise(r=>{grant=r;})}});
 const task=media.connect(config);media.close();grant(new Stream([track]));
 await assert.rejects(task);assert.equal(track.stopped,true);
});
test("insecure signalling never requests camera or microphone",async()=>{
 let permissions=0;
 const media=createBrowserMedia({Device,WebSocketClass:Socket,Stream,mediaDevices:{getUserMedia:async()=>{permissions++;}}});
 await assert.rejects(media.connect({...config,signalUrl:"ws://example.test/signal"}));
 assert.equal(permissions,0);
});
