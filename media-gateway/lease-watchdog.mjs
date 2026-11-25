// Private IPC only. Registration must be acknowledged before media resumes.
import {randomUUID} from "node:crypto";
export function createLeaseWatchdog(proc=process){
 const pending=new Map();
 proc.on("message",msg=>{
  if(msg?.type!=="lease-ack")return;
  const task=pending.get(msg.requestId);
  if(task){pending.delete(msg.requestId);clearTimeout(task.timer);task.resolve();}
 });
 proc.on("disconnect",()=>{
  for(const task of pending.values()){clearTimeout(task.timer);task.reject(Error("Watchdog disconnected"));}
  pending.clear();
 });
 function send(type,sessionId,deadline){
  return new Promise((resolve,reject)=>{
   if(!proc.connected){reject(Error("Watchdog unavailable"));return;}
   const requestId=randomUUID();
   const timer=setTimeout(()=>{pending.delete(requestId);reject(Error("Watchdog timeout"));},400);
   pending.set(requestId,{resolve,reject,timer});
   proc.send({type,sessionId,deadline,requestId},error=>{
    if(error&&pending.delete(requestId)){clearTimeout(timer);reject(error);}
   });
  });
 }
 return {arm:(id,deadline)=>send("lease-arm",id,deadline),clear:(id,deadline)=>send("lease-clear",id,deadline)};
}
