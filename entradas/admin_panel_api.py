from datetime import timedelta

from django.conf import settings
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db import connection, transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .call_models import ChamadaMatchNKATA
from .content_moderation_models import AnaliseAutomaticaConteudoNKATA
from .content_moderation_service import moderation_provider_label, record_human_decision
from .identity_models import nkata_id_expires_at
from .models import (
    DenunciaPerfil,
    MatchPerfil,
    MensagemMatch,
    PedidoEntrada,
    PerfilNKATA,
)
from .moments_models import MOMENT_LIFETIME_HOURS, MomentoNKATA
from .post_safety_models import DenunciaPublicacaoNKATA
from .posts_models import PublicacaoNKATA
from .profile_media_api import profile_photo_url
from .webrtc_credentials import turn_is_configured


SECTION_LIMIT = 50
CONTENT_TYPES = {
    "PUBLICACAO": PublicacaoNKATA,
    "MOMENTO": MomentoNKATA,
}
AUDIT_ACTIONS = {
    1: ("CRIACAO", "Criação"),
    2: ("ALTERACAO", "Alteração"),
    3: ("REMOCAO", "Remoção"),
}

PROFILE_MEDIA_LABELS = (
    ("foto_perfil", "Fotografia principal"),
    ("foto_extra_1", "Fotografia 2"),
    ("foto_extra_2", "Fotografia 3"),
    ("foto_extra_3", "Fotografia 4"),
)
LEGACY_IDENTITY_MEDIA_LABELS = (
    ("bi_frente", "BI — frente"),
    ("bi_verso", "BI — verso"),
    ("selfie_com_bi", "Selfie com BI"),
)
NKATA_ID_MEDIA_LABELS = (
    ("bi_frente", "BI — frente"),
    ("bi_verso", "BI — verso"),
    ("selfie_ao_vivo", "Selfie frontal"),
    ("selfie_desafio", "Selfie do desafio"),
)
CAPTURE_CHECK_LABELS = {
    "bi_frente": "BI — frente",
    "bi_verso": "BI — verso",
    "selfie_ao_vivo": "Selfie frontal",
    "selfie_desafio": "Selfie do desafio",
}


def _safe_limit(request):
    try:
        return min(max(int(request.query_params.get("limit", 30)), 1), SECTION_LIMIT)
    except (TypeError, ValueError):
        return 30


def _audit(user, obj, message):
    try:
        LogEntry.objects.create(
            user_id=user.pk,
            content_type_id=ContentType.objects.get_for_model(
                obj,
                for_concrete_model=False,
            ).pk,
            object_id=str(obj.pk),
            object_repr=str(obj)[:200],
            action_flag=CHANGE,
            change_message=str(message)[:1000],
        )
    except Exception:
        # A ação administrativa não deve falhar apenas porque o registo de
        # auditoria ficou temporariamente indisponível.
        pass


def _database_ready():
    try:
        connection.ensure_connection()
        return connection.is_usable()
    except Exception:
        return False


def _daily_activity(days=7):
    today = timezone.localdate()
    points = []
    for offset in reversed(range(days)):
        day = today - timedelta(days=offset)
        points.append({
            "date": day.isoformat(),
            "members": PerfilNKATA.objects.filter(criado_em__date=day).count(),
            "matches": MatchPerfil.objects.filter(criado_em__date=day).count(),
            "messages": MensagemMatch.objects.filter(criado_em__date=day).count(),
        })
    return points


def _summary_payload():
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    today = timezone.localdate()
    calls_today = ChamadaMatchNKATA.objects.filter(criada_em__date=today)
    pending_posts = PublicacaoNKATA.objects.filter(moderacao_status="PENDENTE").count()
    pending_moments = MomentoNKATA.objects.filter(moderacao_status="PENDENTE").count()
    pending_profile_reports = DenunciaPerfil.objects.filter(analisada=False).count()
    pending_post_reports = DenunciaPublicacaoNKATA.objects.filter(estado="PENDENTE").count()

    return {
        "metrics": {
            "members_total": PerfilNKATA.objects.count(),
            "members_active": PerfilNKATA.objects.filter(status="ATIVO").count(),
            "members_new_7d": PerfilNKATA.objects.filter(criado_em__gte=week_ago).count(),
            "access_pending": PedidoEntrada.objects.filter(
                Q(status__in=["PENDENTE", "EM_ANALISE", "PRECISA_CORRIGIR"])
                | (
                    Q(status="APROVADO", verificacao_identidade__isnull=False)
                    & ~Q(verificacao_identidade__status="APROVADA")
                )
            ).distinct().count(),
            "content_pending": pending_posts + pending_moments,
            "reports_pending": pending_profile_reports + pending_post_reports,
            "matches_active": MatchPerfil.objects.filter(status="ATIVO").count(),
            "calls_today": calls_today.count(),
            "calls_missed_7d": ChamadaMatchNKATA.objects.filter(
                estado="PERDIDA",
                criada_em__gte=week_ago,
            ).count(),
            "messages_24h": MensagemMatch.objects.filter(
                criado_em__gte=now - timedelta(hours=24)
            ).count(),
        },
        "system": {
            "database_ready": _database_ready(),
            "turn_configured": turn_is_configured(),
            "moderation_provider": moderation_provider_label(),
            "moderation_automatic": bool(
                str(getattr(settings, "NKATA_MEDIA_MODERATION_PROVIDER", "manual")).lower()
                != "manual"
            ),
            "environment": "Desenvolvimento" if settings.DEBUG else "Produção",
        },
        "activity": _daily_activity(),
    }


