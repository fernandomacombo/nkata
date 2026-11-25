from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("entradas", "0052_tarifacao_chamadas")]
    operations = [
        migrations.CreateModel(
            name="BonusIdentidadeCreditoNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("documento_chave", models.CharField(max_length=64, unique=True, editable=False)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("movimento", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="bonus_identidade", to="entradas.movimentocreditonkata")),
            ],
        ),
    ]
