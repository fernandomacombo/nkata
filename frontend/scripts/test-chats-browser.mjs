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
createRoot(document.getElementById("root")).render(new URLSearchParams(window.location.search).has("loader") ? <LoaderHarness/> : new URLSearchParams(window.location.search).has("library") ? <LibraryHarness/> : <PresenceProvider member={true} identity="test" page="chats"><Harness/></PresenceProvider>);
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
   await loader.getByRole("button",{name:"Simular perfil carregado"}).click();
   await status.waitFor({state:"detached"});
   await loader.getByRole("heading",{name:/Perfil de teste/}).waitFor();
   await loader.reload();
   await status.waitFor();
   await loader.getByRole("button",{name:"Simular falha"}).click();
   await status.waitFor({state:"detached"});
   await loader.getByRole("heading",{name:"Perfil não disponível"}).waitFor();
   assert.equal(loaderErrors.length,0,loaderErrors.join("\n"));
   await loader.getByRole("button",{name:"Simular carregamento chats"}).click();
   await status.getByText("A preparar as suas conversas",{exact:true}).waitFor();
   await loader.getByRole("button",{name:"Simular carregamento explorar"}).click();
   await status.getByText("A descobrir novas pessoas",{exact:true}).waitFor();
   assert.equal(await status.locator(".nk-heart-loader__particles svg").count(),7);
   assert.equal(loaderErrors.length,0,loaderErrors.join("\n"));
   await loader.close();
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
    await feed.route("**/api/presenca/", route=>route.fulfill({json:{perfis:{}}}));
    await feed.goto("http://127.0.0.1:5178/"+html+"?feed=1");
    await feed.getByRole("heading",{name:"Pergunta de teste"}).waitFor();
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
