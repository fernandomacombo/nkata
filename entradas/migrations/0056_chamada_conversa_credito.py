import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("entradas","0055_nota_voz_conversa"),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="ChamadaConversaCreditoNKATA",fields=[
            ("id",models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
            ("chave",models.UUIDField()),
            ("tipo",models.CharField(max_length=5,choices=[("AUDIO","Áudio"),("VIDEO","Vídeo")])),
            ("estado",models.CharField(max_length=12,default="CHAMANDO",choices=[(s,s) for s in ("CHAMANDO","ACEITE","ATIVA","TERMINADA","RECUSADA","EXPIRADA")])),
            ("custo_minuto",models.PositiveSmallIntegerField()),
            ("max_minutos",models.PositiveSmallIntegerField()),
            ("minutos_pagos",models.PositiveSmallIntegerField(default=0)),
            ("expira_em",models.DateTimeField()),
            ("pago_ate",models.DateTimeField(null=True,blank=True)),
            ("criada_em",models.DateTimeField(auto_now_add=True)),
            ("conversa",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="chamadas_credito",to="entradas.conversa")),
            ("iniciador",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="chamadas_credito_iniciadas",to=settings.AUTH_USER_MODEL)),
            ("destinatario",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="chamadas_credito_recebidas",to=settings.AUTH_USER_MODEL)),
        ],options={"constraints":[
            models.UniqueConstraint(fields=["iniciador","chave"],name="nk_call_native_key"),
            models.CheckConstraint(condition=~models.Q(iniciador=models.F("destinatario")),name="nk_call_native_distinct"),
            models.CheckConstraint(condition=models.Q(max_minutos__gte=1,max_minutos__lte=120,minutos_pagos__lte=models.F("max_minutos")),name="nk_call_native_minutes"),
            models.CheckConstraint(condition=models.Q(tipo="AUDIO",custo_minuto=3)|models.Q(tipo="VIDEO",custo_minuto=5),name="nk_call_native_rate"),
            models.CheckConstraint(condition=models.Q(minutos_pagos=0,pago_ate__isnull=True)|models.Q(minutos_pagos__gt=0,pago_ate__isnull=False),name="nk_call_native_lease"),
        ]}),
    ]
