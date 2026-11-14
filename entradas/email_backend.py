"""Transactional mail through Zoho CPaaS HTTPS; no automatic retry on ambiguity."""
from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend


class ZohoEmailError(RuntimeError):
    pass


def address(value):
    name, mailbox = parseaddr(value)
    if not mailbox or '@' not in mailbox or '\n' in value or '\r' in value:
        raise ValueError('Endereço de e-mail inválido.')
    return {'address': mailbox, 'name': name}


class ZohoAPIEmailBackend(BaseEmailBackend):
    endpoint = 'https://cpaas.zoho.com/v1.1/email'

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        key = getattr(settings, 'NKATA_ZOHO_API_KEY', '').strip()
        prefix = 'Zoho-enczapikey '
        if key.lower().startswith(prefix.lower()):
            key = key[len(prefix):].strip()
        if not key or any(c.isspace() for c in key):
            raise ImproperlyConfigured('Configure NKATA_ZOHO_API_KEY com a chave API do Agent NKATA.')
        self.authorization = prefix + key
        self.timeout = getattr(settings, 'EMAIL_TIMEOUT', 15)

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages or []:
            if not message.recipients():
                continue
            try:
                self._send(message)
            except (ZohoEmailError, ValueError):
                if not self.fail_silently:
                    raise
            else:
                sent += 1
        return sent

    def _send(self, message):
        # Run Django's normal header validation before constructing the API payload.
        message.message()
        if message.attachments or message.extra_headers:
            raise ValueError('Anexos e cabeçalhos personalizados não suportados neste backend.')
        payload = {
            'from': address(message.from_email),
            'subject': message.subject,
            'track_opens': False,
            'track_clicks': False,
        }
        for field in ('to', 'cc', 'bcc'):
            values = getattr(message, field)
            if values:
                payload[field] = [{'email_address': address(v)} for v in values]
        if message.reply_to:
            payload['reply_to'] = [address(v) for v in message.reply_to]
        payload['htmlbody' if message.content_subtype == 'html' else 'textbody'] = message.body
        for content, mimetype in getattr(message, 'alternatives', []):
            if mimetype != 'text/html':
                raise ValueError('Apenas alternativas HTML são suportadas.')
            payload['htmlbody'] = content
        try:
            response = requests.post(
                self.endpoint, json=payload,
                headers={'Authorization': self.authorization, 'Accept': 'application/json'},
                timeout=(5, self.timeout), allow_redirects=False,
            )
        except requests.RequestException:
            # Never include request, token, provider body or reset links in errors.
            raise ZohoEmailError('Falha de ligação à API Zoho; entrega não confirmada. Consulte os logs no Zoho antes de repetir.') from None
        if response.status_code not in (200, 201, 202):
            raise ZohoEmailError(f'API Zoho recusou o envio (HTTP {response.status_code}). Consulte o Agent no Zoho.')
        try:
            result = response.json()
        except ValueError:
            raise ZohoEmailError('Resposta inválida da API Zoho; entrega não confirmada.') from None
        data = result.get('data') if isinstance(result, dict) else None
        if not isinstance(data, list) or not data or not all(
            isinstance(item, dict) and item.get('code') == 'EM_104' for item in data
        ):
            raise ZohoEmailError('API Zoho não confirmou a aceitação do e-mail. Consulte o Agent no Zoho.')
