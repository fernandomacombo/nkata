// Linux-only isolated media process supervisor. The supervised child is a
// process-group leader; its native SFU worker inherits that process group.
// A separate systemd cgroup is required to survive supervisor failure.
import {fork} from "node:child_process";
import {performance} from "node:perf_hooks";
import {fileURLToPath} from "node:url";

export function supervise(script,{startupMs=15000,timeoutMs=1250,intervalMs=100,env=process.env}={}){
 if(process.platform!=="linux")throw Error("Linux media supervisor required");
 const child=fork(script,[],{detached:true,stdio:["ignore","inherit","inherit","ipc"],env});
 let last=performance.now(),ready=false,stopped=false,reason=null,resolve;
 const done=new Promise(r=>{resolve=r;});
 const killGroup=()=>{
  if(!child.pid)return;
  try{process.kill(-child.pid,"SIGKILL");}
  catch(error){if(error.code!=="ESRCH")throw error;}
 };
 function stop(why="shutdown"){
  if(stopped)return;stopped=true;reason=why;
  clearInterval(timer);
  // Do not wait for an unresponsive event loop to handle a signal.
  killGroup();
 }
 const timer=setInterval(()=>{
  if(performance.now()-last>(ready?timeoutMs:startupMs))stop("heartbeat-timeout");
 },intervalMs);
 child.on("message",msg=>{
  if(stopped||msg?.type!=="media-heartbeat")return;
  // Only the private child IPC channel is trusted; no network heartbeat.
  last=performance.now();ready=true;
 });
 child.once("disconnect",()=>stop("ipc-disconnect"));
 child.once("error",()=>{stop("child-error");resolve(reason);});
 child.once("exit",()=>{stop("child-exit");resolve(reason);});
 return {child,stop,done};
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 if(process.env.NKATA_MEDIA_RUNTIME!=="isolated-staging")throw Error("Experimental staging only");
 const supervisor=supervise(fileURLToPath(new URL("./server.mjs",import.meta.url)));
 process.on("SIGTERM",()=>supervisor.stop("shutdown"));
 process.on("SIGINT",()=>supervisor.stop("shutdown"));
 const reason=await supervisor.done;
 console.error("Media supervisor stopped:",reason);
 process.exitCode=reason==="shutdown"?0:1;
}
