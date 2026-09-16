from django.db import migrations, models

import entradas.storage_backends


class Migration(migrations.Migration):

    dependencies = [
        ("entradas", "0014_prepare_feature_tables"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pedidoentrada",
            name="foto_perfil",
            field=models.ImageField(
                storage=entradas.storage_backends.profile_media_storage,
                upload_to="pedidos/fotos/",
            ),
        ),
        migrations.AlterField(
            model_name="pedidoentrada",
            name="foto_extra_1",
            field=models.ImageField(
                storage=entradas.storage_backends.profile_media_storage,
                upload_to="pedidos/fotos/",
            ),
        ),
        migrations.AlterField(
            model_name="pedidoentrada",
            name="foto_extra_2",
            field=models.ImageField(
                storage=entradas.storage_backends.profile_media_storage,
                upload_to="pedidos/fotos/",
            ),
        ),
        migrations.AlterField(
            model_name="pedidoentrada",
            name="foto_extra_3",
            field=models.ImageField(
                storage=entradas.storage_backends.profile_media_storage,
                upload_to="pedidos/fotos/",
            ),
        ),
        migrations.AlterField(
            model_name="pedidoentrada",
            name="bi_frente",
            field=models.ImageField(
                storage=entradas.storage_backends.identity_media_storage,
                upload_to="pedidos/documentos/",
            ),
        ),
        migrations.AlterField(
            model_name="pedidoentrada",
            name="bi_verso",
            field=models.ImageField(
                storage=entradas.storage_backends.identity_media_storage,
                upload_to="pedidos/documentos/",
            ),
        ),
        migrations.AlterField(
            model_name="pedidoentrada",
            name="selfie_com_bi",
            field=models.ImageField(
                storage=entradas.storage_backends.identity_media_storage,
                upload_to="pedidos/documentos/",
            ),
        ),
    ]
