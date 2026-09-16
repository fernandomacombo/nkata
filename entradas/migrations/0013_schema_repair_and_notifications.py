from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def ensure_notification_table(apps, schema_editor):
    """Adota tabelas antigas criadas pelo comando setup sem recriá-las."""
    # SeparateDatabaseAndState entrega aqui o estado anterior. A importação
    # local usa o modelo atual apenas para materializar a tabela quando ela
    # ainda não foi criada pelo antigo comando setup_nkata_notifications.
    from entradas.notification_models import NotificacaoNKATA

    notification = NotificacaoNKATA
    existing = set(schema_editor.connection.introspection.table_names())
    if notification._meta.db_table not in existing:
        schema_editor.create_model(notification)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("entradas", "0012_mensagemmatch"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="mensagemperfil",
            name="mensagem_unica_por_sessao",
        ),
        migrations.RenameField(
            model_name="mensagemperfil",
            old_name="tipo",
            new_name="texto",
        ),
        migrations.AddConstraint(
            model_name="mensagemperfil",
            constraint=models.UniqueConstraint(
                fields=("perfil", "texto", "session_key"),
                name="mensagem_unica_por_sessao",
            ),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    ensure_notification_table,
                    migrations.RunPython.noop,
                ),
            ],
            state_operations=[
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
                                    ("SINAL", "Novo sinal"),
                                    ("MOMENTO", "Reação em Momento"),
                                    ("PUBLICACAO", "Reação em Publicação"),
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
            ],
        ),
    ]
