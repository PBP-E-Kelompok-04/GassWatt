from django.db import migrations


def repair_survey_tables(apps, schema_editor):
    existing_tables = set(
        schema_editor.connection.introspection.table_names()
    )

    for model_name in ["TransportationSurvey", "DailyEmissionLog"]:
        model = apps.get_model("main", model_name)

        if model._meta.db_table not in existing_tables:
            schema_editor.create_model(model)


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0002_savedlocation"),
    ]

    operations = [
        migrations.RunPython(
            repair_survey_tables,
            migrations.RunPython.noop,
        ),
    ]