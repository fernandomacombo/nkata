import uuid
from django.conf import settings
from django.db import models

from .profile_names import validate_profile_name
from .storage_backends import identity_media_storage, profile_media_storage, private_content_storage


class PedidoEntrada(models.Model):
    GENERO_CHOICES = [
        ("MASCULINO", "Masculino"),
        ("FEMININO", "Feminino"),
        ("OUTRO", "Prefiro não dizer"),
    ]

    OBJETIVO_CHOICES = [
        ("RELACIONAMENTO_SERIO", "Relacionamento sério"),
        ("CONHECER_COM_INTENCAO", "Conhecer pessoas com intenção"),
        ("AMIZADE_EVOLUIR", "Amizade que pode evoluir"),
        ("CASAMENTO_FUTURO", "Casamento no futuro"),
    ]

    STATUS_CHOICES = [
        ("PENDENTE", "Pendente"),
        ("EM_ANALISE", "Em análise"),
        ("PRECISA_CORRIGIR", "Precisa corrigir"),
        ("APROVADO", "Aprovado"),
        ("RECUSADO", "Recusado"),
        ("BLOQUEADO", "Bloqueado"),
    ]

    token = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    nome_completo = models.CharField(max_length=160, validators=[validate_profile_name])
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=30)
    telefone_normalizado = models.CharField(max_length=16, blank=True, db_index=True, editable=False)
    documento_chave = models.CharField(max_length=64, blank=True, db_index=True, editable=False)
    verificacao_apos_entrada = models.BooleanField(default=False, editable=False)
    identidade_revogada = models.BooleanField(default=False, editable=False)
    documento_confirmado = models.BooleanField(default=False, editable=False)
    idade = models.PositiveIntegerField()
    cidade = models.CharField(max_length=100)
    genero = models.CharField(max_length=30, choices=GENERO_CHOICES)
    objetivo = models.CharField(max_length=40, choices=OBJETIVO_CHOICES)
    aceita_verificacao = models.BooleanField(default=False)
    foto_perfil = models.ImageField(
        storage=profile_media_storage,
        upload_to="pedidos/fotos/",
    )
    foto_extra_1 = models.ImageField(
        storage=profile_media_storage,
        upload_to="pedidos/fotos/",
    )
    foto_extra_2 = models.ImageField(
        storage=profile_media_storage,
        upload_to="pedidos/fotos/",
    )
    foto_extra_3 = models.ImageField(
        storage=profile_media_storage,
        upload_to="pedidos/fotos/",
    )
    # As fotografias adicionais do registo começam privadas.
    foto_extra_1_visivel = models.BooleanField(default=False)
    foto_extra_1_estado = models.CharField(max_length=12, default="PENDENTE", choices=[("PENDENTE", "Pendente"), ("APROVADO", "Aprovado"), ("REJEITADO", "Rejeitado")])
    foto_extra_2_visivel = models.BooleanField(default=False)
    foto_extra_2_estado = models.CharField(max_length=12, default="PENDENTE", choices=[("PENDENTE", "Pendente"), ("APROVADO", "Aprovado"), ("REJEITADO", "Rejeitado")])
    foto_extra_3_visivel = models.BooleanField(default=False)
    foto_extra_3_estado = models.CharField(max_length=12, default="PENDENTE", choices=[("PENDENTE", "Pendente"), ("APROVADO", "Aprovado"), ("REJEITADO", "Rejeitado")])
    bi_frente = models.ImageField(
        storage=identity_media_storage,
        upload_to="pedidos/documentos/",
        blank=True,
    )
    bi_verso = models.ImageField(
        storage=identity_media_storage,
        upload_to="pedidos/documentos/",
        blank=True,
    )
    selfie_com_bi = models.ImageField(
        storage=identity_media_storage,
        upload_to="pedidos/documentos/",
        blank=True,
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="PENDENTE")
    observacao_admin = models.TextField(blank=True)
    onboarding_aprovado_em = models.DateTimeField(null=True, blank=True, editable=False)
    onboarding_lembrete_em = models.DateTimeField(null=True, blank=True, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pedido de entrada"
        verbose_name_plural = "Pedidos de entrada"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.nome_completo} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        from .account_limits import normalize_phone
        self.telefone_normalizado = normalize_phone(self.telefone)
        if kwargs.get("update_fields") and "telefone" in kwargs["update_fields"]:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"telefone_normalizado"}
        super().save(*args, **kwargs)


