from django.db import migrations, models


CAPABILITY_GROUPS = [
    "NKATA_STAFF_VISAO_GERAL",
    "NKATA_STAFF_PEDIDOS",
    "NKATA_STAFF_MEMBROS",
    "NKATA_STAFF_MODERACAO",
    "NKATA_STAFF_DENUNCIAS",
    "NKATA_STAFF_OPERACOES",
    "NKATA_STAFF_AUDITORIA",
]


def prepare_staff_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    PerfilNKATA = apps.get_model("entradas", "PerfilNKATA")

    for name in CAPABILITY_GROUPS:
        Group.objects.get_or_create(name=name)

    # Contas administrativas não participam na comunidade como perfis normais.
    PerfilNKATA.objects.filter(usuario__is_staff=True).update(
        status="PAUSADO",
        visivel=False,
        destaque_publico=False,
        pausa_iniciada_pelo_usuario=False,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("entradas", "0021_merge_0017_nkata_id_0020_pushsubscriptionnkata"),
    ]

    operations = [
        migrations.AlterField(
            model_name="perfilnkata",
            name="status",
            field=models.CharField(
                choices=[
                    ("ATIVO", "Ativo"),
                    ("PAUSADO", "Pausado"),
                    ("BLOQUEADO", "Bloqueado"),
                    ("ENCERRAMENTO", "Encerramento solicitado"),
                ],
                default="ATIVO",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="perfilnkata",
            name="pausa_iniciada_pelo_usuario",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="perfilnkata",
            name="pausado_ate",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="perfilnkata",
            name="motivo_pausa",
            field=models.CharField(blank=True, max_length=240),
        ),
        migrations.AddField(
            model_name="perfilnkata",
            name="encerramento_solicitado_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="perfilnkata",
            name="motivo_encerramento",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.RunPython(prepare_staff_roles, migrations.RunPython.noop),
    ]
