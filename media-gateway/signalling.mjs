// Experimental dispatcher for an injected WebSocketServer and trusted SFU rooms.
// Configure WSS, maxPayload and connection/rate limits at the HTTP upgrade
// boundary as well. Never expose browser-provided identities to SfuRoom.
export function attachSignalling({wss,origin,admit,createRoom,verifyMedia,maxSockets=100,maxRooms=50,setupMs=45000}){
 if(!origin||new URL(origin).origin!==origin||!origin.startsWith("https://")||
    ![admit,createRoom,verifyMedia].every(x=>typeof x==="function"))throw Error("Invalid signalling config");
 const rooms=new Map(),sockets=new Set();
 const send=(ws,data)=>{if(ws.readyState===1)ws.send(JSON.stringify(data));};
 const end=(ws)=>{try{ws.close(1008,"Session closed");}catch{}};
 function destroy(entry){
  if(!entry||entry.closed)return;
  entry.closed=true;clearTimeout(entry.timer);
  if(rooms.get(entry.id)===entry)rooms.delete(entry.id);
  try{entry.room?.close();}finally{for(const peer of entry.sockets)end(peer);}
 }
 function getRoom(identity){
  let entry=rooms.get(identity.sessionId);
  if(entry)return entry;
  if(rooms.size>=maxRooms)throw Error("Capacity");
  entry={id:identity.sessionId,sockets:new Set(),closed:false,starting:false};
  rooms.set(entry.id,entry);
  entry.timer=setTimeout(()=>destroy(entry),setupMs);entry.timer.unref?.();
  entry.promise=Promise.resolve().then(()=>createRoom(identity)).then(room=>{
   if(entry.closed){room.close();throw Error("Room closed");}
   entry.room=room;return room;
  }).catch(error=>{destroy(entry);throw error;});
  return entry;
 }
 // Server-only readiness check. A client cannot request start or supply proof.
 async function maybeStart(entry){
  if(entry.closed||entry.starting||entry.room?.sealed||!entry.room?.ready())return;
  entry.starting=true;
  try{
   if(!await verifyMedia(entry.room)||entry.closed||!entry.room.ready())return;
   await entry.room.start();
   if(entry.closed)return;
   clearTimeout(entry.timer);
   for(const peer of entry.sockets)send(peer,{event:"active"});
  }catch{destroy(entry);}
  finally{entry.starting=false;}
 }
 // Poll also covers DTLS/ICE transitions that follow the last signalling RPC.
 const timer=setInterval(()=>{
  for(const entry of rooms.values()){
   if(entry.room?.closed)destroy(entry);
   else void maybeStart(entry);
  }
 },500);timer.unref?.();
 wss.on("connection",(ws,req)=>{
  if(req?.headers?.origin!==origin||sockets.size>=maxSockets){end(ws);return;}
  sockets.add(ws);
  let entry=null,identity=null,closed=false,busy=false,count=0,windowAt=Date.now();
  const authTimer=setTimeout(()=>end(ws),5000);authTimer.unref?.();
  ws.on("close",()=>{closed=true;clearTimeout(authTimer);sockets.delete(ws);destroy(entry);});
  ws.on("error",()=>{closed=true;clearTimeout(authTimer);sockets.delete(ws);destroy(entry);end(ws);});
  ws.on("message",async(raw,isBinary)=>{
   if(closed)return;
   if(Date.now()-windowAt>=1000){count=0;windowAt=Date.now();}
   if(busy||++count>20||isBinary||Buffer.byteLength(raw)>32768){end(ws);return;}
   busy=true;
   try{
    const msg=JSON.parse(raw.toString());
    if(!msg||Array.isArray(msg)||typeof msg!=="object"||typeof msg.id!=="string"||
       msg.id.length>80||!msg.id||typeof msg.op!=="string")throw Error("Invalid request");
    const args=msg.args??{};
    if(!args||Array.isArray(args)||typeof args!=="object")throw Error("Invalid arguments");
    const exact=(...keys)=>Object.keys(args).length===keys.length&&keys.every(k=>Object.hasOwn(args,k));
    let result;
    if(!identity){
     if(msg.op!=="join"||!exact("ticket")||typeof args.ticket!=="string"||args.ticket.length>2048)throw Error("Admission required");
     identity=await admit(args.ticket);
     if(!identity||closed||ws.readyState!==1)throw Error("Admission denied");
     entry=getRoom(identity);entry.sockets.add(ws);
     const room=await entry.promise;
     if(closed||entry.closed)throw Error("Room closed");
     result={rtpCapabilities:await room.addPeer(identity),kind:identity.kind};
     clearTimeout(authTimer);
    }else{
     if(entry.closed||!entry.room)throw Error("Room closed");
     const room=entry.room,uid=identity.userId;
     switch(msg.op){
      case "transport":if(!exact("direction"))throw Error("Arguments");result=await room.createTransport(uid,args.direction);break;
      case "connect":if(!exact("direction","dtlsParameters"))throw Error("Arguments");await room.connectTransport(uid,args.direction,args.dtlsParameters);result={};break;
      case "produce":if(!exact("kind","rtpParameters"))throw Error("Arguments");result=await room.produce(uid,args.kind,args.rtpParameters);break;
      case "producers":{
       if(!exact())throw Error("Arguments");
       result=[...room.peers].filter(([id])=>id!==uid).flatMap(([,p])=>[...p.producers.values()].filter(x=>!x.closed).map(x=>({id:x.id,kind:x.kind})));
       break;
      }
      case "consume":if(!exact("producerId","rtpCapabilities"))throw Error("Arguments");result=await room.consume(uid,args.producerId,args.rtpCapabilities);break;
      case "leave":if(!exact())throw Error("Arguments");destroy(entry);return;
      default:throw Error("Unsupported operation");
     }
    }
    if(!closed)send(ws,{id:msg.id,ok:true,result});
   }catch{destroy(entry);end(ws);}
   finally{busy=false;}
  });
 });
 return {close(){clearInterval(timer);for(const entry of rooms.values())destroy(entry);for(const ws of sockets)end(ws);}};
}
