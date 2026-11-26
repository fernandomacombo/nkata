import { useState, useRef, useMemo } from "react";
import { ArrowUpRight, Bookmark, ChevronLeft, ChevronRight, Clock, HeartHandshake, MapPin, RefreshCw, Search, ShieldCheck, SlidersHorizontal, Sparkles, UserRound } from "lucide-react";
import { usePresence, usePresenceSnapshot } from "../profiles/Presence.jsx";
import "./discovery-flow.css";

const isDemo = p => String(p?.id).startsWith("demo-");
const verified = p => p?.verificado === true && !isDemo(p);
const recentDate = p => Date.parse(p?.criado_em || "");
const firstName = p => (p?.nome_publico || "").trim().split(/\s+/)[0];
const isOnline = age => typeof age === "number" && age < 35;

export function recentMembers(profiles) {
  return profiles.filter(p => !isDemo(p) && p.foto_url && Number.isFinite(recentDate(p)))
    .sort((a,b) => recentDate(b)-recentDate(a) || Number(b.id)-Number(a.id)).slice(0,5);
}
function dateLabel(p, english) {
  const date = new Date(p.criado_em);
  const calendarDay = d => Date.UTC(d.getFullYear(),d.getMonth(),d.getDate());
  const days = Math.max(0, Math.round((calendarDay(new Date())-calendarDay(date))/86400000));
  if (days === 0) return english ? "Profile created today" : "Perfil criado hoje";
  if (days === 1) return english ? "Profile created yesterday" : "Perfil criado ontem";
  return english ? `Profile created ${days} days ago` : `Perfil criado há ${days} dias`;
}
function intention(p, english) {
  const value = p.objetivo_display;
  return english ? ({"Relacionamento sério":"Serious relationship","Conhecer pessoas com intenção":"Meet with intention","Conhecer com intenção":"Meet with intention","Casamento no futuro":"Marriage in the future","Amizade que pode evoluir":"Friendship that may grow"}[value] || value) : value;
}
function Photo({profile, eager=false, english}) {
  const [failed,setFailed] = useState(false);
  return profile.foto_url && !failed ? <img src={profile.foto_url} alt={profile.nome_publico} loading={eager?"eager":"lazy"} decoding="async" onError={()=>setFailed(true)}/> : <div className="nk-flow__fallback" aria-label={english?"Photo unavailable":"Fotografia indisponível"}><UserRound size={42}/></div>;
}
function Verification({profile, english}) {
  return verified(profile) ? <ShieldCheck className="nk-flow__verified" size={19} aria-label={english?"Verified identity":"Identidade verificada"}/> : null;
}
function Status({profile,english,compact=false}) {
  const {online,label}=usePresence(profile.id,english);
  if(isDemo(profile)) return <span className="nk-flow__status">{english?"Demo":"Demonstração"}</span>;
  return <span className="nk-flow__status" data-presence-id={profile.id} title={label||undefined} aria-label={label|| (english?"Presence unavailable":"Presença indisponível")}>
    <i className={online?"is-online":""}/>{!compact && (online?(english?"Online now":"Online agora"):(label || (english?"Presence unavailable":"Presença indisponível")))}
  </span>;
}
function Save({profile,english,isSaved,onToggleSaved}) {
  const saved=isSaved(profile);
  return <button type="button" className="nk-flow__save" aria-pressed={saved} aria-label={saved?(english?"Remove saved profile":"Remover dos guardados"):(english?"Save profile":"Guardar perfil")} onClick={()=>onToggleSaved(profile)}><Bookmark size={21} fill={saved?"currentColor":"none"}/></button>;
}

