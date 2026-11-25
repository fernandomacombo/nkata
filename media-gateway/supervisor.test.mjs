import test from "node:test";
import assert from "node:assert/strict";
import {mkdtemp,writeFile,readFile,rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {setTimeout as sleep} from "node:timers/promises";
import {supervise} from "./supervisor.mjs";

test("independent supervisor kills blocked controller and its descendant",{skip:process.platform!=="linux",timeout:15000},async()=>{
 const dir=await mkdtemp(join(tmpdir(),"nkata-watchdog-"));
 const script=join(dir,"blocked.cjs"),pidFile=join(dir,"descendant.pid");
 let supervisor;
 try{
  await writeFile(script,`
   const {spawn}=require("node:child_process");
   const fs=require("node:fs");
   const child=spawn(process.execPath,["-e","setInterval(()=>{},1000)"],{stdio:"ignore"});
   fs.writeFileSync(process.env.TEST_PID_FILE,String(child.pid));
   process.send({type:"media-heartbeat"},()=>{
    setTimeout(()=>Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0),200);
   });
  `);
  supervisor=supervise(script,{startupMs:5000,timeoutMs:700,intervalMs:50,env:{...process.env,TEST_PID_FILE:pidFile}});
  assert.equal(await supervisor.done,"heartbeat-timeout");
  const pid=Number(await readFile(pidFile,"utf8"));
  assert.ok(Number.isInteger(pid)&&pid>0);
  let gone=false;
  for(let i=0;i<40;i++){
   try{const status=await readFile("/proc/"+pid+"/status","utf8");if(/^State:\s+Z/m.test(status)){gone=true;break;}}
   catch(e){if(e.code==="ENOENT"){gone=true;break;}throw e;}
   await sleep(50);
  }
  assert.equal(gone,true,"descendant must be terminated, not left forwarding");
 }finally{supervisor?.stop();await rm(dir,{recursive:true,force:true});}
});
