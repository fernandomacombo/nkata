import django.db.models.deletion
import entradas.storage_backends
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("entradas", "0054_pagamento_simulado")]
    operations = [
        migrations.AlterField(model_name="mensagemmatch", name="tipo", field=models.CharField(
            max_length=16, default="TEXTO", choices=[("TEXTO","Texto"),("SINAL","Sinal"),("QUEBRA_GELO","Quebra-gelo"),("PREDEFINIDA","Predefinida"),("AUDIO","Nota de voz")])),
        migrations.CreateModel(name="NotaVozConversaNKATA", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("audio",models.FileField(storage=entradas.storage_backends.private_content_storage,upload_to="chat-native/%Y/%m/%d/")),
            ("duracao_segundos",models.PositiveSmallIntegerField()),
            ("mensagem",models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name="nota_voz",to="entradas.mensagemmatch")),
            ("movimento",models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name="nota_voz_conversa",to="entradas.movimentocreditonkata")),
        ]),
    ]
