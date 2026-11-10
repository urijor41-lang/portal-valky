from django.urls import path
from . import views, admin_views

urlpatterns = [
    # Portal de estudiantes
    path("", views.inicio, name="inicio"),
    path("registro/", views.registro, name="registro"),
    path("iniciar-sesion/", views.iniciar_sesion, name="iniciar_sesion"),
    path("cerrar-sesion/", views.cerrar_sesion, name="cerrar_sesion"),
    path("mi-perfil/", views.mi_perfil, name="mi_perfil"),
    path("mis-documentos/", views.mis_documentos, name="mis_documentos"),
    path("documento/<int:documento_id>/descargar/",views.descargar_documento,name="descargar_documento"),
    
    path("ejemplo-documento/<int:tipo_id>/descargar/",views.descargar_ejemplo_documento,name="descargar_ejemplo_documento"),

    # Cambio de contraseña
    path(
        "cambiar-contrasena/",
        views.cambiar_contrasena,
        name="cambiar_contrasena"
    ),

    # Creación de estudiantes
    path(
        "gestion/estudiantes/crear/",
        admin_views.admin_crear_estudiante,
        name="admin_crear_estudiante"
    ),

    # Panel administrativo Valky
    path("gestion/", admin_views.admin_inicio, name="admin_inicio"),

    path(
        "gestion/tipos-documentos/",
        admin_views.admin_tipos_documentos,
        name="admin_tipos_documentos"
    ),

    path(
        "gestion/estudiante/<int:estudiante_id>/",
        admin_views.admin_perfil_estudiante,
        name="admin_perfil_estudiante"
    ),

    # Historial de estudiantes
    path(
        "gestion/historial/",
        admin_views.admin_historial_estudiantes,
        name="admin_historial_estudiantes"
    ),

    # Gestión de asesores
    path(
        "gestion/asesores/",
        admin_views.admin_asesores,
        name="admin_asesores"
    ),

    path(
        "gestion/asesores/crear/",
        admin_views.admin_crear_asesor,
        name="admin_crear_asesor"
    ),

    path(
        "gestion/asesores/<int:asesor_id>/permisos/",
        admin_views.admin_editar_permisos_asesor,
        name="admin_editar_permisos_asesor"
    ),
]