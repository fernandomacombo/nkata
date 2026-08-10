import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  Ban,
  BarChart3,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  Clock3,
  Copy,
  ExternalLink,
  FileCheck2,
  HeartHandshake,
  History,
  Image,
  LayoutDashboard,
  Loader2,
  MessageSquare,
  PauseCircle,
  Phone,
  PlayCircle,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  Users,
  Video,
  X,
} from "lucide-react";
import {
  fetchAdminList,
  fetchAdminSummary,
  performAdminAction,
} from "../services/adminApi.js";

const SECTIONS = [
  { id: "overview", label: "Visão geral", description: "Estado da comunidade", icon: LayoutDashboard },
  { id: "access", label: "Pedidos", description: "Entrada e verificação", icon: FileCheck2 },
  { id: "members", label: "Membros", description: "Contas e perfis", icon: Users },
  { id: "content", label: "Moderação", description: "Publicações e momentos", icon: ShieldCheck },
  { id: "reports", label: "Denúncias", description: "Segurança da comunidade", icon: ShieldAlert },
  { id: "operations", label: "Operações", description: "Matches e chamadas", icon: Activity },
  { id: "audit", label: "Auditoria", description: "Histórico administrativo", icon: History },
];

const FILTERS = {
  access: [
    ["", "Todos os estados"], ["PENDENTE", "Pendente"], ["EM_ANALISE", "Em análise"],
    ["PRECISA_CORRIGIR", "Precisa corrigir"], ["APROVADO", "Aprovado"],
    ["RECUSADO", "Recusado"], ["BLOQUEADO", "Bloqueado"],
  ],
  members: [
    ["", "Todos os estados"], ["ATIVO", "Ativo"], ["PAUSADO", "Pausado"],
    ["BLOQUEADO", "Bloqueado"],
  ],
  content: [
    ["", "Todos os estados"], ["PENDENTE", "Pendente"],
    ["APROVADO", "Aprovado"], ["REJEITADO", "Rejeitado"],
  ],
  reports: [["PENDENTE", "Pendentes"], ["ANALISADA", "Analisadas"], ["", "Todas"]],
  operations: [
    ["", "Todos os estados"], ["ATIVA", "Ativa"], ["TERMINADA", "Terminada"],
    ["PERDIDA", "Não atendida"], ["FALHOU", "Falhou"],
  ],
  audit: [
    ["", "Todas as ações"], ["CRIACAO", "Criações"],
    ["ALTERACAO", "Alterações"], ["REMOCAO", "Remoções"],
  ],
};

const METRICS = [
  { key: "members_total", label: "Membros", detailKey: "members_new_7d", detailSuffix: " novos esta semana", icon: Users },
  { key: "access_pending", label: "Pedidos por tratar", icon: FileCheck2 },
  { key: "content_pending", label: "Conteúdos pendentes", icon: ShieldCheck },
  { key: "reports_pending", label: "Denúncias pendentes", icon: ShieldAlert },
  { key: "matches_active", label: "Matches ativos", icon: HeartHandshake },
  { key: "calls_today", label: "Chamadas hoje", icon: Phone },
];

