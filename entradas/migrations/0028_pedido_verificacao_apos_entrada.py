from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("entradas", "0027_fortnight_plan")]

    operations = [
        migrations.AddField(
            model_name="pedidoentrada",
            name="verificacao_apos_entrada",
            field=models.BooleanField(default=False, editable=False),
        ),
    ]