def _member_rows(request, limit):
    query = str(request.query_params.get("q", "")).strip()
    status_filter = str(request.query_params.get("status", "")).strip().upper()
    queryset = (
        PerfilNKATA.objects
        .select_related("pedido", "usuario")
        .annotate(report_count=Count("denuncias", filter=Q(denuncias__analisada=False)))
        .order_by("-criado_em")
    )
    if query:
        queryset = queryset.filter(
            Q(nome_publico__icontains=query)
            | Q(cidade__icontains=query)
            | Q(pedido__email__icontains=query)
            | Q(pedido__telefone__icontains=query)
        )
    if status_filter in {value for value, _label in PerfilNKATA.STATUS_CHOICES}:
        queryset = queryset.filter(status=status_filter)

    total = queryset.count()
    results = []
    for profile in queryset[:limit]:
        results.append({
            "id": profile.id,
            "name": profile.nome_publico,
            "email": profile.pedido.email,
            "phone": profile.pedido.telefone,
            "city": profile.cidade,
            "age": profile.idade,
            "gender_label": profile.get_genero_display(),
            "objective_label": profile.get_objetivo_display(),
            "status": profile.status,
            "status_label": profile.get_status_display(),
            "visible": profile.visivel,
            "verified": profile.pedido.status == "APROVADO",
            "account_active": bool(profile.usuario and profile.usuario.is_active),
            "pending_reports": profile.report_count,
            "photo_url": profile_photo_url(profile),
            "created_at": profile.criado_em,
            "admin_url": f"/admin/entradas/perfilnkata/{profile.id}/change/",
        })
    return {"total": total, "results": results}


def _access_rows(request, limit):
    query = str(request.query_params.get("q", "")).strip()
    status_filter = str(request.query_params.get("status", "")).strip().upper()
    queryset = (
        PedidoEntrada.objects
        .select_related("perfil__usuario", "questionario", "verificacao_identidade")
        .order_by("-criado_em")
    )
    if query:
        queryset = queryset.filter(
            Q(nome_completo__icontains=query)
            | Q(email__icontains=query)
            | Q(telefone__icontains=query)
            | Q(cidade__icontains=query)
        )
    valid_statuses = {value for value, _label in PedidoEntrada.STATUS_CHOICES}
    identity_review = (
        Q(status="APROVADO", verificacao_identidade__isnull=False)
        & ~Q(verificacao_identidade__status="APROVADA")
    )
    if status_filter == "EM_ANALISE":
        queryset = queryset.filter(Q(status="EM_ANALISE") | identity_review)
    elif status_filter == "APROVADO":
        queryset = queryset.filter(status="APROVADO").filter(
            Q(verificacao_identidade__isnull=True)
            | Q(verificacao_identidade__status="APROVADA")
        )
    elif status_filter in valid_statuses:
        queryset = queryset.filter(status=status_filter)

    total = queryset.count()
    results = []
    for item in queryset[:limit]:
        profile = getattr(item, "perfil", None)
        verification = getattr(item, "verificacao_identidade", None)
        has_questionnaire = hasattr(item, "questionario")
        identity_pending = bool(
            item.status == "APROVADO"
            and verification
            and verification.status != "APROVADA"
        )
        results.append({
            "id": item.id,
            "name": item.nome_completo,
            "email": item.email,
            "phone": item.telefone,
            "city": item.cidade,
            "age": item.idade,
            "gender_label": item.get_genero_display(),
            "objective_label": item.get_objetivo_display(),
            "status": item.status,
            "status_label": item.get_status_display(),
            "display_status": "EM_ANALISE" if identity_pending else item.status,
            "display_status_label": (
                "Identidade pendente" if identity_pending else item.get_status_display()
            ),
            "accepted_verification": item.aceita_verificacao,
            "has_questionnaire": has_questionnaire,
            "questionnaire_path": (
                f"/questionario/{item.token}/"
                if item.status == "APROVADO" and not has_questionnaire and not identity_pending
                else ""
            ),
            "has_profile": bool(profile),
            "has_password": bool(
                profile and profile.usuario and profile.usuario.has_usable_password()
            ),
            "note": item.observacao_admin,
            "identity_status": verification.status if verification else "LEGADO",
            "identity_status_label": (
                verification.get_status_display() if verification else "Verificação anterior"
            ),
            "identity_ready": (
                verification.capturas_completas
                if verification
                else all(bool(getattr(item, field)) for field, _label in LEGACY_IDENTITY_MEDIA_LABELS)
            ),
            "photo_url": f"/api/admin/pedidos/{item.id}/media/foto_perfil/",
            "created_at": item.criado_em,
            "admin_url": f"/admin/entradas/pedidoentrada/{item.id}/change/",
        })
    return {"total": total, "results": results}