class ChaveLimiteContaNKATA(models.Model):
    """One lockable row per identity, including while its first account is created."""
    chave = models.CharField(max_length=80, unique=True, editable=False)


class QuestionarioEntrada(models.Model):
    DISPONIBILIDADE_CHOICES = [
        ("SIM", "Sim, estou disponível"),
        ("COM_CALMA", "Quero conhecer com calma"),
        ("NAO_SEI", "Ainda não tenho certeza"),
    ]
    FILHOS_CHOICES = [
        ("SIM", "Sim"),
        ("NAO", "Não"),
        ("PREFIRO_NAO_DIZER", "Prefiro não dizer"),
    ]
    ACEITA_FILHOS_CHOICES = [
        ("SIM", "Sim"),
        ("NAO", "Não"),
        ("DEPENDE", "Depende"),
    ]
    pedido = models.OneToOneField(PedidoEntrada, on_delete=models.CASCADE, related_name="questionario")
    disponibilidade = models.CharField(max_length=30, choices=DISPONIBILIDADE_CHOICES)
    tem_filhos = models.CharField(max_length=30, choices=FILHOS_CHOICES)
    aceita_pessoa_com_filhos = models.CharField(max_length=30, choices=ACEITA_FILHOS_CHOICES)
    cidade_preferida = models.CharField(max_length=120, help_text="Cidade ou região onde gostaria de conhecer pessoas.")
    faixa_etaria_preferida = models.CharField(max_length=80, help_text="Ex: 25 a 35 anos")
    sobre_si = models.TextField(help_text="Fale um pouco sobre si.")
    o_que_valoriza = models.TextField(help_text="O que mais valoriza numa relação?")
    o_que_nao_aceita = models.TextField(help_text="O que não aceita numa relação?")
    aceita_regras = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Questionário de entrada"
        verbose_name_plural = "Questionários de entrada"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Questionário - {self.pedido.nome_completo}"


class PerfilNKATA(models.Model):
    ultima_presenca = models.DateTimeField(null=True, blank=True, editable=False)
    preferencias = models.JSONField(default=dict, blank=True)
    STATUS_CHOICES = [
        ("ATIVO", "Ativo"),
        ("PAUSADO", "Pausado"),
        ("BLOQUEADO", "Bloqueado"),
        ("ENCERRAMENTO", "Encerramento solicitado"),
    ]
    pedido = models.OneToOneField(PedidoEntrada, on_delete=models.CASCADE, related_name="perfil")
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="perfil_nkata")
    nome_publico = models.CharField(max_length=120, validators=[validate_profile_name])
    cidade = models.CharField(max_length=100)
    idade = models.PositiveIntegerField()
    genero = models.CharField(max_length=30, choices=PedidoEntrada.GENERO_CHOICES)
    objetivo = models.CharField(max_length=40, choices=PedidoEntrada.OBJETIVO_CHOICES)
    sobre_si = models.TextField()
    o_que_valoriza = models.TextField()
    o_que_nao_aceita = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="ATIVO")
    visivel = models.BooleanField(default=True)
    destaque_publico = models.BooleanField(default=False, db_index=True)
    destaque_publico_consentido_em = models.DateTimeField(null=True, blank=True)
    foto_destaque_publico_aprovada = models.BooleanField(default=False)
    foto_destaque_publico_estado = models.CharField(max_length=12, default="PENDENTE", choices=[("PENDENTE", "Pendente"), ("APROVADO", "Aprovado"), ("REJEITADO", "Rejeitado")])
    destaque_publico_exibicoes = models.PositiveBigIntegerField(default=0, editable=False)
    destaque_publico_ultima_exibicao_em = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    capa_publicacao_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        db_index=True,
    )
    owner_session_key = models.CharField(max_length=120, blank=True, db_index=True)
    pausa_iniciada_pelo_usuario = models.BooleanField(default=False)
    pausado_ate = models.DateTimeField(null=True, blank=True)
    motivo_pausa = models.CharField(max_length=240, blank=True)
    encerramento_solicitado_em = models.DateTimeField(null=True, blank=True)
    motivo_encerramento = models.CharField(max_length=500, blank=True)
    reativacao_enviada_em = models.DateTimeField(null=True, blank=True, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil NKATA"
        verbose_name_plural = "Perfis NKATA"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.nome_publico} - {self.get_status_display()}"

    @property
    def foto_principal(self):
        return self.pedido.foto_perfil


