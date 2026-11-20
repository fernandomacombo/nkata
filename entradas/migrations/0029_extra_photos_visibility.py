from django.db import migrations, models




def mark_existing_approved_public_photos(apps, schema_editor):
    Profile = apps.get_model("entradas", "PerfilNKATA")
    Profile.objects.filter(foto_destaque_publico_aprovada=True).update(foto_destaque_publico_estado="APROVADO")

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
        migrations.AddField(
            model_name="perfilnkata",
            name="foto_destaque_publico_estado",
            field=models.CharField(choices=[("PENDENTE", "Pendente"), ("APROVADO", "Aprovado"), ("REJEITADO", "Rejeitado")], default="PENDENTE", max_length=12),
        ),
        migrations.RunPython(mark_existing_approved_public_photos, migrations.RunPython.noop),
    ]