def _media_item(owner, field_name, label, url):
    available = bool(getattr(owner, field_name, None))
    return {
        "key": field_name,
        "label": label,
        "available": available,
        "url": url if available else "",
    }


def _quality_checks(verification):
    results = []
    raw_checks = verification.verificacoes_imagem or {}
    for field_name, label in CAPTURE_CHECK_LABELS.items():
        value = raw_checks.get(field_name) or {}
        results.append({
            "key": field_name,
            "label": label,
            "available": bool(getattr(verification, field_name, None)),
            "accepted": bool(value.get("accepted")),
            "score": value.get("score"),
        })
    return results


def _access_detail_payload(item):
    verification = getattr(item, "verificacao_identidade", None)
    profile_media = [
        _media_item(
            item,
            field_name,
            label,
            f"/api/admin/pedidos/{item.id}/media/{field_name}/",
        )
        for field_name, label in PROFILE_MEDIA_LABELS
    ]

    if verification:
        identity_media = [
            _media_item(
                verification,
                field_name,
                label,
                f"/api/admin/nkata-id/{verification.id}/media/{field_name}/",
            )
            for field_name, label in NKATA_ID_MEDIA_LABELS
        ]
        identity = {
            "mode": "NKATA_ID",
            "id": verification.id,
            "status": verification.status,
            "status_label": verification.get_status_display(),
            "risk": verification.risco,
            "risk_label": verification.get_risco_display(),
            "risk_score": verification.pontuacao_risco,
            "captures_complete": verification.capturas_completas,
            "liveness_confirmed": verification.vivacidade_confirmada,
            "face_similarity": verification.correspondencia_facial,
            "face_comparison_available": verification.correspondencia_facial is not None,
            "checks": _quality_checks(verification),
        }
    else:
        identity_media = [
            _media_item(
                item,
                field_name,
                label,
                f"/api/admin/pedidos/{item.id}/media/{field_name}/",
            )
            for field_name, label in LEGACY_IDENTITY_MEDIA_LABELS
        ]
        captures_complete = all(entry["available"] for entry in identity_media)
        identity = {
            "mode": "LEGACY",
            "id": None,
            "status": "LEGADO",
            "status_label": "Verificação anterior",
            "risk": "INDEFINIDO",
            "risk_label": "Revisão humana",
            "risk_score": None,
            "captures_complete": captures_complete,
            "liveness_confirmed": None,
            "face_similarity": None,
            "face_comparison_available": False,
            "checks": [],
        }

    profile = getattr(item, "perfil", None)
    has_questionnaire = hasattr(item, "questionario")
    identity_pending = bool(
        item.status == "APROVADO"
        and verification
        and verification.status != "APROVADA"
    )
    return {
        "id": item.id,
        "name": item.nome_completo,
        "email": item.email,
        "phone": item.telefone,
        "city": item.cidade,
        "age": item.idade,
        "gender_label": item.get_genero_display(),
        "objective_label": item.get_objetivo_display(),
        "status": item.status,
        "status_label": item.get_status_display(),
        "display_status": "EM_ANALISE" if identity_pending else item.status,
        "display_status_label": (
            "Identidade pendente" if identity_pending else item.get_status_display()
        ),
        "accepted_verification": item.aceita_verificacao,
        "has_questionnaire": has_questionnaire,
        "questionnaire_path": (
            f"/questionario/{item.token}/"
            if item.status == "APROVADO" and not has_questionnaire and not identity_pending
            else ""
        ),
        "has_profile": bool(profile),
        "has_password": bool(
            profile and profile.usuario and profile.usuario.has_usable_password()
        ),
        "note": item.observacao_admin,
        "created_at": item.criado_em,
        "updated_at": item.atualizado_em,
        "admin_url": f"/admin/entradas/pedidoentrada/{item.id}/change/",
        "profile_media": profile_media,
        "identity_media": identity_media,
        "identity": identity,
    }


