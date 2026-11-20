from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("entradas", "0028_pedido_verificacao_apos_entrada")]

    operations = [
        migrations.AddField(
            model_name="pedidoentrada",
            name="foto_extra_1_visivel",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="pedidoentrada",
            name="foto_extra_2_visivel",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="pedidoentrada",
            name="foto_extra_3_visivel",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="pedidoentrada",
            name="foto_extra_1_estado",
            field=models.CharField(choices=[("PENDENTE", "Pendente"), ("APROVADO", "Aprovado"), ("REJEITADO", "Rejeitado")], default="PENDENTE", max_length=12),
        ),
        migrations.AddField(
            model_name="pedidoentrada",
            name="foto_extra_2_estado",
            field=models.CharField(choices=[("PENDENTE", "Pendente"), ("APROVADO", "Aprovado"), ("REJEITADO", "Rejeitado")], default="PENDENTE", max_length=12),
        ),
        migrations.AddField(
            model_name="pedidoentrada",
            name="foto_extra_3_estado",
            field=models.CharField(choices=[("PENDENTE", "Pendente"), ("APROVADO", "Aprovado"), ("REJEITADO", "Rejeitado")], default="PENDENTE", max_length=12),
        ),
    ]
