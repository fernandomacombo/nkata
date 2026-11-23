from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("entradas", "0038_resposta_chat")]
    operations = [
        migrations.AddField(
            model_name="perfilnkata", name="ultima_presenca",
            field=models.DateTimeField(null=True, blank=True, editable=False),
        ),
    ]
