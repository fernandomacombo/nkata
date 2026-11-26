from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("entradas", "0051_recibo_audio_creditos"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="TarifacaoChamadaNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chamada_id", models.PositiveBigIntegerField(unique=True)),
                ("match_id", models.PositiveBigIntegerField()),
                ("pagador", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="tarifacoes_chamada_nkata", to=settings.AUTH_USER_MODEL)),
                ("tipo", models.CharField(max_length=12, choices=[("AUDIO", "Áudio"), ("VIDEO", "Vídeo")])),
                ("custo_minuto", models.PositiveSmallIntegerField()),
                ("max_minutos", models.PositiveSmallIntegerField()),
                ("minutos_pagos", models.PositiveSmallIntegerField(default=0)),
                ("pago_ate", models.DateTimeField(null=True, blank=True)),
                ("encerrada_em", models.DateTimeField(null=True, blank=True)),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
            ],
            options={"constraints": [
                models.CheckConstraint(condition=models.Q(custo_minuto__gt=0, max_minutos__gt=0, minutos_pagos__lte=models.F("max_minutos")), name="nk_tarifa_chamada_limites"),
                models.CheckConstraint(condition=(models.Q(minutos_pagos=0, pago_ate__isnull=True) | models.Q(minutos_pagos__gt=0, pago_ate__isnull=False)), name="nk_tarifa_chamada_validade"),
            ]},
        ),
    ]