def _analysis_map(content_type, ids):
    if not ids:
        return {}
    return {
        item.content_id: item
        for item in AnaliseAutomaticaConteudoNKATA.objects.filter(
            content_type=content_type,
            content_id__in=ids,
        )
    }


def _content_rows(request, limit):
    query = str(request.query_params.get("q", "")).strip()
    status_filter = str(request.query_params.get("status", "")).strip().upper()
    kind = str(request.query_params.get("kind", "")).strip().upper()
    rows = []

    def add_queryset(content_type, queryset, text_field):
        if query:
            queryset = queryset.filter(
                Q(perfil__nome_publico__icontains=query)
                | Q(usuario__email__icontains=query)
                | Q(**{f"{text_field}__icontains": query})
            )
        if status_filter in {"PENDENTE", "APROVADO", "REJEITADO"}:
            queryset = queryset.filter(moderacao_status=status_filter)
        items = list(queryset.order_by("-criado_em")[:limit])
        analyses = _analysis_map(content_type, [item.id for item in items])
        for item in items:
            analysis = analyses.get(item.id)
            rows.append({
                "id": item.id,
                "content_type": content_type,
                "content_label": "Publicação" if content_type == "PUBLICACAO" else "Momento",
                "author": item.perfil.nome_publico,
                "author_id": item.perfil_id,
                "media_type": item.tipo_media,
                "text": str(getattr(item, text_field, "") or ""),
                "visibility_label": item.get_visibilidade_display(),
                "status": item.moderacao_status,
                "status_label": item.get_moderacao_status_display(),
                "moderation_note": item.moderacao_motivo,
                "risk": analysis.risk_level if analysis else "INDEFINIDO",
                "risk_label": analysis.get_risk_level_display() if analysis else "Não analisado",
                "analysis_status": analysis.status if analysis else "",
                "analysis_status_label": analysis.get_status_display() if analysis else "Não realizada",
                "analysis_note": analysis.notes if analysis else "",
                "media_url": (
                    f"/api/publicacoes/{item.id}/media/"
                    if content_type == "PUBLICACAO"
                    else f"/api/momentos/{item.id}/media/"
                ) if item.media else None,
                "created_at": item.criado_em,
                "expires_at": getattr(item, "expira_em", None),
                "admin_url": (
                    f"/admin/entradas/publicacaonkata/{item.id}/change/"
                    if content_type == "PUBLICACAO"
                    else f"/admin/entradas/momentonkata/{item.id}/change/"
                ),
            })

    if kind in {"", "PUBLICACAO"}:
        add_queryset(
            "PUBLICACAO",
            PublicacaoNKATA.objects.select_related("perfil", "usuario"),
            "legenda",
        )
    if kind in {"", "MOMENTO"}:
        add_queryset(
            "MOMENTO",
            MomentoNKATA.objects.select_related("perfil", "usuario"),
            "texto",
        )
    rows.sort(key=lambda row: row["created_at"], reverse=True)
    return {"total": len(rows), "results": rows[:limit]}


