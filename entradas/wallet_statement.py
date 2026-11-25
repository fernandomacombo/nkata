"""Read-only personal statement, scoped to the authenticated member."""
from datetime import timedelta
from django.db import transaction
from django.db.models import Q, Sum, Count, Case, When, Value, CharField
from django.utils import timezone

from .models import CarteiraNKATA
from .wallet_service import active_chat_credit_access

PERIODS = {"7": 7, "30": 30, "90": 90, "ALL": None}
KINDS = {"ALL", "RECARGA", "BONUS", "CONSUMO", "ESTORNO", "AJUSTE"}
PAGE_SIZE = 20
CATEGORIES = (
    ("signals", "Sinais"), ("text", "Texto livre"), ("voice", "Notas de voz"),
    ("audio", "Chamadas de áudio"), ("video", "Videochamadas"), ("other", "Outros consumos"),
)


@transaction.atomic
def member_statement(user, *, period="30", kind="ALL", before=0):
    if period not in PERIODS or kind not in KINDS:
        raise ValueError("Invalid filter")
    now = timezone.now()
    start = now - timedelta(days=PERIODS[period]) if PERIODS[period] else None
    summary = {"received": 0, "spent": 0, "recharged": 0, "bonus": 0, "refunded": 0, "adjustments": 0}
    result = {"balance": 0, "period": period, "from": start, "as_of": now, "summary": summary,
              "breakdown": [{"code": code, "label": label, "credits": 0, "count": 0} for code, label in CATEGORIES],
              "results": [], "next_before": None, "chat_expires_at": None}
    # Writers lock the wallet before any ledger insert. This keeps a single
    # response coherent without creating a wallet or touching another account.
    wallet = CarteiraNKATA.objects.select_for_update().filter(usuario=user).first()
    if not wallet:
        return result
    now = timezone.now()
    start = now - timedelta(days=PERIODS[period]) if PERIODS[period] else None
    result.update(balance=wallet.saldo, **{"from": start, "as_of": now})
    access = active_chat_credit_access(user)
    result["chat_expires_at"] = access.fim if access else None
    rows = wallet.movimentos.filter(criado_em__lte=now)
    if start:
        rows = rows.filter(criado_em__gte=start)
    totals = rows.aggregate(
        received=Sum("quantidade", filter=Q(quantidade__gt=0)),
        spent=Sum("quantidade", filter=Q(quantidade__lt=0)),
        recharged=Sum("quantidade", filter=Q(tipo="RECARGA")),
        bonus=Sum("quantidade", filter=Q(tipo="BONUS")),
        refunded=Sum("quantidade", filter=Q(tipo="ESTORNO")),
        adjustments=Sum("quantidade", filter=Q(tipo="AJUSTE")),
    )
    summary.update({k: v or 0 for k, v in totals.items()})
    summary["spent"] = -summary["spent"]
    buckets = rows.filter(tipo="CONSUMO").annotate(category=Case(
        When(chave__startswith="signal:", then=Value("signals")),
        When(chave__startswith="chat24:", then=Value("text")),
        When(chave__startswith="voice:", then=Value("voice")),
        When(chave__startswith="call:", motivo__startswith="Chamada AUDIO", then=Value("audio")),
        When(chave__startswith="call:", motivo__startswith="Chamada VIDEO", then=Value("video")),
        default=Value("other"), output_field=CharField(),
    )).values("category").annotate(amount=Sum("quantidade"), count=Count("pk")).order_by()
    grouped = {row["category"]: row for row in buckets}
    result["breakdown"] = [{"code": code, "label": label, "credits": -grouped.get(code, {}).get("amount", 0),
                            "count": grouped.get(code, {}).get("count", 0)} for code, label in CATEGORIES]
    if kind != "ALL":
        rows = rows.filter(tipo=kind)
    if before:
        rows = rows.filter(pk__lt=before)
    page = list(rows.order_by("-pk")[:PAGE_SIZE+1])
    result["results"] = [{"id": m.pk, "tipo": m.tipo, "quantidade": m.quantidade, "saldo_apos": m.saldo_apos,
                          "motivo": m.motivo, "criado_em": m.criado_em} for m in page[:PAGE_SIZE]]
    result["next_before"] = page[PAGE_SIZE-1].pk if len(page)>PAGE_SIZE else None
    return result
