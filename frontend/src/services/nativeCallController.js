// Central experimental call controller. The host must explicitly enable it
// and supply a trusted staging WSS URL and mediasoup-client Device constructor.
import {createBrowserMedia} from "./nativeCallMedia.js";

const root="/api/chats/chamadas/";
const terminal=new Set(["TERMINADA","RECUSADA","EXPIRADA"]);
export function createNativeCallController({request,Device,signalUrl,onChange=()=>{},onError=()=>{},
 createMedia=createBrowserMedia,resolvePeer=()=>({}),pollMs=2000,
 uuid=()=>globalThis.crypto.randomUUID()}){
 let snapshot=null,media=null,consented=null,startingMedia=false,mediaActive=false,mediaReady=false,
     disposed=false,busy=false,polling=false,timer=null,epoch=0,suppressed=null;
 const publish=value=>{snapshot=value;onChange(value);};
 const post=(path,body)=>request(path,{method:"POST",body,signal:AbortSignal.timeout(6000)});
 const get=path=>request(path,{signal:AbortSignal.timeout(6000)});
 function release(){
  epoch++;const previous=media;media=null;startingMedia=false;mediaActive=false;mediaReady=false;consented=null;
  previous?.close();
 }
 function finish(phase="ended"){
  const previous=snapshot;release();
  if(previous)publish({...previous,phase,busy:false,localStream:null,remoteStream:null});
 }
 async function endRemote(id){try{await post(root+id+"/",{action:"end"});}catch{}}
 function fail(id){
  if(disposed||snapshot?.id!==id)return;
  finish("failed");void endRemote(id);
 }
 function render(server){
  const prior=snapshot?.id===server.id?snapshot:null;
  const paid=Number(server.paid_minutes)||0;
  const now=Date.parse(server.server_time),until=Date.parse(server.paid_until);
  const leaseLeft=Number.isFinite(until)&&Number.isFinite(now)?Math.max(0,Math.ceil((until-now)/1000)):0;
  const extra=server.payer&&Number.isFinite(server.balance)&&server.rate>0?
    Math.min(Math.floor(server.balance/server.rate),Math.max(0,server.max_minutes-paid))*60:0;
  const phase=terminal.has(server.state)?(server.state==="RECUSADA"?"declined":"ended"):
    server.state==="CHAMANDO"?(server.payer?"ringing":"incoming"):
    server.state==="ATIVA"&&mediaActive&&mediaReady?"active":"connecting";
  publish({...resolvePeer(server.conversation_id),...prior,id:server.id,conversationId:server.conversation_id,
   kind:server.kind,payer:server.payer,balance:server.balance,rate:server.rate,phase,
   elapsedSeconds:paid?Math.max(0,paid*60-leaseLeft):0,secondsRemaining:leaseLeft+extra,
   busy,micEnabled:prior?.micEnabled??true,cameraEnabled:prior?.cameraEnabled??server.kind==="VIDEO"});
 }
 async function join(server){
  if(startingMedia||media||disposed||consented!==server.id||server.state!=="ACEITE")return;
  startingMedia=true;const generation=epoch,id=server.id;
  try{
   const ice=await post(root+id+"/ice/",{});
   if(disposed||epoch!==generation)return;
   const ticket=await post(root+id+"/ticket/",{});
   if(disposed||epoch!==generation)return;
   const adapter=createMedia({Device,onStreams:streams=>{
    if(!disposed&&epoch===generation&&snapshot?.id===id)publish({...snapshot,...streams});
   },onActive:()=>{if(epoch===generation&&!disposed){mediaActive=true;void refresh();}},
   onClosed:()=>{if(epoch===generation)fail(id);}});
   media=adapter;
   await adapter.connect({kind:server.kind,ticket:ticket.ticket,iceServers:ice.ice_servers,signalUrl});
   if(epoch===generation&&!disposed){mediaReady=true;void refresh();}
  }catch{if(epoch===generation)fail(id);}
  finally{if(epoch===generation)startingMedia=false;}
 }
 function apply(server){
  if(disposed||!server)return;
  if(snapshot&&["ended","declined","failed"].includes(snapshot.phase))return;
  if(server.id===suppressed)return;
  if(snapshot&&snapshot.id!==server.id)return;
  if(terminal.has(server.state)){finish(server.state==="RECUSADA"?"declined":"ended");return;}
  // Reloading or opening another tab cannot silently enable media.
  if(server.state!=="CHAMANDO"&&consented!==server.id)return;
  if(server.state==="CHAMANDO"&&server.payer&&consented!==server.id)return;
  render(server);void join(server);
 }
 async function refresh(){
  if(disposed||polling||busy)return;
  polling=true;const generation=epoch;
  try{
   const id=snapshot?.id;
   if(id&&["ended","declined","failed"].includes(snapshot.phase))return;
   const result=id?await get(root+id+"/"):await get(root+"actual/");
   if(disposed||generation!==epoch||busy)return;
   const server=id?result:result.call;
   if(server)apply(server);
   else if(id)finish();
  }catch{if(!disposed&&generation===epoch&&snapshot?.id)fail(snapshot.id);}
  finally{polling=false;}
 }
 async function start(conversationId,kind,maxMinutes=10){
  if(disposed||busy||snapshot||!["AUDIO","VIDEO"].includes(kind))return;
  busy=true;epoch++;const generation=epoch;
  try{
   const server=await post("/api/chats/"+conversationId+"/chamadas/",{
    key:uuid(),kind,expected_rate:kind==="AUDIO"?3:5,max_minutes:maxMinutes});
   if(disposed||generation!==epoch){void endRemote(server.id);return;}
   consented=server.id;render(server);
  }catch(error){if(!disposed&&generation===epoch)onError(error.message||"Não foi possível iniciar a chamada.");}
  finally{busy=false;if(snapshot&&!disposed)publish({...snapshot,busy:false});}
 }
 async function decide(accept){
  if(disposed||busy||snapshot?.phase!=="incoming")return;
  const id=snapshot.id;busy=true;epoch++;const generation=epoch;
  publish({...snapshot,busy:true});
  try{
   const server=await post(root+id+"/",{action:accept?"accept":"decline"});
   if(disposed||generation!==epoch){if(accept)void endRemote(id);return;}
   if(accept)consented=id;
   apply(server);
  }catch{if(generation===epoch)fail(id);}
  finally{busy=false;if(snapshot&&!disposed)publish({...snapshot,busy:false});}
 }
 function end(){
  if(!snapshot||disposed)return;const id=snapshot.id;finish();void endRemote(id);
 }
 function dismiss(){if(snapshot&&["ended","declined","failed"].includes(snapshot.phase)){suppressed=snapshot.id;publish(null);}}
 function toggle(kind){
  if(snapshot?.phase!=="active"||!media)return;
  const enabled=kind==="mic"?media.toggleMic():media.toggleCamera();
  publish({...snapshot,[kind==="mic"?"micEnabled":"cameraEnabled"]:enabled});
 }
 function begin(){if(disposed||timer!==null)return;timer=setInterval(()=>void refresh(),pollMs);void refresh();}
 function dispose(){
  if(disposed)return;const id=snapshot?.id;disposed=true;clearInterval(timer);release();
  if(id&&!["ended","declined","failed"].includes(snapshot.phase))void endRemote(id);
 }
 return {begin,dispose,refresh,start,accept:()=>decide(true),decline:()=>decide(false),end,dismiss,
  toggleMic:()=>toggle("mic"),toggleCamera:()=>toggle("camera"),get call(){return snapshot;}};
}