def _report_rows(request, limit):
    status_filter = str(request.query_params.get("status", "PENDENTE")).strip().upper()
    query = str(request.query_params.get("q", "")).strip()
    rows = []
    profile_reports = DenunciaPerfil.objects.select_related(
        "perfil", "perfil__pedido", "denunciante"
    )
    post_reports = DenunciaPublicacaoNKATA.objects.select_related(
        "publicacao__perfil", "publicacao__usuario", "denunciante"
    )
    if status_filter == "PENDENTE":
        profile_reports = profile_reports.filter(analisada=False)
        post_reports = post_reports.filter(estado="PENDENTE")
    elif status_filter == "ANALISADA":
        profile_reports = profile_reports.filter(analisada=True)
        post_reports = post_reports.filter(estado="ANALISADA")
    if query:
        profile_reports = profile_reports.filter(
            Q(perfil__nome_publico__icontains=query)
            | Q(perfil__pedido__email__icontains=query)
            | Q(detalhes__icontains=query)
        )
        post_reports = post_reports.filter(
            Q(publicacao__perfil__nome_publico__icontains=query)
            | Q(publicacao__usuario__email__icontains=query)
        )

    for report in profile_reports[:limit]:
        rows.append({
            "id": report.id,
            "report_type": "PERFIL",
            "report_label": "Perfil",
            "target": report.perfil.nome_publico,
            "target_id": report.perfil_id,
            "reason": report.get_motivo_display(),
            "details": report.detalhes,
            "reporter": report.denunciante.email if report.denunciante else "Anónimo",
            "status": "ANALISADA" if report.analisada else "PENDENTE",
            "created_at": report.criado_em,
            "photo_url": profile_photo_url(report.perfil),
            "media_type": "IMAGEM",
            "admin_url": f"/admin/entradas/denunciaperfil/{report.id}/change/",
        })
    for report in post_reports[:limit]:
        rows.append({
            "id": report.id,
            "report_type": "PUBLICACAO",
            "report_label": "Publicação",
            "target": report.publicacao.perfil.nome_publico,
            "target_id": report.publicacao_id,
            "reason": report.get_motivo_display(),
            "details": report.publicacao.legenda,
            "reporter": report.denunciante.email,
            "status": report.estado,
            "created_at": report.criado_em,
            "media_url": f"/api/publicacoes/{report.publicacao_id}/media/",
            "media_type": report.publicacao.tipo_media,
            "admin_url": f"/admin/entradas/denunciapublicacaonkata/{report.id}/change/",
        })
    rows.sort(key=lambda row: row["created_at"], reverse=True)
    return {"total": len(rows), "results": rows[:limit]}


def _admin_call_duration_seconds(call, now=None):
    """Return only real connected time; ringing time is never billed as a call."""
    if not call.atendida_em:
        return 0
    ended_at = call.terminada_em
    if not ended_at and call.estado == ChamadaMatchNKATA.ESTADO_ATIVA:
        ended_at = now or timezone.now()
    if not ended_at:
        return 0
    return max(0, int((ended_at - call.atendida_em).total_seconds()))


def _admin_call_status(call):
    """Use an operational label when a call ended before WebRTC connected."""
    if call.estado == ChamadaMatchNKATA.ESTADO_TERMINADA and not call.atendida_em:
        return "SEM_ATENDIMENTO", "Sem atendimento"
    return call.estado, call.get_estado_display()


def _audit_rows(request, limit):
    query = str(request.query_params.get("q", "")).strip()
    status_filter = str(request.query_params.get("status", "")).strip().upper()
    queryset = LogEntry.objects.select_related("user", "content_type").filter(
        content_type__app_label="entradas",
    )
    if query:
        queryset = queryset.filter(
            Q(user__username__icontains=query)
            | Q(user__email__icontains=query)
            | Q(object_repr__icontains=query)
            | Q(change_message__icontains=query)
            | Q(content_type__model__icontains=query)
        )
    flag_by_status = {
        "CRIACAO": 1,
        "ALTERACAO": 2,
        "REMOCAO": 3,
    }
    if status_filter in flag_by_status:
        queryset = queryset.filter(action_flag=flag_by_status[status_filter])

    total = queryset.count()
    results = []
    for entry in queryset.order_by("-action_time")[:limit]:
        status, status_label = AUDIT_ACTIONS.get(
            entry.action_flag,
            ("REGISTO", "Registo"),
        )
        operator = entry.user.get_full_name().strip()
        if not operator:
            operator = entry.user.email or entry.user.get_username()
        results.append({
            "id": entry.id,
            "operation_type": "AUDIT",
            "title": entry.object_repr,
            "detail": entry.get_change_message() or "Ação administrativa registada.",
            "object_type": str(entry.content_type.name).title(),
            "operator": operator,
            "status": status,
            "status_label": status_label,
            "created_at": entry.action_time,
        })
    return {"total": total, "results": results}


