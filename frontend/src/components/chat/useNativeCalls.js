import {useEffect,useRef,useState} from "react";
import {request} from "../../services/api.js";
import {createNativeCallController} from "../../services/nativeCallController.js";

// No default bootstrap or production flag. A staging host must supply Device
// and its explicitly configured WSS URL, after real-media validation.
export default function useNativeCalls(config,conversations,onError){
 const [call,setCall]=useState(null),[controller,setController]=useState(null);
 const peers=useRef(conversations),errors=useRef(onError);
 peers.current=conversations;errors.current=onError;
 const enabled=config?.enabled===true,Device=config?.Device,signalUrl=config?.signalUrl;
 useEffect(()=>{
  if(!enabled||typeof Device!=="function"||typeof signalUrl!=="string"){setController(null);setCall(null);return;}
  const instance=createNativeCallController({request,Device,signalUrl,onChange:setCall,onError:message=>errors.current?.(message),
   resolvePeer:id=>{const peer=peers.current.find(p=>p.id===id);return {name:peer?.nome,photoUrl:peer?.perfil?.foto_url};}});
  setController(instance);instance.begin();
  return ()=>instance.dispose();
 },[enabled,Device,signalUrl]);
 return enabled&&controller?{...controller,enabled:true,call}:null;
}
