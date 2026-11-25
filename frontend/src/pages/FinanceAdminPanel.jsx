import { useEffect, useState } from "react";
import { WalletCards, CreditCard, History, Coins, Gift, ShieldCheck, Settings, BarChart3, RefreshCw, Search } from "lucide-react";
import { request } from "../services/api.js";

const TABS = [
  ["overview","Visão geral",BarChart3], ["wallets","Carteiras",WalletCards],
  ["payments","Pagamentos e recargas",CreditCard], ["movements","Movimentos",History],
  ["consumption","Consumo",Coins], ["bonuses","Bónus",Gift],
  ["catalogue","Catálogo e preços",Settings], ["audit","Auditoria financeira",ShieldCheck],
];
const fmt = value => Number(value || 0).toLocaleString("pt-MZ");
const money = value => Number(value || 0).toLocaleString("pt-MZ", {minimumFractionDigits:2, maximumFractionDigits:2}) + " MT";
const date = value => value ? new Date(value).toLocaleString("pt-MZ") : "—";
const labels = {CRIADO:"Criado",PENDENTE:"Pendente",INCERTO:"Incerto",REVISAO:"Em revisão",PAGO:"Pago",FALHOU:"Falhou",BONUS:"Bónus",RECARGA:"Recarga",CONSUMO:"Consumo",ESTORNO:"Estorno",AJUSTE:"Ajuste"};
export default function FinanceAdminPanel() {
  const [tab,setTab] = useState("overview"), [draft,setDraft] = useState(""), [query,setQuery] = useState("");
  const [status,setStatus] = useState(""), [offset,setOffset] = useState(0), [version,setVersion] = useState(0);
  const [data,setData] = useState(null), [error,setError] = useState(""), [loading,setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(""); setData(null);
    const params = new URLSearchParams({section:tab,q:query,status,offset:String(offset)});
    request("/api/painel/financas/?" + params, {signal:controller.signal})
      .then(result => {if(!controller.signal.aborted) setData(result);})
      .catch(err => {if(!controller.signal.aborted) setError(err.message);})
      .finally(() => {if(!controller.signal.aborted) setLoading(false);});
    return () => controller.abort();
  },[tab,query,status,offset,version]);
  const changeTab = next => {if(next===tab)return;setData(null);setTab(next);setDraft("");setQuery("");setStatus("");setOffset(0);};
  const m = data?.metrics;
  const list = !["overview","catalogue"].includes(tab);
  const wallet = ["wallets","audit"].includes(tab);
  return <section className="nk-finance">
    <header className="nk-admin-section-header"><div><small>Gestão financeira</small><h2>Créditos e finanças</h2><p>Receitas, saldos e movimentos da carteira NKATA.</p></div><button type="button" onClick={() => setVersion(v=>v+1)} disabled={loading} aria-label="Atualizar finanças"><RefreshCw size={18}/></button></header>
    <nav className="nk-finance-tabs" aria-label="Áreas financeiras">{TABS.map(([code,label,Icon])=><button type="button" key={code} aria-pressed={tab===code} onClick={()=>changeTab(code)}><Icon size={16}/>{label}</button>)}</nav>
    {list && <form className="nk-admin-filters" onSubmit={event=>{event.preventDefault();setOffset(0);setQuery(draft.trim());setVersion(v=>v+1);}}>
      <label><Search size={17}/><input value={draft} onChange={event=>setDraft(event.target.value)} maxLength={120} placeholder="Pesquisar membro ou referência"/></label>
      {tab==="payments" && <select aria-label="Estado do pagamento" value={status} onChange={event=>{setStatus(event.target.value);setOffset(0);}}><option value="">Todos os estados</option>{["CRIADO","PENDENTE","INCERTO","REVISAO","PAGO","FALHOU"].map(value=><option key={value} value={value}>{labels[value]}</option>)}</select>}
      <button type="submit" className="nk-admin-button is-primary">Pesquisar</button>
    </form>}
    {loading && <p role="status">A carregar dados financeiros…</p>}
    {error && <p role="alert">{error}</p>}
    {!loading && !error && m && <>
      <div className="nk-finance-metrics">{[
        ["Receita bruta confirmada de créditos",money(m.settled_revenue_mzn)],["Carteiras registadas",fmt(m.wallet_count)],
        ["Saldo total",fmt(m.total_balance)+" créditos"],["Pagamentos liquidados",fmt(m.settled_count)],
        ["Pagamentos por concluir",fmt(m.pending_count)],["Em revisão",fmt(m.review_count)],
        ["Créditos de recargas",fmt(m.recharge_credits)],["Créditos consumidos",fmt(m.consumed_credits)],
        ["Créditos de bónus",fmt(m.bonus_credits)],["Carteiras inconsistentes",fmt(m.inconsistent_wallets)]
      ].map(([label,value])=><article className="nk-admin-card" key={label}><small>{label}</small><strong>{value}</strong></article>)}</div>
      <p>Valores acumulados. A receita não inclui planos antigos, pagamentos pendentes, taxas ou custos operacionais.</p>
      <button type="button" className="nk-admin-button" onClick={()=>changeTab("audit")}>Consultar reconciliação</button>
    </>}
    {!loading && !error && tab==="catalogue" && data?.catalogue && <>
      <p>Vendas de créditos: {data.checkout_configured?"configuradas":"desativadas"} · Consumo: {data.spending_enabled?"ativo":"desativado"} · Chamadas por créditos: ainda não disponíveis.</p>
      <div className="nk-finance-metrics">{data.catalogue.packs.map(p=><article className="nk-admin-card" key={p.code}><small>{p.label}</small><strong>{fmt(p.credits)} créditos</strong><span>{money(p.price_mzn)}</span>{p.bonus>0 && <small>Inclui {p.bonus} de bónus</small>}</article>)}</div>
      <h3>Tarifário central</h3>
      <div className="nk-finance-table"><table><thead><tr><th>Funcionalidade</th><th>Custo</th></tr></thead><tbody>{data.catalogue.actions.map(a=><tr key={a.code}><td>{a.label}</td><td>{a.credits===0?"Grátis, com limite":a.credits+" crédito"+(a.credits===1?"":"s")+(a.unit==="minute"?"/min":a.unit==="24h"?"/24 h":"")}</td></tr>)}</tbody></table></div>
      <p>Bónus de boas-vindas: {data.catalogue.welcome_credits} créditos, uma única vez após verificação. Catálogo de consulta, sem edição de preços.</p>
    </>}
    {!loading && !error && list && data && <>
      {tab==="audit" && <p>Verificação entre saldo registado e soma dos movimentos. Esta consulta não modifica saldos.</p>}
      <div className="nk-admin-list-heading"><span>{fmt(data.total)} registo(s)</span><nav aria-label="Paginação financeira"><button type="button" disabled={!offset} onClick={()=>setOffset(v=>Math.max(0,v-50))}>Anterior</button><span>Página {Math.floor(offset/50)+1}</span><button type="button" disabled={offset+50>=data.total} onClick={()=>setOffset(v=>v+50)}>Seguinte</button></nav></div>
      {data.results.length ? <div className="nk-finance-table"><table><thead><tr><th>Membro</th>{wallet?<><th>Saldo</th><th>Movimentos</th><th>Consistência</th><th>Atualizado</th></>:tab==="payments"?<><th>Referência / pacote</th><th>Valor</th><th>Créditos</th><th>Estado</th><th>Data</th></>:<><th>Tipo / motivo</th><th>Movimento</th><th>Saldo após</th><th>Referência</th><th>Data</th></>}</tr></thead><tbody>{data.results.map(row=><tr key={row.id}><td><strong>{row.name}</strong><small>{row.email}</small></td>{wallet?<><td>{fmt(row.balance)}</td><td>{fmt(row.ledger_total)}</td><td>{row.consistent?"Consistente":"Divergência"}</td><td>{date(row.updated_at)}</td></>:tab==="payments"?<><td>{row.reference}<small>{row.product}</small></td><td>{money(row.amount_mzn)}</td><td>{fmt(row.credits)}</td><td>{labels[row.status]||row.status}</td><td>{date(row.created_at)}</td></>:<><td>{labels[row.kind]||row.kind}<small>{row.reason}</small></td><td>{row.amount>0?"+":""}{fmt(row.amount)}</td><td>{fmt(row.balance_after)}</td><td>{row.reference}</td><td>{date(row.created_at)}</td></>}</tr>)}</tbody></table></div>:<p>{tab==="audit"?"Nenhuma divergência encontrada nos saldos consultados.":"Nenhum registo encontrado."}</p>}
    </>}
  </section>;
}
