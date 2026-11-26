import django.db.models.deletion
from django.db import migrations, models


def reconciliar_mensagens(apps, schema_editor):
    db = schema_editor.connection.alias
    Conversa = apps.get_model("entradas", "Conversa")
    Mensagem = apps.get_model("entradas", "MensagemMatch")
    # Only reconcile matches already associated with a conversation.
    # Do not create new conversations or grant consent to unrelated matches.
    for chat_id, match_id in Conversa.objects.using(db).exclude(
        match_origem_id__isnull=True
    ).values_list("pk", "match_origem_id").iterator():
        Mensagem.objects.using(db).filter(
            match_id=match_id, conversa_id__isnull=True
        ).update(conversa_id=chat_id)


class Migration(migrations.Migration):
    dependencies = [("entradas", "0042_associar_historico_chats")]
    operations = [
        migrations.AlterField(
            model_name="conversa",
            name="match_origem",
            field=models.OneToOneField(
                null=True, on_delete=django.db.models.deletion.RESTRICT,
                related_name="chat", to="entradas.matchperfil"
            ),
        ),
        migrations.RunPython(reconciliar_mensagens, migrations.RunPython.noop),
    ]
