from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("helpdesk", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SupportReply",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("body", models.TextField(max_length=4000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("staff", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="nkata_support_replies", to=settings.AUTH_USER_MODEL)),
                ("ticket", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="replies", to="helpdesk.supportticket")),
            ],
            options={
                "ordering": ["created_at"],
                "verbose_name": "Resposta de suporte",
                "verbose_name_plural": "Respostas de suporte",
            },
        ),
    ]
