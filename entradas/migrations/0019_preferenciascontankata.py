from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("entradas", "0018_profile_cover_publication"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PreferenciasContaNKATA",
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
                    "idioma",
                    models.CharField(
                        choices=[("PT", "Português"), ("EN", "English")],
                        default="PT",
                        max_length=2,
                    ),
                ),
                (
                    "tema_perfil",
                    models.CharField(
                        choices=[
                            ("CLASSICO", "Clássico"),
                            ("AREIA", "Areia"),
                            ("NOITE", "Noite"),
                        ],
                        default="CLASSICO",
                        max_length=20,
                    ),
                ),
                (
                    "fundo_conversa",
                    models.CharField(
                        choices=[
                            ("SERENO", "Sereno"),
                            ("BOTANICO", "Botânico"),
                            ("NOTURNO", "Noturno"),
                        ],
                        default="SERENO",
                        max_length=20,
                    ),
                ),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                (
                    "usuario",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="preferencias_nkata",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Preferências da conta NKATA",
                "verbose_name_plural": "Preferências das contas NKATA",
            },
        ),
    ]
