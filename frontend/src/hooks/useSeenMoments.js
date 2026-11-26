import {useCallback,useEffect,useMemo,useState} from "react";
import {pruneSeenMoments,readSeenMoments,seenStorageKey,writeSeenMoments} from "../services/seenMoments.js";
function storage(){try{return window.localStorage;}catch{return null;}}
export default function useSeenMoments(userId){
  const key=seenStorageKey(userId);
  const [state,setState]=useState(()=>({key,entries:readSeenMoments(storage(),key)}));
  const entries=state.key===key?state.entries:{};
  useEffect(()=>{
    const refresh=()=>setState(old=>({key,entries:writeSeenMoments(storage(),key,old.key===key?old.entries:{})}));
    setState({key,entries:readSeenMoments(storage(),key)});
    const sync=event=>{if(key&&event.key===key)setState(old=>({key,entries:pruneSeenMoments({...readSeenMoments(storage(),key),...(old.key===key?old.entries:{})})}));};
    window.addEventListener("storage",sync);
    const timer=window.setInterval(refresh,60000);
    return()=>{window.removeEventListener("storage",sync);window.clearInterval(timer);};
  },[key]);
  const markSeen=useCallback(moment=>{
    if(!moment||moment.mine||moment.moderation_status!=="APROVADO")return;
    const id=String(moment.id),expiry=Date.parse(moment.expires_at),now=Date.now();
    if(!/^\d+$/.test(id)||!Number.isFinite(expiry)||expiry<=now||expiry>now+86400000)return;
    setState(old=>({key,entries:writeSeenMoments(storage(),key,{...(old.key===key?old.entries:{}),[id]:expiry},now)}));
  },[key]);
  const seen=useMemo(()=>new Set(Object.keys(pruneSeenMoments(entries)).map(Number)),[entries]);
  return {seen,markSeen};
}
