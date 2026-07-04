"""Punto de entrada de modelos para la app core.

Este archivo existe para mantener compatibilidad con Django y sirve como
puente entre los modelos definidos en domain/models.py.
"""

from core.domain.models import SiteConfiguration, Page, Section, MenuItem, ContactMessage

__all__ = ["SiteConfiguration", "Page", "Section", "MenuItem", "ContactMessage"]