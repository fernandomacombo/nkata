// Store only opaque Moment IDs and expiry timestamps; never store content or profile details.
export const MAX_SEEN_MOMENTS = 500;
const PREFIX = "nkata_moments_seen_v1:";
export function seenStorageKey(userId) {
  const id=String(userId ?? "");
  return /^\d+$/.test(id) && Number(id)>0 ? PREFIX+id : null;
}
export function pruneSeenMoments(entries, now=Date.now()) {
  return Object.fromEntries(Object.entries(entries && typeof entries==="object" && !Array.isArray(entries)?entries:{})
    .filter(([id,expiry])=>/^\d+$/.test(id)&&typeof expiry==="number"&&Number.isFinite(expiry)&&expiry>now&&expiry<=now+86400000)
    .sort((a,b)=>b[1]-a[1]).slice(0,MAX_SEEN_MOMENTS));
}
export function readSeenMoments(storage,key,now=Date.now()) {
  if(!key)return {};
  try{return pruneSeenMoments(JSON.parse(storage.getItem(key)||"{}"),now);}catch{return {};}
}
export function writeSeenMoments(storage,key,entries,now=Date.now()) {
  if(!key)return pruneSeenMoments(entries,now);
  const merged=pruneSeenMoments({...readSeenMoments(storage,key,now),...entries},now);
  try{storage.setItem(key,JSON.stringify(merged));}catch{}
  return merged;
}
