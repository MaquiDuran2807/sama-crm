from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ingesta", "0006_summaryexecutioncontrol_monthlytextsummary_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatuser",
            name="is_customer",
            field=models.BooleanField(db_index=True, default=True),
        ),
    ]
