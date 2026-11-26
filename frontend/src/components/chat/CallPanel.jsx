import {useEffect,useRef} from "react";
import {Phone,PhoneOff,Video,VideoOff,Mic,MicOff,UserRound} from "lucide-react";
import "./call-panel.css";

const labels={incoming:"Chamada recebida",ringing:"A chamar...",connecting:"A estabelecer ligação...",active:"Em chamada",ended:"Chamada terminada",declined:"Chamada recusada",failed:"Não foi possível ligar"};
const clock=seconds=>{
 const n=Math.max(0,Math.floor(Number(seconds)||0));
 return [Math.floor(n/60),n%60].map(v=>String(v).padStart(2,"0")).join(":");
};
export function CallActions({enabled,disabled,onStart}){
 if(!enabled||typeof onStart!=="function")return null;
 return <div className="nk-call-actions">
  <button className="nk-chat-icon" type="button" aria-label="Chamada de áudio" title="Chamada de áudio" disabled={disabled} onClick={()=>onStart("AUDIO")}><Phone size={20}/></button>
  <button className="nk-chat-icon" type="button" aria-label="Videochamada" title="Videochamada" disabled={disabled} onClick={()=>onStart("VIDEO")}><Video size={22}/></button>
 </div>;
}
function Action({icon:Icon,label,onClick,variant="",pressed,disabled}){
 return <button type="button" className={"nk-call-control "+variant} onClick={onClick} aria-pressed={pressed} disabled={disabled||typeof onClick!=="function"}><span><Icon size={23} aria-hidden="true"/></span><small>{label}</small></button>;
}
// Display only: authoritative state, elapsed duration, credit balance and
// remaining time must be supplied by the controller; no browser billing.
export default function CallPanel({call,onAccept,onDecline,onEnd,onDismiss,onToggleMic,onToggleCamera}){
 const dialog=useRef(null),local=useRef(null),remote=useRef(null);
 const open=!!call;
 useEffect(()=>{
  const el=dialog.current;if(!el)return;
  if(open&&!el.open)el.showModal();
  if(!open&&el.open)el.close();
 },[open]);
 useEffect(()=>{if(local.current)local.current.srcObject=call?.localStream||null;},[call?.localStream,call?.phase,call?.cameraEnabled]);
 useEffect(()=>{if(remote.current)remote.current.srcObject=call?.remoteStream||null;},[call?.remoteStream,call?.phase]);
 if(!call)return null;
 const active=call.phase==="active",incoming=call.phase==="incoming",video=call.kind==="VIDEO";
 const finished=["ended","declined","failed"].includes(call.phase);
 const seconds=Number.isFinite(call.secondsRemaining)?Math.max(0,call.secondsRemaining):null;
 return <dialog ref={dialog} className="nk-call-dialog" aria-labelledby="nk-call-person" onCancel={e=>{e.preventDefault();if(finished)onDismiss?.();}}>
  <div className="nk-call-shell">
   <header><span>NKATA</span><small>{video?"Videochamada":"Chamada de áudio"}</small></header>
   <div className="nk-call-stage">
    {active&&video&&call.remoteStream?<video ref={remote} className="nk-call-remote" autoPlay playsInline aria-label="Vídeo recebido"/>:<div className="nk-call-person-art">{call.photoUrl?<img src={call.photoUrl} alt=""/>:<UserRound size={56} strokeWidth={1.3}/>}</div>}
    {active&&(!video||!call.remoteStream)&&<audio ref={remote} autoPlay/>}
    {active&&video&&call.localStream&&call.cameraEnabled&&<video ref={local} className="nk-call-local" autoPlay playsInline muted aria-label="A sua câmara"/>}
    <div className="nk-call-person-text"><h2 id="nk-call-person">{call.name||"Membro NKATA"}</h2><p role="status">{labels[call.phase]||"A aguardar..."}</p>{active&&Number.isFinite(call.elapsedSeconds)&&<time>{clock(call.elapsedSeconds)}</time>}</div>
   </div>
   {call.payer&&Number.isFinite(call.balance)&&Number.isFinite(call.rate)&&!finished&&<div className="nk-call-wallet"><span>{call.rate} créditos/min</span><strong>{call.balance} créditos</strong></div>}
   {active&&call.payer&&seconds!==null&&seconds<=60&&<p className="nk-call-warning" role="status">Créditos a terminar · {clock(seconds)} restantes</p>}
   <div className="nk-call-controls">
    {incoming?<><Action icon={PhoneOff} label="Recusar" variant="danger" onClick={onDecline} disabled={call.busy}/><Action icon={Phone} label="Aceitar" variant="accept" onClick={onAccept} disabled={call.busy}/></>:
    finished?<button type="button" className="nk-call-dismiss" onClick={onDismiss}>Fechar</button>:
    <>{active&&<Action icon={call.micEnabled?Mic:MicOff} label={call.micEnabled?"Microfone":"Sem microfone"} pressed={!call.micEnabled} onClick={onToggleMic}/>}
    {active&&video&&<Action icon={call.cameraEnabled?Video:VideoOff} label={call.cameraEnabled?"Câmara":"Sem câmara"} pressed={!call.cameraEnabled} onClick={onToggleCamera}/>}
    <Action icon={PhoneOff} label={active?"Terminar":"Cancelar"} variant="danger" onClick={onEnd} disabled={call.busy}/></>}
   </div>
  </div>
 </dialog>;
}
