from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("entradas", "0039_presenca_perfil")]
    operations = [
        migrations.AddField(
            model_name="votoperguntadiaria",
            name="mostrar_participacao",
            field=models.BooleanField(default=False),
        ),
    ]
