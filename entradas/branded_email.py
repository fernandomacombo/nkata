"""Apresentação visual consistente para os emails transaccionais do NKATA.

Mantém sempre uma alternativa em texto simples e não inclui recursos remotos
obrigatórios para que o Gmail e outros clientes exibam a mensagem.
"""
from html import escape
from urllib.parse import urlsplit

from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def _safe_link(url):
    url = str(url or "").strip()
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
        return ""
    return url


def render_email_html(*, title, greeting, paragraphs, action_label=None, action_url=None, notice=None):
    """Compõe um email HTML conservador (tabelas + estilos inline)."""
    title = escape(str(title))
    greeting = escape(str(greeting))
    paragraphs_html = "".join(
        '<p style="margin:0 0 16px;color:#514b49;font-size:15px;line-height:1.75;">'
        + escape(str(paragraph)).replace("\n", "<br>") + "</p>"
        for paragraph in paragraphs if paragraph
    )
    safe_url = _safe_link(action_url)
    button = (
        '<tr><td style="padding:8px 0 25px;text-align:center;">'
        '<a href="' + escape(safe_url, quote=True) + '" style="display:inline-block;'
        'background:#81273e;color:#ffffff;text-decoration:none;'
        'border-radius:12px;padding:16px 25px;font-size:15px;font-weight:bold;">'
        + escape(str(action_label)) + '</a></td></tr>'
    ) if safe_url and action_label else ""
    link_fallback = (
        '<tr><td style="padding:0 0 22px;color:#776b6d;font-size:12px;line-height:1.6;'
        'overflow-wrap:anywhere;">Se o botão não funcionar, copie este endereço:<br>'
        '<a style="color:#81273e;overflow-wrap:anywhere;" href="'
        + escape(safe_url, quote=True) + '">' + escape(safe_url) + '</a></td></tr>'
    ) if button else ""
    security_notice = escape(str(notice or "Se não solicitou esta mensagem, pode ignorá-la."))
    return (
        '<!doctype html><html lang="pt"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
        '<body style="margin:0;padding:28px 12px;background:#f5f0eb;'
        'font-family:Arial,Helvetica,sans-serif;color:#262122;">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0"'
        ' style="width:100%;max-width:600px;margin:0 auto;border-collapse:collapse;">'
        '<tr><td style="padding:14px 4px 24px;text-align:center;">'
        '<span style="color:#81273e;font-size:26px;font-weight:800;letter-spacing:5px;">NKATA</span>'
        '</td></tr><tr><td style="background:#fffdfa;border:1px solid #e8ddd9;'
        'border-radius:20px;padding:38px 34px;">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:100%;">'
        '<tr><td style="color:#81273e;font-size:11px;font-weight:bold;'
        'letter-spacing:2px;padding-bottom:15px;">CONTA E SEGURANÇA</td></tr>'
        '<tr><td style="font-family:Georgia,serif;color:#241e20;font-size:30px;'
        'line-height:1.2;padding-bottom:20px;">' + title + '</td></tr>'
        '<tr><td style="font-size:15px;font-weight:bold;color:#312b2a;padding-bottom:18px;">'
        + greeting + '</td></tr><tr><td>' + paragraphs_html + '</td></tr>'
        + button + link_fallback +
        '<tr><td style="border-top:1px solid #eee5e0;padding-top:19px;'
        'color:#746a68;font-size:13px;line-height:1.65;">'
        + security_notice + '</td></tr></table></td></tr>'
        '<tr><td style="padding:22px 14px;text-align:center;color:#877b79;'
        'font-size:12px;line-height:1.7;">NKATA · Relações sérias. Intenções claras.<br>'
        'Esta é uma mensagem automática.</td></tr></table></body></html>'
    )


def send_branded_email(*, subject, body, recipient, title, greeting, paragraphs, action_label=None, action_url=None, notice=None, fail_silently=True):
    """Envia HTML + texto simples no mesmo email."""
    message = EmailMultiAlternatives(
        subject=subject, body=body, from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    message.attach_alternative(render_email_html(
        title=title, greeting=greeting, paragraphs=paragraphs,
        action_label=action_label, action_url=action_url, notice=notice,
    ), "text/html")
    return message.send(fail_silently=fail_silently)
