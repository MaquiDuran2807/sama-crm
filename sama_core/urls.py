"""
URL configuration for sama_core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as django_auth_views
from django.urls import include, path

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from ingesta.views import EndpointDocsView
from ingesta.views import HomeView
from auth.interfaces.web_views import PortalLoginView, TenantSelectView

urlpatterns = [
    path('home/', HomeView.as_view(), name='home'),
    path('api/docs/', EndpointDocsView.as_view(), name='api-docs'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('admin/', admin.site.urls),
    path('accounts/login/', PortalLoginView.as_view(), name='login'),
    path('accounts/select-tenant/', TenantSelectView.as_view(), name='auth-tenant-select'),
    path('accounts/logout/', django_auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('api/auth/', include('auth.interfaces.urls')),
    path('ingesta/', include('ingesta.urls')),
    path('crm/', include('crm.web_urls')),
    path("api/crm/", include("crm.interfaces.urls")),
    path("api/", include("tenants.interfaces.urls")),
    path('', include('core.web_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