class PreferenciasContaNKATA(models.Model):
    class Idioma(models.TextChoices):
        PORTUGUES = "PT", "Português"
        INGLES = "EN", "English"

    class TemaPerfil(models.TextChoices):
        CLASSICO = "CLASSICO", "Clássico"
        AREIA = "AREIA", "Areia"
        NOITE = "NOITE", "Noite"

    class FundoConversa(models.TextChoices):
        SERENO = "SERENO", "Sereno"
        BOTANICO = "BOTANICO", "Botânico"
        NOTURNO = "NOTURNO", "Noturno"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferencias_nkata",
    )
    idioma = models.CharField(
        max_length=2,
        choices=Idioma.choices,
        default=Idioma.PORTUGUES,
    )
    tema_perfil = models.CharField(
        max_length=20,
        choices=TemaPerfil.choices,
        default=TemaPerfil.CLASSICO,
    )
    aviso_chat_aceite = models.BooleanField(default=False)
    fundo_conversa = models.CharField(
        max_length=20,
        choices=FundoConversa.choices,
        default=FundoConversa.SERENO,
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Preferências da conta NKATA"
        verbose_name_plural = "Preferências das contas NKATA"

    def __str__(self):
        return f"Preferências de {self.usuario.get_username()}"


class AcaoPerfil(models.Model):
    TIPO_CHOICES = [
        ("INTERESSE", "Tenho interesse"),
        ("GOSTAR", "Gostar"),
        ("SEGUIR", "Seguir"),
        ("GUARDADO", "Perfil guardado"),
        ("BLOQUEIO", "Bloquear"),
        ("SINAL_FLOR", "Sinal — Flor"),
        ("SINAL_BEIJINHO", "Sinal — Beijinho"),
        ("SINAL_OLA", "Sinal — Olá"),
    ]
    perfil = models.ForeignKey(PerfilNKATA, on_delete=models.CASCADE, related_name="acoes_recebidas")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="acoes_feitas")
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    session_key = models.CharField(max_length=120, blank=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ação de perfil"
        verbose_name_plural = "Ações de perfil"
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(fields=["perfil", "tipo", "session_key"], name="acao_unica_por_sessao")
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} em {self.perfil.nome_publico}"


class MensagemPerfil(models.Model):
    TEXTO_CHOICES = [
        ("GOSTEI_DO_PERFIL", "Olá, gostei do seu perfil e gostaria de conhecer melhor."),
        ("CONVERSAR_COM_CALMA", "Achei o seu perfil interessante. Podemos conversar com calma?"),
        ("ALGO_SERIO", "Vejo que procuramos algo sério. Gostaria de saber mais sobre si."),
    ]
    perfil = models.ForeignKey(PerfilNKATA, on_delete=models.CASCADE, related_name="mensagens_recebidas")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="mensagens_enviadas")
    texto = models.CharField(max_length=40, choices=TEXTO_CHOICES)
    session_key = models.CharField(max_length=120, blank=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(fields=["perfil", "texto", "session_key"], name="mensagem_unica_por_sessao")
        ]

    def __str__(self):
        return f"{self.get_texto_display()} → {self.perfil.nome_publico}"


class DenunciaPerfil(models.Model):
    MOTIVOS = [
        ("PERFIL_FALSO", "Perfil falso"),
        ("FOTO_SUSPEITA", "Foto suspeita"),
        ("COMPORTAMENTO_INADEQUADO", "Comportamento inadequado"),
        ("DADOS_FALSOS", "Dados falsos"),
        ("OUTRO", "Outro motivo"),
    ]
    denunciante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="denuncias_feitas")
    perfil = models.ForeignKey(PerfilNKATA, on_delete=models.CASCADE, related_name="denuncias")
    motivo = models.CharField(max_length=40, choices=MOTIVOS)
    detalhes = models.TextField(blank=True, help_text="Detalhes adicionais da denúncia.")
    analisada = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Denúncia de perfil"
        verbose_name_plural = "Denúncias de perfis"

    def __str__(self):
        return f"Denúncia contra {self.perfil.nome_publico} - {self.get_motivo_display()}"


