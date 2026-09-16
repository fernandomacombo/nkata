from django.db import migrations


def _feature_models():
    # Estes modelos nasceram como tabelas isoladas, preparadas por comandos
    # setup_nkata_*. A migração passa a ser a única fonte de verdade para que
    # deploys, testes e novas instalações recebam o mesmo esquema.
    from entradas.call_models import ChamadaMatchNKATA, SinalChamadaNKATA
    from entradas.chat_media_models import MensagemAudioMatchNKATA
    from entradas.chat_realtime_models import EstadoConversaNKATA
    from entradas.content_moderation_models import AnaliseAutomaticaConteudoNKATA
    from entradas.moments_models import MomentoNKATA, ReacaoMomentoNKATA
    from entradas.post_safety_models import (
        DenunciaPublicacaoNKATA,
        OcultacaoPublicacaoNKATA,
    )
    from entradas.posts_models import PublicacaoNKATA, ReacaoPublicacaoNKATA

    return [
        PublicacaoNKATA,
        ReacaoPublicacaoNKATA,
        OcultacaoPublicacaoNKATA,
        DenunciaPublicacaoNKATA,
        MomentoNKATA,
        ReacaoMomentoNKATA,
        MensagemAudioMatchNKATA,
        EstadoConversaNKATA,
        ChamadaMatchNKATA,
        SinalChamadaNKATA,
        AnaliseAutomaticaConteudoNKATA,
    ]


def prepare_feature_tables(apps, schema_editor):
    connection = schema_editor.connection

    for model in _feature_models():
        tables = set(connection.introspection.table_names())
        table_name = model._meta.db_table

        if table_name not in tables:
            schema_editor.create_model(model)
            continue

        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(
                cursor,
                table_name,
            )
            constraints = connection.introspection.get_constraints(
                cursor,
                table_name,
            )

        columns = {column.name for column in description}
        for field in model._meta.local_concrete_fields:
            if field.column not in columns:
                schema_editor.add_field(model, field)
                columns.add(field.column)

        known_names = set(constraints)
        for index in model._meta.indexes:
            if index.name and index.name not in known_names:
                schema_editor.add_index(model, index)
                known_names.add(index.name)

        for constraint in model._meta.constraints:
            if constraint.name and constraint.name not in known_names:
                schema_editor.add_constraint(model, constraint)
                known_names.add(constraint.name)


class Migration(migrations.Migration):

    dependencies = [
        ("entradas", "0013_schema_repair_and_notifications"),
    ]

    operations = [
        migrations.RunPython(
            prepare_feature_tables,
            migrations.RunPython.noop,
        ),
    ]
