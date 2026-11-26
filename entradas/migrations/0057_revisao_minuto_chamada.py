import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("entradas", "0056_chamada_conversa_credito")]
    operations = [
        migrations.CreateModel(
            name="RevisaoMinutoChamadaNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("minuto", models.PositiveSmallIntegerField()),
                ("estado", models.CharField(max_length=16, default="AUTORIZADO", choices=[
                    ("AUTORIZADO", "Autorizado"), ("RETOMA_INICIADA", "Retoma iniciada"),
                    ("CONFIRMADO", "Retoma confirmada"), ("ESTORNADO", "Estornado")])),
                ("prazo", models.DateTimeField()),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("atualizada_em", models.DateTimeField(auto_now=True)),
                ("chamada", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="revisoes_minutos", to="entradas.chamadaconversacreditonkata")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=["chamada", "minuto"], name="nk_call_review_minute"),
                    models.CheckConstraint(condition=models.Q(minuto__gte=1, minuto__lte=120), name="nk_call_review_range"),
                ],
                "indexes": [models.Index(fields=["estado", "prazo"], name="nk_call_review_due_idx")],
            },
        ),
    ]
