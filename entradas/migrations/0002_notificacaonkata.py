# Generated manually for the NKATA notification centre.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("entradas", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificacaoNKATA",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("INTERESSE", "Novo interesse"),
                            ("MATCH", "Novo match"),
                            ("MENSAGEM", "Nova mensagem"),
                            ("EQUIPA", "Aviso da equipa"),
                        ],
                        max_length=20,
                    ),
                ),
                ("titulo", models.CharField(max_length=120)),
                ("texto", models.CharField(max_length=320)),
                ("chave", models.CharField(max_length=120)),
                ("lida", models.BooleanField(default=False)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                (
                    "ator",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="notificacoes_nkata_criadas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "destinatario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notificacoes_nkata",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "match",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="notificacoes",
                        to="entradas.matchperfil",
                    ),
                ),
                (
                    "perfil",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="notificacoes",
                        to="entradas.perfilnkata",
                    ),
                ),
            ],
            options={
                "verbose_name": "Notificação NKATA",
                "verbose_name_plural": "Notificações NKATA",
                "ordering": ["-atualizado_em"],
                "indexes": [
                    models.Index(
                        fields=["destinatario", "lida", "atualizado_em"],
                        name="nkata_notif_user_read_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("destinatario", "chave"),
                        name="notificacao_unica_por_destinatario_e_chave",
                    )
                ],
            },
        ),
    ]
