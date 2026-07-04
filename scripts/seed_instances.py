#!/usr/bin/env python
"""Script para generar datos de prueba en la base de datos.
Crea tenants, departamentos, ciudades, contactos, leads, tags y tareas.
"""
import os
import random
from datetime import datetime, timedelta

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sama_core.settings")
django.setup()

from django.utils import timezone
from tenants.models import Tenant
from ingesta.models import EvolutionInstance
from crm.models import Contact, Lead, LeadTask, Department, City, Tag


DEPARTAMENTOS_Y_CIUDADES = [
    {"departamento": "Antioquia", "ciudades": [
        {"nombre": "Medellín", "lat": 6.2442, "lng": -75.5812},
        {"nombre": "Bello", "lat": 6.3313, "lng": -75.5576},
        {"nombre": "Itagüí", "lat": 6.1846, "lng": -75.5992},
        {"nombre": "Envigado", "lat": 6.1704, "lng": -75.5865},
        {"nombre": "Rionegro", "lat": 6.1556, "lng": -75.3739},
        {"nombre": "Apartadó", "lat": 7.8830, "lng": -76.6259},
    ]},
    {"departamento": "Cundinamarca", "ciudades": [
        {"nombre": "Bogotá", "lat": 4.7110, "lng": -74.0721},
        {"nombre": "Soacha", "lat": 4.5760, "lng": -74.2171},
        {"nombre": "Chía", "lat": 4.8612, "lng": -74.0577},
        {"nombre": "Cajicá", "lat": 4.9173, "lng": -74.0289},
        {"nombre": "Zipaquirá", "lat": 5.0349, "lng": -74.0034},
    ]},
    {"departamento": "Valle del Cauca", "ciudades": [
        {"nombre": "Cali", "lat": 3.4516, "lng": -76.5320},
        {"nombre": "Palmira", "lat": 3.6532, "lng": -76.3036},
        {"nombre": "Buenaventura", "lat": 3.8801, "lng": -77.0311},
        {"nombre": "Tuluá", "lat": 4.0848, "lng": -76.1954},
        {"nombre": "Jamundí", "lat": 3.3399, "lng": -76.5500},
    ]},
    {"departamento": "Atlántico", "ciudades": [
        {"nombre": "Barranquilla", "lat": 11.0041, "lng": -74.8070},
        {"nombre": " Soledad", "lat": 10.9177, "lng": -74.7656},
        {"nombre": "Malambo", "lat": 10.8596, "lng": -74.7760},
        {"nombre": "Baranoa", "lat": 10.8262, "lng": -74.9143},
    ]},
    {"departamento": "Santander", "ciudades": [
        {"nombre": "Bucaramanga", "lat": 7.1255, "lng": -73.1198},
        {"nombre": "Floridablanca", "lat": 7.0627, "lng": -73.0529},
        {"nombre": "Girón", "lat": 7.0687, "lng": -73.1687},
        {"nombre": "Piedecuesta", "lat": 6.9928, "lng": -73.0467},
    ]},
    {"departamento": "Bolívar", "ciudades": [
        {"nombre": "Cartagena", "lat": 10.3910, "lng": -75.4794},
        {"nombre": "Magangué", "lat": 9.2424, "lng": -74.7537},
        {"nombre": "Santa Marta", "lat": 11.2408, "lng": -74.2099},
        {"nombre": "Turbo", "lat": 8.0915, "lng": -76.7275},
    ]},
    {"departamento": "Córdoba", "ciudades": [
        {"nombre": "Montería", "lat": 8.7554, "lng": -75.8834},
        {"nombre": "Lorica", "lat": 9.2391, "lng": -75.8141},
        {"nombre": "Sahagún", "lat": 8.9452, "lng": -75.5021},
    ]},
    {"departamento": "Sucre", "ciudades": [
        {"nombre": "Sincelejo", "lat": 9.3048, "lng": -75.3972},
        {"nombre": "Corozal", "lat": 9.3152, "lng": -75.2821},
    ]},
    {"departamento": "Nariño", "ciudades": [
        {"nombre": "Pasto", "lat": 1.2136, "lng": -77.2812},
        {"nombre": "Ipiales", "lat": 0.8309, "lng": -77.6372},
        {"nombre": "Tumaco", "lat": 1.8266, "lng": -78.7831},
    ]},
    {"departamento": "Cauca", "ciudades": [
        {"nombre": "Popayán", "lat": 2.4542, "lng": -76.6146},
        {"nombre": "Santander de Quilichao", "lat": 2.9757, "lng": -76.4838},
    ]},
    {"departamento": "Tolima", "ciudades": [
        {"nombre": "Ibagué", "lat": 4.4389, "lng": -75.2322},
        {"nombre": "Espinal", "lat": 4.1499, "lng": -74.8574},
        {"nombre": "Melgar", "lat": 4.2028, "lng": -74.6419},
    ]},
    {"departamento": "Huila", "ciudades": [
        {"nombre": "Neiva", "lat": 2.5363, "lng": -75.2818},
        {"nombre": "Pitalito", "lat": 1.8558, "lng": -76.0503},
    ]},
    {"departamento": "Meta", "ciudades": [
        {"nombre": "Villavicencio", "lat": 4.1420, "lng": -73.6266},
        {"nombre": "Acacías", "lat": 3.9898, "lng": -73.7620},
    ]},
    {"departamento": "Risaralda", "ciudades": [
        {"nombre": "Pereira", "lat": 4.8133, "lng": -75.6906},
        {"nombre": "Dosquebradas", "lat": 4.8377, "lng": -75.6766},
        {"nombre": "Santa Rosa de Cabal", "lat": 4.7747, "lng": -75.6278},
    ]},
    {"departamento": "Quindío", "ciudades": [
        {"nombre": "Armenia", "lat": 4.5389, "lng": -75.6725},
        {"nombre": "Calarcá", "lat": 4.5435, "lng": -75.6411},
    ]},
    {"departamento": "Caldas", "ciudades": [
        {"nombre": "Manizales", "lat": 5.0689, "lng": -75.5924},
        {"nombre": "La Dorada", "lat": 5.4521, "lng": -74.6613},
    ]},
    {"departamento": "Chocó", "ciudades": [
        {"nombre": "Quibdó", "lat": 5.6950, "lng": -76.6572},
    ]},
    {"departamento": "La Guajira", "ciudades": [
        {"nombre": "Riohacha", "lat": 11.5405, "lng": -72.9276},
        {"nombre": "Maicao", "lat": 11.3778, "lng": -72.2404},
    ]},
    {"departamento": "Cesar", "ciudades": [
        {"nombre": "Valledupar", "lat": 10.4633, "lng": -73.2532},
        {"nombre": "Agustín Codazzi", "lat": 10.0301, "lng": -73.2437},
    ]},
    {"departamento": "Magdalena", "ciudades": [
        {"nombre": "Santa Marta", "lat": 11.2408, "lng": -74.2099},
        {"nombre": "Ciénaga", "lat": 11.0075, "lng": -74.2457},
    ]},
]

