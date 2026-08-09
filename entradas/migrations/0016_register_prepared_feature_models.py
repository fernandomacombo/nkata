"""Regista no estado do Django as tabelas adotadas pela migração 0014.

As tabelas já existem no banco. Como estes modelos continuam ``managed=False``,
as operações ``CreateModel`` abaixo atualizam somente o estado das migrations e
não tentam recriar ou apagar as tabelas existentes.
"""

import entradas.moments_models
import entradas.storage_backends
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("entradas", "0015_protect_identity_and_profile_media"),
    ]

    operations = [
        migrations.CreateModel(
            name="AnaliseAutomaticaConteudoNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content_type", models.CharField(choices=[("MOMENTO", "Momento"), ("PUBLICACAO", "Publicação")], max_length=16)),
                ("content_id", models.PositiveBigIntegerField()),
                ("media_type", models.CharField(choices=[("IMAGEM", "Imagem"), ("VIDEO", "Vídeo")], max_length=12)),
                ("provider", models.CharField(default="manual", max_length=32)),
                ("model_name", models.CharField(blank=True, max_length=80)),
                ("status", models.CharField(choices=[("REVISAO", "Revisão humana necessária"), ("BAIXO_RISCO", "Baixo risco"), ("ALTO_RISCO", "Risco elevado"), ("ERRO", "Análise indisponível")], default="REVISAO", max_length=16)),
                ("risk_level", models.CharField(choices=[("INDEFINIDO", "Indefinido"), ("BAIXO", "Baixo"), ("MEDIO", "Médio"), ("ALTO", "Alto"), ("CRITICO", "Crítico")], default="INDEFINIDO", max_length=12)),
                ("flagged", models.BooleanField(default=False)),
                ("file_sha256", models.CharField(blank=True, db_index=True, max_length=64)),
                ("media_bytes", models.PositiveBigIntegerField(default=0)),
                ("image_width", models.PositiveIntegerField(blank=True, null=True)),
                ("image_height", models.PositiveIntegerField(blank=True, null=True)),
                ("categories", models.JSONField(blank=True, default=dict)),
                ("category_scores", models.JSONField(blank=True, default=dict)),
                ("notes", models.CharField(blank=True, max_length=500)),
                ("human_decision", models.CharField(blank=True, choices=[("", "Sem decisão"), ("APROVADO", "Aprovado"), ("REJEITADO", "Rejeitado"), ("GRAVE", "Rejeitado por violação grave")], max_length=12)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Análise automática de conteúdo NKATA",
                "verbose_name_plural": "Análises automáticas de conteúdo NKATA",
                "db_table": "entradas_analiseautomaticaconteudonkata",
                "ordering": ["-atualizado_em"],
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="ChamadaMatchNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("AUDIO", "Chamada de áudio"), ("VIDEO", "Videochamada")], max_length=12)),
                ("estado", models.CharField(choices=[("CHAMANDO", "A chamar"), ("CONECTANDO", "A conectar"), ("ATIVA", "Ativa"), ("RECUSADA", "Recusada"), ("TERMINADA", "Terminada"), ("PERDIDA", "Não atendida"), ("FALHOU", "Falhou")], db_index=True, default="CHAMANDO", max_length=16)),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("atualizada_em", models.DateTimeField(auto_now=True)),
                ("atendida_em", models.DateTimeField(blank=True, null=True)),
                ("terminada_em", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "entradas_chamadamatchnkata",
                "ordering": ["-criada_em"],
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="DenunciaPublicacaoNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("motivo", models.CharField(choices=[("NUDEZ_SEXUAL", "Nudez ou conteúdo sexual"), ("SERVICOS_SEXUAIS", "Serviços sexuais ou prostituição"), ("CONTACTOS_PUBLICIDADE", "Contactos, publicidade ou venda"), ("ASSEDIO", "Assédio, ameaça ou discurso ofensivo"), ("FRAUDE", "Fraude, perfil falso ou conteúdo enganoso"), ("PRIVACIDADE_TERCEIROS", "Exposição de terceiros sem consentimento")], max_length=32)),
                ("estado", models.CharField(choices=[("PENDENTE", "Pendente"), ("ANALISADA", "Analisada")], db_index=True, default="PENDENTE", max_length=12)),
                ("criado_em", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("analisado_em", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "Denúncia de Publicação NKATA",
                "verbose_name_plural": "Denúncias de Publicações NKATA",
                "db_table": "entradas_denunciapublicacaonkata",
                "ordering": ["-criado_em"],
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="EstadoConversaNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_typing", models.BooleanField(default=False)),
                ("typing_updated_at", models.DateTimeField(blank=True, null=True)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "entradas_estadoconversankata",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="MensagemAudioMatchNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("audio", models.FileField(storage=entradas.storage_backends.private_content_storage, upload_to="chat/%Y/%m/%d/")),
                ("duracao_segundos", models.PositiveSmallIntegerField(default=0)),
                ("lida", models.BooleanField(default=False)),
                ("criado_em", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "verbose_name": "Nota de voz NKATA",
                "verbose_name_plural": "Notas de voz NKATA",
                "db_table": "entradas_mensagemaudiomatchnkata",
                "ordering": ["criado_em", "id"],
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="MomentoNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("texto", models.CharField(blank=True, max_length=500)),
                ("media", models.FileField(blank=True, storage=entradas.storage_backends.private_content_storage, upload_to="moments/%Y/%m/%d/")),
                ("tipo_media", models.CharField(choices=[("TEXTO", "Frase NKATA"), ("IMAGEM", "Imagem"), ("VIDEO", "Vídeo")], default="TEXTO", max_length=12)),
                ("visibilidade", models.CharField(choices=[("TODOS", "Todos os membros"), ("MATCHES", "Apenas matches")], default="TODOS", max_length=12)),
                ("moderacao_status", models.CharField(choices=[("PENDENTE", "Pendente"), ("APROVADO", "Aprovado"), ("REJEITADO", "Rejeitado")], db_index=True, default="PENDENTE", max_length=12)),
                ("moderacao_motivo", models.CharField(blank=True, max_length=240)),
                ("moderado_em", models.DateTimeField(blank=True, null=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("expira_em", models.DateTimeField(db_index=True, default=entradas.moments_models.moment_expires_at)),
            ],
            options={
                "verbose_name": "Momento NKATA",
                "verbose_name_plural": "Momentos NKATA",
                "db_table": "entradas_momentonakata",
                "ordering": ["-criado_em"],
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="OcultacaoPublicacaoNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Publicação ocultada NKATA",
                "verbose_name_plural": "Publicações ocultadas NKATA",
                "db_table": "entradas_ocultacaopublicacaonkata",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="PublicacaoNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("media", models.FileField(storage=entradas.storage_backends.private_content_storage, upload_to="posts/%Y/%m/%d/")),
                ("tipo_media", models.CharField(choices=[("IMAGEM", "Imagem"), ("VIDEO", "Vídeo")], max_length=12)),
                ("legenda", models.CharField(blank=True, max_length=180)),
                ("visibilidade", models.CharField(choices=[("TODOS", "Todos os membros"), ("MATCHES", "Apenas matches")], default="TODOS", max_length=12)),
                ("moderacao_status", models.CharField(choices=[("PENDENTE", "Pendente"), ("APROVADO", "Aprovado"), ("REJEITADO", "Rejeitado")], db_index=True, default="PENDENTE", max_length=12)),
                ("moderacao_motivo", models.CharField(blank=True, max_length=240)),
                ("moderado_em", models.DateTimeField(blank=True, null=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Publicação NKATA",
                "verbose_name_plural": "Publicações NKATA",
                "db_table": "entradas_publicacaonkata",
                "ordering": ["-criado_em"],
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="ReacaoMomentoNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("CORACAO", "Gostei"), ("FLOR", "Flor"), ("APLAUSO", "Bonito")], max_length=16)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Reação a Momento NKATA",
                "verbose_name_plural": "Reações a Momentos NKATA",
                "db_table": "entradas_reacaomomentonakata",
                "ordering": ["-atualizado_em"],
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="ReacaoPublicacaoNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("GOSTEI", "Gostei"), ("FLOR", "Flor"), ("APRECIAR", "Apreciar")], max_length=16)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Reação a Publicação NKATA",
                "verbose_name_plural": "Reações a Publicações NKATA",
                "db_table": "entradas_reacaopublicacaonkata",
                "ordering": ["-atualizado_em"],
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="SinalChamadaNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("OFFER", "Oferta SDP"), ("ANSWER", "Resposta SDP"), ("ICE", "Candidato ICE")], max_length=12)),
                ("payload", models.JSONField(default=dict)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "entradas_sinalchamadankata",
                "ordering": ["id"],
                "managed": False,
            },
        ),
        migrations.AlterModelOptions(
            name="mensagemperfil",
            options={"ordering": ["-criado_em"]},
        ),
        migrations.AlterField(
            model_name="acaoperfil",
            name="tipo",
            field=models.CharField(choices=[("INTERESSE", "Tenho interesse"), ("GOSTAR", "Gostar"), ("SEGUIR", "Seguir"), ("GUARDADO", "Perfil guardado"), ("BLOQUEIO", "Bloquear"), ("SINAL_FLOR", "Sinal — Flor"), ("SINAL_BEIJINHO", "Sinal — Beijinho"), ("SINAL_OLA", "Sinal — Olá")], max_length=30),
        ),
    ]
