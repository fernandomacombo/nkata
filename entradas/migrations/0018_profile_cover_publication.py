from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("entradas", "0017_public_profile_preview"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfilnkata",
            name="capa_publicacao_id",
            field=models.PositiveBigIntegerField(
                blank=True,
                db_index=True,
                null=True,
            ),
        ),
    ]