def _operation_rows(request, limit):
    kind = str(request.query_params.get("kind", "CALLS")).strip().upper()
    status_filter = str(request.query_params.get("status", "")).strip().upper()
    query = str(request.query_params.get("q", "")).strip()
    if kind == "MATCHES":
        queryset = MatchPerfil.objects.select_related("perfil_1", "perfil_2")
        if status_filter in {"ATIVO", "ENCERRADO"}:
            queryset = queryset.filter(status=status_filter)
        if query:
            queryset = queryset.filter(
                Q(perfil_1__nome_publico__icontains=query)
                | Q(perfil_2__nome_publico__icontains=query)
            )
        total = queryset.count()
        return {
            "total": total,
            "results": [{
                "id": item.id,
                "operation_type": "MATCH",
                "title": f"{item.perfil_1.nome_publico} ↔ {item.perfil_2.nome_publico}",
                "detail": item.get_tipo_origem_display(),
                "status": item.status,
                "status_label": item.get_status_display(),
                "created_at": item.criado_em,
                "updated_at": item.atualizado_em,
                "admin_url": f"/admin/entradas/matchperfil/{item.id}/change/",
            } for item in queryset.order_by("-atualizado_em")[:limit]],
        }

    queryset = ChamadaMatchNKATA.objects.select_related(
        "match__perfil_1", "match__perfil_2", "iniciador"
    )
    valid_states = {value for value, _label in ChamadaMatchNKATA.ESTADO_CHOICES}
    if status_filter in valid_states:
        queryset = queryset.filter(estado=status_filter)
    if query:
        queryset = queryset.filter(
            Q(match__perfil_1__nome_publico__icontains=query)
            | Q(match__perfil_2__nome_publico__icontains=query)
            | Q(iniciador__email__icontains=query)
        )
    total = queryset.count()
    results = []
    for call in queryset.order_by("-criada_em")[:limit]:
        duration = _admin_call_duration_seconds(call)
        display_status, display_label = _admin_call_status(call)
        results.append({
            "id": call.id,
            "operation_type": "CALL",
            "call_type": call.tipo,
            "title": (
                f"{call.match.perfil_1.nome_publico} ↔ "
                f"{call.match.perfil_2.nome_publico}"
            ),
            "detail": call.get_tipo_display(),
            "initiator": call.iniciador.email or call.iniciador.get_username(),
            "status": display_status,
            "status_label": display_label,
            "connected": bool(call.atendida_em),
            "duration_seconds": duration,
            "created_at": call.criada_em,
            "answered_at": call.atendida_em,
            "ended_at": call.terminada_em,
            "updated_at": call.atualizada_em,
        })
    return {"total": total, "results": results}


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def api_admin_summary(request):
    return Response(_summary_payload())


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def api_admin_list(request):
    section = str(request.query_params.get("section", "members")).strip().lower()
    limit = _safe_limit(request)
    handlers = {
        "members": _member_rows,
        "access": _access_rows,
        "content": _content_rows,
        "reports": _report_rows,
        "operations": _operation_rows,
        "audit": _audit_rows,
    }
    handler = handlers.get(section)
    if not handler:
        return Response({"detail": "Área administrativa inválida."}, status=400)
    return Response(handler(request, limit))


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def api_admin_access_detail(request, pedido_id):
    item = (
        PedidoEntrada.objects
        .select_related(
            "perfil__usuario",
            "questionario",
            "verificacao_identidade",
            "verificacao_identidade__analisado_por",
        )
        .filter(id=pedido_id)
        .first()
    )
    if not item:
        return Response({"detail": "Pedido não encontrado."}, status=404)
    return Response(_access_detail_payload(item))


def _action_member(request, object_id, action):
    profile = PerfilNKATA.objects.select_related("pedido", "usuario").filter(
        id=object_id
    ).first()
    if not profile:
        return None, "Membro não encontrado.", 404

    if action == "pause":
        PerfilNKATA.objects.filter(id=profile.id).update(status="PAUSADO", visivel=False)
        message = "Membro pausado e retirado da descoberta."
    elif action == "block":
        PerfilNKATA.objects.filter(id=profile.id).update(status="BLOQUEADO", visivel=False)
        if profile.usuario_id:
            type(profile.usuario).objects.filter(id=profile.usuario_id).update(is_active=False)
        message = "Membro bloqueado e acesso desativado."
    elif action == "activate":
        if profile.pedido.status != "APROVADO" or not profile.usuario_id:
            return None, "O membro precisa de pedido aprovado e conta criada.", 400
        type(profile.usuario).objects.filter(id=profile.usuario_id).update(is_active=True)
        PerfilNKATA.objects.filter(id=profile.id).update(status="ATIVO", visivel=True)
        message = "Membro ativado e visível na comunidade."
    else:
        return None, "Ação de membro inválida.", 400
    _audit(request.user, profile, message)
    return profile, message, 200


