import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("entradas", "0057_revisao_minuto_chamada"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="EnvioPublicacaoCreditoNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chave", models.UUIDField()),
                ("publicacao_id", models.PositiveBigIntegerField(unique=True)),
                ("tipo_media", models.CharField(max_length=12)),
                ("dia", models.DateField()),
                ("custo", models.PositiveSmallIntegerField()),
                ("fingerprint", models.CharField(max_length=64)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="envios_publicacao_credito", to=settings.AUTH_USER_MODEL)),
                ("movimento", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="envio_publicacao", to="entradas.movimentocreditonkata")),
            ],
            options={"constraints": [
                models.UniqueConstraint(fields=["usuario", "chave"], name="nk_post_credit_key"),
                models.UniqueConstraint(fields=["usuario", "dia"], condition=models.Q(tipo_media="IMAGEM", custo=0), name="nk_post_daily_free"),
                models.CheckConstraint(condition=models.Q(tipo_media="IMAGEM", custo=0, movimento__isnull=True) | models.Q(tipo_media="IMAGEM", custo=2, movimento__isnull=False) | models.Q(tipo_media="VIDEO", custo=5, movimento__isnull=False), name="nk_post_credit_cost"),
            ]},
        ),
    ]