class MatchPerfil(models.Model):
    STATUS_CHOICES = [("ATIVO", "Ativo"), ("ENCERRADO", "Encerrado")]
    TIPO_ORIGEM_CHOICES = [("INTERESSE", "Interesse mútuo"), ("GOSTAR", "Gosto mútuo")]
    perfil_1 = models.ForeignKey(PerfilNKATA, on_delete=models.CASCADE, related_name="matches_como_perfil_1")
    perfil_2 = models.ForeignKey(PerfilNKATA, on_delete=models.CASCADE, related_name="matches_como_perfil_2")
    tipo_origem = models.CharField(max_length=30, choices=TIPO_ORIGEM_CHOICES, default="INTERESSE")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ATIVO")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Match"
        verbose_name_plural = "Matches"
        constraints = [
            models.UniqueConstraint(fields=["perfil_1", "perfil_2"], name="match_unico_entre_perfis")
        ]

    def __str__(self):
        return f"Match: {self.perfil_1.nome_publico} ↔ {self.perfil_2.nome_publico}"


class MensagemMatch(models.Model):
    tipo = models.CharField(max_length=16, default="TEXTO", choices=[("TEXTO", "Texto"), ("SINAL", "Sinal"), ("QUEBRA_GELO", "Quebra-gelo"), ("PREDEFINIDA", "Predefinida"), ("AUDIO", "Nota de voz")])
    sinal_origem = models.OneToOneField(AcaoPerfil, null=True, blank=True, on_delete=models.SET_NULL, related_name="mensagem_chat")
    resposta_a = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    match = models.ForeignKey(MatchPerfil, null=True, on_delete=models.CASCADE, related_name="mensagens")
    conversa = models.ForeignKey("Conversa", null=True, on_delete=models.CASCADE, related_name="mensagens")
    remetente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="mensagens_match_enviadas")
    apagada_em = models.DateTimeField(null=True, blank=True, editable=False)
    texto = models.TextField(max_length=1200)
    lida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em"]
        verbose_name = "Mensagem de match"
        verbose_name_plural = "Mensagens de matches"
        indexes = [
            models.Index(fields=["conversa", "id"], name="nk_chat_conversa_id_idx"),
            models.Index(fields=["match", "id"], name="nk_chat_match_id_idx"),
        ]

    def __str__(self):
        return f"Mensagem em {self.match} - {self.criado_em:%d/%m/%Y %H:%M}"


# Mantém o NKATA ID num módulo isolado sem deixar de o registar no app Django.
from .identity_models import VerificacaoIdentidadeNKATA  # noqa: E402,F401


class AcessoPlanoNKATA(models.Model):
    """Entitlement with a fixed validity; not evidence of payment."""

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="acesso_plano_nkata")
    plano = models.CharField(max_length=16, choices=[("ESSENCIAL", "Essencial"), ("PREMIUM", "Premium"), ("QUINZENAL", "Quinzenal")])
    inicio = models.DateTimeField()
    fim = models.DateTimeField(db_index=True)
    origem = models.CharField(max_length=32, default="ADMINISTRATIVA", editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(fim__gt=models.F("inicio")), name="nkata_plano_validade_positiva"),
            models.CheckConstraint(condition=models.Q(plano__in=["ESSENCIAL", "PREMIUM", "QUINZENAL"]), name="nkata_plano_pago_valido"),
        ]


class PromocaoLancamentoNKATA(models.Model):
    codigo = models.CharField(max_length=32, primary_key=True)
    vagas_atribuidas = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(vagas_atribuidas__lte=100),
                name="nkata_promocao_lancamento_ate_100",
            ),
        ]


class PedidoPagamentoNKATA(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pagamentos_nkata")
    chave = models.UUIDField()
    referencia = models.CharField(max_length=50, unique=True)
    produto = models.CharField(max_length=24)
    simulado = models.BooleanField(default=False, editable=False, db_index=True)
    valor = models.DecimalField(max_digits=8, decimal_places=2)
    moeda = models.CharField(max_length=3, default="MZN")
    dias = models.PositiveSmallIntegerField(default=0)
    creditos = models.PositiveSmallIntegerField(default=0)
    estado = models.CharField(max_length=16, default="CRIADO", choices=[(s, s) for s in ("CRIADO", "PENDENTE", "INCERTO", "PAGO", "FALHOU", "REVISAO")])
    provedor_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    checkout_url = models.URLField(max_length=500, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    confirmado_em = models.DateTimeField(null=True, blank=True)
    aplicado_em = models.DateTimeField(null=True, blank=True)
    validade_concedida = models.DateTimeField(null=True, blank=True)
    ultima_verificacao = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["usuario", "chave"], name="nkata_pagamento_idempotente"),
            models.CheckConstraint(condition=models.Q(valor__gte=50, valor__lte=500), name="nkata_pagamento_limites"),
            models.CheckConstraint(condition=models.Q(moeda="MZN"), name="nkata_pagamento_mzn"),
        ]


