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
import BottomNavigation from "/src/components/layout/BottomNavigation.jsx";
import { PresenceProvider } from "/src/components/profiles/Presence.jsx";
import useProfileLibrary from "/src/hooks/useProfileLibrary.js";
${css}
function LibraryHarness(){
 const {savedProfiles} = useProfileLibrary();
 function session(id){window.dispatchEvent(new CustomEvent("nkata:session-changed",{detail:id?{authenticated:true,user:{id}}:{authenticated:false}}));}
 return <main><h1>Biblioteca</h1><button onClick={()=>session(1)}>Conta A</button><button onClick={()=>session(2)}>Conta B</button><button onClick={()=>session(null)}>Sair</button><output aria-label="Guardados">{savedProfiles.map(p=>p.nome_publico).join(",")}</output></main>;
}
function Harness(){
 const [page,setPage] = useState(new URLSearchParams(window.location.search).has("profile") ? "profile-test" : new URLSearchParams(window.location.search).has("feed") ? "feed-test" : "chats"), [id,setId] = useState(null), [accepted,setAccepted] = useState(false);
 return <div className="nk-app"><header className="nk-header"><span className="nk-header__member">Member</span></header>
 {page === "profile-test" ? <ProfileDetailPage authenticated profile={{id:2,nome_publico:"Ana Maria de Sousa Fernandes",idade:27,cidade:"Maputo",objetivo_display:"Relacionamento sério",sobre_si:["Prefiro conhecer pessoalmente.","Gosto de ler e pesquisar.","Valorizo o diálogo.","Esta última frase deve ficar visível ao expandir."].join(String.fromCharCode(10)),o_que_valoriza:"Respeito e carinho",o_que_nao_aceita:"Mentiras",preferencias:{ages:[25,35],height:165},foto_url:"/avatar-portrait-test.svg",gallery:[{id:"registo-1",mediaType:"IMAGEM",mediaUrl:"/avatar-extra-test.svg"},{id:22,mediaType:"IMAGEM",mediaUrl:"/avatar-post-test.svg"}],moments:[{id:7,mediaType:"TEXTO",text:"Um dia tranquilo por aqui.",expiresAt:new Date(Date.now()+3600000).toISOString()},{id:8,mediaType:"TEXTO",text:"Momento expirado",expiresAt:new Date(Date.now()-1000).toISOString()}]}} onAskChat={async()=>setPage("other")} onBack={()=>setPage("other")} onToggleInterest={()=>{}} onToggleSaved={()=>{}}/> : page === "feed-test" ? <MemberHomePage onNavigate={setPage} onOpenProfile={()=>setPage("profile")}/> : page === "chats" ? <ChatsPage conversationId={id} onSelect={setId} onBack={()=>setId(null)} onDiscover={()=>setPage("discover")} onOpenProfile={()=>setPage("profile")} safetyAccepted={accepted} onAcceptSafety={async()=>setAccepted(true)} /> : <main><h1>Other page</h1></main>}
 <BottomNavigation activePage={page} onNavigate={p=>{setPage(p);setId(null)}}/>
 </div>;
}
document.body.classList.toggle("nk-app-mode", window.matchMedia("(max-width: 820px)").matches);
createRoot(document.getElementById("root")).render(new URLSearchParams(window.location.search).has("library") ? <LibraryHarness/> : <PresenceProvider member={true} identity="test" page="chats"><Harness/></PresenceProvider>);
`);
process.env.VITE_API_BASE_URL = "http://127.0.0.1:5178";
const server = await createServer({server:{host:"127.0.0.1",port:5178,strictPort:true}});
try {
 await server.listen();
 for (const engine of [chromium, webkit]) {
  const browser = await engine.launch({headless:true});
  try {
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
    await detail.route("**/api/perfis/2/sinais/",route=>route.fulfill({json:{signals:[],quota:{credit_mode:true,credit_balance:45}}}));
    await detail.goto("http://127.0.0.1:5178/"+html+"?profile=1");
    await detail.getByRole("heading",{name:"Ana Maria de Sousa Fernandes, 27",exact:true}).waitFor();
    assert.equal(await detail.getByText("Prefiro conhecer pessoalmente.",{exact:false}).count(),1);
    assert.equal(await detail.getByText("Esta última frase deve ficar visível ao expandir.",{exact:false}).count(),0);
    await detail.getByRole("button",{name:"Ler mais",exact:true}).click();
    await detail.getByText("Esta última frase deve ficar visível ao expandir.",{exact:false}).waitFor();
    await detail.getByRole("button",{name:"Ver menos",exact:true}).click();
    assert.equal(await detail.getByText("Esta última frase deve ficar visível ao expandir.",{exact:false}).count(),0);
    const hero=await detail.locator(".nk-profile-detail__layout").boundingBox(), facts=await detail.locator(".nk-profile-essentials--wide").boundingBox();
    assert.ok(facts.y>=hero.y+hero.height-2 && Math.abs(facts.width-hero.width)<4,"Details must occupy full width below the hero");
    const signals=await detail.locator(".nk-profile-signals__grid > button").first().boundingBox();
    assert.ok(signals.height<100,"Signal actions must remain compact");
    assert.equal(await detail.getByText("25–35 anos",{exact:true}).count(),1);
    assert.equal(await detail.getByText("Relacionamento sério",{exact:true}).count(),1);
    assert.equal(await detail.getByText("Momento expirado",{exact:true}).count(),0);
    await detail.getByRole("button",{name:"Fotografia 2",exact:true}).click();
    assert.ok((await detail.locator(".nk-profile-detail__media > img").getAttribute("src")).includes("avatar-extra-test"));
    await detail.getByRole("button",{name:"Ampliar fotografia"}).click();
    await detail.getByRole("dialog",{name:"Fotografia de perfil"}).waitFor();
    await detail.getByRole("button",{name:"Fechar fotografia"}).click();
    await detail.getByRole("button",{name:"Mais",exact:true}).click();
    await detail.getByRole("button",{name:"Denunciar",exact:true}).waitFor();
    await detail.getByRole("button",{name:"Mais",exact:true}).click();
    await detail.getByRole("button",{name:"Abrir momento 1"}).click();
    await detail.getByRole("dialog",{name:"Momento",exact:true}).waitFor();
    await detail.getByRole("button",{name:"Fechar momento"}).click();
    assert.ok(await detail.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth+2),"Profile must not overflow viewport");
    assert.equal(profileErrors.length,0,profileErrors.join("\n"));
    await detail.getByRole("button",{name:"Pedir conversa",exact:true}).click();
    await detail.getByRole("heading",{name:"Other page"}).waitFor();
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