NOMBRES = [
    "Juan", "María", "Carlos", "Ana", "Luis", "Laura", "Pedro", "Claudia",
    "Miguel", "Diana", "Jorge", "Sandra", "Fernando", "Patricia", "Ricardo",
    "Liliana", "Andrés", "Carmen", "Roberto", "Margarita", "Alberto", "Silvia",
    "Manuel", "Adriana", "Rafael", "Paula", "Gustavo", "Isabel", "Eduardo",
    "Sofía", "Diego", "Valentina", "Mateo", "Camila", "Santiago", "Gabriela",
]

APELLIDOS = [
    "García", "Rodríguez", "Martínez", "Hernández", "López", "González",
    "Rodríguez", "Pérez", "Sánchez", "Ramírez", "Torres", "Flores", "Rivera",
    "Gómez", "Díaz", "Reyes", "Morales", "Cruz", "Ortiz", "Gutiérrez",
    "Chávez", "Jiménez", "Ramos", "Mendoza", "Ruiz", "Vargas", " Medina",
    "Castro", "Vega", "Cortés", "Rojas", "Ríos", "Salas", "Reyes",
]

PRODUCTOS = [
    "Panel Solar 550W", "Sistema Solar Residencial 5kW", "Batería de Litio",
    "Kit Solar Portátil", "Sistema Aislado 10kW", "Microinversor",
    "Estructura de Montaje", "Kit de Conexión", "Bomba Solar",
]

