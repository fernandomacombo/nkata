from rest_framework import serializers

from .models import MatchPerfil, MensagemMatch, PerfilNKATA


class PerfilResumoSerializer(serializers.ModelSerializer):
    foto_principal = serializers.SerializerMethodField()
    objetivo_display = serializers.CharField(source="get_objetivo_display", read_only=True)
    genero_display = serializers.CharField(source="get_genero_display", read_only=True)

    class Meta:
        model = PerfilNKATA
        fields = [
            "id",
            "nome_publico",
            "cidade",
            "idade",
            "genero",
            "genero_display",
            "objetivo",
            "objetivo_display",
            "sobre_si",
            "foto_principal",
            "status",
            "visivel",
        ]

    def get_foto_principal(self, obj):
        request = self.context.get("request")
        foto = obj.foto_principal

        if not foto:
            return None

        url = foto.url
        if request:
            return request.build_absolute_uri(url)
        return url


class MensagemMatchSerializer(serializers.ModelSerializer):
    remetente_id = serializers.IntegerField(source="remetente.id", read_only=True)
    remetente_nome = serializers.SerializerMethodField()

    class Meta:
        model = MensagemMatch
        fields = [
            "id",
            "match",
            "remetente_id",
            "remetente_nome",
            "texto",
            "lida",
            "criado_em",
        ]

    def get_remetente_nome(self, obj):
        if obj.remetente and hasattr(obj.remetente, "perfil_nkata"):
            return obj.remetente.perfil_nkata.nome_publico
        if obj.remetente:
            return obj.remetente.get_username()
        return "Utilizador"


class MatchSerializer(serializers.ModelSerializer):
    perfil_1 = PerfilResumoSerializer(read_only=True)
    perfil_2 = PerfilResumoSerializer(read_only=True)
    tipo_origem_display = serializers.CharField(source="get_tipo_origem_display", read_only=True)
    ultima_mensagem = serializers.SerializerMethodField()
    mensagens_nao_lidas = serializers.SerializerMethodField()

    class Meta:
        model = MatchPerfil
        fields = [
            "id",
            "perfil_1",
            "perfil_2",
            "tipo_origem",
            "tipo_origem_display",
            "status",
            "ultima_mensagem",
            "mensagens_nao_lidas",
            "criado_em",
            "atualizado_em",
        ]

    def get_ultima_mensagem(self, obj):
        mensagem = obj.mensagens.order_by("-criado_em").first()
        if not mensagem:
            return None
        return MensagemMatchSerializer(mensagem, context=self.context).data

    def get_mensagens_nao_lidas(self, obj):
        request = self.context.get("request")
        qs = obj.mensagens.filter(lida=False)

        if request and request.user.is_authenticated:
            qs = qs.exclude(remetente=request.user)

        return qs.count()
