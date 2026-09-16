from rest_framework import serializers

from .notification_models import NotificacaoNKATA
from .serializers import PerfilResumoSerializer


class NotificacaoSerializer(serializers.ModelSerializer):
    perfil = PerfilResumoSerializer(read_only=True)
    match_id = serializers.IntegerField(source="match.id", read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = NotificacaoNKATA
        fields = [
            "id",
            "tipo",
            "tipo_display",
            "titulo",
            "texto",
            "lida",
            "perfil",
            "match_id",
            "criado_em",
            "atualizado_em",
        ]
