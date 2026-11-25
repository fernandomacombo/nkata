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
import BottomNavigation from "/src/components/layout/BottomNavigation.jsx";
${css}
function Harness(){
 const [page,setPage] = useState("chats"), [id,setId] = useState(null), [accepted,setAccepted] = useState(false);
 return <div className="nk-app"><header className="nk-header"><span className="nk-header__member">Member</span></header>
 {page === "chats" ? <ChatsPage conversationId={id} onSelect={setId} onBack={()=>setId(null)} onDiscover={()=>setPage("discover")} onOpenProfile={()=>setPage("profile")} safetyAccepted={accepted} onAcceptSafety={async()=>setAccepted(true)} /> : <main><h1>Other page</h1></main>}
 <BottomNavigation activePage={page} onNavigate={p=>{setPage(p);setId(null)}}/>
 </div>;
}
document.body.classList.toggle("nk-app-mode", window.matchMedia("(max-width: 820px)").matches);
createRoot(document.getElementById("root")).render(<Harness/>);
`);
process.env.VITE_API_BASE_URL = "http://127.0.0.1:5178";
const server = await createServer({server:{host:"127.0.0.1",port:5178,strictPort:true}});
try {
 await server.listen();
 for (const engine of [chromium, webkit]) {
  const browser = await engine.launch({headless:true});
  try {
   for (const width of [1366, 375]) {
    const page = await browser.newPage({viewport:{width,height:820},isMobile:width<820,hasTouch:width<820});
    const profile = {id:2,nome_publico:"Ana",foto_url:null};
    const message = {id:1,texto:"Olá",criado_em:"2026-11-25T07:00:00Z",minha:false,lida:true,apagada_em:null};
    await page.route("**/api/chats/**", async route=>{
     const url = new URL(route.request().url());
     const inbox = {conversas:[{id:1,nome:"Ana",perfil:profile,ultima_mensagem:message,nao_lidas:0,atividade_em:message.criado_em}],pedidos:[],historico_pedidos:[],conexoes:[]};
     const thread = {nome:"Ana",perfil:profile,mensagens:url.searchParams.has("depois")?[]:[message],texto_livre:true,frases:[],mais:false,modo:"inicial",apagadas:[],lidas_ate:0};
     await route.fulfill({json:url.pathname==="/api/chats/"?inbox:thread});
    });
    await page.goto("http://127.0.0.1:5178/"+html);
    await page.getByRole("button",{name:/Ana/}).waitFor();
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
    await page.getByRole("textbox",{name:"Mensagem",exact:true}).fill("Teste");
    const submitted = page.waitForRequest(req=>req.method()==="POST" && new URL(req.url()).pathname==="/api/chats/1/");
    await page.getByRole("button",{name:"Enviar mensagem"}).click();
    assert.equal((await submitted).postDataJSON().texto,"Teste");
    const bubble=await page.locator(".nk-chat-bubble").first().boundingBox();
    assert.ok(bubble.height<100,"Short message bubble must be compact");
    await page.getByRole("button",{name:"Opções da mensagem"}).click();
    await page.getByRole("button",{name:"Responder",exact:true}).click();
    assert.ok(await page.getByText("A responder a:",{exact:false}).isVisible());
    await page.getByRole("button",{name:"Voltar aos chats"}).click();
    await page.getByRole("button",{name:/Ana/}).click();
    if(width<820){
      await page.getByRole("navigation",{name:"Navegação da aplicação"}).getByRole("button",{name:"Início"}).click();
      await page.getByRole("heading",{name:"Other page"}).waitFor();
    }
    await page.close();
   }
  } finally {await browser.close();}
 }
 console.log("Chats: desktop, mobile, aviso modal, resposta e navegação OK em Chromium e WebKit.");
} finally {
 await server.close();
 await fs.rm(html,{force:true});
 await fs.rm(jsx,{force:true});
}