def _action_access(request, object_id, action):
    item = (
        PedidoEntrada.objects
        .select_related("verificacao_identidade")
        .select_for_update()
        .filter(id=object_id)
        .first()
    )
    if not item:
        return None, "Pedido não encontrado.", 404
    if action not in {"review", "approve", "correction", "reject", "block"}:
        return None, "Ação de pedido inválida.", 400
    note = str(request.data.get("note", "")).strip()[:1000]
    if action in {"correction", "reject"} and not note:
        return None, "Indique o motivo desta decisão.", 400

    verification = getattr(item, "verificacao_identidade", None)
    if action == "approve":
        if verification:
            if not verification.capturas_completas:
                return None, "As quatro capturas do NKATA ID são obrigatórias.", 400
            if verification.status not in {"REVISAO", "APROVADA"}:
                return None, "A identidade ainda não está pronta para aprovação.", 400
            if verification.status == "REVISAO":
                verification.status = "APROVADA"
                verification.decisao_origem = "HUMANA"
                verification.analisado_por = request.user
                verification.analisado_em = timezone.now()
                if note:
                    verification.nota_interna = note
                verification.save(update_fields=[
                    "status", "decisao_origem", "analisado_por", "analisado_em",
                    "nota_interna", "atualizado_em",
                ])
        elif not all(
            bool(getattr(item, field_name))
            for field_name, _label in LEGACY_IDENTITY_MEDIA_LABELS
        ):
            return None, "Os documentos de identidade estão incompletos.", 400
        next_status = "APROVADO"
    elif action == "correction":
        next_status = "PRECISA_CORRIGIR"
        if verification:
            for field_name in verification.CAPTURE_FIELDS:
                field = getattr(verification, field_name)
                if field:
                    field.delete(save=False)
            verification.status = "REPETIR"
            verification.risco = "INDEFINIDO"
            verification.pontuacao_risco = 0
            verification.etapa_atual = "bi_frente"
            verification.verificacoes_imagem = {}
            verification.sinais_risco = {}
            verification.documento_sha256 = ""
            verification.selfie_sha256 = ""
            verification.provedor_biometrico = "qualidade_local"
            verification.correspondencia_facial = None
            verification.vivacidade_confirmada = False
            verification.decisao_origem = "HUMANA"
            verification.nota_interna = note
            verification.analisado_por = request.user
            verification.analisado_em = timezone.now()
            verification.expira_em = nkata_id_expires_at()
            verification.save()
    elif action == "reject":
        next_status = "RECUSADO"
        if verification:
            verification.status = "REJEITADA"
            verification.risco = "ALTO"
            verification.decisao_origem = "HUMANA"
            verification.nota_interna = note
            verification.analisado_por = request.user
            verification.analisado_em = timezone.now()
            verification.save(update_fields=[
                "status", "risco", "decisao_origem", "nota_interna",
                "analisado_por", "analisado_em", "atualizado_em",
            ])
    else:
        next_status = "EM_ANALISE" if action == "review" else "BLOQUEADO"

    item.status = next_status
    if note:
        item.observacao_admin = note
    fields = ["status", "atualizado_em"]
    if note:
        fields.append("observacao_admin")
    item.save(update_fields=fields)
    message = f"Pedido atualizado para {item.get_status_display()}."
    _audit(request.user, item, message)
    return item, message, 200


def _action_content(request, object_id, action):
    content_type = str(request.data.get("content_type", "")).strip().upper()
    model = CONTENT_TYPES.get(content_type)
    item = model.objects.select_related("perfil").filter(id=object_id).first() if model else None
    if not item:
        return None, "Conteúdo não encontrado.", 404
    note = str(request.data.get("note", "")).strip()[:240]
    if action in {"reject", "severe"} and not note:
        return None, "Indique o motivo da decisão de moderação.", 400
    if action == "approve":
        item.moderacao_status = "APROVADO"
        item.moderacao_motivo = ""
        if content_type == "MOMENTO":
            item.expira_em = timezone.now() + timedelta(hours=MOMENT_LIFETIME_HOURS)
        decision = "APROVADO"
        message = "Conteúdo aprovado e disponibilizado."
    elif action in {"reject", "severe"}:
        if content_type == "PUBLICACAO":
            PerfilNKATA.objects.filter(capa_publicacao_id=item.id).update(
                capa_publicacao_id=None,
            )
        item.moderacao_status = "REJEITADO"
        item.moderacao_motivo = note
        decision = "GRAVE" if action == "severe" else "REJEITADO"
        message = "Conteúdo rejeitado."
        if action == "severe":
            PerfilNKATA.objects.filter(id=item.perfil_id).exclude(
                status="BLOQUEADO"
            ).update(status="PAUSADO", visivel=False)
            message = "Conteúdo rejeitado e perfil pausado para revisão."
    else:
        return None, "Ação de moderação inválida.", 400
    item.moderado_em = timezone.now()
    update_fields = ["moderacao_status", "moderacao_motivo", "moderado_em"]
    if content_type == "MOMENTO" and action == "approve":
        update_fields.append("expira_em")
    if hasattr(item, "atualizado_em"):
        update_fields.append("atualizado_em")
    item.save(update_fields=update_fields)
    record_human_decision(content_type, item.id, decision)
    _audit(request.user, item, message)
    return item, message, 200


