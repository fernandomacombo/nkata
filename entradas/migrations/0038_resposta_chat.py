from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("entradas", "0037_chat_safety_notice")]
    operations = [
        migrations.AddField(
            model_name="mensagemmatch",
            name="resposta_a",
            field=models.ForeignKey("entradas.mensagemmatch", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"),
        ),
    ]
