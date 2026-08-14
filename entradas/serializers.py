import re

from django.db import DatabaseError
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from .call_history_api import serialize_call_message
from .call_models import ChamadaMatchNKATA
from .chat_media_models import MensagemAudioMatchNKATA
from .models import MatchPerfil, MensagemMatch, PerfilNKATA
from .profile_media_api import profile_photo_url


TEXT_RULES = {
    "sobre_si": {
        "min_chars": 30,
        "min_words": 5,
        "label": "Sobre si",
    },
    "o_que_valoriza": {
        "min_chars": 18,
        "min_words": 3,
        "label": "O que valoriza",
    },
    "o_que_nao_aceita": {
        "min_chars": 12,
        "min_words": 2,
        "label": "O que não aceita",
    },
}


def _validar_texto_natural(value, *, min_chars, min_words, label):
    texto = " ".join(str(value or "").split())

    if len(texto) < min_chars:
        raise serializers.ValidationError(
            f"{label}: escreva pelo menos {min_chars} caracteres."
        )

    palavras = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]{2,}", texto)
    if len(palavras) < min_words:
        raise serializers.ValidationError(
            f"{label}: escreva pelo menos {min_words} palavras completas."
        )

    palavras_com_vogal = sum(
        bool(re.search(r"[aeiouáéíóúâêôãõà]", palavra, flags=re.IGNORECASE))
        for palavra in palavras
    )
    minimo_com_vogal = max(1, (len(palavras) + 1) // 2)

    if palavras_com_vogal < minimo_com_vogal:
        raise serializers.ValidationError(
            f"{label}: reveja o texto e use palavras mais claras e naturais."
        )

    return texto


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
        return profile_photo_url(obj)

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


class MinhaContaSerializer(serializers.ModelSerializer):
    foto_principal = serializers.SerializerMethodField()
    objetivo_display = serializers.CharField(source="get_objetivo_display", read_only=True)
    genero_display = serializers.CharField(source="get_genero_display", read_only=True)
    email = serializers.EmailField(source="usuario.email", read_only=True)
    membro_desde = serializers.DateTimeField(source="criado_em", read_only=True)
    total_matches = serializers.SerializerMethodField()
    total_interesses_enviados = serializers.SerializerMethodField()
    destaque_publico_elegivel = serializers.SerializerMethodField()

    class Meta:
        model = PerfilNKATA
        fields = [
            "id",
            "nome_publico",
            "email",
            "cidade",
            "idade",
            "genero",
            "genero_display",
            "objetivo",
            "objetivo_display",
            "sobre_si",
            "o_que_valoriza",
            "o_que_nao_aceita",
            "foto_principal",
            "status",
            "visivel",
            "destaque_publico",
            "destaque_publico_consentido_em",
            "destaque_publico_exibicoes",
            "foto_destaque_publico_aprovada",
            "destaque_publico_elegivel",
            "capa_publicacao_id",
            "membro_desde",
            "total_matches",
            "total_interesses_enviados",
        ]
        read_only_fields = [
            "id",
            "email",
            "idade",
            "genero",
            "status",
            "foto_principal",
            "destaque_publico_consentido_em",
            "destaque_publico_exibicoes",
            "foto_destaque_publico_aprovada",
            "destaque_publico_elegivel",
            "capa_publicacao_id",
            "membro_desde",
            "total_matches",
            "total_interesses_enviados",
        ]
        extra_kwargs = {
            "nome_publico": {"required": False, "min_length": 2, "max_length": 120},
            "cidade": {"required": False, "min_length": 2, "max_length": 100},
            "objetivo": {"required": False},
            "sobre_si": {"required": False, "max_length": 1800},
            "o_que_valoriza": {"required": False, "max_length": 1800},
            "o_que_nao_aceita": {"required": False, "max_length": 1800},
            "visivel": {"required": False},
            "destaque_publico": {"required": False},
        }

    def get_foto_principal(self, obj):
        return profile_photo_url(obj)

    def get_total_matches(self, obj):
        return MatchPerfil.objects.filter(
            Q(perfil_1=obj) | Q(perfil_2=obj),
            status="ATIVO",
        ).count()

    def get_total_interesses_enviados(self, obj):
        if not obj.usuario_id:
            return 0
        return obj.usuario.acoes_feitas.filter(tipo="INTERESSE").count()

    def get_destaque_publico_elegivel(self, obj):
        return bool(
            obj.status == "ATIVO"
            and obj.visivel
            and obj.foto_destaque_publico_aprovada
            and obj.foto_principal
            and getattr(obj.pedido, "status", "") == "APROVADO"
        )

    def validate(self, attrs):
        text_fields = [
            "nome_publico",
            "cidade",
            "sobre_si",
            "o_que_valoriza",
            "o_que_nao_aceita",
        ]

        for field in text_fields:
            if field in attrs and isinstance(attrs[field], str):
                attrs[field] = " ".join(attrs[field].split())

        errors = {}

        for required_field in ["nome_publico", "cidade"]:
            if required_field in attrs and not attrs[required_field]:
                errors[required_field] = "Este campo não pode ficar vazio."

        for field, rules in TEXT_RULES.items():
            if field not in attrs:
                continue
            try:
                attrs[field] = _validar_texto_natural(attrs[field], **rules)
            except serializers.ValidationError as error:
                errors[field] = error.detail

        next_visible = attrs.get("visivel", getattr(self.instance, "visivel", True))
        if not next_visible:
            attrs["destaque_publico"] = False

        if attrs.get("destaque_publico"):
            instance = self.instance
            eligible = bool(
                instance
                and instance.status == "ATIVO"
                and next_visible
                and instance.foto_destaque_publico_aprovada
                and instance.foto_principal
                and getattr(instance.pedido, "status", "") == "APROVADO"
            )
            if not eligible:
                errors["destaque_publico"] = (
                    "A fotografia e o perfil precisam estar aprovados e visíveis."
                )

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def update(self, instance, validated_data):
        enabling_public_preview = bool(
            validated_data.get("destaque_publico")
            and not instance.destaque_publico
        )
        if enabling_public_preview:
            validated_data["destaque_publico_consentido_em"] = timezone.now()
        return super().update(instance, validated_data)


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

    def _audio_payload(self, audio):
        request = self.context.get("request")
        return {
            "id": f"audio-{audio.id}",
            "audio_id": audio.id,
            "match": audio.match_id,
            "remetente_id": audio.remetente_id,
            "remetente_nome": (
                getattr(getattr(audio.remetente, "perfil_nkata", None), "nome_publico", None)
                or getattr(audio.remetente, "first_name", "")
                or "Membro NKATA"
            ),
            "texto": "",
            "tipo": "AUDIO",
            "audio_url": f"/api/minha-conta/matches/{audio.match_id}/audio/{audio.id}/media/",
            "duracao_segundos": int(audio.duracao_segundos or 0),
            "lida": bool(audio.lida),
            "minha": bool(
                request
                and request.user.is_authenticated
                and audio.remetente_id == request.user.id
            ),
            "criado_em": audio.criado_em,
        }

    def _call_payload(self, call):
        request = self.context.get("request")
        user_id = request.user.id if request and request.user.is_authenticated else None
        return serialize_call_message(call, user_id)

    def get_ultima_mensagem(self, obj):
        candidates = []
        texto = obj.mensagens.order_by("-criado_em").first()
        if texto:
            candidates.append((texto.criado_em, MensagemMatchSerializer(texto, context=self.context).data))

        try:
            audio = (
                MensagemAudioMatchNKATA.objects
                .filter(match=obj)
                .select_related("remetente", "remetente__perfil_nkata")
                .order_by("-criado_em")
                .first()
            )
        except DatabaseError:
            audio = None
        if audio:
            candidates.append((audio.criado_em, self._audio_payload(audio)))

        try:
            call = (
                ChamadaMatchNKATA.objects
                .filter(match=obj)
                .order_by("-atualizada_em", "-criada_em")
                .first()
            )
        except DatabaseError:
            call = None
        if call:
            call_time = call.terminada_em or call.atualizada_em or call.criada_em
            candidates.append((call_time, self._call_payload(call)))

        if not candidates:
            return None
        return max(candidates, key=lambda item: item[0])[1]

    def get_mensagens_nao_lidas(self, obj):
        request = self.context.get("request")
        text_qs = obj.mensagens.filter(lida=False)

        if request and request.user.is_authenticated:
            text_qs = text_qs.exclude(remetente=request.user)

        unread = text_qs.count()
        try:
            audio_qs = MensagemAudioMatchNKATA.objects.filter(match=obj, lida=False)
            if request and request.user.is_authenticated:
                audio_qs = audio_qs.exclude(remetente=request.user)
            unread += audio_qs.count()
        except DatabaseError:
            pass

        return unread