function RecentCarousel({profiles,english,onOpenProfile,isSaved,onToggleSaved}) {
  const [activeId,setActiveId]=useState(null);
  const activeIndex=Math.max(0,profiles.findIndex(p=>p.id===activeId));
  const active=profiles[activeIndex];
  const count=profiles.length;
  const pointer=useRef(null), dragged=useRef(false);
  function go(delta){if(count>1)setActiveId(profiles[(activeIndex+delta+count)%count].id);}
  if(!active)return null;
  return <section className="nk-flow__recent" aria-label={english?"Recent members":"Membros recentes"}>
    <header className="nk-flow__recent-head"><div><span><Sparkles size={15}/>{english?"NEW MEMBERS":"RECÉM-CHEGADOS"}</span><h2>{english?"New faces":"Novos rostos"}</h2><p>{english?"New stories start here.":"Novas histórias começam aqui."}</p></div><span className="nk-flow__counter">{String(activeIndex+1).padStart(2,"0")} / {String(count).padStart(2,"0")}</span></header>
    <div className="nk-flow__stage" aria-label={english?"Recent profiles carousel":"Carrossel de perfis recentes"} onPointerDown={e=>{pointer.current={x:e.clientX,y:e.clientY};dragged.current=false;}} onPointerCancel={()=>{pointer.current=null;dragged.current=false;}} onPointerUp={e=>{const p=pointer.current;pointer.current=null;if(p&&Math.abs(e.clientX-p.x)>35&&Math.abs(e.clientX-p.x)>Math.abs(e.clientY-p.y)){dragged.current=true;go(e.clientX<p.x?1:-1);}}} onKeyDown={e=>{if(e.key==="ArrowLeft"||e.key==="ArrowRight"){e.preventDefault();go(e.key==="ArrowLeft"?-1:1);}}}>
      {profiles.map((profile,i)=>{
        let position=(i-activeIndex+count)%count;if(position>count/2)position-=count;
        const visible=Math.abs(position)<=1;
        return <button type="button" key={profile.id} className="nk-flow__slide" data-position={position} aria-hidden={!visible} tabIndex={visible?0:-1} aria-label={profile.nome_publico} onClick={e=>{if(dragged.current&&e.detail!==0){dragged.current=false;return;}if(position===0)onOpenProfile(profile);else setActiveId(profile.id);}}><Photo key={profile.foto_url} profile={profile} english={english} eager={visible}/></button>;
      })}
    </div>
    {count>1&&<nav className="nk-flow__pagination" aria-label={english?"Carousel navigation":"Navegação dos destaques"}><button type="button" onClick={()=>go(-1)} aria-label={english?"Previous":"Anterior"}><ChevronLeft size={20}/></button><div>{profiles.map((p,i)=><button key={p.id} type="button" className={i===activeIndex?"is-active":""} aria-current={i===activeIndex?"true":undefined} aria-label={p.nome_publico} onClick={()=>setActiveId(p.id)}><i/></button>)}</div><button type="button" onClick={()=>go(1)} aria-label={english?"Next":"Seguinte"}><ChevronRight size={20}/></button></nav>}
    <div className="nk-flow__identity" key={active.id} aria-live="polite">
      <span className="nk-flow__joined"><Clock size={13}/>{dateLabel(active,english)}</span>
      <h2>{active.nome_publico}{active.idade?", "+active.idade:""} <Verification profile={active} english={english}/></h2>
      <div className="nk-flow__meta"><span><MapPin size={15}/>{active.cidade}</span><Status profile={active} english={english}/></div>
      {active.objetivo_display&&<p><HeartHandshake size={17}/>{intention(active,english)}</p>}
    </div>
    <div className="nk-flow__actions"><button className="nk-flow__meet" type="button" onClick={()=>onOpenProfile(active)}>{english?"Meet":"Conhecer"} {firstName(active)} <ArrowUpRight size={19}/></button><Save {...{profile:active,english,isSaved,onToggleSaved}}/></div>
    <div className="nk-flow__ornament" aria-hidden="true"><i/><b/><i/></div>
  </section>;
}
export default function DiscoveryFlow({english,profiles,filteredProfiles,loadError,onReload,onOpenProfile,isSaved,onToggleSaved,query,setQuery,city,setCity,objective,setObjective,minAge,setMinAge,maxAge,setMaxAge,clearFilters,hasActiveFilters}) {
  const [filter,setFilter]=useState("all"),[search,setSearch]=useState(false),[advanced,setAdvanced]=useState(false);
  const snapshot=usePresenceSnapshot();
  const recent=useMemo(()=>recentMembers(profiles),[profiles]);
  const recentIds=new Set(recent.map(p=>p.id));
  const filtered=filteredProfiles.filter(p=>filter==="online"?isOnline(snapshot[p.id])&&!isDemo(p):filter==="saved"?isSaved(p):true);
  const rest=filtered.filter(p=>!recentIds.has(p.id));
  const visible=filter==="all"&&!hasActiveFilters&&rest.length?rest:filtered;
  const cities=[...new Set(profiles.map(p=>p.cidade).filter(Boolean))].sort();
  const goals=[...new Set(profiles.map(p=>p.objetivo_display).filter(Boolean))];
  const clear=()=>{clearFilters();setFilter("all");};
  return <main className="nk-discover nk-flow">
    <section className="nk-shell nk-discover__content nk-flow__shell">
      <header className="nk-flow__top"><div><h1>{english?"Profiles":"Perfis"}</h1><p>{english?"Discover. Meet. Connect.":"Descobre. Conhece. Conecta."}</p></div><button type="button" aria-expanded={search} aria-label={english?"Search profiles":"Pesquisar perfis"} onClick={()=>setSearch(v=>!v)}><Search size={21}/></button><button type="button" aria-pressed={filter==="saved"} aria-label={english?"Saved profiles":"Perfis guardados"} onClick={()=>setFilter(f=>f==="saved"?"all":"saved")}><Bookmark size={21} fill={filter==="saved"?"currentColor":"none"}/></button></header>
      {search&&<label className="nk-flow__search"><Search size={18}/><input type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder={english?"Name or city":"Nome ou cidade"} aria-label={english?"Search":"Pesquisar"}/></label>}
      {loadError&&<div className="nk-api-notice" role="status">{english?"Unable to refresh profiles":"Não foi possível atualizar os perfis"}</div>}
      <div hidden aria-hidden="true">{profiles.filter(p=>!isDemo(p)).map(p=><span key={p.id} data-presence-id={p.id}/>)}</div>
      <RecentCarousel profiles={recent} {...{english,onOpenProfile,isSaved,onToggleSaved}}/>
      <section className="nk-flow__explore">
        <header><div><h2>{english?"Explore people":"Explorar pessoas"}</h2><p aria-live="polite">{visible.length} {english?"profiles in this selection":"perfis nesta selecção"}</p></div><button type="button" aria-label={english?"Refresh profiles":"Atualizar perfis"} onClick={onReload}><RefreshCw size={18}/></button><button type="button" aria-expanded={advanced} aria-label={english?"Filters":"Filtros"} onClick={()=>setAdvanced(v=>!v)}><SlidersHorizontal size={21}/></button></header>
        <div className="nk-flow__filters" aria-label={english?"Quick filters":"Filtros rápidos"}>{[["all",english?"All":"Todos"],["online","Online"],["saved",english?"Saved":"Guardados"]].map(([value,label])=><button type="button" key={value} aria-pressed={filter===value} onClick={()=>setFilter(value)}>{value==="online"&&<i/>}{label}</button>)}</div>
        {advanced&&<div className="nk-flow__advanced"><label>{english?"City":"Cidade"}<select value={city} onChange={e=>setCity(e.target.value)}><option value="">{english?"All":"Todas"}</option>{cities.map(c=><option key={c}>{c}</option>)}</select></label><label>{english?"Intention":"Intenção"}<select value={objective} onChange={e=>setObjective(e.target.value)}><option value="">{english?"Any":"Todas"}</option>{goals.map(g=><option key={g} value={g}>{intention({objetivo_display:g},english)}</option>)}</select></label><label>{english?"Minimum age":"Idade mínima"}<input type="number" min="18" max="99" value={minAge} onChange={e=>setMinAge(e.target.value)}/></label><label>{english?"Maximum age":"Idade máxima"}<input type="number" min="18" max="99" value={maxAge} onChange={e=>setMaxAge(e.target.value)}/></label><button type="button" onClick={clear}>{english?"Clear filters":"Limpar filtros"}</button><button type="button" onClick={()=>setAdvanced(false)}>{english?"Show profiles":"Mostrar perfis"}</button></div>}
        {visible.length?<div className="nk-flow__grid">{visible.map((p,i)=><article className="nk-flow__mini" key={p.id} style={{"--nk-flow-delay":Math.min(i,12)*25+"ms"}}><button type="button" className="nk-flow__mini-open" onClick={()=>onOpenProfile(p)} aria-label={(english?"Open profile of ":"Abrir perfil de ")+p.nome_publico}><div className="nk-flow__mini-photo"><Photo key={p.foto_url} profile={p} english={english}/></div><div className="nk-flow__mini-info"><h3><span title={p.nome_publico}>{firstName(p)}</span>{p.idade&&<span>, {p.idade}</span>}<Verification profile={p} english={english}/></h3><div><Status profile={p} english={english} compact/><span>{p.cidade}</span></div></div></button></article>)}</div>:<div className="nk-flow__empty"><UserRound size={30}/><p>{english?"No profiles in this selection":"Nenhum perfil nesta selecção."}</p><button type="button" onClick={hasActiveFilters||filter!=="all"?clear:onReload}>{hasActiveFilters||filter!=="all"?(english?"Show all":"Ver todos"):(english?"Refresh profiles":"Atualizar perfis")}</button></div>}
      </section>
    </section>
  </main>;
}
