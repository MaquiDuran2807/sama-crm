# Generated migration for EvolutionInstance with data migration

from django.db import migrations, models
import django.db.models.deletion


def create_instances_from_existing_names(apps, schema_editor):
    """Migrate existing instance_name values into EvolutionInstance"""
    IngestionControl = apps.get_model('ingesta', 'IngestionControl')
    EvolutionInstance = apps.get_model('ingesta', 'EvolutionInstance')
    
    # Get all unique instance names from existing IngestionControl records
    instance_names = IngestionControl.objects.values_list('instance_name', flat=True).distinct()
    
    for name in instance_names:
        if name:  # Skip empty/None values
            EvolutionInstance.objects.get_or_create(
                instance_name=name,
                defaults={'description': f'Migrated instance: {name}', 'is_active': True}
            )


def reverse_migration(apps, schema_editor):
    """Reverse the data migration"""
    EvolutionInstance = apps.get_model('ingesta', 'EvolutionInstance')
    EvolutionInstance.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ingesta', '0001_initial'),
    ]

    operations = [
        # Create the new EvolutionInstance model
        migrations.CreateModel(
            name='EvolutionInstance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('instance_name', models.CharField(max_length=120, unique=True)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['instance_name'],
            },
        ),
        # Migrate existing data into EvolutionInstance
        migrations.RunPython(create_instances_from_existing_names, reverse_migration),
        # Add the new OneToOne relationship (nullable first for data migration)
        migrations.AddField(
            model_name='ingestioncontrol',
            name='instance',
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='ingestion_control',
                to='ingesta.evolutioninstance'
            ),
        ),
        # Migrate the foreign keys from EvolutionInstance by instance_name
        migrations.RunSQL(
            sql="""
            UPDATE ingesta_ingestioncontrol 
            SET instance_id = (
                SELECT id FROM ingesta_evolutioninstance 
                WHERE ingesta_evolutioninstance.instance_name = ingesta_ingestioncontrol.instance_name
            )
            WHERE instance_id IS NULL
            """,
            reverse_sql="UPDATE ingesta_ingestioncontrol SET instance_id = NULL"
        ),
        # Remove the old instance_name field from IngestionControl
        migrations.RemoveField(
            model_name='ingestioncontrol',
            name='instance_name',
        ),
        # Finally, make the field NOT NULL
        migrations.AlterField(
            model_name='ingestioncontrol',
            name='instance',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='ingestion_control',
                to='ingesta.evolutioninstance'
            ),
        ),
    ]
