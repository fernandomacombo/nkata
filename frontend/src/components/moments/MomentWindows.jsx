import { useMemo, useState } from "react";
import { ArrowUpRight, Camera, Clock3, Globe, Heart, Play, Plus, Shuffle, Sparkles, Sun } from "lucide-react";
import "./moment-windows.css";

export function activeMomentGroups(groups, now = Date.now()) {
  return groups.map(group => ({...group, moments: group.moments.filter(moment =>
    moment.moderation_status === "APROVADO" &&
    Number.isFinite(Date.parse(moment.expires_at)) && Date.parse(moment.expires_at) > now
  )})).filter(group => group.moments.length);
}

const accents = [Sun, Globe, Sparkles, Heart];
const inspirations = [
  ["O que te faz sorrir?", "What makes you smile?"],
  ["Qual é o teu lugar de paz?", "Where do you find peace?"],
  ["Que pequeno momento tornou o teu dia especial?", "What small moment made your day special?"],
  ["O que gostas de fazer no teu tempo livre?", "What do you enjoy in your free time?"],
];

function WindowCard({ group, index, seen, english, onOpen }) {
  const moment = group.moments.find(item => !seen.has(item.id)) || group.moments[0];
  const Accent = accents[index % accents.length];
  const allSeen = group.moments.every(item => seen.has(item.id));
  const tall = index % 4 === 0 || index % 4 === 3;
  return <button type="button" className={"nk-janelas__window " + (tall ? "is-tall" : "is-short") + (allSeen ? " is-seen" : "")}
    aria-label={(english ? "Open Moment by " : "Abrir momento de ") + group.profile.nome_publico} onClick={() => onOpen(group, moment.id)}>
    <span className={"nk-janelas__media nk-moment-theme-" + (moment.theme || "wine") + " nk-moment-font-" + (moment.font || "serif")}>
      {moment.media_type === "IMAGEM" && moment.media_url ? <img src={moment.media_url} alt="" loading="lazy" decoding="async"/> :
       moment.media_type === "VIDEO" && moment.media_url ? <><video src={moment.media_url} muted playsInline preload="none" aria-hidden="true"/><span className="nk-janelas__play"><Play size={20} fill="currentColor"/></span></> :
       <span className="nk-janelas__phrase"><Accent size={25}/>{moment.text || (english ? "A moment" : "Um momento")}</span>}
    </span>
    <span className="nk-janelas__details">
      <Accent size={17} aria-hidden="true"/>
      <strong>{group.mine ? (english ? "Your Moment" : "O teu momento") : group.profile.nome_publico}</strong>
      <span className="nk-janelas__meta"><span>{group.moments.length} {group.moments.length === 1 ? (english ? "moment" : "momento") : (english ? "moments" : "momentos")} · {allSeen ? (english ? "Seen" : "Visto") : (english ? "New" : "Novo")}</span><ArrowUpRight size={15}/></span>
    </span>
  </button>;
}

export default function MomentWindows({groups, english, composerOpen, onCreate, onOpen, seen = new Set()}) {
  const active = activeMomentGroups(groups);
  const [filter, setFilter] = useState("all");
  const unseen = active.flatMap(group => group.mine ? [] : group.moments.filter(moment => !seen.has(moment.id)).map(moment => ({group, id:moment.id})));
  const visible = active.filter(group => filter === "all" || (filter === "new" ? group.moments.some(m => !seen.has(m.id)) : group.moments.every(m => seen.has(m.id))));
  const inspiration = useMemo(() => inspirations[Math.floor(Date.now()/86400000) % inspirations.length][english ? 1 : 0], [english]);
  const left = visible.filter((_,i) => i%2===0);
  const right = visible.filter((_,i) => i%2===1);
  const surprise = () => {if(unseen.length){const pick = unseen[Math.floor(Math.random()*unseen.length)];onOpen(pick.group,pick.id);}};
  return <section className="nk-janelas" aria-label={english ? "Today's windows" : "Janelas de hoje"}>
    <header className="nk-janelas__hero">
      <div><span className="nk-janelas__eyebrow">{english ? "ONE DAY. MANY STORIES." : "UM DIA. MUITAS HISTÓRIAS."}</span><h2>{english ? "Open a window into someone's world." : "Abre uma janela para o mundo de alguém."}</h2><p>{english ? "Small moments that live for just 24 hours." : "Pequenos momentos que vivem apenas 24h."}</p></div>
      <button className="nk-janelas__add" type="button" onClick={onCreate} aria-expanded={Boolean(composerOpen)} aria-label={english ? "New Moment" : "Novo Momento"}><Plus size={26}/></button>
    </header>
    <div className="nk-janelas__toolbar"><h3>{english ? "Today's windows" : "Janelas de hoje"}</h3><span>{unseen.length} {english ? "to discover" : "por descobrir"}</span></div>
    <div className="nk-janelas__filters" aria-label={english ? "Filter Moments" : "Filtrar Momentos"}>{[["all","Todos","All"],["new","Por ver","Unseen"],["seen","Já vistos","Seen"]].map(([value,pt,en]) => <button type="button" key={value} aria-pressed={filter===value} onClick={()=>setFilter(value)}>{english?en:pt}</button>)}</div>
    <div className="nk-janelas__grid">
      <div className="nk-janelas__column">
        {left.slice(0,1).map(group=><WindowCard key={group.profile.id} group={group} index={0} seen={seen} english={english} onOpen={onOpen}/>)}
        <button type="button" className="nk-janelas__surprise" disabled={!unseen.length} onClick={surprise}><span className="nk-janelas__cards" aria-hidden="true"><span><Heart size={26}/></span><span><Sparkles size={27}/></span></span><strong>{english ? "Surprise me!" : "Surpreende-me!"}</strong><small>{english ? "Open an unseen Moment" : "Abre um momento por descobrir"}</small><Shuffle size={17}/></button>
        {left.slice(1).map((group,i)=><WindowCard key={group.profile.id} group={group} index={(i+1)*2} seen={seen} english={english} onOpen={onOpen}/>)}
      </div>
      <div className="nk-janelas__column">
        {right.slice(0,1).map(group=><WindowCard key={group.profile.id} group={group} index={1} seen={seen} english={english} onOpen={onOpen}/>)}
        <button type="button" className="nk-janelas__inspiration" onClick={onCreate}><span><Camera size={25}/></span><strong>{inspiration}</strong><small>{english ? "Share your Moment" : "Partilha o teu momento"}</small></button>
        {right.slice(1).map((group,i)=><WindowCard key={group.profile.id} group={group} index={(i+1)*2+1} seen={seen} english={english} onOpen={onOpen}/>)}
      </div>
    </div>
    {!visible.length && <p className="nk-janelas__empty" role="status">{english ? "No Moments here yet." : "Ainda não há momentos nesta seleção."}</p>}
    <p className="nk-janelas__foot"><Clock3 size={14}/>{english ? "Tomorrow, new windows open." : "Amanhã, novas janelas se abrem."}</p>
  </section>;
}