CATEGORIAS = ["Residencial", "Comercial", "Industrial", "Agrícola"]

NOTAS_TAREAS = [
    "Llamar para confirmar cita", "Enviar cotización por correo",
    "Revisar requisitos de instalación", "Coordinar visita técnica",
    "Enviar brochure de productos", "Verificar disponibilidad en bodega",
    "Confirmar pago del anticipo", "Programar instalación",
]

TAGS_TENANT_1 = [
    {"nombre": "Interesado Solar", "color": "#2ecc71"},
    {"nombre": "Cliente Anterior", "color": "#3498db"},
    {"nombre": "Zona Rural", "color": "#9b59b6"},
    {"nombre": "Alto Potencial", "color": "#e74c3c"},
    {"nombre": "Sin Responder", "color": "#f39c12"},
]

TAGS_TENANT_2 = [
    {"nombre": "Prospecto", "color": "#1abc9c"},
    {"nombre": "En Negociación", "color": "#e67e22"},
    {"nombre": "Cliente Frecuente", "color": "#9b59b6"},
    {"nombre": "Rechazado", "color": "#95a5a6"},
]

UTM_SOURCES = ["facebook", "google", "instagram", "tiktok", "referido", "web"]
UTM_MEDIUMS = ["cpc", "organic", "social", "referral", "email"]


def crear_tenants():
    print("\n=== Creando Tenants ===")
    tenants_data = [
        {
            "name": "Codensolar SAS",
            "slug": "codensolar",
            "tier": "full",
            "period": "monthly",
        },
        {
            "name": "EcoTech Soluciones",
            "slug": "ecotech",
            "tier": "pro",
            "period": "quarterly",
        },
    ]

    tenants = []
    for data in tenants_data:
        tenant, created = Tenant.objects.get_or_create(
            slug=data["slug"],
            defaults=data,
        )
        tenants.append(tenant)
        print(f"  {'+ Creado' if created else '= Ya existe'}: {tenant.name}")

    return tenants


def crear_departamentos_y_ciudades():
    print("\n=== Creando Departamentos y Ciudades ===")
    all_cities = []
    for dept_data in DEPARTAMENTOS_Y_CIUDADES:
        dept, created = Department.objects.get_or_create(
            name=dept_data["departamento"]
        )
        if created:
            print(f"  + Dept: {dept.name}")

        for city_data in dept_data["ciudades"]:
            city, created = City.objects.get_or_create(
                department=dept,
                name=city_data["nombre"].strip(),
                defaults={
                    "latitude": city_data["lat"],
                    "longitude": city_data["lng"],
                },
            )
            all_cities.append(city)
            if created:
                print(f"    + Ciudad: {city.name}")

    return all_cities


def crear_evolution_instance():
    print("\n=== Creando Evolution Instance ===")
    instance, created = EvolutionInstance.objects.get_or_create(
        instance_name="Deya3",
        defaults={"description": "Production WhatsApp Instance", "is_active": True},
    )
    print(f"  {'+ Creado' if created else '= Ya existe'}: {instance.instance_name}")
    return instance


