"""Commercial rules for temporary Moments, independent of permanent posts."""
import uuid
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from .identity_models import pedido_tem_identidade_verificada
from .models import EnvioMomentoCreditoNKATA, PerfilNKATA
from .moments_models import MomentoNKATA, MOMENT_LIFETIME_HOURS
from .content_moderation_service import record_human_decision
from .user_roles import active_member_profile_for_user
from .wallet_service import credit_balance, credit_spending_enabled, record_movement, WalletError

PHOTO_COST = 2
VIDEO_COST = 5

def moment_offer(user):
    free = not EnvioMomentoCreditoNKATA.objects.filter(
        usuario=user, dia=timezone.localdate(), tipo_media="IMAGEM", custo=0
    ).exists()
    return {"free_photo_remaining": int(free), "photo_cost": 0 if free else PHOTO_COST,
            "video_cost": VIDEO_COST, "balance": credit_balance(user),
            "spending_enabled": credit_spending_enabled()}

class MomentCreditError(WalletError):
    def __init__(self, message, status=409):
        super().__init__(message)
        self.status = status

def parse_moment_confirmation(data):
    try:
        key = uuid.UUID(str(data.get("key")))
        expected = str(data.get("expected_cost"))
        if expected not in ("0", str(PHOTO_COST), str(VIDEO_COST)):
            raise ValueError()
        return key, int(expected)
    except (ValueError, TypeError, AttributeError):
        raise MomentCreditError("Confirme o preço e a chave do Momento.", 400) from None

def submit_moment(user, *, key, expected, fingerprint, media_type, media, text, theme, font, visibility):
    moment = None
    try:
        with transaction.atomic():
            locked = get_user_model().objects.select_for_update().get(pk=user.pk)
            profile = active_member_profile_for_user(locked)
            if not profile or profile.status != "ATIVO" or not pedido_tem_identidade_verificada(profile.pedido):
                raise MomentCreditError("Verifique a sua identidade para publicar fotografias ou vídeos.", 403)
            prior = EnvioMomentoCreditoNKATA.objects.filter(usuario=locked, chave=key).first()
            if prior:
                if prior.fingerprint != fingerprint or prior.custo != expected:
                    raise MomentCreditError("Chave do Momento já utilizada.")
                previous = MomentoNKATA.objects.filter(pk=prior.momento_id, usuario=locked).first()
                if not previous:
                    raise MomentCreditError("Este Momento já foi removido.")
                return previous, prior.custo, False
            offer = moment_offer(locked)
            cost = offer["photo_cost"] if media_type == "IMAGEM" else offer["video_cost"]
            if expected != cost:
                raise MomentCreditError("O preço mudou. Confirme o valor actualizado.")
            if cost and not offer["spending_enabled"]:
                raise MomentCreditError("O consumo de créditos ainda não está disponível.")
            if offer["balance"] < cost:
                raise MomentCreditError("Saldo insuficiente.")
            movement = record_movement(locked, key=f"moment:{key}", kind="CONSUMO",
                amount=-cost, reference=f"MOMENTO:{key}",
                reason="Momento de fotografia" if media_type == "IMAGEM" else "Momento de vídeo") if cost else None
            moment = MomentoNKATA(usuario=locked, perfil=profile, texto=text, tema=theme,
                fonte=font, visibilidade=visibility, tipo_media=media_type, media=media,
                moderacao_status="PENDENTE")
            moment.save()
            EnvioMomentoCreditoNKATA.objects.create(usuario=locked, chave=key, momento_id=moment.pk,
                tipo_media=media_type, dia=timezone.localdate(), custo=cost, fingerprint=fingerprint, movimento=movement)
        return moment, cost, True
    except Exception:
        if moment and moment.media and moment.media._committed:
            try:
                moment.media.storage.delete(moment.media.name)
            except OSError:
                pass
        raise

@transaction.atomic
def refund_rejected_moment(moment):
    """Exact retry returns the existing refund. No debit means no refund."""
    if moment.moderacao_status != "REJEITADO":
        raise MomentCreditError("Só um Momento rejeitado pode receber devolução.")
    get_user_model().objects.select_for_update().get(pk=moment.usuario_id)
    receipt = EnvioMomentoCreditoNKATA.objects.filter(momento_id=moment.pk, usuario_id=moment.usuario_id).first()
    if not receipt or not receipt.custo:
        return None
    return record_movement(moment.usuario, key=f"moment-refund:{receipt.chave}", kind="ESTORNO",
        amount=receipt.custo, reference=f"MOMENTO:{receipt.chave}", reason="Devolução por rejeição de Momento")

@transaction.atomic
def moderate_moment(moment_id, *, action, note=""):
    """One locked decision path for both administration interfaces."""
    item = MomentoNKATA.objects.select_for_update().filter(pk=moment_id).first()
    if not item:
        raise MomentCreditError("Momento não encontrado.", 404)
    if action not in {"approve", "reject", "severe"}:
        raise MomentCreditError("Ação de moderação inválida.", 400)
    receipt = EnvioMomentoCreditoNKATA.objects.filter(momento_id=item.pk, usuario_id=item.usuario_id).first()
    if action == "approve":
        if item.moderacao_status == "APROVADO":
            return item, None
        if receipt and item.moderacao_status == "REJEITADO":
            raise MomentCreditError("Este Momento já foi rejeitado. O membro deve enviar um novo conteúdo.")
        now = timezone.now()
        item.moderacao_status = "APROVADO"
        item.moderacao_motivo = ""
        item.moderado_em = now
        item.expira_em = now + timedelta(hours=MOMENT_LIFETIME_HOURS)
        item.save(update_fields=["moderacao_status", "moderacao_motivo", "moderado_em", "expira_em"])
        with transaction.atomic():
            record_human_decision("MOMENTO", item.pk, "APROVADO")
        return item, None
    if not note.strip():
        raise MomentCreditError("Indique o motivo da decisão de moderação.", 400)
    item.moderacao_status = "REJEITADO"
    item.moderacao_motivo = note.strip()[:240]
    item.moderado_em = timezone.now()
    item.save(update_fields=["moderacao_status", "moderacao_motivo", "moderado_em"])
    refund = refund_rejected_moment(item) if receipt else None
    if action == "severe":
        PerfilNKATA.objects.filter(pk=item.perfil_id).exclude(status="BLOQUEADO").update(status="PAUSADO", visivel=False)
    with transaction.atomic():
        record_human_decision("MOMENTO", item.pk, "GRAVE" if action == "severe" else "REJEITADO")
    return item, refund
