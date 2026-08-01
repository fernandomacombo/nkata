from rest_framework import serializers

from .models import MatchPerfil, MensagemMatch, PerfilNKATA


class PerfilResumoSerializer(serializers.ModelSerializer):
    foto_principal = serializers.SerializerMethodField()
    objetivo_display = serializers.CharField(source="get_objetivo_display", read_only=True)
    genero_display = serializers.CharField(source="get_genero_display", read_only=True)
    verificado = serializers.SerializerMethodField()

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
            "verificado",
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

    def get_verificado(self, obj):
        pedido_status = getattr(obj.pedido, "status", "")
        return pedido_status == "APROVADO" and obj.status == "ATIVO" and obj.visivel


class PerfilDetalheSerializer(PerfilResumoSerializer):
    class Meta(PerfilResumoSerializer.Meta):
        fields = PerfilResumoSerializer.Meta.fields + [
            "o_que_valoriza",
            "o_que_nao_aceita",
            "criado_em",
        ]


class MensagemMatchSerializer(serializers.ModelSerializer):
    remetente_id = serializers.IntegerField(source="remetente.id", read_only=True)
    remetente_nome = serializers.SerializerMethodField()
    minha = serializers.SerializerMethodField()

    class Meta:
        model = MensagemMatch
        fields = [
            "id",
            "match",
            "remetente_id",
            "remetente_nome",
            "texto",
            "lida",
            "minha",
            "criado_em",
        ]

    def get_remetente_nome(self, obj):
        if obj.remetente and hasattr(obj.remetente, "perfil_nkata"):
            return obj.remetente.perfil_nkata.nome_publico
        if obj.remetente:
            return obj.remetente.get_username()
        return "Membro NKATA"

    def get_minha(self, obj):
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and obj.remetente_id == request.user.id
        )


class MatchSerializer(serializers.ModelSerializer):
    perfil_1 = PerfilResumoSerializer(read_only=True)
    perfil_2 = PerfilResumoSerializer(read_only=True)
    outro_perfil = serializers.SerializerMethodField()
    tipo_origem_display = serializers.CharField(source="get_tipo_origem_display", read_only=True)
    ultima_mensagem = serializers.SerializerMethodField()
    mensagens_nao_lidas = serializers.SerializerMethodField()

    class Meta:
        model = MatchPerfil
        fields = [
            "id",
            "perfil_1",
            "perfil_2",
            "outro_perfil",
            "tipo_origem",
            "tipo_origem_display",
            "status",
            "ultima_mensagem",
            "mensagens_nao_lidas",
            "criado_em",
            "atualizado_em",
        ]

    def get_outro_perfil(self, obj):
        request = self.context.get("request")
        perfil_atual = None

        if request and request.user.is_authenticated:
            perfil_atual = getattr(request.user, "perfil_nkata", None)

        if perfil_atual and obj.perfil_1_id == perfil_atual.id:
            outro = obj.perfil_2
        elif perfil_atual and obj.perfil_2_id == perfil_atual.id:
            outro = obj.perfil_1
        else:
            outro = obj.perfil_2

        return PerfilResumoSerializer(outro, context=self.context).data

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
