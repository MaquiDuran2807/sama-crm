"""Sincroniza el esquema local de auth con el modelo custom local_auth.

Este script evita perder datos existentes en `auth_user` y crea las tablas
faltantes para `LoginAttempt` y `PasswordResetToken`. También registra la
migración `local_auth.0001_initial` como aplicada para que Django deje de ver
la historia como inconsistente.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sama_core.settings")

from django import setup

setup()

from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

from auth.domain.models import LoginAttempt, PasswordResetToken, User


def main() -> None:
	"""Aplica cambios mínimos sobre la base SQLite existente."""

	tables = set(connection.introspection.table_names())
	with connection.cursor() as cursor:
		columns = {column.name for column in connection.introspection.get_table_description(cursor, "auth_user")}

	added_columns: list[str] = []
	with connection.cursor() as cursor:
		column_sql = [
			("tenant_id", "INTEGER NULL REFERENCES tenants_tenant(id) DEFERRABLE INITIALLY DEFERRED"),
			("user_type", "varchar(20) NOT NULL DEFAULT 'agent'"),
			("phone_number", "varchar(32) NOT NULL DEFAULT ''"),
			("avatar_url", "varchar(200) NOT NULL DEFAULT ''"),
			("is_active_portal", "bool NOT NULL DEFAULT 1"),
			("last_login_portal", "datetime NULL"),
		]
		for column_name, column_definition in column_sql:
			if column_name not in columns:
				cursor.execute(f'ALTER TABLE auth_user ADD COLUMN {column_name} {column_definition}')
				added_columns.append(column_name)

	with connection.schema_editor() as schema_editor:
		if "local_auth_loginattempt" not in tables:
			schema_editor.create_model(LoginAttempt)
			added_columns.append("local_auth_loginattempt")

		if "local_auth_passwordresettoken" not in tables:
			schema_editor.create_model(PasswordResetToken)
			added_columns.append("local_auth_passwordresettoken")

	recorder = MigrationRecorder(connection)
	if not recorder.Migration.objects.filter(app="local_auth", name="0001_initial").exists():
		recorder.record_applied("local_auth", "0001_initial")

	print("OK", ", ".join(added_columns) if added_columns else "no changes")


if __name__ == "__main__":
	main()
