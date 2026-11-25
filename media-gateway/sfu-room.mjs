// Experimental mediasoup room adapter. One dedicated Router per call.
// This is NOT a network server; only an authenticated server-side dispatcher
// may pass the identities returned by createAdmissionClient to addPeer.
import {LeaseGate} from "./lease-gate.mjs";

const connected=t=>!!t&&!t.closed&&t.dtlsState==="connected"&&["connected","completed"].includes(t.iceState);
const transportInfo=t=>({id:t.id,iceParameters:t.iceParameters,iceCandidates:t.iceCandidates,dtlsParameters:t.dtlsParameters});

export class SfuRoom{
 constructor({router,sessionId,kind,transportOptions,authorize}){
  if(!router||!["AUDIO","VIDEO"].includes(kind)||!sessionId||typeof authorize!=="function")throw Error("Invalid room");
  Object.assign(this,{router,sessionId,kind,transportOptions,authorize});
  this.peers=new Map();this.closed=false;this.sealed=false;this.queue=Promise.resolve();
 }
 // Serialize topology updates; no new producers or consumers after activation.
 run(fn){
  const task=this.queue.then(()=>{if(this.closed||this.sealed)throw Error("Room unavailable");return fn();});
  this.queue=task.catch(()=>{});return task;
 }
 peer(uid){const p=this.peers.get(uid);if(!p)throw Error("Peer unavailable");return p;}
 addPeer(admission){
  return this.run(()=>{
   if(admission?.sessionId!==this.sessionId||admission.kind!==this.kind||
      !Number.isSafeInteger(admission.userId)||admission.userId<=0||
      this.peers.size>=2||this.peers.has(admission.userId))throw Error("Admission denied");
   this.peers.set(admission.userId,{transports:new Map(),producers:new Map(),consumers:new Map()});
   return this.router.rtpCapabilities;
  });
 }
 createTransport(uid,direction){
  return this.run(async()=>{
   const p=this.peer(uid);
   if(!["send","recv"].includes(direction)||p.transports.has(direction))throw Error("Invalid transport");
   const t=await this.router.createWebRtcTransport(this.transportOptions);
   if(this.closed){t.close();throw Error("Room closed");}
   p.transports.set(direction,t);
   t.on("dtlsstatechange",s=>{if(["failed","closed"].includes(s))this.close();});
   t.on("icestatechange",s=>{if(s==="disconnected"||s==="closed")this.close();});
   t.on("routerclose",()=>this.close());
   return transportInfo(t);
  });
 }
 connectTransport(uid,direction,dtlsParameters){
  return this.run(async()=>{
   const t=this.peer(uid).transports.get(direction);
   if(!t||t.closed)throw Error("Transport unavailable");
   await t.connect({dtlsParameters});
  });
 }
 produce(uid,kind,rtpParameters){
  return this.run(async()=>{
   const p=this.peer(uid),t=p.transports.get("send");
   if(!t||t.closed||!["audio","video"].includes(kind)||
      (kind==="video"&&this.kind!=="VIDEO")||p.producers.has(kind))throw Error("Producer denied");
   const producer=await t.produce({kind,rtpParameters});
   if(this.closed){producer.close();throw Error("Room closed");}
   p.producers.set(kind,producer);
   producer.on("transportclose",()=>this.close());
   return {id:producer.id};
  });
 }
 consume(uid,producerId,rtpCapabilities){
  return this.run(async()=>{
   const p=this.peer(uid),t=p.transports.get("recv");
   const other=[...this.peers].find(([id])=>id!==uid)?.[1];
   const producer=[...(other?.producers.values()||[])].find(x=>x.id===producerId);
   if(!t||t.closed||!producer||producer.closed||p.consumers.has(producerId)||
      !this.router.canConsume({producerId,rtpCapabilities}))throw Error("Consumer denied");
   const c=await t.consume({producerId,rtpCapabilities,paused:true});
   if(this.closed){c.close();throw Error("Room closed");}
   p.consumers.set(producerId,c);
   c.on("producerclose",()=>this.close());c.on("transportclose",()=>this.close());
   return {id:c.id,producerId,kind:c.kind,rtpParameters:c.rtpParameters};
  });
 }
 ready(){
  if(this.closed||this.peers.size!==2)return false;
  return [...this.peers.values()].every(p=>
   connected(p.transports.get("send"))&&connected(p.transports.get("recv"))&&
   !!p.producers.get("audio")&&!p.producers.get("audio").closed&&
   [...p.consumers.values()].some(c=>!c.closed&&c.kind==="audio")&&
   [...p.producers.values()].every(x=>!x.closed)&&[...p.consumers.values()].every(x=>!x.closed));
 }
 // Only called by the server after transport and client preparation; never
 // expose as a direct browser command. Actual RTP checks remain an open task.
 start(){
  return this.run(async()=>{
   if(!this.ready())throw Error("Room not ready");
   this.sealed=true;
   this.gate=new LeaseGate({sessionId:this.sessionId,userIds:[...this.peers.keys()],authorize:this.authorize,
    connected:()=>this.ready(),consumers:()=>[...this.peers.values()].flatMap(p=>[...p.consumers.values()]),
    closeTransport:()=>this.close()});
   await this.gate.tick();
   if(this.closed||!this.gate.deadline)throw Error("Media not authorized");
  });
 }
 close(){
  if(this.closed)return;
  this.closed=true;
  // Dedicated router closure terminates every transport; no browser command.
  try{this.router.close();}finally{
   if(this.gate&&!this.gate.closed)void this.gate.stop().catch(()=>{});
   this.peers.clear();
  }
 }
}
