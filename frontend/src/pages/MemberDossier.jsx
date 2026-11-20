import { useEffect, useState } from "react";
import { Activity, CreditCard, FileCheck2, History, RefreshCw, ShieldCheck, X } from "lucide-react";
import { fetchAdminMemberDossier } from "../services/adminApi.js";
import "../member-dossier.css";

const dateText = (value) => value ? new Date(value).toLocaleString("pt-MZ") : "—";
const boolText = (value) => value ? "Sim" : "Não";

function Stat({ label, value }) {
  return <div className="nk-dossier__stat"><strong>{value ?? "—"}</strong><span>{label}</span></div>;
}

function Row({ label, children }) {
  return <div className="nk-dossier__row"><dt>{label}</dt><dd>{children ?? "—"}</dd></div>;
}

export default function MemberDossier({ item, actions, onClose, onAction }) {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [section, setSection] = useState("overview");
  const memberId = item.id;

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setBusy(true);
    fetchAdminMemberDossier(memberId, { signal: controller.signal })
      .then((value) => { if (!controller.signal.aborted) setData(value); })
      .catch((e) => { if (!controller.signal.aborted) setError(e.message || "Erro ao carregar a ficha."); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, [memberId]);

  async function reload() {
    setBusy(true);
    setError("");
    try { setData(await fetchAdminMemberDossier(memberId)); }
    catch (e) { setError(e.message || "Erro ao atualizar a ficha."); }
    finally { setBusy(false); }
  }

  const m = data?.member, identity = data?.identity, a = data?.activity;
  const sections = [
    ["overview", "Resumo"], ["identity", "Identidade"], ["activity", "Atividade"],
    ["billing", "Planos e pagamentos"], ["audit", "Auditoria"],
  ];

  return <div className="nk-dossier__overlay" role="presentation">
    <button type="button" className="nk-dossier__backdrop" onClick={onClose} aria-label="Fechar ficha"/>
    <section role="dialog" aria-modal="true" aria-labelledby="nk-dossier-heading" className="nk-dossier">
      <header className="nk-dossier__header">
        <div><small>NKATA · Centro de gestão do membro</small><h2 id="nk-dossier-heading">{m?.name || item.name}</h2>
          <p>Ficha administrativa confidencial · Dados e operações do perfil</p></div>
        <div className="nk-dossier__tools">
          <button type="button" onClick={reload} disabled={busy} title="Atualizar"><RefreshCw size={18}/></button>
          <button type="button" onClick={onClose} aria-label="Fechar"><X size={20}/></button>
        </div>
      </header>
      {busy && !data && <div className="nk-dossier__state">A carregar ficha do membro...</div>}
      {error && <p role="alert" className="nk-dossier__error">{error}</p>}
      {data && <div className="nk-dossier__body">
        <aside className="nk-dossier__sidebar">
          {m.photo_url && <img src={m.photo_url} alt="" className="nk-dossier__avatar"/>}
          <strong>{m.name}</strong>
          <small>{m.city} · {m.age} anos</small>
          <span className="nk-dossier__status">{m.status_label} · {m.visible ? "Visível" : "Oculto"}</span>
          <nav aria-label="Secções da ficha">{sections.map(([key,label])=><button type="button" key={key} className={section === key ? "is-active" : ""} onClick={() => setSection(key)}>{label}</button>)}</nav>
        </aside>
        <div className="nk-dossier__main">
          {section === "overview" && <>
            <h3>Conta e perfil</h3>
            <dl className="nk-dossier__details">
              <Row label="Email">{m.email}</Row><Row label="Telefone">{m.phone}</Row>
              <Row label="Objetivo">{m.objective}</Row><Row label="Registo">{dateText(m.registered_at)}</Row>
              <Row label="Conta ativa">{boolText(m.account_active)}</Row><Row label="Perfil visível">{boolText(m.visible)}</Row>
              <Row label="Apresentação pública">{boolText(m.public_presentation_enabled)}</Row>
              <Row label="Foto pública aprovada">{boolText(m.public_photo_approved)}</Row>
            </dl>
            <h3>Informações de apresentação</h3>
            <div className="nk-dossier__text"><strong>Sobre si</strong><p>{m.about || "Não preenchido"}</p></div>
            <div className="nk-dossier__text"><strong>O que valoriza</strong><p>{m.values || "Não preenchido"}</p></div>
            <div className="nk-dossier__text"><strong>O que não aceita</strong><p>{m.boundaries || "Não preenchido"}</p></div>
          </>}
          {section === "identity" && <>
            <h3><ShieldCheck size={19}/> Estado de verificação</h3>
            <p className="nk-dossier__notice">A entrada aprovada não equivale ao NKATA ID confirmado. Documentos de identidade não são mostrados nesta ficha.</p>
            <dl className="nk-dossier__details">
              <Row label="Pedido de entrada">{identity.entry_status_label}</Row>
              <Row label="NKATA ID">{identity.nkata_id_label}</Row>
              <Row label="Capturas completas">{boolText(identity.captures_complete)}</Row>
              <Row label="Identidade confirmada">{boolText(identity.confirmed)}</Row>
              <Row label="Documento confirmado">{boolText(identity.document_confirmed)}</Row>
              <Row label="Risco registado">{identity.risk}</Row>
            </dl>
          </>}
          {section === "activity" && <>
            <h3><Activity size={19}/> Atividade da comunidade</h3>
            <div className="nk-dossier__stats">
              <Stat label="Matches" value={a.matches}/><Stat label="Matches ativos" value={a.active_matches}/>
              <Stat label="Interesses enviados" value={a.interests_sent}/><Stat label="Seguidores" value={a.followers}/>
              <Stat label="Mensagens enviadas" value={a.messages_sent}/><Stat label="Publicações" value={a.posts}/>
              <Stat label="Publicações pendentes" value={a.posts_pending}/><Stat label="Momentos" value={a.moments}/>
              <Stat label="Momentos pendentes" value={a.moments_pending}/>
              <Stat label="Denúncias pendentes" value={a.reports_pending}/>
              <Stat label="Denúncias totais" value={a.reports_total}/>
            </div>
            <p className="nk-dossier__notice">São apresentados indicadores agregados, não o conteúdo de mensagens privadas.</p>
          </>}
          {section === "billing" && <>
            <h3><CreditCard size={19}/> Plano e pagamentos</h3>
            <dl className="nk-dossier__details">
              <Row label="Plano">{data.subscription.label}</Row>
              <Row label="Início">{dateText(data.subscription.starts_at)}</Row>
              <Row label="Validade">{dateText(data.subscription.expires_at)}</Row>
              <Row label="Origem">{data.subscription.origin || "—"}</Row>
              <Row label="Pagamentos registados">{data.payments.total}</Row>
              <Row label="Pagamentos confirmados">{data.payments.successful}</Row>
            </dl>
            <h3>Últimas transações</h3>
            {!data.payments.recent.length ? <p>Sem pagamentos registados.</p> :
              <div className="nk-dossier__table-wrap"><table><thead><tr><th>Referência</th><th>Produto</th><th>Valor</th><th>Estado</th><th>Data</th></tr></thead>
              <tbody>{data.payments.recent.map(p=><tr key={p.reference}><td>{p.reference}</td><td>{p.product}</td><td>{p.amount} {p.currency}</td><td>{p.status}</td><td>{dateText(p.created_at)}</td></tr>)}</tbody></table></div>}
            <p className="nk-dossier__notice">Consulta apenas. Alterações de plano usam as ações administrativas com confirmação; pagamentos históricos nunca são modificados nesta ficha.</p>
          </>}
          {section === "audit" && <>
            <h3><History size={19}/> Histórico administrativo</h3>
            {!data.audit.length ? <p>Sem ações administrativas registadas para este perfil.</p> :
              <ol className="nk-dossier__audit">{data.audit.map((entry,i)=><li key={i}><strong>{entry.description || "Alteração administrativa"}</strong><small>{entry.operator} · {dateText(entry.date)}</small></li>)}</ol>}
            <p className="nk-dossier__notice">Esta área apresenta as últimas 15 ações registadas no perfil. Não representa um histórico completo de toda a atividade do membro.</p>
          </>}
        </div>
      </div>}
      <footer className="nk-dossier__footer">
        <div><strong>Ferramentas administrativas</strong><small>As ações exigem confirmação e permissões de membro.</small></div>
        <div className="nk-dossier__actions">{actions.map(action=>{
          const Icon=action.icon;
          return <button key={action.action} className={action.danger ? "is-danger" : ""} type="button" onClick={()=>onAction({...action,item,section:"members"})}><Icon size={15}/>{action.label}</button>;
        })}</div>
      </footer>
    </section>
  </div>;
}
