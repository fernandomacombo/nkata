import {useEffect,useRef,useState} from "react";
import {Mic,Square,Trash2,Send} from "lucide-react";
import {request} from "../../services/api.js";

export default function VoiceRecorder({conversationId,offer,onSent}){
 const [state,setState]=useState("idle"),[seconds,setSeconds]=useState(0),[draft,setDraft]=useState(null),[error,setError]=useState("");
 const session=useRef(null),alive=useRef(true),preview=useRef(null),busy=useRef(false);
 function release(s){if(!s)return;clearInterval(s.timer);s.stream?.getTracks().forEach(t=>t.stop());}
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;const s=session.current;if(s){s.cancelled=true;if(s.recorder?.state==="recording")s.recorder.stop();release(s);}if(preview.current)URL.revokeObjectURL(preview.current);};},[]);
 async function start(){
  if(busy.current||state!=="idle"||offer.balance<offer.cost)return;
  busy.current=true;setError("");setState("starting");
  let s={cancelled:false,chunks:[]};session.current=s;
  try{
   if(!navigator.mediaDevices?.getUserMedia||typeof MediaRecorder==="undefined")throw Error("O navegador não suporta gravação de voz.");
   s.stream=await navigator.mediaDevices.getUserMedia({audio:true});
   if(!alive.current||s.cancelled){release(s);return;}
   const type=["audio/webm;codecs=opus","audio/mp4","audio/webm","audio/ogg"].find(t=>MediaRecorder.isTypeSupported?.(t));
   s.recorder=type?new MediaRecorder(s.stream,{mimeType:type}):new MediaRecorder(s.stream);
   s.recorder.ondataavailable=e=>{if(e.data.size)s.chunks.push(e.data);};
   s.recorder.onerror=()=>{s.cancelled=true;release(s);if(alive.current){setError("Falha na gravação.");setState("idle");}};
   s.recorder.onstop=()=>{release(s);if(!alive.current||s.cancelled)return;const mime=s.recorder.mimeType||type||"audio/webm";const blob=new Blob(s.chunks,{type:mime});if(!blob.size){setError("Gravação vazia.");setState("idle");return;}const url=URL.createObjectURL(blob);preview.current=url;setDraft({blob,url,seconds:Math.max(1,Math.min(180,Math.round((Date.now()-s.start)/1000))),key:crypto.randomUUID()});setState("ready");};
   s.start=Date.now();s.recorder.start();setSeconds(0);setState("recording");
   s.timer=setInterval(()=>{const elapsed=Math.floor((Date.now()-s.start)/1000);setSeconds(Math.min(180,elapsed));if(elapsed>=180&&s.recorder.state==="recording")s.recorder.stop();},250);
  }catch(e){release(s);if(alive.current){setError(e.message||"Não foi possível aceder ao microfone.");setState("idle");}}
  finally{busy.current=false;}
 }
 function clear(){if(preview.current)URL.revokeObjectURL(preview.current);preview.current=null;setDraft(null);setState("idle");setSeconds(0);}
 function cancel(){const s=session.current;if(s){s.cancelled=true;if(s.recorder?.state==="recording")s.recorder.stop();release(s);}clear();}
 async function send(){
  if(!draft||busy.current)return;
  if(!window.confirm("Enviar nota de voz por 2 créditos?"))return;
  busy.current=true;setState("sending");setError("");
  try{const form=new FormData();const type=draft.blob.type;const ext=type.includes("mp4")?"m4a":type.includes("ogg")?"ogg":"webm";form.append("audio",draft.blob,"nota."+ext);form.append("duracao_segundos",String(draft.seconds));form.append("key",draft.key);form.append("expected_cost",String(offer.cost));await request("/api/chats/"+conversationId+"/audio/",{method:"POST",body:form});if(alive.current){clear();onSent();}}
  catch(e){if(alive.current){setError(e.message);setState("ready");}}
  finally{busy.current=false;}
 }
 return <div className="nk-native-recorder">
 {state==="idle"&&<button type="button" disabled={offer.balance<offer.cost} onClick={start}><Mic size={17}/>Nota de voz · {offer.cost} créditos</button>}
 {state==="starting"&&<button type="button" onClick={cancel}>Cancelar acesso ao microfone</button>}
 {state==="recording"&&<><span role="status">A gravar · {seconds}s / 180s</span><button type="button" onClick={cancel} aria-label="Cancelar gravação"><Trash2 size={17}/></button><button type="button" onClick={()=>session.current?.recorder?.state==="recording"&&session.current.recorder.stop()} aria-label="Terminar gravação"><Square size={17}/></button></>}
 {draft&&<><audio controls src={draft.url} aria-label="Pré-visualizar nota de voz"/><button type="button" disabled={state==="sending"} onClick={clear} aria-label="Apagar gravação"><Trash2 size={17}/></button><button type="button" disabled={state==="sending"} onClick={send}><Send size={17}/>{state==="sending"?"A enviar…":"Enviar · 2 créditos"}</button></>}
 {error&&<small role="alert">{error}</small>}
 </div>;
}
