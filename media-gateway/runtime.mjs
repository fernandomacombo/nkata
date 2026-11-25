import {isIP} from "node:net";
export function readConfig(env){
 if(env.NKATA_MEDIA_RUNTIME!=="isolated-staging")throw Error("Experimental staging only");
 const httpsOrigin=value=>{
  const u=new URL(value);
  if(u.protocol!=="https:"||u.origin!==value||u.username||u.password)throw Error("HTTPS origin required");
  return value;
 };
 const port=(v,d)=>{const n=Number(v??d);if(!Number.isInteger(n)||n<1024||n>65535)throw Error("Invalid port");return n;};
 const origin=httpsOrigin(env.NKATA_STAGING_WEB_ORIGIN),backend=httpsOrigin(env.NKATA_STAGING_API_ORIGIN);
 // Deliberately exclude known live domains, including subdomains.
 for(const v of [origin,backend]){
  const h=new URL(v).hostname;
  if(h==="nkata.date"||h.endsWith(".nkata.date")&&!h.startsWith("staging."))throw Error("Production origin forbidden");
 }
 const secret=env.NKATA_MEDIA_GATEWAY_SECRET;
 if(typeof secret!=="string"||secret.length<32)throw Error("Missing gateway secret");
 const announcedAddress=env.NKATA_MEDIA_ANNOUNCED_IP;
 if(isIP(announcedAddress)!==4||announcedAddress==="0.0.0.0"||announcedAddress.startsWith("127."))throw Error("Routable media IP required");
 const mediaPort=port(env.NKATA_MEDIA_PORT,44444),httpPort=port(env.NKATA_SIGNAL_PORT,8085);
 if(mediaPort===httpPort)throw Error("Ports must differ");
 return {origin,backend,secret,announcedAddress,mediaPort,httpPort};
}
// This proves the SFU received RTP, not that a remote human heard/saw it.
// Consumers remain paused while sampling. Never use browser counters.
export async function verifyInboundMedia(room,{sampleMs=350,sleep=ms=>new Promise(r=>setTimeout(r,ms))}={}){
 if(!room.ready())return false;
 const producers=[...room.peers.values()].flatMap(p=>[...p.producers.values()]);
 const count=async p=>{
  const stats=await p.getStats();
  return stats.filter(s=>s.type==="inbound-rtp"&&Number.isFinite(s.packetCount)).reduce((n,s)=>n+s.packetCount,0);
 };
 const a=await Promise.all(producers.map(count));
 await sleep(sampleMs);
 if(!room.ready())return false;
 const b=await Promise.all(producers.map(count));
 return producers.length>=2&&b.every((n,i)=>n>a[i]);
}