class VotoPerguntaDiaria(models.Model):
    mostrar_participacao = models.BooleanField(default=False)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    data = models.DateField()
    opcao = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["data", "usuario"], name="nkata_um_voto_por_dia"),
            models.CheckConstraint(condition=models.Q(opcao__in=[0, 1]), name="nkata_voto_diario_valido"),
        ]


class Conversa(models.Model):
    ESTADO_ATIVA = "ATIVA"
    ESTADO_ENCERRADA = "ENCERRADA"
    estado = models.CharField(max_length=10, default=ESTADO_ATIVA, choices=[(ESTADO_ATIVA, "Ativa"), (ESTADO_ENCERRADA, "Encerrada")])
    # Legacy audio, calls and messages still depend on this match.
    # Do not allow a standalone match deletion to destroy chat history.
    match_origem = models.OneToOneField(MatchPerfil, null=True, on_delete=models.RESTRICT, related_name="chat")
    perfil_1 = models.ForeignKey(PerfilNKATA, on_delete=models.CASCADE, related_name="+")
    perfil_2 = models.ForeignKey(PerfilNKATA, on_delete=models.CASCADE, related_name="+")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(perfil_1__lt=models.F("perfil_2")), name="conversa_par_ordenado"),
            models.UniqueConstraint(fields=["perfil_1", "perfil_2"], name="conversa_unica_por_par"),
            models.CheckConstraint(condition=models.Q(estado__in=["ATIVA", "ENCERRADA"]), name="conversa_estado_valido"),
        ]


class PedidoConversa(models.Model):
    remetente = models.ForeignKey(PerfilNKATA, on_delete=models.CASCADE, related_name="pedidos_chat_enviados")
    destinatario = models.ForeignKey(PerfilNKATA, on_delete=models.CASCADE, related_name="pedidos_chat_recebidos")
    ESTADOS = [(s, label) for s, label in (("PENDENTE", "Pendente"), ("ACEITE", "Aceite"), ("RECUSADO", "Recusado"), ("EXPIRADO", "Expirado"), ("CANCELADO", "Cancelado"))]
    estado = models.CharField(max_length=10, default="PENDENTE", choices=ESTADOS)
    expira_em = models.DateTimeField()
    decidido_em = models.DateTimeField(null=True)
    conversa = models.ForeignKey(Conversa, null=True, on_delete=models.SET_NULL)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~models.Q(remetente=models.F("destinatario")), name="pedido_chat_perfis_distintos"),
            models.UniqueConstraint(fields=["remetente", "destinatario"], condition=models.Q(estado="PENDENTE"), name="pedido_chat_pendente_unico"),
            models.CheckConstraint(condition=models.Q(estado__in=["PENDENTE", "ACEITE", "RECUSADO", "EXPIRADO", "CANCELADO"]), name="pedido_chat_estado_valido"),
        ]



# Financial records are separate from subscriptions and historical signal grants.
class CarteiraNKATA(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="carteira_nkata")
    saldo = models.PositiveBigIntegerField(default=0, editable=False)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)


class MovimentoCreditoNKATA(models.Model):
    carteira = models.ForeignKey(CarteiraNKATA, on_delete=models.PROTECT, related_name="movimentos")
    chave = models.CharField(max_length=120)
    tipo = models.CharField(max_length=20, choices=[("BONUS", "Bónus"), ("RECARGA", "Recarga"), ("CONSUMO", "Consumo"), ("ESTORNO", "Estorno"), ("AJUSTE", "Ajuste")])
    quantidade = models.BigIntegerField()
    saldo_apos = models.PositiveBigIntegerField()
    referencia = models.CharField(max_length=120)
    motivo = models.CharField(max_length=240)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(fields=["carteira", "chave"], name="nk_credito_chave_unica"),
            models.CheckConstraint(condition=(
                models.Q(tipo__in=["BONUS", "RECARGA", "ESTORNO"], quantidade__gt=0)
                | models.Q(tipo="CONSUMO", quantidade__lt=0)
                | (models.Q(tipo="AJUSTE") & ~models.Q(quantidade=0))
            ), name="nk_credito_movimento_valido"),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Movimentos financeiros não podem ser alterados.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Movimentos financeiros não podem ser apagados.")



