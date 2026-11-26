from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("entradas", "0050_acesso_chat_creditos")]
    operations = [
        migrations.CreateModel(
            name="EnvioAudioCreditoNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("audio_id", models.PositiveBigIntegerField(unique=True)),
                ("match_id", models.PositiveBigIntegerField()),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("movimento", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="envio_audio", to="entradas.movimentocreditonkata")),
            ],
        ),
    ]
