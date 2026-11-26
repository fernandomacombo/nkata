from rest_framework import serializers

from .notification_models import NotificacaoNKATA
from .serializers import PerfilResumoSerializer


class NotificacaoSerializer(serializers.ModelSerializer):
    photo_slot = serializers.SerializerMethodField()

    def get_photo_slot(self, obj):
        parts = obj.chave.split(":")
        if obj.tipo == "EQUIPA" and len(parts) == 3 and parts[0] == "foto-rejeitada" and parts[1] in ("0", "1", "2", "3"):
            return int(parts[1])
        return None

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
            "conversation_id",
            "request_id",
            "photo_slot",
            "criado_em",
            "atualizado_em",
        ]