class AcessoChatCreditoNKATA(models.Model):
    movimento = models.OneToOneField(MovimentoCreditoNKATA, on_delete=models.PROTECT, related_name="acesso_chat")
    inicio = models.DateTimeField()
    fim = models.DateTimeField(db_index=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(fim__gt=models.F("inicio")), name="nk_credito_chat_validade")]



class EnvioAudioCreditoNKATA(models.Model):
    """Receipt linking one paid upload to its original private audio record."""
    movimento = models.OneToOneField(MovimentoCreditoNKATA, on_delete=models.PROTECT, related_name="envio_audio")
    audio_id = models.PositiveBigIntegerField(unique=True)
    match_id = models.PositiveBigIntegerField()
    criado_em = models.DateTimeField(auto_now_add=True)


class TarifacaoChamadaNKATA(models.Model):
    """Commercial authorization for a historical call; not a media transport."""
    chamada_id = models.PositiveBigIntegerField(unique=True)
    match_id = models.PositiveBigIntegerField()
    pagador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tarifacoes_chamada_nkata")
    tipo = models.CharField(max_length=12, choices=[("AUDIO", "Áudio"), ("VIDEO", "Vídeo")])
    custo_minuto = models.PositiveSmallIntegerField()
    max_minutos = models.PositiveSmallIntegerField()
    minutos_pagos = models.PositiveSmallIntegerField(default=0)
    pago_ate = models.DateTimeField(null=True, blank=True)
    encerrada_em = models.DateTimeField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(custo_minuto__gt=0, max_minutos__gt=0, minutos_pagos__lte=models.F("max_minutos")), name="nk_tarifa_chamada_limites"),
            models.CheckConstraint(condition=(models.Q(minutos_pagos=0, pago_ate__isnull=True) | models.Q(minutos_pagos__gt=0, pago_ate__isnull=False)), name="nk_tarifa_chamada_validade"),
        ]


class BonusIdentidadeCreditoNKATA(models.Model):
    """One welcome award per confirmed document, even across account changes."""
    documento_chave = models.CharField(max_length=64, unique=True, editable=False)
    movimento = models.OneToOneField(MovimentoCreditoNKATA, on_delete=models.PROTECT, related_name="bonus_identidade")
    criado_em = models.DateTimeField(auto_now_add=True)


class NotaVozConversaNKATA(models.Model):
    mensagem = models.OneToOneField(MensagemMatch, on_delete=models.PROTECT, related_name="nota_voz")
    movimento = models.OneToOneField(MovimentoCreditoNKATA, on_delete=models.PROTECT, related_name="nota_voz_conversa")
    audio = models.FileField(storage=private_content_storage, upload_to="chat-native/%Y/%m/%d/")
    duracao_segundos = models.PositiveSmallIntegerField()


class ChamadaConversaCreditoNKATA(models.Model):
    """Internal session for a future trusted media gateway; no browser billing."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversa = models.ForeignKey(Conversa, on_delete=models.PROTECT, related_name="chamadas_credito")
    iniciador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="chamadas_credito_iniciadas")
    destinatario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="chamadas_credito_recebidas")
    chave = models.UUIDField()
    tipo = models.CharField(max_length=5, choices=[("AUDIO","Áudio"),("VIDEO","Vídeo")])
    estado = models.CharField(max_length=12, default="CHAMANDO", choices=[(s,s) for s in ("CHAMANDO","ACEITE","ATIVA","TERMINADA","RECUSADA","EXPIRADA")])
    custo_minuto = models.PositiveSmallIntegerField()
    max_minutos = models.PositiveSmallIntegerField()
    minutos_pagos = models.PositiveSmallIntegerField(default=0)
    expira_em = models.DateTimeField()
    pago_ate = models.DateTimeField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["iniciador","chave"],name="nk_call_native_key"),
            models.CheckConstraint(condition=~models.Q(iniciador=models.F("destinatario")),name="nk_call_native_distinct"),
            models.CheckConstraint(condition=models.Q(max_minutos__gte=1,max_minutos__lte=120,minutos_pagos__lte=models.F("max_minutos")),name="nk_call_native_minutes"),
            models.CheckConstraint(condition=models.Q(tipo="AUDIO",custo_minuto=3)|models.Q(tipo="VIDEO",custo_minuto=5),name="nk_call_native_rate"),
            models.CheckConstraint(condition=models.Q(minutos_pagos=0,pago_ate__isnull=True)|models.Q(minutos_pagos__gt=0,pago_ate__isnull=False),name="nk_call_native_lease"),
        ]
