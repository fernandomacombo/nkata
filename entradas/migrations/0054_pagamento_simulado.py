from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("entradas", "0053_bonus_identidade_creditos")]
    operations = [
        migrations.AddField(model_name="pedidopagamentonkata", name="simulado",
            field=models.BooleanField(default=False, editable=False, db_index=True)),
    ]
