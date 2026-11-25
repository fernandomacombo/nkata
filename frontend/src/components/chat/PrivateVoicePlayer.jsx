import {useEffect,useRef,useState} from "react";
import {Play,Pause} from "lucide-react";

const clock=value=>{const n=Math.max(0,Math.floor(Number(value)||0));return Math.floor(n/60)+":"+String(n%60).padStart(2,"0");};
export default function PrivateVoicePlayer({src,duration=0,label="Nota de voz"}){
 const ref=useRef(null);
 const [playing,setPlaying]=useState(false),[elapsed,setElapsed]=useState(0),[length,setLength]=useState(duration),[error,setError]=useState(false);
 useEffect(()=>{setPlaying(false);setElapsed(0);setLength(duration);setError(false);},[src,duration]);
 async function toggle(){
  const audio=ref.current;if(!audio)return;
  if(!audio.paused){audio.pause();return;}
  try{setError(false);await audio.play();}catch{setError(true);}
 }
 const progress=length?Math.min(100,elapsed/length*100):0;
 return <div className="nk-private-voice" role="group" aria-label={label} onContextMenu={e=>e.preventDefault()}>
   <audio ref={ref} src={src} preload="none" controlsList="nodownload noremoteplayback" disableRemotePlayback playsInline
     onPlay={()=>{document.querySelectorAll("audio").forEach(a=>{if(a!==ref.current)a.pause();});setPlaying(true);}}
     onPause={()=>setPlaying(false)} onEnded={()=>{setPlaying(false);setElapsed(0);}}
     onLoadedMetadata={e=>{if(Number.isFinite(e.currentTarget.duration))setLength(e.currentTarget.duration);}}
     onTimeUpdate={e=>setElapsed(e.currentTarget.currentTime)} onError={()=>{setPlaying(false);setError(true);}}/>
   <button className="nk-private-voice__play" type="button" onClick={toggle} aria-label={playing?"Pausar nota de voz":"Reproduzir nota de voz"}>{playing?<Pause size={17} fill="currentColor"/>:<Play size={17} fill="currentColor"/>}</button>
   <div className="nk-private-voice__body">
    <input className="nk-private-voice__progress" type="range" min="0" max="100" step="1" value={progress} aria-label="Progresso do áudio" aria-valuetext={clock(elapsed)+" de "+clock(length)} style={{"--voice-progress":progress+"%"}} onChange={e=>{const a=ref.current;if(a&&Number.isFinite(a.duration)){a.currentTime=Number(e.target.value)*a.duration/100;setElapsed(a.currentTime);}}}/>
    <small>{error?"Áudio indisponível":clock(playing?elapsed:length)}</small>
   </div>
 </div>;
}
