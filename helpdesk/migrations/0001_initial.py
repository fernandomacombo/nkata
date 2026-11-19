import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="SupportTicket",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False, default=uuid.uuid4, editable=False)),
                ("email", models.EmailField(max_length=254)),
                ("category", models.CharField(max_length=24, choices=[("conta", "Conta e acesso"), ("identidade", "Verificação de identidade"), ("pagamentos", "Pagamentos e pacotes"), ("mensagens", "Mensagens e momentos"), ("seguranca", "Segurança e denúncias"), ("outro", "Outro assunto")])),
                ("subject", models.CharField(max_length=140)),
                ("description", models.TextField(max_length=4000)),
                ("status", models.CharField(max_length=24, default="aberto", db_index=True, choices=[("aberto", "Aberto"), ("em_analise", "Em análise"), ("aguarda_resposta", "A aguardar resposta"), ("resolvido", "Resolvido")])),
                ("internal_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="nkata_support_tickets", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Pedido de suporte", "verbose_name_plural": "Pedidos de suporte", "ordering": ["-created_at"]},
        ),
    ]
