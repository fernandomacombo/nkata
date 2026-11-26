import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { chromium, webkit } from "playwright";
import { createServer } from "vite";

const main = await fs.readFile("src/main.jsx", "utf8");
const css = [...main.matchAll(/^import "(\.\/[^"]+\.css)";$/gm)].map(m => 'import "/src/' + m[1].slice(2) + '";').join("\n");
const html = "__chats_regression.html";
const jsx = "__chats_regression.jsx";
await fs.writeFile(html, '<!doctype html><meta name="viewport" content="width=device-width, initial-scale=1"><div id="root"></div><script type="module" src="/' + jsx + '"></script>');
await fs.writeFile(jsx, `
import React, {useState} from "react";
import {createRoot} from "react-dom/client";
import ChatsPage from "/src/pages/ChatsPage.jsx";
import MemberHomePage from "/src/pages/MemberHomePage.jsx";
import MomentWindows from "/src/components/moments/MomentWindows.jsx";
import AutoplayMomentViewer from "/src/components/moments/AutoplayMomentViewer.jsx";
import MomentsPage from "/src/pages/MomentsPage.jsx";
import useSeenMoments from "/src/hooks/useSeenMoments.js";
import DiscoverPage from "/src/pages/DiscoverPage.jsx";
import ProfileDetailPage from "/src/pages/ProfileDetailPage.jsx";
import HeartLoader from "/src/components/HeartLoader.jsx";
import BottomNavigation from "/src/components/layout/BottomNavigation.jsx";
import { PresenceProvider } from "/src/components/profiles/Presence.jsx";
import useProfileLibrary from "/src/hooks/useProfileLibrary.js";
${css}
function LibraryHarness(){
 const {savedProfiles} = useProfileLibrary();
 function session(id){window.dispatchEvent(new CustomEvent("nkata:session-changed",{detail:id?{authenticated:true,user:{id}}:{authenticated:false}}));}
 return <main><h1>Biblioteca</h1><button onClick={()=>session(1)}>Conta A</button><button onClick={()=>session(2)}>Conta B</button><button onClick={()=>session(null)}>Sair</button><output aria-label="Guardados">{savedProfiles.map(p=>p.nome_publico).join(",")}</output></main>;
}
function DiscoveryHarness(){
 const [loading,setLoading]=useState(true),[saved,setSaved]=useState([]),[opened,setOpened]=useState("");
 const profiles=Array.from({length:7},(_,i)=>({id:i+11,nome_publico:"Pessoa "+(i+1),idade:25+i,cidade:i%2?"Beira":"Maputo",verificado:i!==1,objetivo_display:"Relacionamento sério",foto_url:"/discovery-test.svg",criado_em:new Date(Date.now()-i*86400000).toISOString()})).reverse();
 return <PresenceProvider member={true} identity="discovery" page={loading?"loading":"discover"}><div className="nk-app"><button onClick={()=>setLoading(false)}>Carregar descoberta</button><output aria-label="Perfil aberto">{opened}</output><DiscoverPage authenticated profiles={profiles} loading={loading} onReload={()=>{}} onOpenProfile={p=>setOpened(p.nome_publico)} isSaved={p=>saved.includes(p.id)} onToggleSaved={p=>setSaved(old=>old.includes(p.id)?old.filter(id=>id!==p.id):[...old,p.id])}/></div></PresenceProvider>;
}
function WindowsHarness(){
 const [seen,setSeen]=useState(new Set()),[opened,setOpened]=useState(""),[composer,setComposer]=useState(false);
 const groups=Array.from({length:4},(_,i)=>({profile:{id:i+1,nome_publico:"Janela "+(i+1)},moments:[{id:i+20,moderation_status:i===3?"PENDENTE":"APROVADO",expires_at:new Date(Date.now()+(i===2?-1000:3600000)).toISOString(),media_type:"TEXTO",text:"Frase "+i}]}));
 return <main><output aria-label="Janela aberta">{opened}</output><MomentWindows groups={groups} english={false} seen={seen} composerOpen={composer} onCreate={()=>setComposer(x=>!x)} onOpen={(group,id)=>{setSeen(s=>new Set([...s,id]));setOpened(group.profile.nome_publico)}}/></main>;
}
function SeenMemoryHarness(){
 const [user,setUser]=useState(101);
 const {seen,markSeen}=useSeenMoments(user);
 return <main><button onClick={()=>setUser(101)}>Membro A</button><button onClick={()=>setUser(102)}>Membro B</button><button onClick={()=>markSeen({id:70,moderation_status:"APROVADO",expires_at:new Date(Date.now()+3600000).toISOString()})}>Ver 70</button><output aria-label="Vistos">{Array.from(seen).join(",")}</output></main>;
}
function WindowViewerHarness(){
 const [opened,setOpened]=useState(true),[profile,setProfile]=useState("");
 const [groups]=useState(()=>Array.from({length:2},(_,i)=>{const profile={id:i+1,nome_publico:"Pessoa "+(i+1)};return {profile,moments:[{id:50+i,profile,moderation_status:"APROVADO",expires_at:new Date(Date.now()+3600000).toISOString(),media_type:"TEXTO",text:"Frase "+i,visibility:"TODOS",visibility_label:"Todos os membros"}]};}));
 return <main><output aria-label="Perfil do momento">{profile}</output>{opened&&<AutoplayMomentViewer groups={groups} windowsMode onClose={()=>setOpened(false)} onOpenProfile={p=>{setProfile(p.nome_publico);setOpened(false)}}/>}</main>;
}
function LoaderHarness(){
 const [context,setContext]=useState("profile");
 const [state,setState]=useState("loading");
 return <div>
   <button onClick={()=>setState("loaded")}>Simular perfil carregado</button>
   <button onClick={()=>{setContext("chats");setState("loading");}}>Simular carregamento chats</button>
   <button onClick={()=>{setContext("discover");setState("loading");}}>Simular carregamento explorar</button>
   <button onClick={()=>setState("error")}>Simular falha</button>
   {context!=="profile" && state==="loading" ? <HeartLoader page={context}/> : <ProfileDetailPage loading={state==="loading"} profile={state==="loaded"?{id:"demo-loader",nome_publico:"Perfil de teste",idade:29}:null} error={state==="error"?"Falha de teste":""} onBack={()=>{}}/>}
 </div>;
}
function Harness(){
 const [page,setPage] = useState(new URLSearchParams(window.location.search).has("profile") ? "profile-test" : new URLSearchParams(window.location.search).has("feed") ? "feed-test" : "chats"), [id,setId] = useState(null), [accepted,setAccepted] = useState(false);
 return <div className="nk-app"><header className="nk-header"><span className="nk-header__member">Member</span></header>
 {page === "profile-test" ? <ProfileDetailPage authenticated profile={{id:2,nome_publico:"Ana Maria de Sousa Fernandes",verificado:!new URLSearchParams(window.location.search).has("unverified"),idade:27,cidade:"Maputo",objetivo_display:"Relacionamento sério",sobre_si:["Prefiro conhecer pessoalmente.","Gosto de ler e pesquisar.","Valorizo o diálogo.","Esta última frase deve ficar visível ao expandir."].join(String.fromCharCode(10)),o_que_valoriza:"Respeito e carinho",o_que_nao_aceita:"Mentiras",preferencias:{ages:[25,35],height:165},foto_url:"/avatar-portrait-test.svg",gallery:[{id:"registo-1",mediaType:"IMAGEM",mediaUrl:"/avatar-extra-test.svg"},{id:22,mediaType:"IMAGEM",mediaUrl:"/avatar-post-test.svg"}],moments:[{id:7,mediaType:"TEXTO",text:"Um dia tranquilo por aqui.",expiresAt:new Date(Date.now()+3600000).toISOString()},{id:8,mediaType:"TEXTO",text:"Momento expirado",expiresAt:new Date(Date.now()-1000).toISOString()}]}} onAskChat={async()=>setPage("other")} onBack={()=>setPage("other")} onToggleInterest={()=>{}} onToggleSaved={()=>{}}/> : page === "feed-test" ? <MemberHomePage onNavigate={setPage} onOpenProfile={()=>setPage("profile")}/> : page === "chats" ? <ChatsPage conversationId={id} onSelect={setId} onBack={()=>setId(null)} onDiscover={()=>setPage("discover")} onOpenProfile={()=>setPage("profile")} safetyAccepted={accepted} onAcceptSafety={async()=>setAccepted(true)} /> : <main><h1>Other page</h1></main>}
 <BottomNavigation activePage={page} onNavigate={p=>{setPage(p);setId(null)}}/>
 </div>;
}
document.body.classList.toggle("nk-app-mode", window.matchMedia("(max-width: 820px)").matches);
createRoot(document.getElementById("root")).render(new URLSearchParams(window.location.search).has("seenmemory") ? <SeenMemoryHarness/> : new URLSearchParams(window.location.search).has("momentstudio") ? <MomentsPage/> : new URLSearchParams(window.location.search).has("windowviewer") ? <WindowViewerHarness/> : new URLSearchParams(window.location.search).has("windows") ? <WindowsHarness/> : new URLSearchParams(window.location.search).has("loader") ? <LoaderHarness/> : new URLSearchParams(window.location.search).has("library") ? <LibraryHarness/> : new URLSearchParams(window.location.search).has("discovery") ? <DiscoveryHarness/> : <PresenceProvider member={true} identity="test" page="chats"><Harness/></PresenceProvider>);
`);
process.env.VITE_API_BASE_URL = "http://127.0.0.1:5178";
const server = await createServer({server:{host:"127.0.0.1",port:5178,strictPort:true}});
try {
 await server.listen();
 for (const engine of [chromium, webkit]) {
  const browser = await engine.launch({headless:true});
  try {
   const loader=await browser.newPage({viewport:{width:375,height:812},reducedMotion:"reduce"});
   const loaderErrors=[];
   loader.on("pageerror",error=>loaderErrors.push(error.message));
   await loader.goto("http://127.0.0.1:5178/"+html+"?loader=1");
   const status=loader.locator(".nk-heart-loader[role='status']");
   await status.getByText("A preparar este perfil para si",{exact:true}).waitFor();
   assert.equal(await status.locator(".nk-heart-loader__particles svg").count(),7);
   assert.equal(await status.locator(".nk-heart-loader__heart").evaluate(el=>getComputedStyle(el).animationName),"none","Reduced-motion setting must disable animation");
   assert.ok(await loader.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+2),"Loader must fit mobile viewport");
   for(const viewport of [{width:375,height:812},{width:1366,height:820}]){
     await loader.setViewportSize(viewport);
     await loader.waitForFunction(({width,height}) => {
       const el=document.querySelector(".nk-heart-loader--fullscreen");
       if(!el || innerWidth!==width || innerHeight!==height) return false;
       const r=el.getBoundingClientRect();
       return Math.abs(r.x)<=1 && Math.abs(r.y)<=1 && Math.abs(r.width-width)<=1 && Math.abs(r.height-height)<=1;
     },viewport,{timeout:5000});
     const geometry=await status.evaluate(el=>{
       const rect=el.getBoundingClientRect(),brand=el.querySelector(".nk-heart-loader__brand").getBoundingClientRect(),bar=el.querySelector(".nk-heart-loader__progress").getBoundingClientRect(),heart=el.querySelector(".nk-heart-loader__heart").getBoundingClientRect();
       return {x:rect.x,y:rect.y,width:rect.width,height:rect.height,groupCenter:(brand.top+bar.bottom)/2,heartCenter:(heart.left+heart.right)/2,viewportWidth:innerWidth,viewportHeight:innerHeight,topmost:el.contains(document.elementFromPoint(1,1)),bodyOverflow:getComputedStyle(document.body).overflow};
     });
     assert.ok(Math.abs(geometry.x)<=1&&Math.abs(geometry.y)<=1&&Math.abs(geometry.width-geometry.viewportWidth)<=1&&Math.abs(geometry.height-geometry.viewportHeight)<=1,"Page loader must cover the entire viewport: "+JSON.stringify(geometry));
     assert.ok(Math.abs(geometry.groupCenter-geometry.viewportHeight/2)<=3&&Math.abs(geometry.heartCenter-geometry.viewportWidth/2)<=3,"Brand, animation and messages must form a centered group: "+JSON.stringify(geometry));
     assert.equal(geometry.topmost,true,"Header and other content must be covered");
     assert.equal(geometry.bodyOverflow,"hidden","Prevent scrolling the underlying page");
   }
   await loader.getByRole("button",{name:"Simular perfil carregado"}).evaluate(button=>button.click());
   await status.waitFor({state:"detached"});
   assert.notEqual(await loader.evaluate(()=>getComputedStyle(document.body).overflow),"hidden","Restore normal scrolling after loading");
   await loader.getByRole("heading",{name:/Perfil de teste/}).waitFor();
   await loader.reload();
   await status.waitFor();
   await loader.getByRole("button",{name:"Simular falha"}).evaluate(button=>button.click());
   await status.waitFor({state:"detached"});
   await loader.getByRole("heading",{name:"Perfil não disponível"}).waitFor();
   assert.equal(loaderErrors.length,0,loaderErrors.join("\n"));
   await loader.getByRole("button",{name:"Simular carregamento chats"}).click();
   await status.getByText("A preparar as suas conversas",{exact:true}).waitFor();
   await loader.getByRole("button",{name:"Simular carregamento explorar"}).evaluate(button=>button.click());
   await status.getByText("A descobrir novas pessoas",{exact:true}).waitFor();
   assert.equal(await status.locator(".nk-heart-loader__particles svg").count(),7);
   assert.equal(loaderErrors.length,0,loaderErrors.join("\n"));
   await loader.close();
   const windows = await browser.newPage({viewport:{width:375,height:812},reducedMotion:"reduce"});
   const windowErrors=[];windows.on("pageerror",e=>windowErrors.push(e.message));
   await windows.goto("http://127.0.0.1:5178/"+html+"?windows=1");
   await windows.getByRole("heading",{name:"Janelas de hoje"}).waitFor();
   assert.equal(await windows.locator(".nk-janelas__window").count(),2,"Only approved, nonexpired Moments");
   await windows.getByRole("button",{name:"Abrir momento de Janela 1"}).click();
   await windows.getByRole("button",{name:"Por ver",exact:true}).click();
   assert.equal(await windows.locator(".nk-janelas__window").count(),1);
   await windows.getByRole("button",{name:/Surpreende-me/}).click();
   assert.equal(await windows.getByLabel("Janela aberta").textContent(),"Janela 2");
   assert.equal(await windows.getByRole("button",{name:/Surpreende-me/}).isDisabled(),true);
   await windows.getByRole("button",{name:"Já vistos",exact:true}).click();
   assert.equal(await windows.locator(".nk-janelas__window").count(),2);
   await windows.getByRole("button",{name:"Novo Momento"}).click();
   assert.equal(await windows.getByRole("button",{name:"Novo Momento"}).getAttribute("aria-expanded"),"true");
   for(const width of [375,1366]){await windows.setViewportSize({width,height:812});assert.ok(await windows.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),"Windows must fit viewport");}
   assert.equal(windowErrors.length,0,windowErrors.join("; "));
   await windows.close();
   const wviewer=await browser.newPage({viewport:{width:375,height:812},reducedMotion:"reduce"});
   const viewerErrors=[];wviewer.on("pageerror",e=>viewerErrors.push(e.message));
   await wviewer.route("**/api/momentos/*/reacoes/",route=>route.fulfill({json:{reactions:{enabled:true,options:[],counts:{}}}}));
   await wviewer.goto("http://127.0.0.1:5178/"+html+"?windowviewer=1");
   await wviewer.getByRole("dialog",{name:"Momento de Pessoa 1"}).waitFor();
   assert.equal(await wviewer.locator(".nk-janelas__reveal").evaluate(el=>getComputedStyle(el).display),"none");
   const cta=wviewer.getByRole("button",{name:"Conhecer Pessoa 1"});
   assert.ok(await cta.evaluate(el=>{const r=el.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight&&r.height>=40;}),"CTA must fit viewport");
   await wviewer.keyboard.press("ArrowRight");
   await wviewer.getByRole("dialog",{name:"Momento de Pessoa 2"}).waitFor();
   await wviewer.getByRole("button",{name:"Conhecer Pessoa 2"}).click();
   assert.equal(await wviewer.getByLabel("Perfil do momento").textContent(),"Pessoa 2");
   assert.equal(viewerErrors.length,0,viewerErrors.join("; "));
   await wviewer.close();
   const denied=await browser.newPage({viewport:{width:375,height:812},reducedMotion:"reduce"});
   await denied.route("**/api/momentos/*/reacoes/",route=>route.fulfill({status:403,json:{detail:"Acesso revogado"}}));
   const deniedResponse=denied.waitForResponse(response=>response.url().includes("/api/momentos/50/reacoes/")&&response.status()===403);
   await denied.goto("http://127.0.0.1:5178/"+html+"?windowviewer=1");
   await deniedResponse;
   await denied.getByLabel("Perfil do momento").waitFor({state:"attached"});
   await denied.getByRole("dialog",{name:/Momento de Pessoa/}).waitFor({state:"detached"});
   await denied.close();
   const studio=await browser.newPage({viewport:{width:375,height:812},reducedMotion:"reduce"});
   const studioErrors=[];studio.on("pageerror",e=>studioErrors.push(e.message));
   let submitted=null;
   await studio.route("**/api/momentos/",async route=>{
     if(route.request().method()==="POST"){submitted=route.request().postData();return route.fulfill({json:{moment:{id:90,moderation_status:"PENDENTE",media_type:"TEXTO"},message:"Enviado"}});}
     return route.fulfill({json:{results:[],review_items:[],capabilities:{media_enabled:false}}});
   });
   await studio.goto("http://127.0.0.1:5178/"+html+"?momentstudio=1");
   await studio.getByRole("button",{name:"Novo Momento",exact:true}).click();
   await studio.getByRole("button",{name:"Romântico",exact:true}).click();
   assert.equal(await studio.getByLabel("Frase do Momento").inputValue(),"CONHECER_COM_CALMA");
   await studio.getByRole("button",{name:"Noite",exact:true}).click();
   await studio.getByRole("button",{name:/Itálica/}).click();
   await studio.getByRole("button",{name:"Apenas matches",exact:true}).click();
   assert.equal(await studio.getByRole("button",{name:/Adicionar foto ou vídeo/}).isDisabled(),true);
   assert.ok(await studio.locator(".nk-janelas-studio__canvas").evaluate(el=>el.classList.contains("nk-moment-theme-midnight")&&el.classList.contains("nk-moment-font-italic")));
   assert.ok(await studio.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
   await studio.getByRole("button",{name:"Publicar",exact:true}).click();
   await studio.getByText("Enviado",{exact:true}).waitFor();
   assert.match(submitted,/CONHECER_COM_CALMA/);assert.match(submitted,/MATCHES/);assert.match(submitted,/midnight/);assert.match(submitted,/italic/);
   assert.equal(studioErrors.length,0,studioErrors.join("; "));
   await studio.close();
   const memory=await browser.newPage({viewport:{width:375,height:812}});
   await memory.goto("http://127.0.0.1:5178/"+html+"?seenmemory=1");
   await memory.getByRole("button",{name:"Ver 70"}).click();
   await memory.waitForFunction(()=>document.querySelector('[aria-label="Vistos"]').textContent==="70");
   await memory.reload();
   await memory.waitForFunction(()=>document.querySelector('[aria-label="Vistos"]')?.textContent==="70");
   await memory.getByRole("button",{name:"Membro B"}).click();
   await memory.waitForFunction(()=>document.querySelector('[aria-label="Vistos"]').textContent==="");
   await memory.getByRole("button",{name:"Membro A"}).click();
   await memory.waitForFunction(()=>document.querySelector('[aria-label="Vistos"]').textContent==="70");
   await memory.close();
   for (const width of [375,1366]) {
     const discovery=await browser.newPage({viewport:{width,height:820},reducedMotion:"reduce"});
     const discoveryErrors=[];
     discovery.on("pageerror",error=>discoveryErrors.push(error.message));
     await discovery.route("**/discovery-test.svg",route=>route.fulfill({contentType:"image/svg+xml",body:'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="130"><rect width="100" height="130" fill="#987"/></svg>'}));
     await discovery.route("**/api/presenca/",route=>route.fulfill({json:{perfis:{11:0,12:120,13:120,14:120,15:120,16:0,17:120}}}));
     await discovery.goto("http://127.0.0.1:5178/"+html+"?discovery=1");
     await discovery.locator(".nk-heart-loader").getByText("A descobrir novas pessoas",{exact:true}).waitFor();
     await discovery.getByRole("button",{name:"Carregar descoberta"}).evaluate(button=>button.click());
     const recent=discovery.locator(".nk-flow__recent");
     await recent.getByRole("heading",{name:"Novos rostos"}).waitFor();
     await recent.getByRole("heading",{name:"Pessoa 1, 25"}).waitFor();
     assert.equal(await recent.locator(".nk-flow__slide").count(),5);
     assert.equal(await discovery.locator(".nk-flow__mini").count(),2);
     const geometry=await recent.locator(".nk-flow__stage").evaluate(el=>{
       const stage=el.getBoundingClientRect(),center=el.querySelector('[data-position="0"]').getBoundingClientRect(),left=el.querySelector('[data-position="-1"]').getBoundingClientRect(),right=el.querySelector('[data-position="1"]').getBoundingClientRect();
       return {center:Math.abs((stage.left+stage.width/2)-(center.left+center.width/2)),left:left.width,right:right.width,main:center.width};
     });
     assert.ok(geometry.center<2 && Math.abs(geometry.left-geometry.right)<2 && geometry.main>geometry.left,"Featured card must be centered and larger: "+JSON.stringify(geometry));
     await recent.getByRole("button",{name:"Seguinte"}).click();
     await recent.getByRole("heading",{name:"Pessoa 2, 26"}).waitFor();
     assert.equal(await recent.locator(".nk-flow__identity .nk-flow__verified").count(),0);
     await recent.getByRole("button",{name:"Conhecer Pessoa"}).click();
     await discovery.getByLabel("Perfil aberto").getByText("Pessoa 2").waitFor();
     await recent.getByRole("button",{name:"Guardar perfil"}).click();
     await discovery.getByRole("button",{name:"Guardados",exact:true}).click();
     assert.equal(await discovery.locator(".nk-flow__mini").count(),1);
     await discovery.getByRole("button",{name:"Todos",exact:true}).click();
     await discovery.getByRole("button",{name:"Pesquisar perfis"}).click();
     await discovery.getByRole("searchbox").fill("Pessoa 7");
     assert.equal(await discovery.locator(".nk-flow__mini").count(),1);
     assert.ok(await discovery.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),"Discovery must fit viewport");
     assert.equal(discoveryErrors.length,0,discoveryErrors.join("\\n"));
     await discovery.close();
   }
   const library=await browser.newPage();
   let privateRequests=0, releaseFirst;
   await library.route("**/api/minha-conta/guardados/",async route=>{
     const number=++privateRequests;
     if(number===1) await new Promise(resolve=>{releaseFirst=resolve;});
     await route.fulfill({json:{results:[{id:number,nome_publico:number===1?"Perfil A":"Perfil B"}]}}).catch(()=>{});
   });
   await library.goto("http://127.0.0.1:5178/"+html+"?library=1");
   await library.getByRole("heading",{name:"Biblioteca"}).waitFor();
   assert.equal(privateRequests,0,"Guest must not fetch saved profiles");
   await library.getByRole("button",{name:"Conta A"}).click();
   for(let i=0;i<50&&!releaseFirst;i++)await library.waitForTimeout(50);
   assert.equal(privateRequests,1);
   await library.getByRole("button",{name:"Conta B"}).click();
   await library.getByText("Perfil B",{exact:true}).waitFor();
   releaseFirst();
   await library.getByRole("button",{name:"Sair",exact:true}).click();
   await library.waitForFunction(()=>document.querySelector("output").textContent==="");
   assert.equal(privateRequests,2,"Logout must not query private endpoint");
   await library.close();
   for (const width of [1366, 375]) {
    const page = await browser.newPage({viewport:{width,height:820},isMobile:width<820,hasTouch:width<820});
    const profile = {id:2,nome_publico:"Ana",foto_url:"/avatar-portrait-test.svg"};
    await page.route("**/avatar-portrait-test.svg", route=>route.fulfill({contentType:"image/svg+xml",body:'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="300"><rect width="100" height="300" fill="#987"/><circle cx="50" cy="40" r="30" fill="#fff"/></svg>'}));
    await page.route("**/api/presenca/", route=>route.fulfill({json:{perfis:{"2":120}}}));
    const message = {id:1,texto:"Olá",criado_em:"2026-11-25T07:00:00Z",minha:false,lida:true,apagada_em:null};
    const sentMessage = {...message,id:2,texto:"Tudo bem?",minha:true};
    let rejectMessage=false, successfulPolls=0, freeText=true, voiceEnabled=true;
    await page.route("**/api/chats/**", async route=>{
     const url = new URL(route.request().url());
     if(url.pathname==="/api/chats/1/" && route.request().method()==="POST" && rejectMessage){await route.fulfill({status:409,json:{detail:"Saldo insuficiente para esta operação."}});return;}
     if(url.pathname==="/api/chats/1/" && route.request().method()==="GET")successfulPolls++;
     const inbox = {conversas:[{id:1,nome:"Ana",perfil:profile,ultima_mensagem:message,nao_lidas:0,atividade_em:message.criado_em}],pedidos:[],historico_pedidos:[],conexoes:[]};
     const thread = {nome:"Ana",perfil:profile,mensagens:url.searchParams.has("depois")?[]:[message,sentMessage,{...sentMessage,id:3,tipo:"AUDIO",texto:"",audio_url:"/api/chats/1/audio/3/media/",duracao_segundos:5}],credito_voz:{enabled:voiceEnabled,cost:2,balance:20},texto_livre:freeText,frases:freeText?[]:["Olá"],mais:false,modo:"inicial",apagadas:[],lidas_ate:0};
     await route.fulfill({json:url.pathname==="/api/chats/"?inbox:thread});
    });
    await page.goto("http://127.0.0.1:5178/"+html);
    await page.getByRole("button",{name:/Ana/}).waitFor();
    const avatar = page.locator(".nk-chat-conversation .nk-chat-avatar").first();
    await avatar.locator("img").evaluate(img=>img.decode());
    await avatar.locator(".nk-chat-avatar-dot[aria-label]").waitFor();
    const shape = await avatar.evaluate(el=>{
      const photo=el.querySelector(".nk-chat-avatar-photo"), img=photo.querySelector("img"), dot=el.querySelector(".nk-chat-avatar-dot");
      const frame=photo.getBoundingClientRect(), image=img.getBoundingClientRect(), marker=dot.getBoundingClientRect();
      return {w:frame.width,h:frame.height,iw:image.width,ih:image.height,fit:getComputedStyle(img).objectFit,
        radius:getComputedStyle(photo).borderRadius,overflow:getComputedStyle(photo).overflow,
        dotWidth:marker.width,dotHeight:marker.height,dotRadius:getComputedStyle(dot).borderRadius,
        before:getComputedStyle(dot,"::before").content,after:getComputedStyle(dot,"::after").content,
        count:el.querySelectorAll("[data-presence-id]").length, legacy:el.querySelectorAll(".nk-presence").length};
    });
    assert.equal(shape.w,shape.h,"Avatar must remain square even with tall portrait");
    assert.equal(shape.iw,shape.ih); assert.equal(shape.fit,"cover");
    assert.equal(shape.radius,"50%"); assert.equal(shape.overflow,"hidden");
    assert.equal(shape.dotWidth,shape.dotHeight); assert.equal(shape.dotRadius,"50%");
    assert.equal(shape.before,"none"); assert.equal(shape.after,"none"); assert.equal(shape.count,1); assert.equal(shape.legacy,0);
    if(width>820){
      const empty = page.locator(".nk-chat-empty-panel");
      const panel=await empty.boundingBox(), sidebar=await page.locator(".nk-chat-sidebar").boundingBox(), layout=await page.locator(".nk-chats-layout").boundingBox();
      assert.ok(panel && sidebar && layout && panel.x >= sidebar.x+sidebar.width-2 && panel.width>layout.width/2, "Desktop empty panel must fill grid, not overlay sidebar");
      assert.notEqual(await empty.evaluate(el=>getComputedStyle(el).position),"fixed");
    }
    await page.getByRole("button",{name:/Ana/}).click();
    const dialog=page.locator("dialog.nk-chat-welcome");
    await dialog.waitFor({state:"visible"});
    assert.equal(await dialog.evaluate(el=>el.open),true);
    await page.getByRole("button",{name:"Sair da conversa"}).click();
    await page.getByRole("button",{name:/Ana/}).waitFor();
    assert.equal(await page.locator("dialog[open]").count(),0);
    await page.getByRole("button",{name:/Ana/}).click();
    await page.getByRole("button",{name:"OK",exact:true}).click();
    await dialog.waitFor({state:"detached"});
    const composer = page.locator(".nk-chat-compose");
    await composer.getByRole("button",{name:"Gravar nota de voz"}).waitFor();
    const player=page.getByRole("group",{name:"Nota de voz",exact:true});
    await player.getByRole("button",{name:"Reproduzir nota de voz"}).waitFor();
    assert.equal(await player.locator("audio[controls]").count(),0);
    assert.equal(await player.locator("audio").getAttribute("controlslist"),"nodownload noremoteplayback");
    assert.equal(await page.locator("a[download]").count(),0);
    const historyBefore = await page.locator(".nk-chat-lines").boundingBox();
    assert.ok((await composer.boundingBox()).height < 90, "Composer must remain compact");
    await composer.getByRole("button",{name:"Acções da conversa",exact:true}).click();
    await page.getByRole("region",{name:"Acções da conversa",exact:true}).waitFor();
    const historyAfter = await page.locator(".nk-chat-lines").boundingBox();
    assert.equal(historyBefore.height,historyAfter.height,"Extras must not shrink message history");
    await page.keyboard.press("Escape");
    await page.getByRole("region",{name:"Acções da conversa",exact:true}).waitFor({state:"detached"});
    await page.getByRole("textbox",{name:"Mensagem",exact:true}).fill("Teste");
    const submitted = page.waitForRequest(req=>req.method()==="POST" && new URL(req.url()).pathname==="/api/chats/1/");
    await page.getByRole("button",{name:"Enviar mensagem"}).click();
    assert.equal((await submitted).postDataJSON().texto,"Teste");
    await page.waitForFunction(()=>document.querySelector('textarea[aria-label="Mensagem"]')?.value==="");
    assert.equal(await page.getByRole("button",{name:"Chamada de áudio",exact:true}).count(),0);
    assert.equal(await page.getByRole("button",{name:"Videochamada",exact:true}).count(),0);
    if(width===1366){
      rejectMessage=true;
      await page.getByRole("textbox",{name:"Mensagem",exact:true}).fill("Teste de erro");
      await page.getByRole("button",{name:"Enviar mensagem"}).click();
      const alert=page.getByRole("alert").filter({hasText:"Saldo insuficiente"});
      await alert.waitFor();
      const before=successfulPolls;
      for(let i=0;i<60 && successfulPolls<=before;i++)await page.waitForTimeout(100);
      assert.ok(successfulPolls>before,"Polling must continue");
      assert.ok(await alert.isVisible(),"Polling must not erase a send error");
      await alert.getByRole("button",{name:"Fechar aviso"}).click();
      rejectMessage=false;
    }
    const bubble=await page.locator(".nk-chat-bubble").first().boundingBox();
    assert.ok(bubble.height<100,"Short message bubble must be compact");
    const own = await page.locator(".nk-chat-bubble-row.is-mine .nk-chat-bubble").first().boundingBox();
    const received = await page.locator(".nk-chat-bubble-row:not(.is-mine) .nk-chat-bubble").boundingBox();
    const lines = await page.locator(".nk-chat-lines").boundingBox();
    assert.ok(received.x < lines.x+lines.width/2 && own.x+own.width > lines.x+lines.width/2 && own.x > received.x, "Received left; sent right");
    assert.equal(await page.locator(".nk-chat-day").count(),1);
    const trigger = page.locator(".nk-chat-bubble-row:not(.is-mine)").getByRole("button",{name:"Opções da mensagem"});
    await trigger.hover();
    await trigger.click();
    const popover = page.locator(".nk-chat-floating-actions");
    await popover.waitFor();
    const receivedAfter = await page.locator(".nk-chat-bubble-row:not(.is-mine) .nk-chat-bubble").boundingBox();
    assert.equal(receivedAfter.x,received.x); assert.equal(receivedAfter.y,received.y);
    await page.getByRole("button",{name:"Responder",exact:true}).click();
    assert.ok(await page.getByText("A responder a:",{exact:false}).isVisible());
    if(width===1366){
      freeText=false;voiceEnabled=false;
      await page.getByRole("combobox",{name:"Mensagem predefinida"}).waitFor();
      await page.locator(".nk-independent-chat-reply").waitFor({state:"detached"});
      assert.equal(await page.getByRole("combobox",{name:"Mensagem predefinida"}).inputValue(),"");
      assert.equal(await page.getByRole("button",{name:"Gravar nota de voz"}).count(),0);
      freeText=true;voiceEnabled=true;
    }
    await page.getByRole("button",{name:"Voltar aos chats"}).click();
    await page.getByRole("button",{name:/Ana/}).click();
    if(width<820){
      await page.getByRole("navigation",{name:"Navegação da aplicação"}).getByRole("button",{name:"Início"}).click();
      await page.getByRole("heading",{name:"Other page"}).waitFor();
    }
    await page.close();
    // Exercise the real feed after the asynchronous poll arrives. A successful
    // bundle build alone does not catch undefined JSX variables at render time.
    const feed = await browser.newPage({viewport:{width,height:820},isMobile:width<820,hasTouch:width<820});
    const errors = [];
    feed.on("pageerror", error => errors.push(error.message));
    await feed.route("**/api/descoberta/sugestoes/", route=>route.fulfill({json:{results:[]}}));
    await feed.route("**/api/descoberta/pergunta/", route=>route.fulfill({json:{
      date:"2026-11-25",question:{pt:"Pergunta de teste",en:"Test question"},
      options:[{pt:"Sim",en:"Yes"},{pt:"Não",en:"No"}],choice:0,counts:[1,0],participants:[]
    }}));
    await feed.route("**/api/publicacoes/", route=>route.fulfill({json:{
      results:[],review_items:[],capabilities:{publish_media_enabled:true,credit_mode:true,
      publication_offer:{free_photo_remaining:1,photo_cost:0,video_cost:5,balance:55,spending_enabled:true}}
    }}));
    await feed.route("**/api/momentos/",route=>route.fulfill({json:{results:[{id:301,profile:{id:44,nome_publico:"Janela de teste"},moderation_status:"APROVADO",expires_at:new Date(Date.now()+3600000).toISOString(),media_type:"TEXTO",text:"Momento do Início",visibility:"TODOS",visibility_label:"Todos os membros"},{id:302,profile:{id:45,nome_publico:"Janela expirada"},moderation_status:"APROVADO",expires_at:new Date(Date.now()-1000).toISOString(),media_type:"TEXTO",text:"Expirado"}]}}));
    await feed.route("**/api/momentos/*/reacoes/",route=>route.fulfill({json:{reactions:{enabled:true,options:[],counts:{}}}}));
    await feed.route("**/api/presenca/", route=>route.fulfill({json:{perfis:{}}}));
    await feed.goto("http://127.0.0.1:5178/"+html+"?feed=1");
    await feed.getByRole("heading",{name:"Pergunta de teste"}).waitFor();
    await feed.getByRole("button",{name:"Abrir momento de Janela de teste"}).waitFor();
    assert.equal(await feed.getByRole("button",{name:"Abrir momento de Janela expirada"}).count(),0);
    await feed.getByRole("button",{name:"Abrir momento de Janela de teste"}).click();
    await feed.getByRole("dialog",{name:"Momento de Janela de teste"}).waitFor();
    await feed.getByRole("button",{name:"Fechar Momento"}).click();
    assert.ok(await feed.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),"Home Windows must fit viewport");
    assert.equal(await feed.locator(".nk-poll-share").count(),0);
    assert.equal(await feed.locator("#nk-feed-composer").isVisible(),false,"Composer must not appear until plus is pressed");
    await feed.getByRole("button",{name:"Nova publicação",exact:true}).click();
    await feed.locator("#nk-feed-composer").waitFor({state:"visible"});
    await feed.getByText("Saldo: 55",{exact:false}).waitFor();
    assert.equal(errors.length,0,errors.join("\n"));
    await feed.close();
    const detail = await browser.newPage({viewport:{width,height:820},isMobile:width<820,hasTouch:width<820});
    const profileErrors=[];
    detail.on("pageerror",error=>profileErrors.push(error.message));
    await detail.route("**/avatar-*-test.svg",route=>route.fulfill({contentType:"image/svg+xml",body:'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="300"><rect width="100" height="300" fill="#987"/></svg>'}));
    await detail.route("**/api/presenca/",route=>route.fulfill({json:{perfis:{"2":120}}}));
    let signalPosts=0, nativeSignalDialogs=0;
    const signalOffers=[{type:"OLA",label:"Olá",cost:1,available:true},{type:"FLOR",label:"Flor",cost:2,available:true},{type:"BEIJINHO",label:"Beijinho",cost:3,available:true}];
    detail.on("dialog",async dialog=>{nativeSignalDialogs++;await dialog.dismiss();});
    await detail.route("**/api/perfis/2/sinais/",async route=>{
      if(route.request().method()==="POST"){
        signalPosts++;
        assert.deepEqual(route.request().postDataJSON(),{tipo:"FLOR",expected_cost:2});
      }
      return route.fulfill({json:{signals:signalOffers.map(item=>({...item,sent_to_profile_today:signalPosts>0&&item.type==="FLOR"})),quota:{credit_mode:true,credit_balance:45-2*signalPosts},message:"Sinal enviado."}});
    });
    await detail.goto("http://127.0.0.1:5178/"+html+"?profile=1");
    await detail.getByRole("heading",{name:/Ana Maria de Sousa Fernandes/}).waitFor();
    await detail.getByText("27 anos",{exact:true}).waitFor();
    await detail.getByText("Identidade verificada pelo NKATA",{exact:true}).waitFor();
    assert.equal(await detail.locator(".nk-profile-intro__verified").count(),1,"Verified profile must show one badge");
    await detail.locator(".nk-profile-editorial__presence").getByText(/Offline/).waitFor();
    assert.equal(await detail.locator("[data-presence-id='2']").count(),1,"Presence marker must not be duplicated");
    assert.equal(await detail.getByRole("tab",{name:"Sobre mim"}).getAttribute("aria-selected"),"true");
    assert.equal(await detail.getByText("Prefiro conhecer pessoalmente.",{exact:false}).count(),1);
    assert.equal(await detail.getByText("Esta última frase deve ficar visível ao expandir.",{exact:false}).count(),0);
    await detail.getByRole("button",{name:"Ler mais",exact:true}).click();
    await detail.getByText("Esta última frase deve ficar visível ao expandir.",{exact:false}).waitFor();
    await detail.getByRole("button",{name:"Ver menos",exact:true}).click();
    assert.equal(await detail.getByText("Esta última frase deve ficar visível ao expandir.",{exact:false}).count(),0);
    const hero=await detail.locator(".nk-profile-detail__layout").boundingBox(), facts=await detail.locator(".nk-profile-sections").boundingBox();
    assert.ok(facts.y>=hero.y+hero.height-2 && Math.abs(facts.width-hero.width)<4,"Details must occupy full width below the hero");
    const portrait=await detail.locator(".nk-profile-detail__media").boundingBox(), name=await detail.locator(".nk-profile-intro__name").boundingBox();
    assert.ok(name.y>=portrait.y+portrait.height-2,"Name must appear below the full-width photo");
    assert.ok(Math.abs(portrait.width-hero.width)<4,"Photo must span the profile width");
    const secondary=detail.locator(".nk-profile-editorial__secondary");
    assert.equal(await secondary.getAttribute("open"),null,"Secondary actions should start collapsed");
    await secondary.locator("summary").click();
    const signals=await detail.locator(".nk-profile-signals__grid > button").first().boundingBox();
    assert.ok(signals && signals.height<100,"Signal actions must remain compact");
    const flower=detail.locator(".nk-profile-signals__grid").getByRole("button",{name:/Flor/});
    const confirmSignal=detail.getByRole("dialog",{name:"Enviar flor?"});
    await flower.click();
    await confirmSignal.waitFor();
    await confirmSignal.getByText("2 créditos",{exact:true}).waitFor();
    const modalBounds=await confirmSignal.boundingBox();
    const viewport=detail.viewportSize();
    assert.ok(modalBounds && Math.abs(modalBounds.x+modalBounds.width/2-viewport.width/2)<=2 && Math.abs(modalBounds.y+modalBounds.height/2-viewport.height/2)<=2,"Signal dialog must be centered in the viewport, even on a scrolled profile");
    assert.equal(await confirmSignal.getByText("45 créditos",{exact:true}).count(),0,"Keep modal concise: balance is already shown outside");
    assert.equal(await confirmSignal.getByText("43 créditos",{exact:true}).count(),0);
    assert.equal(signalPosts,0,"Opening the modal must not send a signal");
    await confirmSignal.getByRole("button",{name:"Cancelar",exact:true}).click();
    await confirmSignal.waitFor({state:"detached"});
    assert.equal(signalPosts,0,"Cancel must not spend credits");
    await flower.click();
    await confirmSignal.waitFor();
    await detail.keyboard.press("Escape");
    await confirmSignal.waitFor({state:"detached"});
    assert.equal(signalPosts,0,"Escape must not spend credits");
    await flower.click();
    await confirmSignal.getByRole("button",{name:"Enviar",exact:true}).click();
    await confirmSignal.waitFor({state:"detached"});
    await detail.locator(".nk-profile-signals__quota").getByText("43 créditos",{exact:true}).waitFor();
    assert.equal(signalPosts,1,"One explicit confirmation must send exactly one request");
    assert.equal(nativeSignalDialogs,0,"Browser confirmation prompts must not appear");
    await secondary.locator("summary").click();
    assert.equal(await detail.getByText("Gostaria de conhecer alguém entre 25–35 anos",{exact:true}).count(),1);
    assert.equal(await detail.getByText("Relacionamento sério",{exact:true}).count(),1);
    assert.equal(await detail.getByText("Momento expirado",{exact:true}).count(),0);
    await detail.getByRole("button",{name:"Fotografia seguinte",exact:true}).click();
    assert.equal(await detail.locator(".nk-profile-editorial__photo-count").innerText(),"2 / 2");
    assert.ok((await detail.locator(".nk-profile-detail__media > img").getAttribute("src")).includes("avatar-extra-test"));
    await detail.getByRole("button",{name:"Ampliar fotografia"}).click();
    await detail.getByRole("dialog",{name:"Fotografia de perfil"}).waitFor();
    await detail.getByRole("button",{name:"Fechar fotografia"}).click();
    await detail.getByRole("button",{name:"Mais",exact:true}).click();
    await detail.getByRole("button",{name:"Denunciar",exact:true}).waitFor();
    await detail.getByRole("button",{name:"Mais",exact:true}).click();
    await detail.getByRole("tab",{name:"Afinidades"}).click();
    await detail.getByText("Respeito e carinho",{exact:true}).waitFor();
    assert.equal(await detail.getByRole("tab",{name:"Afinidades"}).getAttribute("aria-selected"),"true");
    await detail.getByRole("tab",{name:"Momentos"}).click();
    assert.equal(await detail.getByText("Momento expirado",{exact:true}).count(),0);
    await detail.getByRole("heading",{name:"As minhas fotografias",exact:true}).waitFor();
    const registrationPhotos=detail.locator(".nk-profile-registration-gallery");
    assert.equal(await registrationPhotos.locator("button").count(),2,"Only the profile portrait and approved registration photo belong in this section");
    await registrationPhotos.getByText("2 fotografias",{exact:true}).waitFor();
    await registrationPhotos.getByRole("button",{name:"Abrir fotografia do perfil 2",exact:true}).click();
    const registrationViewer=detail.getByRole("dialog",{name:"Fotografia de perfil"});
    await registrationViewer.waitFor();
    assert.ok((await registrationViewer.locator("img").getAttribute("src")).includes("avatar-extra-test"),"Additional registration photo must open in the portrait viewer");
    await detail.getByRole("button",{name:"Fechar fotografia"}).click();
    await detail.getByRole("heading",{name:"Momentos recentes",exact:true}).waitFor();
    await detail.getByRole("heading",{name:"Publicações",exact:true}).waitFor();
    assert.equal(await detail.locator(".nk-profile-gallery__grid > button").count(),1,"Publications must remain separate from registration photos");
    await detail.getByRole("button",{name:"Abrir momento 1"}).click();
    await detail.getByRole("dialog",{name:"Momento",exact:true}).waitFor();
    await detail.getByRole("button",{name:"Fechar momento"}).click();
    assert.ok(await detail.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth+2),"Profile must not overflow viewport");
    assert.equal(profileErrors.length,0,profileErrors.join("\n"));
    await detail.getByRole("button",{name:"Pedir para conversar",exact:true}).click();
    await detail.getByRole("heading",{name:"Other page"}).waitFor();
    await detail.goto("http://127.0.0.1:5178/"+html+"?profile=1&unverified=1");
    await detail.getByRole("heading",{name:/Ana Maria de Sousa Fernandes/}).waitFor();
    assert.equal(await detail.locator(".nk-profile-intro__verified").count(),0,"Unverified profiles must never display a verified badge");
    assert.equal(await detail.getByText("Identidade verificada pelo NKATA",{exact:true}).count(),0);
    assert.equal(profileErrors.length,0,profileErrors.join("\n"));
    await detail.close();
   }
  } finally {await browser.close();}
 }
 console.log("Chats: desktop, mobile, aviso modal, resposta e navegação OK em Chromium e WebKit.");
} finally {
 await server.close();
 await fs.rm(html,{force:true});
 await fs.rm(jsx,{force:true});
}
