import re
import unicodedata

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.crypto import salted_hmac


MAX_ACCOUNTS_PER_IDENTITY = 1


def normalize_phone(value):
    raw = str(value or "").strip()
    if not re.fullmatch(r"[+\d\s().-]+", raw):
        return ""
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 9:
        digits = "258" + digits
    return digits if 8 <= len(digits) <= 15 else ""


def document_key(value):
    number = unicodedata.normalize("NFKC", str(value or "")).strip().upper()
    if not re.fullmatch(r"[A-Z0-9\s.-]+", number):
        raise ValidationError("Informe o número do BI tal como aparece no documento.")
    number = re.sub(r"[\s.-]", "", number)
    if not 6 <= len(number) <= 30:
        raise ValidationError("Informe um número de BI válido.")
    secret = getattr(settings, "NKATA_IDENTITY_HASH_KEY", "") or settings.SECRET_KEY
    return salted_hmac("nkata.document-number.v1", number, secret=secret, algorithm="sha256").hexdigest()


def _lock_keys(keys):
    from .models import ChaveLimiteContaNKATA
    # Callers must hold a transaction. Sorted order avoids cross-key deadlocks.
    for key in sorted(keys):
        item, _ = ChaveLimiteContaNKATA.objects.get_or_create(chave=key)
        ChaveLimiteContaNKATA.objects.select_for_update().get(pk=item.pk)


def _check_capacity(phone, document, exclude_pk=None):
    from .models import PedidoEntrada
    requests = PedidoEntrada.objects.all()
    if exclude_pk:
        requests = requests.exclude(pk=exclude_pk)
    for field, value, label in (
        ("telefone_normalizado", phone, "telefone"),
        ("documento_chave", document, "BI"),
    ):
        if value and requests.filter(**{field: value}).count() >= MAX_ACCOUNTS_PER_IDENTITY:
            raise ValidationError(f"Este {label} já está associado a um pedido ou conta NKATA. Recupere o acesso à conta existente ou contacte a equipa.")


@transaction.atomic
def save_limited_request(form):
    item = form.save(commit=False)
    phone = normalize_phone(item.telefone)
    if not phone:
        raise ValidationError("Informe um telefone válido, incluindo o indicativo se não for de Moçambique.")
    document = document_key(form.cleaned_data["numero_bi"])
    _lock_keys(["phone:" + phone, "bi:" + document])
    _check_capacity(phone, document)
    item.telefone_normalizado = phone
    item.documento_chave = document
    item.save()
    return item


@transaction.atomic
def confirm_document(item, number):
    document = document_key(number)
    phone = normalize_phone(item.telefone)
    # The number read by the reviewer is authoritative. A false declaration
    # cannot escape the capacity check by using a different number at intake.
    _lock_keys(["phone:" + phone, "bi:" + document])
    _check_capacity(phone, document, exclude_pk=item.pk)
    item.documento_chave = document
    item.documento_confirmado = True
    item.save(update_fields=["documento_chave", "documento_confirmado"])
