import uuid
from django.conf import settings
from django.db import models


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
    nome_completo = models.CharField(max_length=160)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=30)
    idade = models.PositiveIntegerField()
    cidade = models.CharField(max_length=100)
    genero = models.CharField(max_length=30, choices=GENERO_CHOICES)
    objetivo = models.CharField(max_length=40, choices=OBJETIVO_CHOICES)
    aceita_verificacao = models.BooleanField(default=False)
    foto_perfil = models.ImageField(upload_to="pedidos/fotos/")
    foto_extra_1 = models.ImageField(upload_to="pedidos/fotos/")
    foto_extra_2 = models.ImageField(upload_to="pedidos/fotos/")
    foto_extra_3 = models.ImageField(upload_to="pedidos/fotos/")
    bi_frente = models.ImageField(upload_to="pedidos/documentos/")
    bi_verso = models.ImageField(upload_to="pedidos/documentos/")
    selfie_com_bi = models.ImageField(upload_to="pedidos/documentos/")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="PENDENTE")
    observacao_admin = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pedido de entrada"
        verbose_name_plural = "Pedidos de entrada"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.nome_completo} - {self.get_status_display()}"


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
    STATUS_CHOICES = [
        ("ATIVO", "Ativo"),
        ("PAUSADO", "Pausado"),
        ("BLOQUEADO", "Bloqueado"),
    ]
    pedido = models.OneToOneField(PedidoEntrada, on_delete=models.CASCADE, related_name="perfil")
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="perfil_nkata")
    nome_publico = models.CharField(max_length=120)
    cidade = models.CharField(max_length=100)
    idade = models.PositiveIntegerField()
    genero = models.CharField(max_length=30, choices=PedidoEntrada.GENERO_CHOICES)
    objetivo = models.CharField(max_length=40, choices=PedidoEntrada.OBJETIVO_CHOICES)
    sobre_si = models.TextField()
    o_que_valoriza = models.TextField()
    o_que_nao_aceita = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="ATIVO")
    visivel = models.BooleanField(default=True)
    owner_session_key = models.CharField(max_length=120, blank=True, db_index=True)
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
    match = models.ForeignKey(MatchPerfil, on_delete=models.CASCADE, related_name="mensagens")
    remetente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="mensagens_match_enviadas")
    texto = models.TextField(max_length=1200)
    lida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em"]
        verbose_name = "Mensagem de match"
        verbose_name_plural = "Mensagens de matches"

    def __str__(self):
        return f"Mensagem em {self.match} - {self.criado_em:%d/%m/%Y %H:%M}"
