
from types import MethodType

from django.contrib import admin

from .models import (
    TipoDocumento,
    Documento,
    RequisitoDocumento,
    PerfilEstudiante,
)


# Restringir el administrador técnico de Django
# exclusivamente a superusuarios activos.
def solo_superusuarios(self, request):
    return (
        request.user.is_active
        and request.user.is_superuser
    )


admin.site.has_permission = MethodType(
    solo_superusuarios,
    admin.site
)


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo")
    list_editable = ("activo",)
    search_fields = ("nombre",)


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = (
        "tipo_documento",
        "estudiante",
        "estado",
        "habilitado",
        "fecha_carga",
    )
    list_filter = ("estado", "habilitado", "tipo_documento")
    search_fields = (
        "estudiante__username",
        "tipo_documento__nombre",
    )
    list_editable = ("estado", "habilitado")


@admin.register(RequisitoDocumento)
class RequisitoDocumentoAdmin(admin.ModelAdmin):
    list_display = ("estudiante", "tipo_documento", "habilitado")
    list_filter = ("habilitado", "tipo_documento")
    search_fields = (
        "estudiante__username",
        "tipo_documento__nombre",
    )
    list_editable = ("habilitado",)


@admin.register(PerfilEstudiante)
class PerfilEstudianteAdmin(admin.ModelAdmin):
    list_display = (
        "estudiante",
        "nombres",
        "apellidos",
        "telefono",
        "intake",
    )
    search_fields = (
        "estudiante__username",
        "nombres",
        "apellidos",
        "estudiante__email",
    )
