from django.db import migrations, models


def add_appearance(apps, schema_editor):
    # Isolated unmanaged table, also created by 0014 on fresh installs.
    from entradas.moments_models import MomentoNKATA
    with schema_editor.connection.cursor() as cursor:
        columns = {c.name for c in schema_editor.connection.introspection.get_table_description(cursor, MomentoNKATA._meta.db_table)}
    for name in ("tema", "fonte"):
        field = MomentoNKATA._meta.get_field(name)
        if field.column not in columns:
            schema_editor.add_field(MomentoNKATA, field)


class Migration(migrations.Migration):
    dependencies = [("entradas", "0025_account_identity_limits")]
    operations = [migrations.RunPython(add_appearance, migrations.RunPython.noop)]
