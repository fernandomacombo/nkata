from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("entradas", "0048_mensagem_predefinida"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="CarteiraNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("saldo", models.PositiveBigIntegerField(default=0, editable=False)),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("atualizada_em", models.DateTimeField(auto_now=True)),
                ("usuario", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="carteira_nkata", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="MovimentoCreditoNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chave", models.CharField(max_length=120)),
                ("tipo", models.CharField(choices=[("BONUS", "Bónus"), ("RECARGA", "Recarga"), ("CONSUMO", "Consumo"), ("ESTORNO", "Estorno"), ("AJUSTE", "Ajuste")], max_length=20)),
                ("quantidade", models.BigIntegerField()),
                ("saldo_apos", models.PositiveBigIntegerField()),
                ("referencia", models.CharField(max_length=120)),
                ("motivo", models.CharField(max_length=240)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("carteira", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="movimentos", to="entradas.carteirankata")),
            ],
            options={"ordering": ["-id"], "constraints": [
                models.UniqueConstraint(fields=("carteira", "chave"), name="nk_credito_chave_unica"),
                models.CheckConstraint(condition=(models.Q(tipo__in=["BONUS", "RECARGA", "ESTORNO"], quantidade__gt=0) | models.Q(tipo="CONSUMO", quantidade__lt=0) | (models.Q(tipo="AJUSTE") & ~models.Q(quantidade=0))), name="nk_credito_movimento_valido"),
            ]},
        ),
    ]
