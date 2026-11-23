from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("entradas", "0036_mensagemmatch_apagada_em_and_more")]
    operations = [
        migrations.AddField(
            model_name="preferenciascontankata",
            name="aviso_chat_aceite",
            field=models.BooleanField(default=False),
        ),
    ]
