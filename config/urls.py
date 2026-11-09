# ==========================================================
# 1. IMPORTACIONES
# ==========================================================

from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.views import LoginView
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from django.urls import path, include, reverse
from django.conf import settings
from django.conf.urls.static import static


# ==========================================================
# 2. INICIO DE SESIÓN DEL ADMINISTRADOR Y ASESORES
# ==========================================================

class ValkyAdminLoginView(LoginView):

    authentication_form = AdminAuthenticationForm

    template_name = "portal/admin_login.html"

    def get_success_url(self):

        # Administrador principal y asesores entran al panel Valky.
        # Ignora el parámetro next=/admin/.

        return reverse("admin_inicio")


# ==========================================================
# 3. VISTA PERSONALIZADA DEL LOGIN ADMINISTRATIVO
# ==========================================================

def admin_login(request):

    extra_context = admin.site.each_context(request)

    return ValkyAdminLoginView.as_view(
        extra_context=extra_context
    )(request)


# ==========================================================
# 4. CONFIGURACIÓN DE RUTAS PRINCIPALES
# ==========================================================

urlpatterns = [

    # Inicio de sesión personalizado del área administrativa.
    # Debe estar antes de admin.site.urls.

    path(
        "admin/login/",
        admin_login,
        name="admin_login"
    ),

    # Administración de Django.

    path(
        "admin/",
        admin.site.urls
    ),

    # Rutas de la aplicación Valky.

    path(
        "",
        include("portal.urls")
    ),

]


# ==========================================================
# 5. ARCHIVOS ESTÁTICOS
# LOGOS, IMÁGENES, CSS Y JAVASCRIPT
# ==========================================================

if settings.DEBUG:

    urlpatterns += staticfiles_urlpatterns()


# ==========================================================
# 6. ARCHIVOS MULTIMEDIA
# DOCUMENTOS CARGADOS POR LOS ESTUDIANTES
# ==========================================================

if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )