import { useCallback, useEffect, useState } from "react";
import { ArrowRight, ArrowUpRight, Clock3, Heart, Play, Plus, Shuffle, Sparkles, UserRound } from "lucide-react";
import { fetchMoments, groupMomentsByProfile, MOMENTS_REFRESH_MS } from "../../services/momentsApi.js";
import useSeenMoments from "../../hooks/useSeenMoments.js";
import { activeMomentGroups } from "./MomentWindows.jsx";
import AutoplayMomentViewer from "./AutoplayMomentViewer.jsx";
import "./home-windows.css";

export default function HomeWindows({english,userId,onOpenProfile,onExplore,onCreate}){
  const [data,setData]=useState(null),[failed,setFailed]=useState(false),[viewer,setViewer]=useState(null);
  const {seen,markSeen}=useSeenMoments(userId);
  const close=useCallback(()=>setViewer(null),[]);
  useEffect(()=>{
    let pending=null;
    const load=async()=>{
      if(pending||document.hidden)return;
      const controller=new AbortController();pending=controller;
      try{
        const result=await fetchMoments({signal:controller.signal});
        if(!controller.signal.aborted){setData(result.results||[]);setFailed(false);}
      }catch(error){
        if(!controller.signal.aborted){setFailed(true);setData(null);setViewer(null);}
      }finally{if(pending===controller)pending=null;}
    };
    load();
    const timer=window.setInterval(load,MOMENTS_REFRESH_MS);
    document.addEventListener("visibilitychange",load);
    return()=>{pending?.abort();window.clearInterval(timer);document.removeEventListener("visibilitychange",load);};
  },[]);
  const groups=activeMomentGroups(groupMomentsByProfile(data||[])).filter(group=>!group.mine);
  const unseen=groups.flatMap(group=>group.moments.filter(m=>!seen.has(Number(m.id))).map(moment=>({group,moment})));
  const ordered=[...groups].sort((a,b)=>Number(b.moments.some(m=>!seen.has(Number(m.id))))-Number(a.moments.some(m=>!seen.has(Number(m.id)))));
  const open=(group,moment)=>{
    const index=groups.findIndex(g=>g.profile.id===group.profile.id);
    if(index<0||!(Date.parse(moment.expires_at)>Date.now()))return;
    setViewer({groups,index,momentIndex:groups[index].moments.findIndex(m=>m.id===moment.id)});
  };
  // Close an open snapshot if any included Moment is no longer authorised by the latest feed.
  useEffect(()=>{
    if(!viewer||!data)return;
    const ids=new Set(data.filter(m=>m.moderation_status==="APROVADO").map(m=>m.id));
    if(viewer.groups.some(group=>group.moments.some(m=>!ids.has(m.id))))close();
  },[data,viewer,close]);
  return <section className="nk-living-windows" aria-label={english?"Today's windows":"Janelas de hoje"}>
    <header className="nk-living-windows__header"><div><span className="nk-living-windows__eyebrow"><Sparkles size={13}/>{english?"ONE DAY. MANY STORIES.":"UM DIA. MUITAS HISTÓRIAS."}</span><h2>{english?"Today's windows":"Janelas de hoje"}</h2><p>{english?"Discover a little of someone's world.":"Descobre um pouco do mundo de alguém."}</p></div><button type="button" className="nk-living-windows__all" onClick={onExplore}>{english?"All Moments":"Ver Momentos"}<ArrowRight size={15}/></button></header>
    <div className="nk-living-windows__rail">
      <button type="button" className="nk-living-windows__tile nk-living-windows__create" onClick={onCreate}><span className="nk-living-windows__add"><Plus size={28}/></span><strong>{english?"Your window":"A tua janela"}</strong><small>{english?"Share today":"Partilha hoje"}</small></button>
      {ordered.slice(0,5).map((group,i)=>{
        const moment=group.moments.find(m=>!seen.has(Number(m.id)))||group.moments[0],isNew=group.moments.some(m=>!seen.has(Number(m.id)));
        return <button key={group.profile.id} type="button" className={"nk-living-windows__tile nk-living-windows__moment "+(isNew?"is-new":"is-seen")} aria-label={(english?"Open Moment by ":"Abrir momento de ")+group.profile.nome_publico} onClick={()=>open(group,moment)}>
          <span className={"nk-living-windows__picture nk-moment-theme-"+(moment.theme||"wine")}>
            {moment.media_type==="IMAGEM"&&moment.media_url?<img src={moment.media_url} alt="" loading="lazy" decoding="async"/>:moment.media_type==="VIDEO"&&moment.media_url?<>{group.profile.foto_url&&<img src={group.profile.foto_url} alt="" loading="lazy" decoding="async"/>}<span className="nk-living-windows__play"><Play size={19} fill="currentColor"/></span></>:<span className="nk-living-windows__phrase"><Heart size={18}/>{moment.text}</span>}
            <span className="nk-living-windows__status">{isNew?(english?"New":"Novo"):(english?"Seen":"Visto")}</span>
          </span>
          <span className="nk-living-windows__name"><strong>{group.profile.nome_publico}</strong><ArrowUpRight size={13}/></span>
        </button>;
      })}
      {unseen.length>0&&<button type="button" className="nk-living-windows__tile nk-living-windows__surprise" onClick={()=>{const pick=unseen[Math.floor(Math.random()*unseen.length)];open(pick.group,pick.moment);}}><span className="nk-living-windows__shuffle"><Shuffle size={25}/></span><strong>{english?"Surprise me!":"Surpreende-me!"}</strong><small>{english?"An unseen Moment":"Uma nova janela"}</small></button>}
    </div>
    <footer className="nk-living-windows__footer"><span><Clock3 size={14}/>{english?"Available for 24h":"Disponíveis durante 24h"}</span><span>{failed?(english?"Temporarily unavailable":"Temporariamente indisponíveis"):data===null?(english?"Loading Moments…":"A carregar Momentos…"):groups.length===0?(english?"No active Moments":"Nenhum momento activo"):unseen.length+" "+(english?"to discover":"por descobrir")}</span></footer>
    {viewer&&<AutoplayMomentViewer groups={viewer.groups} initialGroupIndex={viewer.index} initialMomentIndex={viewer.momentIndex} windowsMode onViewed={markSeen} onClose={close} onOpenProfile={profile=>{close();onOpenProfile?.(profile);}}/>}
  </section>;
}
