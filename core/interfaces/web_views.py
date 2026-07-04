"""Vistas públicas (HTML) de la app core.

Este módulo contiene las vistas que renderizan el sitio web principal de SAMA,
incluyendo la página de inicio, login, y redirección según tipo de usuario.
"""

from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


class HomePageView(View):
    """Vista de la página de inicio pública de SAMA."""

    template_name = "core/home.html"

    def get(self, request):
        """Renderiza la página de inicio."""
        if request.user.is_authenticated:
            return redirect("core-dashboard")
        return render(request, self.template_name)


class LoginView(View):
    """Vista de login que redirige según el tipo de usuario."""

    template_name = "core/login.html"

    def get(self, request):
        """Muestra el formulario de login."""
        if request.user.is_authenticated:
            return redirect("core-dashboard")
        return render(request, self.template_name)

    def post(self, request):
        """Procesa el login y redirige según tipo de usuario."""
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if not username or not password:
            messages.error(request, "Usuario y contraseña son requeridos")
            return render(request, self.template_name)

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)

            return redirect("core-dashboard")
        else:
            messages.error(request, "Usuario o contraseña incorrectos")
            return render(request, self.template_name)


class LogoutView(View):
    """Vista para cerrar sesión."""

    def get(self, request):
        logout(request)
        return redirect("core-home")


class DashboardView(LoginRequiredMixin, View):
    """Dashboard que redirige según el tipo de usuario."""

    def get(self, request):
        user = request.user
        from auth.domain.models import User

        if user.user_type == User.UserType.ADMIN:
            return redirect("/admin/")
        elif user.user_type == User.UserType.TENANT_ADMIN and user.tenant:
            return redirect(f"/crm/{user.tenant.slug}/dashboard/")
        elif user.user_type == User.UserType.AGENT and user.tenant:
            return redirect(f"/crm/{user.tenant.slug}/dashboard/")
        elif user.user_type == User.UserType.VIEWER and user.tenant:
            return redirect(f"/crm/{user.tenant.slug}/dashboard/")

        messages.error(request, "No tienes acceso a ningún dashboard")
        logout(request)
        return redirect("core-login")


class FeaturesView(View):
    """Vista de características/servicios."""

    template_name = "core/features.html"

    def get(self, request):
        return render(request, self.template_name)


class PricingView(View):
    """Vista de precios."""

    template_name = "core/pricing.html"

    def get(self, request):
        return render(request, self.template_name)


class AboutView(View):
    """Vista información de la empresa."""

    template_name = "core/about.html"

    def get(self, request):
        return render(request, self.template_name)


class ContactView(View):
    """Vista de contacto."""

    template_name = "core/contact.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        message = request.POST.get("message", "").strip()

        if not name or not email or not message:
            messages.error(request, "Todos los campos son requeridos")
            return render(request, self.template_name)

        messages.success(request, "Mensaje enviado correctamente")
        return render(request, self.template_name)