def crear_contacts_con_leads(tenants, cities, count=50):
    print("\n=== Creando Contacts y Leads ===")
    contacts = []
    stages = ["nuevo", "contactado", "calificado", "propuesta", "negociacion", "cerrado"]

    for i in range(count):
        tenant = random.choice(tenants)
        city = random.choice(cities)
        nombre = random.choice(NOMBRES)
        apellido = random.choice(APELLIDOS)
        nombre_completo = f"{nombre} {apellido}"

        phone = f"+57{random.randint(300, 399)}{random.randint(1000000, 9999999)}"

        contact, created = Contact.objects.get_or_create(
            tenant=tenant,
            phone_number=phone,
            defaults={
                "full_name": nombre_completo,
                "email": f"{nombre.lower()}.{apellido.lower()}@email.com",
                "address": f"Cra {random.randint(1, 99)} #{random.randint(1, 99)}-{random.randint(1, 99)}",
                "city": city,
                "utm_source": random.choice(UTM_SOURCES),
                "utm_medium": random.choice(UTM_MEDIUMS),
            },
        )
        contacts.append(contact)
        if created:
            stage = random.choice(stages)
            Lead.objects.get_or_create(
                tenant=tenant,
                contact=contact,
                defaults={
                    "current_stage": stage,
                    "product_of_interest": random.choice(PRODUCTOS),
                    "product_category": random.choice(CATEGORIAS),
                    "is_closed": stage == "cerrado",
                    "closed_result": "won" if random.random() > 0.3 else "lost",
                    "created_at": timezone.now() - timedelta(days=random.randint(1, 90)),
                    "last_contacted_at": timezone.now() - timedelta(days=random.randint(0, 30)),
                },
            )

    print(f"  Creados {len(contacts)} contacts con leads")
    return contacts


def crear_tags(tenants):
    print("\n=== Creando Tags ===")
    all_tags = []
    for tenant in tenants:
        tags_data = TAGS_TENANT_1 if tenant.slug == "codensolar" else TAGS_TENANT_2
        for tag_data in tags_data:
            tag, created = Tag.objects.get_or_create(
                tenant=tenant,
                name=tag_data["nombre"],
                defaults={"color": tag_data["color"]},
            )
            all_tags.append(tag)
            if created:
                print(f"  + Tag: {tag.name} ({tag.tenant.name})")
    return all_tags


def asignar_tags_a_contacts(contacts, tags, contacts_per_tag=10):
    print("\n=== Asignando Tags a Contacts ===")
    for tag in tags:
        contacts_con_tag = random.sample(contacts, min(contacts_per_tag, len(contacts)))
        for contact in contacts_con_tag:
            if contact not in tag.contacts.all():
                tag.contacts.add(contact)
    print(f"  Tags asignados a contactos")


def crear_tasks(leads, tasks_per_lead=2):
    print("\n=== Creando Tasks ===")
    count = 0
    for lead in leads:
        num_tasks = random.randint(1, tasks_per_lead)
        for _ in range(num_tasks):
            days_offset = random.randint(0, 14)
            due = timezone.now() + timedelta(days=days_offset)

            task, created = LeadTask.objects.get_or_create(
                lead=lead,
                description=random.choice(NOTAS_TAREAS),
                defaults={
                    "due_date": due,
                    "is_completed": random.random() > 0.6,
                },
            )
            if created:
                count += 1

    print(f"  Creadas {count} tareas")
    return count


def main():
    print("=" * 60)
    print(" SEED: Generando datos de prueba para SAMA CRM")
    print("=" * 60)

    instance = crear_evolution_instance()
    tenants = crear_tenants()
    cities = crear_departamentos_y_ciudades()

    contacts = crear_contacts_con_leads(tenants, cities, count=50)
    tags = crear_tags(tenants)
    asignar_tags_a_contacts(contacts, tags)

    leads = Lead.objects.all()
    crear_tasks(leads)

    print("\n" + "=" * 60)
    print(" RESUMEN")
    print("=" * 60)
    print(f"  Evolution Instances : {EvolutionInstance.objects.count()}")
    print(f"  Tenants             : {Tenant.objects.count()}")
    print(f"  Departments         : {Department.objects.count()}")
    print(f"  Cities              : {City.objects.count()}")
    print(f"  Contacts            : {Contact.objects.count()}")
    print(f"  Leads               : {Lead.objects.count()}")
    print(f"  Tags                : {Tag.objects.count()}")
    print(f"  Tasks               : {LeadTask.objects.count()}")
    print("=" * 60)


if __name__ == "__main__":
    main()