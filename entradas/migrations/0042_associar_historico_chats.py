from django.db import migrations


def associar_historico(apps, schema_editor):
    db = schema_editor.connection.alias
    Match = apps.get_model("entradas", "MatchPerfil")
    Chat = apps.get_model("entradas", "Conversa")
    Message = apps.get_model("entradas", "MensagemMatch")
    activity = ["MensagemMatch", "MensagemAudioMatchNKATA", "ChamadaMatchNKATA", "EstadoConversaNKATA"]
    # Migration 0016 registered the unmanaged tables without their FK fields.
    tables = [apps.get_model("entradas", model)._meta.db_table for model in activity]
    from django.db.models.expressions import RawSQL
    history_ids = " UNION ".join(
        f"SELECT match_id FROM {schema_editor.quote_name(table)}" for table in tables
    )
    for match in Match.objects.using(db).filter(pk__in=RawSQL(history_ids, [])).iterator():
        a, b = sorted((match.perfil_1_id, match.perfil_2_id))
        if a == b:
            raise ValueError(f"Match {match.pk} tem participantes iguais.")
        chat, _ = Chat.objects.using(db).get_or_create(
            perfil_1_id=a, perfil_2_id=b, defaults={"match_origem_id": match.pk})
        if chat.match_origem_id != match.pk:
            raise ValueError(f"O par do match {match.pk} tem mais de um histórico.")
        Message.objects.using(db).filter(match_id=match.pk).update(conversa_id=chat.pk)


class Migration(migrations.Migration):
    dependencies = [("entradas", "0041_chats_independentes")]
    operations = [migrations.RunPython(associar_historico, migrations.RunPython.noop)]
