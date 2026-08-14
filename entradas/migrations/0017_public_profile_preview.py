from django.db import migrations, models


def approve_existing_verified_photos(apps, schema_editor):
    PerfilNKATA = apps.get_model("entradas", "PerfilNKATA")
    PerfilNKATA.objects.filter(
        pedido__status="APROVADO",
    ).exclude(
        pedido__foto_perfil="",
    ).update(foto_destaque_publico_aprovada=True)


def disable_public_previews(apps, schema_editor):
    PerfilNKATA = apps.get_model("entradas", "PerfilNKATA")
    PerfilNKATA.objects.update(
        destaque_publico=False,
        foto_destaque_publico_aprovada=False,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("entradas", "0016_register_prepared_feature_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfilnkata",
            name="destaque_publico",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="perfilnkata",
            name="destaque_publico_consentido_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="perfilnkata",
            name="destaque_publico_exibicoes",
            field=models.PositiveBigIntegerField(default=0, editable=False),
        ),
        migrations.AddField(
            model_name="perfilnkata",
            name="destaque_publico_ultima_exibicao_em",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="perfilnkata",
            name="foto_destaque_publico_aprovada",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            approve_existing_verified_photos,
            disable_public_previews,
        ),
    ]
