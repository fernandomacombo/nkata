// Isolated CI experiment: real browsers, worker, WebSocket and local TURN.
// No Django, no real accounts, no live domains or financial transactions.
import assert from "node:assert/strict";
import {createServer} from "node:https";
import {readFile,mkdtemp,rm,writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join,resolve} from "node:path";
import {execFileSync,spawn} from "node:child_process";
import {createHmac,randomBytes} from "node:crypto";
import {setTimeout as sleep} from "node:timers/promises";
import {createWorker} from "mediasoup";
import {WebSocketServer} from "ws";
import {chromium} from "playwright";
import {build} from "esbuild";
import {SfuRoom} from "../sfu-room.mjs";
import {attachSignalling} from "../signalling.mjs";
import {verifyInboundMedia} from "../runtime.mjs";

if(process.env.NKATA_MEDIA_BROWSER_TEST!=="isolated-ci")throw Error("Isolated CI only");
const dir=await mkdtemp(join(tmpdir(),"nkata-media-"));
let worker,turn,server,wss,signalling,browser;
const secret=randomBytes(32).toString("hex");
const tickets=new Map(),rooms=new Map(),attempts=new Map();
const eventually=async(fn,label,ms=20000)=>{
 const deadline=Date.now()+ms;
 while(Date.now()<deadline){if(await fn())return;await sleep(100);}
 throw Error(label);
};
try{
 const key=join(dir,"key.pem"),cert=join(dir,"cert.pem");
 execFileSync("openssl",["req","-x509","-newkey","rsa:2048","-nodes","-days","1","-subj","/CN=127.0.0.1","-addext","subjectAltName=IP:127.0.0.1","-keyout",key,"-out",cert],{stdio:"ignore"});
 // Loopback allowance is exclusively for this ephemeral local test.
 turn=spawn("turnserver",["-n","--listening-ip=127.0.0.1","--relay-ip=127.0.0.1","--listening-port=34780",
  "--min-port=49220","--max-port=49320","--realm=nkata-ci.test","--use-auth-secret","--static-auth-secret="+secret,
  "--allow-loopback-peers","--no-multicast-peers","--no-tls","--no-dtls","--no-cli","--no-tcp-relay",
  "--pidfile="+join(dir,"turn.pid"),"--log-file="+join(dir,"turn.log"),"--simple-log"],{stdio:"ignore"});
 let turnError;turn.on("error",e=>{turnError=e;});
 await sleep(1000);if(turnError||turn.exitCode!==null)throw Error("Local TURN failed");
 worker=await createWorker({logLevel:"warn"});
 const wrtc=await worker.createWebRtcServer({listenInfos:[{protocol:"udp",ip:"127.0.0.1",port:44445}]});
 const bundle=await build({stdin:{contents:`
 import {Device} from "mediasoup-client";
 import {createBrowserMedia} from "../frontend/src/services/nativeCallMedia.js";
 window.startTest=async config=>{
  window.active=false;window.closed=false;window.streams=null;
  const media=createBrowserMedia({Device,onActive:()=>window.active=true,onClosed:()=>window.closed=true,onStreams:s=>{
   window.streams=s;
   const el=document.querySelector("video");el.srcObject=s.remoteStream;el.play().catch(()=>{});
  }});
  window.media=media;
  await media.connect(config);
 };
 `,resolveDir:process.cwd(),sourcefile:"browser-entry.js"},bundle:true,platform:"browser",write:false});
 server=createServer({key:await readFile(key),cert:await readFile(cert)},(req,res)=>{
  if(req.url==="/bundle.js"){res.writeHead(200,{"Content-Type":"application/javascript"});res.end(bundle.outputFiles[0].text);}
  else{res.writeHead(200,{"Content-Type":"text/html"});res.end('<!doctype html><video autoplay playsinline muted></video><script src="/bundle.js"></script>');}
 });
 await new Promise(r=>server.listen(0,"127.0.0.1",r));
 const origin="https://127.0.0.1:"+server.address().port;
 wss=new WebSocketServer({server,maxPayload:32768,perMessageDeflate:false});
 signalling=attachSignalling({wss,origin,admit:async ticket=>{
  const id=tickets.get(ticket);tickets.delete(ticket);return id||null;
 },verifyMedia:verifyInboundMedia,createRoom:async identity=>{
  const router=await worker.createRouter({mediaCodecs:[{kind:"audio",mimeType:"audio/opus",clockRate:48000,channels:2},{kind:"video",mimeType:"video/VP8",clockRate:90000}]});
  const room=new SfuRoom({router,sessionId:identity.sessionId,kind:identity.kind,
   transportOptions:{webRtcServer:wrtc,enableUdp:true,enableTcp:false},
   authorize:async({minute})=>{
    const a=attempts.get(identity.sessionId)||[];a.push(minute);attempts.set(identity.sessionId,a);
    // Short synthetic lease; never applies to production billing.
    if(minute!==1)return null;
    if(!room.testDeadline)room.testDeadline=Date.now()+4500;
    return room.testDeadline;
   }});
  rooms.set(identity.sessionId,room);return room;
 }});
 browser=await chromium.launch({headless:true,args:["--use-fake-device-for-media-stream","--use-fake-ui-for-media-stream","--autoplay-policy=no-user-gesture-required"]});
 for(const kind of ["AUDIO","VIDEO"]){
  const sid="ci-"+kind,contexts=[],pages=[];
  try{
   for(const uid of [1,2]){
    const context=await browser.newContext({ignoreHTTPSErrors:true,permissions:["microphone","camera"]});contexts.push(context);
    const page=await context.newPage();pages.push(page);
    await page.goto(origin);await page.waitForFunction(()=>typeof window.startTest==="function");
   }
   const configs=[1,2].map(uid=>{
    const ticket=randomBytes(16).toString("hex");tickets.set(ticket,{sessionId:sid,userId:uid,kind});
    const username=Math.floor(Date.now()/1000+600)+":"+uid;
    const credential=createHmac("sha1",secret).update(username).digest("base64");
    return {kind,ticket,signalUrl:origin.replace("https:","wss:")+"/signal",
     iceServers:[{urls:"turn:127.0.0.1:34780?transport=udp",username,credential}]};
   });
   await Promise.all(pages.map((p,i)=>p.evaluate(config=>window.startTest(config),configs[i])));
   await eventually(async()=> (await Promise.all(pages.map(p=>p.evaluate(()=>window.active)))).every(Boolean),"Both clients must activate");
   const room=rooms.get(sid);assert.ok(room);
   await eventually(async()=>{
    const consumers=[...room.peers.values()].flatMap(p=>[...p.consumers.values()]);
    if(consumers.length!==(kind==="VIDEO"?4:2))return false;
    return (await Promise.all(consumers.map(async c=>(await c.getStats()).some(s=>s.type==="outbound-rtp"&&s.packetCount>0)))).every(Boolean);
   },"Both directions must forward media",3000);
   // The two browsers must have received actual decoded video frames.
   if(kind==="VIDEO")await Promise.all(pages.map(p=>p.waitForFunction(()=>document.querySelector("video").videoWidth>0,{},{timeout:3000})));
   await eventually(()=>room.closed,"Denied renewal must close SFU room",10000);
   await eventually(async()=> (await Promise.all(pages.map(p=>p.evaluate(()=>window.closed&&window.streams.localStream.getTracks().every(t=>t.readyState==="ended"))))).every(Boolean),"Both clients must release local tracks");
   assert.deepEqual(attempts.get(sid),[1,2]);
   console.log(kind+": real browser relay and denied renewal validated");
  }finally{for(const context of contexts)await context.close();}
 }
}finally{
 await browser?.close();signalling?.close();for(const ws of wss?.clients||[])ws.terminate();wss?.close();
 server?.close();worker?.close();turn?.kill("SIGTERM");await rm(dir,{recursive:true,force:true});
}