function formatDate(value, includeTime = true) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("pt-PT", {
    day: "2-digit",
    month: "short",
    ...(includeTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(date);
}

function formatDuration(seconds = 0) {
  const value = Math.max(0, Number(seconds) || 0);
  if (!value) return "Sem duração";
  const minutes = Math.floor(value / 60);
  const remaining = value % 60;
  return minutes ? `${minutes} min ${remaining}s` : `${remaining}s`;
}

async function copyText(value) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const field = document.createElement("textarea");
  field.value = value;
  field.setAttribute("readonly", "");
  field.style.position = "fixed";
  field.style.opacity = "0";
  document.body.appendChild(field);
  field.select();
  try {
    if (!document.execCommand("copy")) throw new Error("copy_failed");
  } finally {
    document.body.removeChild(field);
  }
}

function statusTone(status = "") {
  const value = String(status).toUpperCase();
  if (["ATIVO", "ATIVA", "APROVADO", "TERMINADA", "ANALISADA", "BAIXO", "CRIACAO"].includes(value)) return "positive";
  if (["BLOQUEADO", "REJEITADO", "FALHOU", "CRITICO", "ALTO", "REMOCAO"].includes(value)) return "danger";
  if (["PENDENTE", "EM_ANALISE", "CHAMANDO", "CONECTANDO", "MEDIO"].includes(value)) return "warning";
  return "neutral";
}

function StatusBadge({ status, label }) {
  return <span className={`nk-admin-status is-${statusTone(status)}`}>{label || status || "—"}</span>;
}

function EmptyState({ loading, error, onRetry }) {
  if (loading) {
    return (
      <div className="nk-admin-empty">
        <Loader2 className="nk-spin" size={25} />
        <strong>A atualizar o painel</strong>
        <span>A reunir informação da comunidade.</span>
      </div>
    );
  }
  return (
    <div className="nk-admin-empty">
      {error ? <CircleAlert size={28} /> : <CheckCircle2 size={28} />}
      <strong>{error ? "Não foi possível carregar" : "Nenhum registo encontrado"}</strong>
      <span>{error || "Não existem itens para os filtros selecionados."}</span>
      {error && <button type="button" onClick={onRetry}><RefreshCw size={16} /> Tentar novamente</button>}
    </div>
  );
}

function ActionDialog({ pending, busy, onClose, onConfirm }) {
  const [note, setNote] = useState("");
  if (!pending) return null;
  return (
    <div className="nk-admin-dialog-layer" role="presentation">
      <button type="button" className="nk-admin-dialog-backdrop" onClick={onClose} aria-label="Fechar" />
      <section className="nk-admin-dialog" role="dialog" aria-modal="true" aria-labelledby="admin-action-title">
        <header>
          <span className={pending.danger ? "is-danger" : ""}>
            {pending.danger ? <ShieldAlert size={22} /> : <ShieldCheck size={22} />}
          </span>
          <button type="button" onClick={onClose} aria-label="Fechar"><X size={19} /></button>
        </header>
        <div>
          <small>Confirmar ação administrativa</small>
          <h2 id="admin-action-title">{pending.label}</h2>
          <p>{pending.description}</p>
          {pending.acceptsNote && (
            <label>
              <span>Observação interna {pending.noteRequired ? "" : "(opcional)"}</span>
              <textarea
                rows="3"
                value={note}
                maxLength="240"
                placeholder="Indique o motivo para a equipa..."
                onChange={(event) => setNote(event.target.value)}
              />
            </label>
          )}
        </div>
        <footer>
          <button type="button" className="nk-admin-button is-quiet" onClick={onClose} disabled={busy}>Cancelar</button>
          <button
            type="button"
            className={`nk-admin-button ${pending.danger ? "is-danger" : "is-primary"}`}
            onClick={() => onConfirm(note)}
            disabled={busy || (pending.noteRequired && !note.trim())}
          >
            {busy ? <Loader2 className="nk-spin" size={17} /> : <Check size={17} />}
            Confirmar
          </button>
        </footer>
      </section>
    </div>
  );
}

function Overview({ summary, loading, error, onRetry, onOpenSection }) {
  if (!summary) return <EmptyState loading={loading} error={error} onRetry={onRetry} />;
  const maxActivity = Math.max(
    1,
    ...summary.activity.map((point) => point.members + point.matches + point.messages),
  );
  return (
    <div className="nk-admin-overview">
      <section className="nk-admin-metrics" aria-label="Indicadores principais">
        {METRICS.map((metric) => {
          const Icon = metric.icon;
          const count = Number(summary.metrics?.[metric.key] || 0);
          return (
            <article key={metric.key}>
              <header><span><Icon size={19} /></span><small>{metric.label}</small></header>
              <strong>{count.toLocaleString("pt-PT")}</strong>
              <p>
                {metric.detailKey
                  ? `${summary.metrics?.[metric.detailKey] || 0}${metric.detailSuffix}`
                  : count > 0 ? "Requer acompanhamento" : "Sem pendências agora"}
              </p>
            </article>
          );
        })}
      </section>

      <div className="nk-admin-overview-grid">
        <section className="nk-admin-card nk-admin-activity-card">
          <header className="nk-admin-card-title">
            <div><small>Últimos sete dias</small><h2>Atividade da comunidade</h2></div>
            <BarChart3 size={21} />
          </header>
          <div className="nk-admin-chart" aria-label="Atividade nos últimos sete dias">
            {summary.activity.map((point) => {
              const total = point.members + point.matches + point.messages;
              return (
                <div key={point.date} className="nk-admin-chart__column" title={`${total} atividades`}>
                  <span className="nk-admin-chart__value">{total}</span>
                  <div><i style={{ height: `${Math.max(8, (total / maxActivity) * 100)}%` }} /></div>
                  <small>{formatDate(`${point.date}T12:00:00`, false).split(" ")[0]}</small>
                </div>
              );
            })}
          </div>
          <footer>
            <span><i className="is-members" /> Novos membros</span>
            <span><i className="is-matches" /> Matches</span>
            <span><i className="is-messages" /> Mensagens</span>
          </footer>
        </section>

        <section className="nk-admin-card nk-admin-system-card">
          <header className="nk-admin-card-title">
            <div><small>Infraestrutura</small><h2>Estado do sistema</h2></div>
            <Activity size={21} />
          </header>
          <ul>
            <li>
              <span><strong>Base de dados</strong><small>Ligação principal</small></span>
              <StatusBadge status={summary.system.database_ready ? "ATIVO" : "FALHOU"} label={summary.system.database_ready ? "Operacional" : "Indisponível"} />
            </li>
            <li>
              <span><strong>Chamadas móveis</strong><small>Servidor TURN</small></span>
              <StatusBadge status={summary.system.turn_configured ? "ATIVO" : "PENDENTE"} label={summary.system.turn_configured ? "Configurado" : "Por configurar"} />
            </li>
            <li>
              <span><strong>Moderação</strong><small>{summary.system.moderation_provider}</small></span>
              <StatusBadge status={summary.system.moderation_automatic ? "ATIVO" : "PENDENTE"} label={summary.system.moderation_automatic ? "Automática" : "Revisão humana"} />
            </li>
            <li>
              <span><strong>Ambiente</strong><small>Configuração ativa</small></span>
              <StatusBadge status="NEUTRAL" label={summary.system.environment} />
            </li>
          </ul>
        </section>
      </div>

      <section className="nk-admin-priorities">
        <header className="nk-admin-card-title">
          <div><small>Fila de trabalho</small><h2>Prioridades da equipa</h2></div>
          <Clock3 size={21} />
        </header>
        <div>
          {[
            ["access", "Pedidos de entrada", summary.metrics.access_pending, "Rever identidade e elegibilidade"],
            ["content", "Conteúdo pendente", summary.metrics.content_pending, "Aprovar antes de aparecer no feed"],
            ["reports", "Denúncias abertas", summary.metrics.reports_pending, "Proteger rapidamente a comunidade"],
          ].map(([id, label, count, detail]) => (
            <button type="button" key={id} onClick={() => onOpenSection(id)}>
              <span>{Number(count || 0)}</span>
              <div><strong>{label}</strong><small>{detail}</small></div>
              <ChevronRight size={18} />
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

function MediaThumb({ item }) {
  if (item.operation_type === "CALL") {
    const CallIcon = item.call_type === "VIDEO" ? Video : Phone;
    return <span className="nk-admin-thumb is-operation"><CallIcon size={20} /></span>;
  }
  if (item.operation_type === "MATCH") {
    return <span className="nk-admin-thumb is-operation"><HeartHandshake size={20} /></span>;
  }
  if (item.operation_type === "AUDIT") {
    return <span className="nk-admin-thumb is-operation"><History size={20} /></span>;
  }
  if (!item.photo_url && !item.media_url) {
    return <span className="nk-admin-thumb is-empty"><Image size={19} /></span>;
  }
  const source = item.photo_url || item.media_url;
  if (item.media_type === "VIDEO") {
    return <span className="nk-admin-thumb is-video"><PlayCircle size={20} /></span>;
  }
  return <img className="nk-admin-thumb" src={source} alt="" loading="lazy" />;
}

function actionsFor(section, item) {
  if (section === "access") {
    const review = { action: "review", label: "Analisar", description: `Colocar o pedido de ${item.name} em análise.`, icon: Clock3 };
    const approve = { action: "approve", label: "Aprovar", description: `Aprovar o pedido de ${item.name} e libertar o questionário.`, icon: UserCheck };
    const correction = { action: "correction", label: "Pedir correção", description: `Devolver o pedido de ${item.name} para correção.`, acceptsNote: true, noteRequired: true, icon: CircleAlert };
    const reject = { action: "reject", label: "Recusar", description: `Recusar o pedido de ${item.name}. O perfil associado ficará oculto.`, acceptsNote: true, danger: true, icon: Ban };
    if (item.status === "PENDENTE") return [review, approve, correction];
    if (item.status === "EM_ANALISE") return [approve, correction, reject];
    if (item.status === "PRECISA_CORRIGIR") return [review, approve, reject];
    if (["RECUSADO", "BLOQUEADO"].includes(item.status)) return [review];
    return [];
  }
  if (section === "members") {
    return [
      item.status !== "ATIVO" && { action: "activate", label: "Ativar", description: `Ativar ${item.name} e tornar o perfil visível.`, icon: PlayCircle },
      item.status === "ATIVO" && { action: "pause", label: "Pausar", description: `Retirar temporariamente ${item.name} da descoberta.`, icon: PauseCircle },
      item.status !== "BLOQUEADO" && { action: "block", label: "Bloquear", description: `Bloquear ${item.name} e desativar o acesso à conta.`, danger: true, icon: Ban },
    ].filter(Boolean);
  }
  if (section === "content") {
    return [
      item.status !== "APROVADO" && { action: "approve", label: "Aprovar", description: `Aprovar esta ${item.content_label.toLowerCase()} de ${item.author}.`, icon: CheckCircle2 },
      item.status !== "REJEITADO" && { action: "reject", label: "Rejeitar", description: "Retirar este conteúdo da comunidade.", acceptsNote: true, icon: Ban },
      { action: "severe", label: "Violação grave", description: "Rejeitar o conteúdo e pausar o perfil para revisão.", acceptsNote: true, danger: true, icon: ShieldAlert },
    ].filter(Boolean);
  }
  if (section === "reports") {
    const profile = item.report_type === "PERFIL";
    return [
      item.status !== "ANALISADA" && { action: "resolve", label: "Concluir", description: "Marcar a denúncia como analisada, sem outra intervenção.", icon: CheckCircle2 },
      item.status !== "ANALISADA" && { action: profile ? "pause" : "remove", label: profile ? "Pausar perfil" : "Retirar publicação", description: profile ? "Concluir a denúncia e ocultar temporariamente o perfil." : "Concluir a denúncia e retirar a publicação.", danger: true, icon: PauseCircle },
      item.status !== "ANALISADA" && { action: profile ? "block" : "severe", label: profile ? "Bloquear membro" : "Violação grave", description: profile ? "Concluir a denúncia e desativar a conta do membro." : "Retirar a publicação e pausar o respetivo perfil.", danger: true, icon: Ban },
    ].filter(Boolean);
  }
  if (section === "operations" && item.operation_type === "MATCH") {
    return [item.status === "ATIVO"
      ? { action: "close", label: "Encerrar", description: `Encerrar o match entre ${item.title}.`, danger: true, icon: Ban }
      : { action: "reopen", label: "Reativar", description: `Reativar o match entre ${item.title}.`, icon: PlayCircle }];
  }
  return [];
}

function AdminRow({ section, item, onAction, onCopyQuestionnaire }) {
  const actions = actionsFor(section, item);
  const title = item.name || item.author || item.target || item.title;
  const subtitle = section === "access"
    ? `${item.email} · ${item.city}`
    : section === "members"
      ? `${item.email} · ${item.city}`
      : section === "content"
        ? `${item.content_label} · ${item.media_type}`
        : section === "reports"
          ? `${item.report_label} · ${item.reason}`
          : section === "audit"
            ? item.object_type
          : item.detail;
  const status = item.status;
  const statusLabel = item.status_label || (status === "ANALISADA" ? "Analisada" : status === "PENDENTE" ? "Pendente" : status);
  return (
    <article className="nk-admin-row">
      <MediaThumb item={item} />
      <div className="nk-admin-row__identity">
        <div><strong>{title}</strong><StatusBadge status={status} label={statusLabel} /></div>
        <span>{subtitle}</span>
        {section === "content" && item.text && <p>{item.text}</p>}
        {section === "reports" && item.details && <p>{item.details}</p>}
        {section === "audit" && item.detail && <p>{item.detail}</p>}
      </div>
      <div className="nk-admin-row__meta">
        {section === "access" && <><span>{item.age} anos · {item.gender_label}</span><small>{item.has_questionnaire ? "Questionário concluído" : "Aguardando questionário"}</small></>}
        {section === "members" && <><span>{item.age} anos · {item.visible ? "Visível" : "Oculto"}</span><small>{item.pending_reports ? `${item.pending_reports} denúncia(s) pendente(s)` : "Sem denúncias pendentes"}</small></>}
        {section === "content" && <><span>Risco: {item.risk_label}</span><small>{item.visibility_label}</small></>}
        {section === "reports" && <><span>Por {item.reporter}</span><small>{formatDate(item.created_at)}</small></>}
        {section === "operations" && item.operation_type === "CALL" && (
          <>
            <span>Iniciada por {item.initiator}</span>
            <small>
              {item.connected ? `${formatDuration(item.duration_seconds)} · ` : ""}
              {formatDate(item.created_at)}
            </small>
          </>
        )}
        {section === "operations" && item.operation_type === "MATCH" && <><span>{item.detail}</span><small>Atualizado {formatDate(item.updated_at)}</small></>}
        {section === "audit" && <><span>Por {item.operator}</span><small>{formatDate(item.created_at)}</small></>}
        {!['reports', 'operations', 'audit'].includes(section) && <small>{formatDate(item.created_at)}</small>}
      </div>
      <div className="nk-admin-row__actions">
        {section === "access" && item.questionnaire_path && (
          <button
            type="button"
            onClick={() => onCopyQuestionnaire(item)}
            title="Copiar link do questionário"
          >
            <Copy size={16} /><span>Copiar link</span>
          </button>
        )}
        {actions.slice(0, 3).map((action) => {
          const Icon = action.icon;
          return (
            <button
              type="button"
              key={action.action}
              className={action.danger ? "is-danger" : ""}
              onClick={() => onAction({ ...action, item, section })}
              title={action.label}
            >
              <Icon size={16} /><span>{action.label}</span>
            </button>
          );
        })}
        {item.admin_url && (
          <a href={item.admin_url} target="_blank" rel="noreferrer" title="Abrir ficha técnica">
            <ExternalLink size={16} /><span>Detalhes</span>
          </a>
        )}
      </div>
    </article>
  );
}

export default function AdminPanelPage({ session }) {
  const [activeSection, setActiveSection] = useState("overview");
  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState("");
  const [listData, setListData] = useState({ total: 0, results: [] });
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState("");
  const [draftQuery, setDraftQuery] = useState("");
  const [filters, setFilters] = useState({ query: "", status: "", kind: "" });
  const [pendingAction, setPendingAction] = useState(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [toast, setToast] = useState("");

  const loadSummary = useCallback(async ({ signal } = {}) => {
    setSummaryLoading(true);
    setSummaryError("");
    try {
      setSummary(await fetchAdminSummary({ signal }));
    } catch (error) {
      if (error.name !== "AbortError") setSummaryError(error.message || "Não foi possível carregar o resumo.");
    } finally {
      if (!signal?.aborted) setSummaryLoading(false);
    }
  }, []);

  const loadList = useCallback(async ({ signal } = {}) => {
    if (activeSection === "overview") return;
    setListLoading(true);
    setListError("");
    try {
      const payload = await fetchAdminList({ section: activeSection, ...filters, signal });
      setListData(payload || { total: 0, results: [] });
    } catch (error) {
      if (error.name !== "AbortError") setListError(error.message || "Não foi possível carregar esta área.");
    } finally {
      if (!signal?.aborted) setListLoading(false);
    }
  }, [activeSection, filters]);

  useEffect(() => {
    const controller = new AbortController();
    loadSummary({ signal: controller.signal });
    return () => controller.abort();
  }, [loadSummary]);

  useEffect(() => {
    if (activeSection === "overview") return undefined;
    const controller = new AbortController();
    loadList({ signal: controller.signal });
    return () => controller.abort();
  }, [activeSection, loadList]);

  useEffect(() => {
    setDraftQuery("");
    setFilters({
      query: "",
      status: activeSection === "reports" ? "PENDENTE" : "",
      kind: activeSection === "operations" ? "CALLS" : "",
    });
  }, [activeSection]);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 3500);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const selectedSection = useMemo(
    () => SECTIONS.find((section) => section.id === activeSection) || SECTIONS[0],
    [activeSection],
  );

  const submitSearch = (event) => {
    event.preventDefault();
    setFilters((current) => ({ ...current, query: draftQuery.trim() }));
  };

  const openAction = (action) => setPendingAction(action);

  const copyQuestionnaire = async (item) => {
    try {
      const url = new URL(item.questionnaire_path, window.location.origin).toString();
      await copyText(url);
      setToast(`Link do questionário de ${item.name} copiado.`);
    } catch {
      setToast("Não foi possível copiar o link do questionário.");
    }
  };

  const confirmAction = async (note) => {
    if (!pendingAction) return;
    const { section, item, action } = pendingAction;
    const resourceMap = {
      access: "access",
      members: "member",
      content: "content",
      reports: "report",
      operations: "match",
    };
    setActionBusy(true);
    try {
      const result = await performAdminAction({
        resource: resourceMap[section],
        action,
        id: item.id,
        note: note.trim(),
        content_type: item.content_type,
        report_type: item.report_type,
      });
      setPendingAction(null);
      setToast(result.message || "Alteração concluída.");
      await Promise.all([loadList(), loadSummary()]);
    } catch (error) {
      setToast(error.message || "Não foi possível concluir a alteração.");
    } finally {
      setActionBusy(false);
    }
  };

  return (
    <main className="nk-admin-page">
      <div className="nk-admin-shell">
        <header className="nk-admin-hero">
          <div>
            <span><ShieldCheck size={16} /> Central de operações</span>
            <h1>Painel NKATA</h1>
            <p>Administração, segurança e saúde da comunidade num único lugar.</p>
          </div>
          <div className="nk-admin-hero__operator">
            <span>{(session?.user?.name || "A").slice(0, 1).toUpperCase()}</span>
            <div><small>Operador autenticado</small><strong>{session?.user?.name || session?.user?.email}</strong></div>
            <ShieldCheck size={18} />
          </div>
        </header>

        <div className="nk-admin-layout">
          <aside className="nk-admin-sidebar">
            <nav aria-label="Áreas administrativas">
              {SECTIONS.map((section) => {
                const Icon = section.icon;
                const active = section.id === activeSection;
                const badge = section.id === "access" ? summary?.metrics?.access_pending
                  : section.id === "content" ? summary?.metrics?.content_pending
                    : section.id === "reports" ? summary?.metrics?.reports_pending : 0;
                return (
                  <button type="button" key={section.id} className={active ? "is-active" : ""} onClick={() => setActiveSection(section.id)}>
                    <span><Icon size={18} /></span>
                    <div><strong>{section.label}</strong><small>{section.description}</small></div>
                    {badge > 0 ? <em>{badge > 99 ? "99+" : badge}</em> : <ChevronRight size={16} />}
                  </button>
                );
              })}
            </nav>
            <footer>
              <ShieldCheck size={17} />
              <div><strong>Acesso restrito</strong><small>Ações ficam registadas</small></div>
            </footer>
          </aside>

          <section className="nk-admin-content">
            {activeSection === "overview" ? (
              <Overview
                summary={summary}
                loading={summaryLoading}
                error={summaryError}
                onRetry={() => loadSummary()}
                onOpenSection={setActiveSection}
              />
            ) : (
              <>
                <header className="nk-admin-section-header">
                  <div><small>Gestão operacional</small><h2>{selectedSection.label}</h2><p>{selectedSection.description}</p></div>
                  <button type="button" onClick={() => loadList()} disabled={listLoading} title="Atualizar">
                    <RefreshCw className={listLoading ? "nk-spin" : ""} size={18} />
                  </button>
                </header>

                <form className="nk-admin-filters" onSubmit={submitSearch}>
                  <label>
                    <Search size={17} />
                    <input value={draftQuery} onChange={(event) => setDraftQuery(event.target.value)} placeholder="Pesquisar por nome, email ou cidade" />
                    {draftQuery && <button type="button" onClick={() => { setDraftQuery(""); setFilters((current) => ({ ...current, query: "" })); }} aria-label="Limpar pesquisa"><X size={16} /></button>}
                  </label>
                  {activeSection === "content" && (
                    <select value={filters.kind} onChange={(event) => setFilters((current) => ({ ...current, kind: event.target.value }))} aria-label="Tipo de conteúdo">
                      <option value="">Publicações e momentos</option><option value="PUBLICACAO">Publicações</option><option value="MOMENTO">Momentos</option>
                    </select>
                  )}
                  {activeSection === "operations" && (
                    <select value={filters.kind} onChange={(event) => setFilters((current) => ({ ...current, kind: event.target.value, status: "" }))} aria-label="Tipo de operação">
                      <option value="CALLS">Chamadas</option><option value="MATCHES">Matches</option>
                    </select>
                  )}
                  <select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))} aria-label="Estado">
                    {(activeSection === "operations" && filters.kind === "MATCHES"
                      ? [["", "Todos os estados"], ["ATIVO", "Ativo"], ["ENCERRADO", "Encerrado"]]
                      : FILTERS[activeSection] || []).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
                  </select>
                  <button type="submit" className="nk-admin-button is-primary"><Search size={16} /> Pesquisar</button>
                </form>

                <div className="nk-admin-list-heading">
                  <span>{listData.total || 0} registo(s)</span>
                  <small>Mostrando até 50 resultados recentes</small>
                </div>

                <div className="nk-admin-list">
                  {listData.results?.length && !listLoading
                    ? listData.results.map((item) => (
                      <AdminRow
                        key={`${item.content_type || item.report_type || item.operation_type || activeSection}-${item.id}`}
                        section={activeSection}
                        item={item}
                        onAction={openAction}
                        onCopyQuestionnaire={copyQuestionnaire}
                      />
                    ))
                    : <EmptyState loading={listLoading} error={listError} onRetry={() => loadList()} />}
                </div>
              </>
            )}
          </section>
        </div>
      </div>

      {toast && <div className="nk-admin-toast" role="status"><CheckCircle2 size={18} />{toast}</div>}
      <ActionDialog pending={pendingAction} busy={actionBusy} onClose={() => !actionBusy && setPendingAction(null)} onConfirm={confirmAction} />
    </main>
  );
}
