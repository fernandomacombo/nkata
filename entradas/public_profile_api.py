from django.db.models import F
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import PerfilNKATA
from .profile_media_api import public_profile_photo_url


PUBLIC_PREVIEW_BATCH_SIZE = 9


def _preview_payload(perfil):
    preferences = getattr(perfil.usuario, "preferencias_nkata", None)
    return {
        "id": perfil.id,
        "nome_publico": perfil.nome_publico,
        "idade": perfil.idade,
        "cidade": perfil.cidade,
        "objetivo_display": perfil.get_objetivo_display(),
        "verificado": True,
        "foto_principal": public_profile_photo_url(perfil),
        "tema_perfil": preferences.tema_perfil if preferences else "CLASSICO",
    }


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def api_destaques_publicos(request):
    # Os menos exibidos e há mais tempo sem aparecer são escolhidos primeiro.
    # Assim, a rotação continua justa mesmo quando a comunidade crescer.
    perfis = list(
        PerfilNKATA.objects
        .filter(
            status="ATIVO",
            visivel=True,
            destaque_publico=True,
            foto_destaque_publico_aprovada=True,
            pedido__status="APROVADO",
            usuario__is_active=True,
            usuario__is_staff=False,
        )
        .exclude(pedido__foto_perfil="")
        .select_related("pedido", "usuario", "usuario__preferencias_nkata")
        .order_by(
            F("destaque_publico_ultima_exibicao_em").asc(nulls_first=True),
            "destaque_publico_exibicoes",
            "id",
        )[:PUBLIC_PREVIEW_BATCH_SIZE]
    )

    if perfis:
        PerfilNKATA.objects.filter(id__in=[perfil.id for perfil in perfis]).update(
            destaque_publico_exibicoes=F("destaque_publico_exibicoes") + 1,
            destaque_publico_ultima_exibicao_em=timezone.now(),
        )

    response = Response({
        "count": len(perfis),
        "results": [_preview_payload(perfil) for perfil in perfis],
        "rotation_seconds": 7,
    })
    response["Cache-Control"] = "no-store"
    response["X-Robots-Tag"] = "noindex, noarchive"
    return response
