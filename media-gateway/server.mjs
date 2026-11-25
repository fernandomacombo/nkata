// Run only on an isolated staging host with TLS reverse proxy and public media ports.
import {createServer} from "node:http";
import {createWorker} from "mediasoup";
import {WebSocketServer} from "ws";
import {readConfig,verifyInboundMedia} from "./runtime.mjs";
import {createAdmissionClient,createLeaseClient} from "./lease-client.mjs";
import {SfuRoom} from "./sfu-room.mjs";
import {attachSignalling} from "./signalling.mjs";

const config=readConfig(process.env);
const worker=await createWorker({logLevel:"warn"});
const webRtcServer=await worker.createWebRtcServer({listenInfos:["udp","tcp"].map(protocol=>({
 protocol,ip:"0.0.0.0",announcedAddress:config.announcedAddress,port:config.mediaPort
}))});
const gateway={origin:config.backend,secret:config.secret};
const authorize=createLeaseClient(gateway);
const server=createServer((req,res)=>{
 const ok=req.method==="GET"&&req.url==="/healthz"&&!worker.closed;
 res.writeHead(ok?200:404,{"Content-Type":"application/json","Cache-Control":"no-store"});
 res.end(ok?'{"status":"ok"}':'{}');
});
const wss=new WebSocketServer({noServer:true,maxPayload:32768,perMessageDeflate:false});
const control=attachSignalling({wss,origin:config.origin,admit:createAdmissionClient(gateway),verifyMedia:verifyInboundMedia,
 maxSockets:40,maxRooms:20,
 createRoom:async identity=>{
  const router=await worker.createRouter({mediaCodecs:[
   {kind:"audio",mimeType:"audio/opus",clockRate:48000,channels:2},
   {kind:"video",mimeType:"video/VP8",clockRate:90000}
  ]});
  try{return new SfuRoom({router,sessionId:identity.sessionId,kind:identity.kind,
   transportOptions:{webRtcServer,enableUdp:true,enableTcp:true,preferUdp:true,enableSctp:false},authorize});}
  catch(error){router.close();throw error;}
 }
});
server.on("upgrade",(req,socket,head)=>{
 if(req.url!=="/signal"||req.headers.origin!==config.origin||wss.clients.size>=40){
  socket.destroy();return;
 }
 wss.handleUpgrade(req,socket,head,ws=>wss.emit("connection",ws,req));
});
let stopping=false;
function shutdown(code){
 if(stopping)return;stopping=true;
 try{control.close();for(const ws of wss.clients)ws.terminate();wss.close();worker.close();server.close();}finally{process.exit(code);}
}
worker.on("died",()=>shutdown(1));
server.on("error",()=>shutdown(1));
process.on("SIGTERM",()=>shutdown(0));
process.on("SIGINT",()=>shutdown(0));
server.listen(config.httpPort,"127.0.0.1",()=>console.log("NKATA isolated staging media listening"));
