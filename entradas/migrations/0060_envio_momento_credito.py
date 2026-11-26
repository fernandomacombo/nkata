import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("entradas", "0059_integrar_regras_e_fotografias"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="EnvioMomentoCreditoNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chave", models.UUIDField()),
                ("momento_id", models.PositiveBigIntegerField(unique=True)),
                ("tipo_media", models.CharField(max_length=12)),
                ("dia", models.DateField()),
                ("custo", models.PositiveSmallIntegerField()),
                ("fingerprint", models.CharField(max_length=64)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="envios_momento_credito", to=settings.AUTH_USER_MODEL)),
                ("movimento", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="envio_momento", to="entradas.movimentocreditonkata")),
            ],
            options={"constraints": [
                models.UniqueConstraint(fields=["usuario", "chave"], name="nk_moment_credit_key"),
                models.UniqueConstraint(fields=["usuario", "dia"], condition=models.Q(tipo_media="IMAGEM", custo=0), name="nk_moment_daily_free"),
                models.CheckConstraint(condition=models.Q(tipo_media="IMAGEM", custo=0, movimento__isnull=True) | models.Q(tipo_media="IMAGEM", custo=2, movimento__isnull=False) | models.Q(tipo_media="VIDEO", custo=5, movimento__isnull=False), name="nk_moment_credit_cost"),
            ]},
        ),
    ]
