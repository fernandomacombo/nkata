import assert from "node:assert/strict";
import fs from "node:fs/promises";
import {chromium,webkit} from "playwright";
import {createServer} from "vite";
const html="__call_panel_test.html",jsx="__call_panel_test.jsx";
await fs.writeFile(html,'<!doctype html><meta name="viewport" content="width=device-width, initial-scale=1"><div id="root"></div><script type="module" src="/'+jsx+'"></script>');
await fs.writeFile(jsx,`
import React,{useState} from "react";
import {createRoot} from "react-dom/client";
import CallPanel,{CallActions} from "/src/components/chat/CallPanel.jsx";
function Harness(){
 const [call,setCall]=useState(null);
 return <><CallActions enabled={false} onStart={()=>{throw Error("Disabled")}}/><CallActions enabled onStart={kind=>setCall({kind,phase:"incoming",name:"Ana",payer:true,balance:5,rate:5})}/>
 <CallPanel call={call} onAccept={()=>setCall(c=>({...c,phase:"active",micEnabled:true,cameraEnabled:true,elapsedSeconds:65,secondsRemaining:30}))} onDecline={()=>setCall(c=>({...c,phase:"declined"}))} onEnd={()=>setCall(c=>({...c,phase:"ended"}))} onDismiss={()=>setCall(null)} onToggleMic={()=>setCall(c=>({...c,micEnabled:!c.micEnabled}))} onToggleCamera={()=>setCall(c=>({...c,cameraEnabled:!c.cameraEnabled}))}/></>;
}
createRoot(document.getElementById("root")).render(<Harness/>);
`);
const server=await createServer({server:{host:"127.0.0.1",port:5181,strictPort:true}});
try{
 await server.listen();
 for(const engine of [chromium,webkit]){
  const browser=await engine.launch({headless:true});
  try{
   for(const width of [375,1366]){
    const page=await browser.newPage({viewport:{width,height:720}});
    await page.goto("http://127.0.0.1:5181/"+html);
    await page.getByRole("button",{name:"Videochamada",exact:true}).click();
    const dialog=page.getByRole("dialog");
    await dialog.getByRole("button",{name:"Aceitar"}).click();
    await dialog.getByText("01:05",{exact:true}).waitFor();
    await dialog.getByText("Créditos a terminar",{exact:false}).waitFor();
    await dialog.getByRole("button",{name:"Microfone",exact:true}).click();
    await dialog.getByRole("button",{name:"Sem microfone"}).waitFor();
    await dialog.getByRole("button",{name:"Câmara",exact:true}).click();
    await dialog.getByRole("button",{name:"Sem câmara"}).waitFor();
    const bounds=await dialog.boundingBox();assert.ok(bounds.width<=width);
    await dialog.getByRole("button",{name:"Terminar"}).click();
    await dialog.getByText("Chamada terminada").waitFor();
    await dialog.getByRole("button",{name:"Fechar"}).click();
    await dialog.waitFor({state:"hidden"});
    await page.getByRole("button",{name:"Chamada de áudio",exact:true}).click();
    await dialog.getByRole("button",{name:"Recusar"}).click();
    await dialog.getByText("Chamada recusada").waitFor();
    await dialog.getByRole("button",{name:"Fechar"}).click();
    await page.close();
   }
  }finally{await browser.close();}
 }
}finally{await server.close();await Promise.all([html,jsx].map(p=>fs.rm(p,{force:true})));}
