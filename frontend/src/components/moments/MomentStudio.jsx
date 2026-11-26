import { Camera, Clock3, Globe, Heart, ImagePlus, LockKeyhole, Moon, Sparkles, Sun, X } from "lucide-react";

const presets = [
  {id:"sun",icon:Sun,pt:"Boas energias",en:"Good energy",theme:"sand",font:"sans",caption:"BOAS_ENERGIAS"},
  {id:"heart",icon:Heart,pt:"Romântico",en:"Romantic",theme:"wine",font:"serif",caption:"CONHECER_COM_CALMA"},
  {id:"globe",icon:Globe,pt:"O meu mundo",en:"My world",theme:"forest",font:"italic",caption:"APROVEITAR_MOMENTO"},
  {id:"moon",icon:Moon,pt:"Em paz",en:"At peace",theme:"midnight",font:"serif",caption:"FIM_DE_DIA"},
];
const palettes = [["wine","Vinho","Wine"],["forest","Floresta","Forest"],["midnight","Noite","Night"],["sand","Areia","Sand"]];
const fonts = [["serif","Clássica","Classic"],["sans","Simples","Simple"],["italic","Itálica","Italic"]];

export default function MomentStudio({english,captionOptions,captionLabel,caption,theme,font,visibility,visibilityOptions,mediaEnabled,mediaPreview,isVideo,publishing,onCaption,onTheme,onFont,onVisibility,onPreset,onPickMedia,onRemoveMedia}) {
  const phrase = caption === "SEM_LEGENDA" ? "" : captionLabel(captionOptions.find(option=>option.value===caption));
  return <div className="nk-janelas-studio">
    <header className="nk-janelas-studio__intro"><Sparkles size={21}/><div><h3>{english?"Make it yours":"Dá-lhe a tua personalidade"}</h3><p>{english?"A little of your world, for 24 hours.":"Um pouco do teu mundo, durante 24 horas."}</p></div></header>
    <div className="nk-janelas-studio__preview" aria-label={english?"Moment preview":"Pré-visualização do Momento"}>
      <div className={`nk-janelas-studio__canvas nk-moment-theme-${theme} nk-moment-font-${font}`}>
        {mediaPreview && (isVideo?<video src={mediaPreview} controls playsInline preload="metadata"/>:<img src={mediaPreview} alt={english?"Selected photo":"Fotografia seleccionada"}/>)}
        <span className="nk-janelas-studio__corner"><Clock3 size={12}/>24h</span>
        <span className="nk-janelas-studio__frame" aria-hidden="true"/>
        {(!mediaPreview || phrase) && <p className={mediaPreview?"has-media":""}>{phrase || (english?"Choose a phrase or add media":"Escolhe uma frase ou adiciona uma imagem")}</p>}
        {mediaPreview && <button type="button" className="nk-janelas-studio__remove" disabled={publishing} onClick={onRemoveMedia} aria-label={english?"Remove file":"Remover ficheiro"}><X size={19}/></button>}
      </div>
      <span className="nk-janelas-studio__preview-label">{english?"Preview · before publishing":"Pré-visualização · antes de publicar"}</span>
    </div>
    <fieldset disabled={publishing}><legend>{english?"Inspiration":"Inspiração"}</legend><div className="nk-janelas-studio__presets">{presets.filter(p=>captionOptions.some(o=>o.value===p.caption)).map(p=>{
      const Icon=p.icon,selected=theme===p.theme&&font===p.font&&caption===p.caption;
      return <button key={p.id} type="button" aria-pressed={selected} onClick={()=>onPreset(p)} className={`nk-janelas-studio__preset nk-moment-theme-${p.theme}`}><Icon size={23}/><span>{english?p.en:p.pt}</span></button>;
    })}</div></fieldset>
    <fieldset disabled={publishing}><legend>{english?"Colour":"Cor do fundo"}</legend><div className="nk-janelas-studio__palette">{palettes.map(([value,pt,en])=><button key={value} type="button" aria-pressed={theme===value} onClick={()=>onTheme(value)}><span className={`nk-moment-swatch nk-moment-theme-${value}`} aria-hidden="true"/><small>{english?en:pt}</small></button>)}</div></fieldset>
    <fieldset disabled={publishing}><legend>{english?"Lettering":"Estilo da letra"}</legend><div className="nk-janelas-studio__fonts">{fonts.map(([value,pt,en])=><button key={value} type="button" aria-pressed={font===value} onClick={()=>onFont(value)} className={`nk-moment-font-${value}`}><b>Aa</b><small>{english?en:pt}</small></button>)}</div></fieldset>
    <label className="nk-janelas-studio__label"><span>{english?"Phrase":"Frase"}</span><select disabled={publishing} value={caption} onChange={e=>onCaption(e.target.value)} aria-label={english?"Moment caption":"Frase do Momento"}>{captionOptions.map(option=><option key={option.value} value={option.value}>{captionLabel(option)}</option>)}</select></label>
    <button type="button" className="nk-janelas-studio__pick" disabled={publishing || !mediaEnabled} onClick={onPickMedia}>{mediaEnabled?<ImagePlus size={22}/>:<LockKeyhole size={22}/>}<span><strong>{english?(mediaPreview?"Change photo or video":"Add photo or video"):(mediaPreview?"Trocar foto ou vídeo":"Adicionar foto ou vídeo")}</strong><small>{mediaEnabled?(english?"Choose from your device":"Escolhe no teu dispositivo"):(english?"Media not included in your current plan":"O teu plano actual não inclui fotografias e vídeos")}</small></span></button>
    <fieldset disabled={publishing}><legend>{english?"Who can see?":"Quem pode ver?"}</legend><div className="nk-janelas-studio__audience">{visibilityOptions.map(option=><button key={option.value} type="button" aria-pressed={visibility===option.value} onClick={()=>onVisibility(option.value)}>{option.value==="MATCHES"?<LockKeyhole size={16}/>:<Globe size={16}/>}<span>{english?(option.value==="MATCHES"?"Matches only":"All members"):option.label}</span></button>)}</div></fieldset>
  </div>;
}
