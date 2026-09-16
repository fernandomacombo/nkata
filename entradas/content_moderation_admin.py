from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from .content_moderation_service import analysis_for


RISK_COLORS = {
    "BAIXO": ("#315b40", "#edf5ef"),
    "MEDIO": ("#7a5a16", "#fbf4dd"),
    "ALTO": ("#8a3d22", "#f9e8df"),
    "CRITICO": ("#8a1f32", "#f7e3e8"),
    "INDEFINIDO": ("#625753", "#f0ece9"),
}

CATEGORY_LABELS = {
    "nkata/contact_phone": "Telefone ou WhatsApp visível",
    "nkata/contact_email": "Email visível",
    "nkata/contact_username": "@username visível",
    "nkata/contact_url": "Link/URL visível",
    "nkata/qr_code": "QR Code detectado",
    "nkata/advertising_or_sales": "Publicidade ou venda",
    "nkata/sexual_services_solicitation": "Serviços sexuais/prostituição",
    "nkata/duplicate_severe_media": "Ficheiro grave já rejeitado anteriormente",
    "sexual": "Conteúdo sexual",
    "sexual/minors": "Conteúdo sexual envolvendo menores",
    "violence/graphic": "Violência gráfica",
    "violence": "Violência",
    "harassment": "Assédio",
    "harassment/threatening": "Assédio/ameaça",
}


def _category_label(key):
    return CATEGORY_LABELS.get(
        key,
        key.replace("/", " / ").replace("_", " "),
    )


def automatic_risk_badge(content_type, content_id):
    analysis = analysis_for(content_type, content_id)
    if not analysis:
        return mark_safe(
            '<span style="display:inline-block;padding:5px 9px;border-radius:999px;'
            'background:#f0ece9;color:#625753;font-weight:700;">Sem análise</span>'
        )

    foreground, background = RISK_COLORS.get(
        analysis.risk_level,
        RISK_COLORS["INDEFINIDO"],
    )
    return format_html(
        '<span style="display:inline-block;padding:5px 9px;border-radius:999px;'
        'background:{};color:{};font-weight:800;">{}</span>',
        background,
        foreground,
        analysis.get_risk_level_display(),
    )


def automatic_review_panel(content_type, content_id):
    analysis = analysis_for(content_type, content_id)
    if not analysis:
        return mark_safe(
            '<div style="max-width:760px;line-height:1.6;padding:12px;border-radius:10px;'
            'background:#f5f1ee;">Sem registo automático. Confirme que as migrações '
            'foram aplicadas e que o worker de moderação está ativo. '
            '<strong>O conteúdo continua a exigir revisão humana.</strong></div>'
        )

    flagged_categories = [
        _category_label(key)
        for key, value in (analysis.categories or {}).items()
        if bool(value)
    ]
    categories_html = (
        format_html_join(
            "",
            '<span style="display:inline-block;margin:2px 4px 2px 0;padding:4px 7px;'
            'border-radius:999px;background:#f7e3e8;color:#7d2638;font-size:12px;">{}</span>',
            ((category,) for category in flagged_categories),
        )
        if flagged_categories
        else mark_safe('<span style="color:#6c615d;">Nenhum sinal automático encontrado.</span>')
    )

    dimensions = (
        f"{analysis.image_width} × {analysis.image_height}px"
        if analysis.image_width and analysis.image_height
        else "—"
    )
    file_size_text = f"{((analysis.media_bytes or 0) / (1024 * 1024)):.2f} MB"

    return format_html(
        '<div style="max-width:760px;line-height:1.6;padding:14px;border-radius:12px;'
        'border:1px solid #e6ddd8;background:#fffaf7;">'
        '<div style="margin-bottom:10px;">{}</div>'
        '<strong>Estado automático:</strong> {}<br>'
        '<strong>Motor:</strong> {}{}<br>'
        '<strong>Ficheiro:</strong> {} · dimensões {}<br>'
        '<strong>SHA-256:</strong> <code style="font-size:11px;">{}</code><br>'
        '<strong>Sinais:</strong> <span>{}</span><br>'
        '<strong>Nota:</strong> {}<br><br>'
        '<span style="color:#7d2638;font-weight:800;">A análise automática não aprova conteúdo. '
        'A decisão final continua a ser humana.</span>'
        '</div>',
        automatic_risk_badge(content_type, content_id),
        analysis.get_status_display(),
        analysis.provider,
        f" · {analysis.model_name}" if analysis.model_name else "",
        file_size_text,
        dimensions,
        analysis.file_sha256 or "—",
        categories_html,
        analysis.notes or "—",
    )
