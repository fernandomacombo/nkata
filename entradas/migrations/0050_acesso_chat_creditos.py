from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("entradas", "0049_carteira_creditos")]
    operations = [
        migrations.CreateModel(
            name="AcessoChatCreditoNKATA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("inicio", models.DateTimeField()),
                ("fim", models.DateTimeField(db_index=True)),
                ("movimento", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="acesso_chat", to="entradas.movimentocreditonkata")),
            ],
            options={"constraints": [models.CheckConstraint(condition=models.Q(fim__gt=models.F("inicio")), name="nk_credito_chat_validade")]},
        ),
    ]