def _action_report(request, object_id, action):
    report_type = str(request.data.get("report_type", "")).strip().upper()
    if report_type == "PERFIL":
        report = DenunciaPerfil.objects.select_related("perfil").filter(id=object_id).first()
        if not report:
            return None, "Denúncia não encontrada.", 404
        if action not in {"resolve", "pause", "block"}:
            return None, "Ação de denúncia inválida.", 400
        report.analisada = True
        report.save(update_fields=["analisada"])
        if action == "pause":
            PerfilNKATA.objects.filter(id=report.perfil_id).exclude(
                status="BLOQUEADO"
            ).update(status="PAUSADO", visivel=False)
        elif action == "block":
            PerfilNKATA.objects.filter(id=report.perfil_id).update(
                status="BLOQUEADO", visivel=False
            )
            if report.perfil.usuario_id:
                type(report.perfil.usuario).objects.filter(
                    id=report.perfil.usuario_id
                ).update(is_active=False)
        message = "Denúncia analisada."
        if action == "pause":
            message = "Denúncia analisada e perfil pausado."
        elif action == "block":
            message = "Denúncia analisada e membro bloqueado."
    elif report_type == "PUBLICACAO":
        report = DenunciaPublicacaoNKATA.objects.select_related(
            "publicacao__perfil"
        ).filter(id=object_id).first()
        if not report:
            return None, "Denúncia não encontrada.", 404
        if action not in {"resolve", "remove", "severe"}:
            return None, "Ação de denúncia inválida.", 400
        report.estado = "ANALISADA"
        report.analisado_em = timezone.now()
        report.save(update_fields=["estado", "analisado_em"])
        if action in {"remove", "severe"}:
            publication = report.publicacao
            PerfilNKATA.objects.filter(capa_publicacao_id=publication.id).update(
                capa_publicacao_id=None,
            )
            publication.moderacao_status = "REJEITADO"
            publication.moderacao_motivo = (
                "Publicação retirada por violação grave após denúncia."
                if action == "severe"
                else "Publicação retirada após análise de denúncia."
            )
            publication.moderado_em = timezone.now()
            publication.save(update_fields=[
                "moderacao_status", "moderacao_motivo", "moderado_em", "atualizado_em"
            ])
            record_human_decision(
                "PUBLICACAO", publication.id, "GRAVE" if action == "severe" else "REJEITADO"
            )
            if action == "severe":
                PerfilNKATA.objects.filter(id=publication.perfil_id).exclude(
                    status="BLOQUEADO"
                ).update(status="PAUSADO", visivel=False)
        message = "Denúncia analisada."
        if action == "remove":
            message = "Denúncia analisada e publicação retirada."
        elif action == "severe":
            message = "Publicação retirada e perfil pausado."
    else:
        return None, "Tipo de denúncia inválido.", 400
    _audit(request.user, report, message)
    return report, message, 200


def _action_match(request, object_id, action):
    item = MatchPerfil.objects.filter(id=object_id).first()
    if not item:
        return None, "Match não encontrado.", 404
    if action == "close":
        item.status = "ENCERRADO"
        message = "Match encerrado pela equipa."
    elif action == "reopen":
        item.status = "ATIVO"
        message = "Match reativado pela equipa."
    else:
        return None, "Ação de match inválida.", 400
    item.save(update_fields=["status", "atualizado_em"])
    _audit(request.user, item, message)
    return item, message, 200


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
@transaction.atomic
def api_admin_action(request):
    resource = str(request.data.get("resource", "")).strip().lower()
    action = str(request.data.get("action", "")).strip().lower()
    try:
        object_id = int(request.data.get("id"))
    except (TypeError, ValueError):
        return Response({"detail": "Identificador inválido."}, status=400)

    handlers = {
        "member": _action_member,
        "access": _action_access,
        "content": _action_content,
        "report": _action_report,
        "match": _action_match,
    }
    handler = handlers.get(resource)
    if not handler:
        return Response({"detail": "Recurso administrativo inválido."}, status=400)
    _obj, message, response_status = handler(request, object_id, action)
    return Response(
        {"ok": response_status < 400, "message": message},
        status=response_status,
    )
