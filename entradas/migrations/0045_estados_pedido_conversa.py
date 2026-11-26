from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("entradas", "0044_estado_independente_conversa")]
    operations = [
        migrations.AlterField(
            model_name="pedidoconversa",
            name="estado",
            field=models.CharField(max_length=10, default="PENDENTE", choices=[
                ("PENDENTE", "Pendente"), ("ACEITE", "Aceite"),
                ("RECUSADO", "Recusado"), ("EXPIRADO", "Expirado"),
                ("CANCELADO", "Cancelado"),
            ]),
        ),
        migrations.AddConstraint(
            model_name="pedidoconversa",
            constraint=models.CheckConstraint(
                condition=models.Q(estado__in=["PENDENTE", "ACEITE", "RECUSADO", "EXPIRADO", "CANCELADO"]),
                name="pedido_chat_estado_valido",
            ),
        ),
    ]
