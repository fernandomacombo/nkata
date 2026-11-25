// Server-side only. Never expose the signing secret or this client to browsers.
import {createHmac,randomUUID} from "node:crypto";
export const path="/api/internal/media-gateway/minute/";
export const joinPath="/api/internal/media-gateway/join/";

function createSignedPost({origin,secret,fetcher=fetch}){
 const base=new URL(origin);
 if(base.protocol!=="https:"||base.username||base.password||typeof secret!=="string"||secret.length<32)throw Error("Invalid gateway config");
 return async (endpoint,payload)=>{
  const body=JSON.stringify(payload);
  const stamp=String(Math.floor(Date.now()/1000)),nonce=randomUUID();
  const signature=createHmac("sha256",secret).update("POST\n"+endpoint+"\n"+stamp+"\n"+nonce+"\n"+body).digest("hex");
  const response=await fetcher(new URL(endpoint,base),{method:"POST",redirect:"error",signal:AbortSignal.timeout(1800),headers:{"Content-Type":"application/json","X-NKATA-Media-Time":stamp,"X-NKATA-Media-Nonce":nonce,"X-NKATA-Media-Signature":signature},body});
  if(!response.ok)return null;
  return await response.json();
 };
}
export function createLeaseClient(config){
 const post=createSignedPost(config);
 return async ({sessionId,userIds,minute})=>{
  const data=await post(path,{session_id:sessionId,connected_user_ids:userIds,expected_minute:minute});
  const deadline=Date.parse(data?.paid_until);
  if(data?.authorized!==true||data.minute!==minute||!Number.isFinite(deadline)||deadline<=Date.now()||deadline>Date.now()+61000)return null;
  return deadline;
 };
}

// Identity and room come solely from Django, not from the signalling message.
// A redeemed ticket is not proof of a connected WebRTC transport.
export function createAdmissionClient(config){
 const post=createSignedPost(config);
 return async (ticket)=>{
  if(typeof ticket!=="string"||ticket.length===0||ticket.length>2048)return null;
  const data=await post(joinPath,{ticket});
  if(data?.authorized!==true||typeof data.session_id!=="string"||
     !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(data.session_id)||
     !Number.isSafeInteger(data.user_id)||data.user_id<=0||!["AUDIO","VIDEO"].includes(data.kind))return null;
  return Object.freeze({sessionId:data.session_id,userId:data.user_id,kind:data.kind});
 };
}


export const reconcilePath="/api/internal/media-gateway/reconcile/";
export function createReconcileClient(config){
 const post=createSignedPost(config);
 return async ({sessionId,userIds,minute})=>{
  for(let attempt=0;attempt<3;attempt++){
   try{
    const result=await post(reconcilePath,{session_id:sessionId,user_ids:userIds,minute,outcome:"RESUME_NOT_ATTEMPTED"});
    if(result?.reconciled===true&&Number.isSafeInteger(result.refunded)&&result.refunded>=0)return true;
   }catch{}
   if(attempt<2)await new Promise(resolve=>setTimeout(resolve,250*(attempt+1)));
  }
  return false;
 };
}
