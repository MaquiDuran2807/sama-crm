#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sama_core.settings')
django.setup()

from ingesta.models import EvolutionInstance

# Create or get the Deya3 instance
instance, created = EvolutionInstance.objects.get_or_create(
    instance_name='Deya3',
    defaults={'description': 'Production WhatsApp Instance', 'is_active': True}
)

print(f"✓ Instance ID: {instance.id}, Created: {created}, Name: {instance.instance_name}")

# List all instances
instances = EvolutionInstance.objects.all()
print(f"\n✓ Total instances: {instances.count()}")
for inst in instances:
    print(f"  - {inst.instance_name}: {inst.description} (Active: {inst.is_active})")
