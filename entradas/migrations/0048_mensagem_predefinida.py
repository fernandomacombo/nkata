from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("entradas", "0047_tipos_mensagem_chat")]
    operations = [
        migrations.AlterField(
            model_name="mensagemmatch", name="tipo",
            field=models.CharField(max_length=16, default="TEXTO", choices=[("TEXTO", "Texto"), ("SINAL", "Sinal"), ("QUEBRA_GELO", "Quebra-gelo"), ("PREDEFINIDA", "Predefinida")]),
        ),
    ]
