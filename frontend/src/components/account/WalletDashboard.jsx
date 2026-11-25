import { useEffect, useRef, useState } from "react";
import { ArrowDownLeft, ArrowUpRight, WalletCards, Gift, History, RefreshCw, BarChart3, CreditCard } from "lucide-react";
import { fetchWalletStatement } from "../../services/planApi.js";

const labels = { RECARGA:["Recarga","Top-up"], BONUS:["Bónus","Bonus"], CONSUMO:["Consumo","Spending"], ESTORNO:["Estorno","Refund"], AJUSTE:["Ajuste","Adjustment"] };
const categoryEN = { signals:"Signals", text:"Text chat", voice:"Voice notes", audio:"Audio calls", video:"Video calls", other:"Other spending" };
export default function WalletDashboard({english, refreshKey, onRecharge}) {
  const t = (pt,en) => english ? en : pt;
  const locale = english ? "en-GB" : "pt-MZ";
  const fmt = value => Number(value || 0).toLocaleString(locale);
  const [period,setPeriod] = useState("30"), [kind,setKind] = useState("ALL"), [version,setVersion] = useState(0);
  const [data,setData] = useState(null), [rows,setRows] = useState([]), [next,setNext] = useState(null);
  const [loading,setLoading] = useState(true), [error,setError] = useState("");
  const [more,setMore] = useState(false);
  const moreRequest = useRef(null);
  useEffect(()=>{
    const controller = new AbortController();
    setLoading(true); setError(""); setData(null); setRows([]); setNext(null); setMore(false);
    fetchWalletStatement({period,kind,signal:controller.signal})
      .then(result=>{if(!controller.signal.aborted){setData(result);setRows(result.results);setNext(result.next_before);}})
      .catch(err=>{if(!controller.signal.aborted)setError(err.message);})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>{controller.abort();moreRequest.current?.abort();moreRequest.current=null;};
  },[period,kind,version,refreshKey]);
  async function loadMore(){
    if(!next || loading || more || moreRequest.current) return;
    const controller = new AbortController();
    moreRequest.current = controller;
    setMore(true);setError("");
    try{
      const result = await fetchWalletStatement({period,kind,before:next,signal:controller.signal});
      if(!controller.signal.aborted){
        setRows(current=>[...current,...result.results.filter(row=>!current.some(old=>old.id===row.id))]);
        setNext(result.next_before);
      }
    }catch(err){if(!controller.signal.aborted)setError(err.message);}
    finally{if(moreRequest.current===controller){moreRequest.current=null;setMore(false);}}
  }
  const summary=data?.summary;
  const consumed=data?.breakdown.reduce((sum,row)=>sum+row.credits,0)||0;
  return <section className="nk-wallet-dashboard" aria-label={t("Controlo de créditos","Credit tracking")}>
    <header><div><small>{t("A minha carteira","My wallet")}</small><h3>{t("Controlo de créditos","Credit tracking")}</h3></div><button type="button" disabled={loading||more} onClick={()=>setVersion(v=>v+1)} aria-label={t("Atualizar movimentos","Refresh transactions")}><RefreshCw size={17}/></button></header>
    <label className="nk-wallet-filter">{t("Período","Period")}<select disabled={more} value={period} onChange={e=>setPeriod(e.target.value)}>{[["7",t("Últimos 7 dias","Last 7 days")],["30",t("Últimos 30 dias","Last 30 days")],["90",t("Últimos 90 dias","Last 90 days")],["ALL",t("Desde o início","All time")]].map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
    {loading && <p role="status">{t("A carregar movimentos…","Loading transactions…")}</p>}
    {error && <p role="alert">{error}</p>}
    {data && <>
      <div className="nk-wallet-stat-grid">
        {[[WalletCards,t("Saldo atual","Current balance"),data.balance],[ArrowUpRight,t("Créditos utilizados","Credits spent"),summary.spent],[CreditCard,t("Créditos comprados","Purchased credits"),summary.recharged],[Gift,t("Bónus recebidos","Bonuses received"),summary.bonus],[ArrowDownLeft,t("Créditos devolvidos","Refunded credits"),summary.refunded]].map(([Icon,label,value])=><article key={label}><Icon size={18}/><small>{label}</small><strong>{fmt(value)}</strong></article>)}
      </div>
      <small>{t("O saldo é atual. Os restantes valores referem-se ao período seleccionado, em créditos, não em meticais.","Balance is current. Other totals are for the selected period, in credits, not money.")}</small>
      {data.chat_expires_at && <p>{t("Texto livre ativo até","Text chat active until")} {new Date(data.chat_expires_at).toLocaleString(locale)}</p>}
      <button className="nk-wallet-dashboard__recharge" type="button" onClick={onRecharge}>{t("Ver pacotes de recarga","View top-up packs")}</button>
      <h4><BarChart3 size={18}/>{t("Onde utilizei os créditos","Where I spent credits")}</h4>
      {!consumed?<p>{t("Ainda não utilizou créditos neste período.","No credit spending in this period.")}</p>:data.breakdown.filter(row=>row.credits>0).map(row=><div key={row.code} className="nk-wallet-breakdown"><div><span>{english?categoryEN[row.code]:row.label}</span><strong>{fmt(row.credits)} {t("créditos","credits")}</strong></div><progress max={consumed} value={row.credits} aria-label={english?categoryEN[row.code]:row.label}/></div>)}
      <h4><History size={18}/>{t("Extrato de movimentos","Transaction statement")}</h4>
      <label className="nk-wallet-filter">{t("Tipo de movimento","Transaction type")}<select disabled={more} value={kind} onChange={e=>setKind(e.target.value)}><option value="ALL">{t("Todos","All")}</option>{Object.entries(labels).map(([code,label])=><option key={code} value={code}>{label[english?1:0]}</option>)}</select></label>
      <div className="nk-wallet-statement">{rows.length===0?<p>{t("Nenhum movimento neste período.","No transactions in this period.")}</p>:rows.map(row=><article key={row.id}><span className="nk-wallet-statement__icon">{row.quantidade>0?<ArrowDownLeft size={18}/>:<ArrowUpRight size={18}/>}</span><div><strong>{row.motivo}</strong><small>{labels[row.tipo]?.[english?1:0]||row.tipo} · {new Date(row.criado_em).toLocaleString(locale)}</small><small>{t("Movimento","Transaction")} #{row.id}</small></div><div className="nk-wallet-statement__amount"><strong className={row.quantidade>0?"is-positive":"is-negative"}>{row.quantidade>0?"+":""}{fmt(row.quantidade)}</strong><small>{t("Saldo","Balance")}: {fmt(row.saldo_apos)}</small></div></article>)}</div>
      {next && <button type="button" className="nk-wallet-dashboard__recharge" disabled={more} onClick={loadMore}>{more?t("A carregar…","Loading…"):t("Carregar mais movimentos","Load more transactions")}</button>}
      <small>{t("O extrato é privado e não pode ser alterado pelo membro.","Your statement is private and cannot be edited by you.")}</small>
    </>}
  </section>;
}
