import {useEffect,useState} from "react";
import {request} from "../../services/api.js";
import {mediaBuildConfig,mediaServerMatches} from "../../services/nativeCallConfig.js";
export default function useNativeCallConfig(allowed){
 const [config,setConfig]=useState(null);
 useEffect(()=>{
  setConfig(null);
  const local=mediaBuildConfig({mode:import.meta.env.MODE,
   webOrigin:import.meta.env.VITE_NKATA_MEDIA_STAGING_ORIGIN,
   signalUrl:import.meta.env.VITE_NKATA_MEDIA_SIGNAL_URL,
   location:window.location,secure:window.isSecureContext});
  if(!allowed||!local)return;
  const abort=new AbortController();
  (async()=>{
   try{
    const remote=await request("/api/chats/chamadas/config/",{signal:abort.signal});
    if(abort.signal.aborted||!mediaServerMatches(local,remote))return;
    const {Device}=await import("#nkata-native-device");
    if(!abort.signal.aborted&&typeof Device==="function")setConfig({enabled:true,Device,...local});
   }catch{}
  })();
  return ()=>abort.abort();
 },[allowed]);
 return allowed?config:null;
}
