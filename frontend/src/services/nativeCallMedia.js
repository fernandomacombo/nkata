// Experimental browser media adapter. Device is injected by the staging
// bootstrap (mediasoup-client); no billing, no direct peer-to-peer fallback.
export function createBrowserMedia({Device,WebSocketClass=globalThis.WebSocket,
 mediaDevices=globalThis.navigator?.mediaDevices,Stream=globalThis.MediaStream,
 onActive=()=>{},onClosed=()=>{},onStreams=()=>{}}){
 let socket,sendTransport,recvTransport,local,remote,closed=false,pending=null,seq=0,queue=Promise.resolve();
 let started=false;
 const delay=ms=>new Promise(r=>setTimeout(r,ms));
 function stop(){
  if(closed)return;closed=true;
  if(pending){clearTimeout(pending.timer);pending.reject(Error("Chamada encerrada."));pending=null;}
  for(const obj of [sendTransport,recvTransport])try{obj?.close();}catch{}
  for(const stream of [local,remote])for(const track of stream?.getTracks()||[])track.stop();
  try{socket?.close();}catch{}
 }
 function failed(){if(closed)return;stop();onClosed();}
 function rpc(op,args={}){
  const task=queue.then(()=>new Promise((resolve,reject)=>{
   if(closed||socket?.readyState!==1){reject(Error("Ligação indisponível."));return;}
   const id=String(++seq);
   const timer=setTimeout(()=>{failed();},4000);
   pending={id,resolve,reject,timer};
   try{socket.send(JSON.stringify({id,op,args}));}catch{failed();}
  }));
  queue=task.catch(()=>{});return task;
 }
 function bindTransport(t,direction){
  t.on("connect",({dtlsParameters},ok,err)=>{rpc("connect",{direction,dtlsParameters}).then(()=>ok(),err);});
  t.on("connectionstatechange",state=>{if(["failed","closed","disconnected"].includes(state))failed();});
 }
 async function connect({kind,ticket,iceServers,signalUrl}){
  if(started||closed)throw Error("Sessão já utilizada.");
  started=true;
  try{
   const url=new URL(signalUrl);
   if(url.protocol!=="wss:"||url.username||url.password||url.search||url.hash||url.pathname!=="/signal"||
      typeof ticket!=="string"||!ticket||!["AUDIO","VIDEO"].includes(kind)||
      !Array.isArray(iceServers)||!iceServers.some(s=>s.credential&&s.username)||
      !mediaDevices?.getUserMedia||typeof Device!=="function")throw Error("Configuração de chamada indisponível.");
   // The caller must obtain consent before invoking connect; microphone/camera
   // access is not requested by the UI component itself.
   local=await mediaDevices.getUserMedia({audio:true,video:kind==="VIDEO"});
   if(closed){local.getTracks().forEach(t=>t.stop());throw Error("Chamada encerrada.");}
   const audio=local.getAudioTracks(),video=local.getVideoTracks();
   if(audio.length!==1||(kind==="VIDEO"&&video.length!==1))throw Error("Media indisponível.");
   remote=new Stream();
   onStreams({localStream:local,remoteStream:remote});
   socket=new WebSocketClass(url.href);
   await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>{reject(Error("Ligação indisponível."));failed();},4000);
    socket.addEventListener("open",()=>{clearTimeout(timer);resolve();},{once:true});
    socket.addEventListener("error",()=>{clearTimeout(timer);reject(Error("Ligação indisponível."));failed();},{once:true});
    socket.addEventListener("close",()=>{clearTimeout(timer);reject(Error("Chamada encerrada."));failed();},{once:true});
   });
   socket.addEventListener("message",event=>{
    try{
     const msg=JSON.parse(event.data);
     if(msg.event==="active"){if(!closed)onActive();return;}
     if(!pending||msg.id!==pending.id||msg.ok!==true){failed();return;}
     const task=pending;pending=null;clearTimeout(task.timer);task.resolve(msg.result);
    }catch{failed();}
   });
   const joined=await rpc("join",{ticket});
   if(joined.kind!==kind)throw Error("Tipo de chamada inválido.");
   const device=new Device();
   await device.load({routerRtpCapabilities:joined.rtpCapabilities});
   sendTransport=device.createSendTransport({...await rpc("transport",{direction:"send"}),iceServers,iceTransportPolicy:"relay"});
   bindTransport(sendTransport,"send");
   sendTransport.on("produce",({kind,rtpParameters},ok,err)=>rpc("produce",{kind,rtpParameters}).then(ok,err));
   recvTransport=device.createRecvTransport({...await rpc("transport",{direction:"recv"}),iceServers,iceTransportPolicy:"relay"});
   bindTransport(recvTransport,"recv");
   for(const track of [...audio,...video]){
    if(closed)throw Error("Chamada encerrada.");
    // The local stream owns its tracks; closing a producer must not obscure cleanup.
    await sendTransport.produce({track,stopTracks:false});
   }
   const required=kind==="VIDEO"?["audio","video"]:["audio"];
   let peer;
   const deadline=Date.now()+30000;
   while(!closed&&Date.now()<deadline){
    peer=await rpc("producers");
    if(required.every(k=>peer.some(p=>p.kind===k)))break;
    await delay(500);
   }
   if(closed||!peer||!required.every(k=>peer.some(p=>p.kind===k)))throw Error("Sem ligação ao outro participante.");
   for(const k of required){
    const producerId=peer.find(p=>p.kind===k).id;
    const data=await rpc("consume",{producerId,rtpCapabilities:device.rtpCapabilities});
    const consumer=await recvTransport.consume(data);
    if(closed){consumer.close();throw Error("Chamada encerrada.");}
    remote.addTrack(consumer.track);
   }
   onStreams({localStream:local,remoteStream:remote});
   // No browser "start" or credit authorization operation exists.
  }catch(error){stop();throw error;}
 }
 function toggle(kind){
  if(closed)return false;
  const tracks=kind==="audio"?local?.getAudioTracks():local?.getVideoTracks();
  if(!tracks?.length)return false;
  const enabled=!tracks[0].enabled;
  for(const t of tracks)t.enabled=enabled;
  return enabled;
 }
 return {connect,close:stop,toggleMic:()=>toggle("audio"),toggleCamera:()=>toggle("video")};
}
