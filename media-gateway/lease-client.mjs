// Server-side only. The browser must never have this signing secret.
import {createHmac,randomUUID} from "node:crypto";
export const path="/api/internal/media-gateway/minute/";
export function createLeaseClient({origin,secret,fetcher=fetch}){
 const url=new URL(path,origin);
 if(url.protocol!=="https:"||typeof secret!=="string"||secret.length<32)throw Error("Invalid gateway config");
 return async ({sessionId,userIds,minute})=>{
  const body=JSON.stringify({session_id:sessionId,connected_user_ids:userIds,expected_minute:minute});
  const stamp=String(Math.floor(Date.now()/1000)),nonce=randomUUID();
  const signature=createHmac("sha256",secret).update("POST\n"+path+"\n"+stamp+"\n"+nonce+"\n"+body).digest("hex");
  const response=await fetcher(url,{method:"POST",redirect:"error",signal:AbortSignal.timeout(1800),headers:{"Content-Type":"application/json","X-NKATA-Media-Time":stamp,"X-NKATA-Media-Nonce":nonce,"X-NKATA-Media-Signature":signature},body});
  if(!response.ok)return null;
  const data=await response.json(),deadline=Date.parse(data.paid_until);
  if(data.authorized!==true||data.minute!==minute||!Number.isFinite(deadline)||deadline<=Date.now()||deadline>Date.now()+61000)return null;
  return deadline;
 };
}
