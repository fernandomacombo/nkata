from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("entradas", "0045_estados_pedido_conversa")]
    operations = [
        migrations.AddIndex(
            model_name="mensagemmatch",
            index=models.Index(fields=["conversa", "id"], name="nk_chat_conversa_id_idx"),
        ),
        migrations.AddIndex(
            model_name="mensagemmatch",
            index=models.Index(fields=["match", "id"], name="nk_chat_match_id_idx"),
        ),
    ]
