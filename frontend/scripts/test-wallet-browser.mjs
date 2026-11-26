import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { chromium, webkit } from "playwright";
import { createServer } from "vite";

const html="__wallet_regression.html", jsx="__wallet_regression.jsx";
const main=await fs.readFile("src/main.jsx","utf8");
const css=[...main.matchAll(/^import "(\.\/[^"]+\.css)";$/gm)].map(m=>'import "/src/'+m[1].slice(2)+'";').join("\n");
await fs.writeFile(html,'<!doctype html><meta name="viewport" content="width=device-width, initial-scale=1"><div id="root"></div><script type="module" src="/'+jsx+'"></script>');
await fs.writeFile(jsx,`
import React,{useState} from "react";
import {createRoot} from "react-dom/client";
import WalletDashboard from "/src/components/account/WalletDashboard.jsx";
${css}
function Harness(){
 const [refresh,setRefresh]=useState(0);
 return <main className="nk-plan-panel" style={{maxWidth:720,margin:"0 auto",minWidth:0,boxSizing:"border-box",padding:12}}>
 <button onClick={()=>setRefresh(v=>v+1)}>Atualizar conta</button>
 <WalletDashboard english={false} refreshKey={refresh} onRecharge={()=>{}}/>
 </main>
}
createRoot(document.getElementById("root")).render(<Harness/>);
`);
process.env.VITE_API_BASE_URL="http://127.0.0.1:5179";
const server=await createServer({server:{host:"127.0.0.1",port:5179,strictPort:true}});
try {
 await server.listen();
 for(const engine of [chromium,webkit]){
  const browser=await engine.launch({headless:true});
  try{
   for(const width of [1366,375]){
    const page=await browser.newPage({viewport:{width,height:820},isMobile:width<820,hasTouch:width<820});
    const tx=(id,tipo,quantidade,motivo,saldo_apos)=>({id,tipo,quantidade,motivo,saldo_apos,criado_em:"2026-11-25T07:00:00Z"});
    const topup=tx(3,"RECARGA",50,"Recarga Inicial",55);
    const spent=tx(4,"CONSUMO",-2,"Sinal — Flor",53);
    const bonus=tx(2,"BONUS",5,"Bónus de boas-vindas",5);
    let delayed=null;
    let delayPage=false;
    await page.route("**/api/minha-conta/carteira/movimentos/**",async route=>{
     const q=new URL(route.request().url()).searchParams;
     const kind=q.get("kind"),period=q.get("period"),before=q.get("before");
     const old=before!=="0";
     if(old && delayPage) await new Promise(resolve=>{delayed=resolve;});
     const rows=period==="7"?[]:old?[bonus]:kind==="CONSUMO"?[spent]:kind==="RECARGA"?[topup]:[spent,topup];
     await route.fulfill({json:{balance:53,summary:{received:55,spent:period==="7"?0:2,recharged:50,bonus:5,refunded:0,adjustments:0},
      breakdown:[{code:"signals",label:"Sinais",credits:period==="7"?0:2,count:1}],results:rows,
      next_before:!old&&kind==="ALL"&&period!=="7"?3:null,chat_expires_at:null}}).catch(()=>{});
    });
    await page.goto("http://127.0.0.1:5179/"+html);
    const root=page.locator(".nk-wallet-dashboard");
    await root.getByText("Sinal — Flor",{exact:true}).waitFor();
    assert.equal(await root.locator(".nk-wallet-statement article").count(),2);
    assert.equal(await root.locator(".nk-wallet-stat-grid article").first().locator("strong").textContent(),"53");
    const bounds=await root.evaluate(el=>({w:el.clientWidth,scroll:el.scrollWidth,viewport:window.innerWidth,doc:document.documentElement.scrollWidth}));
    assert.ok(bounds.scroll<=bounds.w+2 && bounds.doc<=bounds.viewport+2,"Wallet must not overflow viewport");
    await root.getByRole("button",{name:"Carregar mais movimentos"}).click();
    await root.getByText("Bónus de boas-vindas",{exact:true}).waitFor();
    assert.equal(await root.locator(".nk-wallet-statement article").count(),3);
    await root.getByLabel("Tipo de movimento").selectOption("CONSUMO");
     await page.waitForFunction(()=>{const rows=document.querySelectorAll(".nk-wallet-statement article");return rows.length===1 && rows[0].textContent.includes("Sinal — Flor");});
     assert.equal(await root.locator(".nk-wallet-statement article").count(),1);
    await root.getByLabel("Período",{exact:true}).selectOption("7");
    await root.getByText("Nenhum movimento neste período.",{exact:true}).waitFor();
    await root.getByLabel("Período",{exact:true}).selectOption("30");
    await root.getByText("Sinal — Flor",{exact:true}).waitFor();
    await root.getByLabel("Tipo de movimento").selectOption("ALL");
    await root.getByText("Recarga Inicial",{exact:true}).waitFor();
    delayPage=true;
    await root.getByRole("button",{name:"Carregar mais movimentos"}).click();
    await page.waitForFunction(()=>document.querySelector(".nk-wallet-dashboard__recharge:disabled")!==null);
    // Refreshing the parent must not allow a stale page to append to the new statement.
    const refreshed = page.waitForResponse(response => {const url=new URL(response.url()); return url.pathname==="/api/minha-conta/carteira/movimentos/" && url.searchParams.get("before")==="0" && response.ok();});
    await page.getByRole("button",{name:"Atualizar conta"}).click();
    if(delayed) delayed();
    await refreshed;
    await page.waitForFunction(()=>document.querySelectorAll(".nk-wallet-statement article").length===2);
    await root.getByText("Recarga Inicial",{exact:true}).waitFor();
    assert.equal(await root.getByText("Bónus de boas-vindas",{exact:true}).count(),0);
    await page.close();
   }
  }finally{await browser.close();}
 }
 console.log("Carteira: saldo, filtros, paginação e layout desktop/mobile OK em Chromium e WebKit.");
}finally{
 await server.close();
 await fs.rm(html,{force:true});await fs.rm(jsx,{force:true});
}
