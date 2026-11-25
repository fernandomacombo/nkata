from django.db import migrations, models


def preservar_encerramentos(apps, schema_editor):
    Conversa = apps.get_model("entradas", "Conversa")
    Conversa.objects.using(schema_editor.connection.alias).filter(
        match_origem__status="ENCERRADO"
    ).update(estado="ENCERRADA")


class Migration(migrations.Migration):
    dependencies = [("entradas", "0043_proteger_historico_chats")]
    operations = [
        migrations.AddField(
            model_name="conversa",
            name="estado",
            field=models.CharField(
                max_length=10, default="ATIVA",
                choices=[("ATIVA", "Ativa"), ("ENCERRADA", "Encerrada")],
            ),
        ),
        migrations.RunPython(preservar_encerramentos, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="conversa",
            constraint=models.CheckConstraint(
                condition=models.Q(estado__in=["ATIVA", "ENCERRADA"]),
                name="conversa_estado_valido",
            ),
        ),
    ]
