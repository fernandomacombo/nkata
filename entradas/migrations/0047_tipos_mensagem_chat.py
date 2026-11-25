from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("entradas", "0046_indices_paginacao_chats")]
    operations = [
        migrations.AddField(
            model_name="mensagemmatch", name="tipo",
            field=models.CharField(max_length=16, default="TEXTO", choices=[("TEXTO", "Texto"), ("SINAL", "Sinal"), ("QUEBRA_GELO", "Quebra-gelo")]),
        ),
        migrations.AddField(
            model_name="mensagemmatch", name="sinal_origem",
            field=models.OneToOneField(to="entradas.acaoperfil", null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name="mensagem_chat"),
        ),
    ]
