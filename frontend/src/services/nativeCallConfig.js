// A normal build never loads the SFU client. The experimental build must
// match two exact, separately configured HTTPS/WSS origins and server consent.
const safeHost=h=>!!h&&h!=="nkata.date"&&(!h.endsWith(".nkata.date")||h.startsWith("staging."));
export function mediaBuildConfig({mode,webOrigin,signalUrl,location,secure}){
 if(mode!=="media-staging"||secure!==true||location?.origin!==webOrigin)return null;
 try{
  const web=new URL(webOrigin),signal=new URL(signalUrl);
  if(web.protocol!=="https:"||web.origin!==webOrigin||!safeHost(web.hostname)||
     signal.protocol!=="wss:"||signal.pathname!=="/signal"||signal.username||signal.password||
     signal.search||signal.hash||signal.port||!safeHost(signal.hostname)||signal.href!==signalUrl)return null;
  return {signalUrl};
 }catch{return null;}
}
export function mediaServerMatches(local,remote){
 return !!local&&remote?.enabled===true&&remote.signal_url===local.signalUrl;
}
