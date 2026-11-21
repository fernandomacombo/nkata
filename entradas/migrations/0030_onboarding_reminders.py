from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("entradas", "0029_extra_photos_visibility")]

    operations = [
        migrations.AddField(
            model_name="pedidoentrada",
            name="onboarding_aprovado_em",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="pedidoentrada",
            name="onboarding_lembrete_em",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]
