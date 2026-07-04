"""Punto de entrada de modelos para la app auth.

Este archivo existe para mantener compatibilidad con Django y sirve como
puente entre el modelo User definido en domain/models.py y Django.
"""

from auth.domain.models import User, LoginAttempt, PasswordResetToken

__all__ = ["User", "LoginAttempt", "PasswordResetToken"]