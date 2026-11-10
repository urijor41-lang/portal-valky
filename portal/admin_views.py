from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.crypto import get_random_string

from .models import (
    PerfilEstudiante,
    Documento,
    RequisitoDocumento,
    TipoDocumento,
    NotaSeguimiento,
    HistorialEstudiante,
    PermisosAsesor,
)


# ==========================================================
# COMPROBACIÓN DE PERMISOS
# ==========================================================

PERMISOS_VALIDOS = {
    "ver_estudiantes",
    "crear_estudiantes",
    "eliminar_estudiantes",
    "editar_informacion",
    "gestionar_documentos",
    "revisar_documentos",
    "registrar_notas",
    "gestionar_tipos_documentales",
    "ver_historial",
    "restablecer_contrasenas",
}


def asesor_tiene_permiso(usuario, nombre_permiso):

    if usuario.is_superuser:
        return True

    if not usuario.is_staff or not usuario.is_active:
        return False

    if nombre_permiso not in PERMISOS_VALIDOS:
        return False

    permisos, creado = PermisosAsesor.objects.get_or_create(
        asesor=usuario
    )

    return getattr(permisos, nombre_permiso, False)


def denegar_permiso(request, nombre_permiso, destino="admin_inicio", **kwargs):

    if asesor_tiene_permiso(request.user, nombre_permiso):
        return False

    messages.error(
        request,
        "Permiso deshabilitado. Habla con el administrador."
    )

    return redirect(destino, **kwargs)


# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================

def eliminar_archivos_estudiante(archivos):

    for almacenamiento, nombre in archivos:

        if not nombre:
            continue

        documento_en_uso = Documento.objects.filter(
            archivo=nombre
        ).exists()

        ejemplo_en_uso = TipoDocumento.objects.filter(
            archivo_ejemplo=nombre
        ).exists()

        if documento_en_uso or ejemplo_en_uso:
            continue

        almacenamiento.delete(nombre)


def obtener_estado_semaforo(estudiante):

    hoy = timezone.localdate()
    limite_rojo = hoy + timezone.timedelta(days=10)

    requisitos = list(
        RequisitoDocumento.objects.filter(
            estudiante=estudiante,
            habilitado=True
        ).select_related("tipo_documento")
    )

    if not requisitos:
        return {
            "estado": "neutro",
            "documentos_pendientes": [],
            "total_documentos": 0,
            "total_aprobados": 0,
            "deadlines_proximos": [],
        }

    documentos = Documento.objects.filter(
        estudiante=estudiante
    ).order_by("-fecha_carga", "-id")

    documentos_por_tipo = {}

    for documento in documentos:
        if documento.tipo_documento_id not in documentos_por_tipo:
            documentos_por_tipo[documento.tipo_documento_id] = documento

    documentos_pendientes = []
    total_aprobados = 0
    hay_documento_antiguo_sin_aprobar = False

    for requisito in requisitos:

        documento = documentos_por_tipo.get(
            requisito.tipo_documento_id
        )

        esta_aprobado = (
            documento is not None
            and bool(documento.archivo)
            and documento.estado == "aprobado"
        )

        if esta_aprobado:
            total_aprobados += 1
            continue

        dias_solicitado = None

        if requisito.fecha_solicitud:
            dias_solicitado = (
                hoy - timezone.localtime(
                    requisito.fecha_solicitud
                ).date()
            ).days

            if dias_solicitado >= 15:
                hay_documento_antiguo_sin_aprobar = True

        documentos_pendientes.append({
            "tipo_documento": requisito.tipo_documento.nombre,
            "fecha_solicitud": requisito.fecha_solicitud,
            "dias_solicitado": dias_solicitado,
            "estado_documento": (
                documento.estado if documento else "sin_cargar"
            ),
        })

    if total_aprobados == len(requisitos):
        return {
            "estado": "verde",
            "documentos_pendientes": [],
            "total_documentos": len(requisitos),
            "total_aprobados": total_aprobados,
            "deadlines_proximos": [],
        }

    perfil = getattr(estudiante, "perfil", None)
    deadlines_proximos = []

    if perfil:
        for numero in range(1, 5):

            fecha_deadline = getattr(
                perfil,
                f"deadline_{numero}",
                None
            )

            if fecha_deadline and fecha_deadline <= limite_rojo:
                deadlines_proximos.append({
                    "universidad": getattr(
                        perfil,
                        f"universidad_{numero}",
                        ""
                    ),
                    "carrera": getattr(
                        perfil,
                        f"carrera_{numero}",
                        ""
                    ),
                    "pais": getattr(
                        perfil,
                        f"pais_{numero}",
                        ""
                    ),
                    "deadline": fecha_deadline,
                    "dias_restantes": (
                        fecha_deadline - hoy
                    ).days,
                })

    if deadlines_proximos:
        estado = "rojo"
    elif hay_documento_antiguo_sin_aprobar:
        estado = "amarillo"
    else:
        estado = "neutro"

    return {
        "estado": estado,
        "documentos_pendientes": documentos_pendientes,
        "total_documentos": len(requisitos),
        "total_aprobados": total_aprobados,
        "deadlines_proximos": deadlines_proximos,
    }


def obtener_resumen_semaforo(estudiantes):

    estudiantes_verdes = []
    estudiantes_amarillos = []
    estudiantes_rojos = []
    estudiantes_neutros = []

    alertas_deadline = []
    alertas_documentos = []

    for estudiante in estudiantes:

        perfil = getattr(estudiante, "perfil", None)

        if perfil:
            nombre = (
                f"{perfil.nombres} {perfil.apellidos}".strip()
                or estudiante.get_full_name().strip()
                or estudiante.username
            )
        else:
            nombre = (
                estudiante.get_full_name().strip()
                or estudiante.username
            )

        resultado = obtener_estado_semaforo(estudiante)

        fila_estudiante = {
            "estudiante": estudiante,
            "nombre_estudiante": nombre,
            **resultado,
        }

        if resultado["estado"] == "verde":
            estudiantes_verdes.append(fila_estudiante)

        elif resultado["estado"] == "rojo":
            estudiantes_rojos.append(fila_estudiante)

            for deadline in resultado["deadlines_proximos"]:
                alertas_deadline.append({
                    "estudiante": estudiante,
                    "nombre_estudiante": nombre,
                    **deadline,
                })

        elif resultado["estado"] == "amarillo":
            estudiantes_amarillos.append(fila_estudiante)

            for documento in resultado["documentos_pendientes"]:
                if (
                    documento["dias_solicitado"] is not None
                    and documento["dias_solicitado"] >= 15
                ):
                    alertas_documentos.append({
                        "estudiante": estudiante,
                        "nombre_estudiante": nombre,
                        **documento,
                    })

        else:
            estudiantes_neutros.append(fila_estudiante)

    alertas_deadline.sort(
        key=lambda alerta: alerta["deadline"]
    )

    alertas_documentos.sort(
        key=lambda alerta: alerta["fecha_solicitud"]
    )

    return {
        "estudiantes_verdes": estudiantes_verdes,
        "estudiantes_amarillos": estudiantes_amarillos,
        "estudiantes_rojos": estudiantes_rojos,
        "estudiantes_neutros": estudiantes_neutros,
        "alertas_deadline": alertas_deadline,
        "alertas_documentos": alertas_documentos,
    }


def obtener_estadisticas_documentos(estudiantes):

    categorias = {
        "aprobado": {
            "nombre": "Aprobados",
            "cantidad": 0,
        },
        "pendiente": {
            "nombre": "Pendientes de revisión",
            "cantidad": 0,
        },
        "corregir": {
            "nombre": "Por corregir",
            "cantidad": 0,
        },
        "sin_cargar": {
            "nombre": "Sin cargar",
            "cantidad": 0,
        },
    }

    requisitos = RequisitoDocumento.objects.filter(
        estudiante__in=estudiantes,
        habilitado=True
    ).select_related(
        "estudiante",
        "tipo_documento"
    )

    documentos = Documento.objects.filter(
        estudiante__in=estudiantes
    ).select_related(
        "tipo_documento"
    ).order_by(
        "-fecha_carga",
        "-id"
    )

    documentos_por_tipo = {}

    for documento in documentos:

        clave = (
            documento.estudiante_id,
            documento.tipo_documento_id
        )

        if clave not in documentos_por_tipo:
            documentos_por_tipo[clave] = documento

    filas = []

    for requisito in requisitos:

        estudiante = requisito.estudiante
        tipo = requisito.tipo_documento

        documento = documentos_por_tipo.get((
            estudiante.id,
            tipo.id
        ))

        if not documento or not documento.archivo:
            categoria = "sin_cargar"
            fecha_carga = None

        elif documento.estado == "aprobado":
            categoria = "aprobado"
            fecha_carga = documento.fecha_carga

        elif documento.estado == "corregir":
            categoria = "corregir"
            fecha_carga = documento.fecha_carga

        else:
            categoria = "pendiente"
            fecha_carga = documento.fecha_carga

        perfil = getattr(estudiante, "perfil", None)

        if perfil:
            nombre = (
                f"{perfil.nombres} {perfil.apellidos}".strip()
                or estudiante.get_full_name().strip()
                or estudiante.username
            )
        else:
            nombre = (
                estudiante.get_full_name().strip()
                or estudiante.username
            )

        categorias[categoria]["cantidad"] += 1

        filas.append({
            "estudiante": estudiante,
            "nombre_estudiante": nombre,
            "tipo_documento": tipo.nombre,
            "categoria": categoria,
            "estado": categorias[categoria]["nombre"],
            "fecha_carga": fecha_carga,
        })

    filas.sort(
        key=lambda fila: (
            fila["nombre_estudiante"].lower(),
            fila["tipo_documento"].lower()
        )
    )

    total = sum(
        categoria["cantidad"]
        for categoria in categorias.values()
    )

    return {
        "categorias_documentos": categorias,
        "filas_documentos": filas,
        "total_documentos_estadistica": total,
    }



# ==========================================================
# ==========================================================
# INICIO DEL PANEL DE GESTIÓN
# ==========================================================

@staff_member_required(login_url="/admin/login/")
def admin_inicio(request):

    if not asesor_tiene_permiso(
        request.user,
        "ver_estudiantes"
    ):
        messages.error(
            request,
            "Permiso deshabilitado. Habla con el administrador."
        )
        return redirect("/admin/login/")

    busqueda = request.GET.get("buscar", "").strip()

    estudiantes_base = list(
        User.objects.filter(
            is_staff=False,
            is_superuser=False
        ).select_related("perfil").order_by("-date_joined")
    )

    estudiantes = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).select_related("perfil").order_by("-date_joined")

    if busqueda:
        estudiantes = estudiantes.filter(
            Q(username__icontains=busqueda) |
            Q(email__icontains=busqueda) |
            Q(perfil__nombres__icontains=busqueda) |
            Q(perfil__apellidos__icontains=busqueda)
        )

    total_estudiantes = len(estudiantes_base)

    resumen = obtener_resumen_semaforo(estudiantes_base)

    estadisticas_documentos = obtener_estadisticas_documentos(
        estudiantes_base
    )

    contexto = {
        "estudiantes": estudiantes,
        "busqueda": busqueda,

        # Permisos de acceso a funciones del panel.

        "puede_crear_estudiantes": asesor_tiene_permiso(
            request.user,
            "crear_estudiantes"
        ),

        "puede_gestionar_documentos": asesor_tiene_permiso(
            request.user,
            "gestionar_documentos"
        ),

        "puede_revisar_documentos": asesor_tiene_permiso(
            request.user,
            "revisar_documentos"
        ),

        "puede_registrar_notas": asesor_tiene_permiso(
            request.user,
            "registrar_notas"
        ),

        "puede_ver_historial": asesor_tiene_permiso(
            request.user,
            "ver_historial"
        ),

        "puede_gestionar_tipos_documentales": asesor_tiene_permiso(
            request.user,
            "gestionar_tipos_documentales"
        ),

        "es_administrador_principal": request.user.is_superuser,

        # ESTADÍSTICAS GENERALES

        "total_estudiantes": total_estudiantes,
        "total_documentos": Documento.objects.count(),
        "total_tipos": TipoDocumento.objects.count(),

        "categorias_documentos": estadisticas_documentos[
            "categorias_documentos"
        ],

        "filas_documentos": estadisticas_documentos[
            "filas_documentos"
        ],

        "total_documentos_estadistica": estadisticas_documentos[
            "total_documentos_estadistica"
        ],

        # ALERTAS DE DEADLINES

        "alertas_deadline": resumen["alertas_deadline"],

        "total_alertas_deadline": len(
            resumen["alertas_deadline"]
        ),

        "total_estudiantes_alerta_deadline": len(
            resumen["estudiantes_rojos"]
        ),

        # ALERTAS DOCUMENTALES

        "alertas_documentos": resumen["alertas_documentos"],

        "total_alertas_documentos": len(
            resumen["alertas_documentos"]
        ),

        "total_estudiantes_alerta_documentos": len(
            resumen["estudiantes_amarillos"]
        ),

        # ESTUDIANTES EN VERDE

        "estudiantes_verdes": resumen["estudiantes_verdes"],

        "total_estudiantes_verdes": len(
            resumen["estudiantes_verdes"]
        ),

        # ESTUDIANTES EN AMARILLO

        "estudiantes_amarillos": resumen["estudiantes_amarillos"],

        "total_estudiantes_amarillos": len(
            resumen["estudiantes_amarillos"]
        ),

        # ESTUDIANTES EN ROJO

        "estudiantes_rojos": resumen["estudiantes_rojos"],

        "total_estudiantes_rojos": len(
            resumen["estudiantes_rojos"]
        ),

        # ESTUDIANTES SIN ALERTAS

        "estudiantes_neutros": resumen["estudiantes_neutros"],

        "total_estudiantes_neutros": len(
            resumen["estudiantes_neutros"]
        ),
    }

    return render(
        request,
        "portal/admin/inicio.html",
        contexto
    )



# ==========================================================


# TIPOS DE DOCUMENTOS
# ==========================================================

@staff_member_required(login_url="/admin/login/")
def admin_tipos_documentos(request):

    # 1. VERIFICAR SI EL USUARIO PUEDE CONSULTAR LA PÁGINA

    # Todos los asesores y el administrador principal
    # pueden consultar los tipos de documentos.

    # 2. PROCESAR ACCIONES DE MODIFICACIÓN

    if request.method == "POST":

        if not asesor_tiene_permiso(
            request.user,
            "gestionar_tipos_documentales"
        ):
            return denegar_permiso(
                request,
                "gestionar_tipos_documentales",
                "admin_tipos_documentos"
            )

        accion = request.POST.get("accion", "")

        # 3. AGREGAR TIPO DE DOCUMENTO

        if accion == "agregar":

            nombre = request.POST.get("nombre", "").strip()

            if not nombre:
                messages.error(
                    request,
                    "Escribe el nombre del tipo de documento."
                )

            elif TipoDocumento.objects.filter(
                nombre__iexact=nombre
            ).exists():
                messages.error(
                    request,
                    "Este tipo de documento ya existe."
                )

            else:
                TipoDocumento.objects.create(nombre=nombre)

                messages.success(
                    request,
                    "El tipo de documento se agregó correctamente."
                )

        # 4. EDITAR TIPO DE DOCUMENTO

        elif accion == "editar":

            tipo = get_object_or_404(
                TipoDocumento,
                id=request.POST.get("tipo_id")
            )

            nombre = request.POST.get("nombre", "").strip()
            archivo = request.FILES.get("archivo_ejemplo")

            if not nombre:
                messages.error(
                    request,
                    "El nombre del documento no puede estar vacío."
                )

            elif TipoDocumento.objects.filter(
                nombre__iexact=nombre
            ).exclude(id=tipo.id).exists():

                messages.error(
                    request,
                    "Ya existe otro tipo de documento con ese nombre."
                )

            else:

                archivo_anterior = tipo.archivo_ejemplo

                tipo.nombre = nombre

                if archivo:
                    tipo.archivo_ejemplo = archivo

                tipo.save()

                # Eliminar el archivo anterior solamente
                # después de guardar correctamente el nuevo.
                if archivo and archivo_anterior:
                    archivo_anterior.delete(save=False)

                messages.success(
                    request,
                    "El tipo de documento se actualizó correctamente."
                )

        # 5. ACTIVAR O DESACTIVAR TIPO DE DOCUMENTO

        elif accion == "cambiar_estado":

            tipo = get_object_or_404(
                TipoDocumento,
                id=request.POST.get("tipo_id")
            )

            tipo.activo = not tipo.activo
            tipo.save(update_fields=["activo"])

            if tipo.activo:
                messages.success(
                    request,
                    "El tipo de documento fue activado."
                )
            else:
                messages.success(
                    request,
                    "El tipo de documento fue desactivado."
                )

        # 6. RETIRAR ARCHIVO DE EJEMPLO

        elif accion == "eliminar_ejemplo":

            tipo = get_object_or_404(
                TipoDocumento,
                id=request.POST.get("tipo_id")
            )

            if tipo.archivo_ejemplo:

                tipo.archivo_ejemplo.delete(save=True)

                messages.success(
                    request,
                    "El archivo de ejemplo fue retirado."
                )

            else:

                messages.info(
                    request,
                    "Este tipo de documento no tiene un ejemplo cargado."
                )

        # 7. ELIMINAR TIPO DE DOCUMENTO

        elif accion == "eliminar":

            tipo = get_object_or_404(
                TipoDocumento,
                id=request.POST.get("tipo_id")
            )

            tiene_requisitos = RequisitoDocumento.objects.filter(
                tipo_documento=tipo
            ).exists()

            tiene_documentos = Documento.objects.filter(
                tipo_documento=tipo
            ).exists()

            if tiene_requisitos or tiene_documentos:

                messages.error(
                    request,
                    "No se puede eliminar este tipo porque está asociado a estudiantes o tiene documentos registrados. Puedes desactivarlo para conservar su historial."
                )

            else:

                if tipo.archivo_ejemplo:
                    tipo.archivo_ejemplo.delete(save=False)

                tipo.delete()

                messages.success(
                    request,
                    "El tipo de documento fue eliminado correctamente."
                )

        # 8. RECHAZAR ACCIONES NO RECONOCIDAS

        else:

            messages.error(
                request,
                "La acción solicitada no es válida."
            )

        return redirect("admin_tipos_documentos")

    # 9. CONSULTAR TIPOS DE DOCUMENTOS

    tipos_documentos = TipoDocumento.objects.all().order_by("nombre")

    # 10. PREPARAR INFORMACIÓN PARA LA PLANTILLA

    contexto = {
        "tipos_documentos": tipos_documentos,

        "puede_gestionar_tipos_documentales": asesor_tiene_permiso(
            request.user,
            "gestionar_tipos_documentales"
        ),
    }

    return render(
        request,
        "portal/admin/tipos_documentos.html",
        contexto
    )


# ==========================================================


# ==========================================================
# PERFIL DEL ESTUDIANTE
# ==========================================================

@staff_member_required(login_url="/admin/login/")
def admin_perfil_estudiante(request, estudiante_id):

    # ------------------------------------------------------
    # 1. VERIFICAR PERMISO PARA CONSULTAR ESTUDIANTES
    # ------------------------------------------------------

    if not asesor_tiene_permiso(
        request.user,
        "ver_estudiantes"
    ):
        return denegar_permiso(
            request,
            "ver_estudiantes"
        )

    # ------------------------------------------------------
    # 2. OBTENER ESTUDIANTE Y PERFIL
    # ------------------------------------------------------

    estudiante = get_object_or_404(
        User,
        id=estudiante_id,
        is_staff=False,
        is_superuser=False
    )

    perfil, creado = PerfilEstudiante.objects.get_or_create(
        estudiante=estudiante
    )

    contraseña_temporal = None

    if request.method == "POST":

        accion = request.POST.get("accion", "")

        # --------------------------------------------------
        # 3. ELIMINAR ESTUDIANTE
        # Permiso: eliminar_estudiantes
        # --------------------------------------------------

        if accion == "eliminar_estudiante":

            if not asesor_tiene_permiso(
                request.user,
                "eliminar_estudiantes"
            ):
                return denegar_permiso(
                    request,
                    "eliminar_estudiantes",
                    "admin_perfil_estudiante",
                    estudiante_id=estudiante.id
                )

            resultado = request.POST.get("resultado", "")

            observacion = request.POST.get(
                "observacion", ""
            ).strip()

            confirmacion = request.POST.get(
                "confirmar_eliminacion"
            )

            resultados_validos = [
                "completado",
                "desistio",
                "otra_agencia",
                "otro",
            ]

            if resultado not in resultados_validos:
                messages.error(
                    request,
                    "Selecciona un resultado válido para cerrar el proceso."
                )
                return redirect(
                    "admin_perfil_estudiante",
                    estudiante_id=estudiante.id
                )

            if confirmacion != "si":
                messages.error(
                    request,
                    "Debes confirmar que deseas eliminar al estudiante."
                )
                return redirect(
                    "admin_perfil_estudiante",
                    estudiante_id=estudiante.id
                )

            nombre_estudiante = (
                f"{perfil.nombres} {perfil.apellidos}".strip()
                or estudiante.get_full_name().strip()
                or estudiante.username
            )

            responsable = (
                request.user.get_full_name().strip()
                or request.user.username
            )

            archivos = []

            for documento in Documento.objects.filter(
                estudiante=estudiante
            ):
                if documento.archivo:
                    archivos.append((
                        documento.archivo.storage,
                        documento.archivo.name
                    ))

            with transaction.atomic():

                HistorialEstudiante.objects.create(
                    nombre_estudiante=nombre_estudiante,
                    resultado=resultado,
                    observacion=observacion,
                    responsable_nombre=responsable,
                )

                estudiante.delete()

                transaction.on_commit(
                    lambda archivos=archivos: eliminar_archivos_estudiante(
                        archivos
                    )
                )

            messages.success(
                request,
                "El estudiante fue eliminado y su historial quedó guardado."
            )

            return redirect("admin_inicio")

        # --------------------------------------------------
        # 4. RESTABLECER CONTRASEÑA DEL ESTUDIANTE
        # Permiso: restablecer_contrasenas
        # --------------------------------------------------

        elif accion == "restablecer_contrasena":

            if not asesor_tiene_permiso(
                request.user,
                "restablecer_contrasenas"
            ):
                return denegar_permiso(
                    request,
                    "restablecer_contrasenas",
                    "admin_perfil_estudiante",
                    estudiante_id=estudiante.id
                )

            caracteres = (
                "abcdefghijkmnopqrstuvwxyz"
                "ABCDEFGHJKLMNPQRSTUVWXYZ"
                "23456789"
                "!@#$%&*"
            )

            contraseña_temporal = None

            for intento in range(10):

                candidata = get_random_string(
                    20,
                    allowed_chars=caracteres
                )

                try:
                    validate_password(
                        candidata,
                        user=estudiante
                    )

                    contraseña_temporal = candidata
                    break

                except ValidationError:
                    continue

            if not contraseña_temporal:

                messages.error(
                    request,
                    "No fue posible generar una contraseña válida. Inténtalo nuevamente."
                )

                return redirect(
                    "admin_perfil_estudiante",
                    estudiante_id=estudiante.id
                )

            # Guardar únicamente el hash de la contraseña.

            estudiante.set_password(contraseña_temporal)

            estudiante.save(
                update_fields=["password"]
            )

            messages.success(
                request,
                "La contraseña del estudiante fue restablecida correctamente."
            )

        # --------------------------------------------------
        # 5. GESTIONAR REQUISITOS DOCUMENTALES
        # Permiso: gestionar_documentos
        # --------------------------------------------------

        elif accion == "guardar_requisitos":

            if not asesor_tiene_permiso(
                request.user,
                "gestionar_documentos"
            ):
                return denegar_permiso(
                    request,
                    "gestionar_documentos",
                    "admin_perfil_estudiante",
                    estudiante_id=estudiante.id
                )

            tipos_seleccionados = request.POST.getlist(
                "tipos_documentos"
            )

            tipos_validos = list(
                TipoDocumento.objects.filter(
                    activo=True,
                    id__in=tipos_seleccionados
                ).values_list("id", flat=True)
            )

            with transaction.atomic():

                for tipo_id in tipos_validos:

                    requisito, creado = (
                        RequisitoDocumento.objects.get_or_create(
                            estudiante=estudiante,
                            tipo_documento_id=tipo_id,
                            defaults={
                                "habilitado": True,
                                "fecha_solicitud": timezone.now(),
                            }
                        )
                    )

                    if not creado:

                        campos_actualizados = []

                        if not requisito.habilitado:
                            requisito.habilitado = True
                            campos_actualizados.append("habilitado")

                        if requisito.fecha_solicitud is None:
                            requisito.fecha_solicitud = timezone.now()
                            campos_actualizados.append("fecha_solicitud")

                        if campos_actualizados:
                            requisito.save(
                                update_fields=campos_actualizados
                            )

                RequisitoDocumento.objects.filter(
                    estudiante=estudiante
                ).exclude(
                    tipo_documento_id__in=tipos_validos
                ).update(
                    habilitado=False
                )

            messages.success(
                request,
                "Los requisitos documentales del estudiante se actualizaron correctamente. Las fechas originales de solicitud se conservaron."
            )

        # --------------------------------------------------
        # 6. EDITAR INFORMACIÓN PERSONAL DEL ESTUDIANTE
        # Permiso: editar_informacion
        # --------------------------------------------------

        elif accion == "guardar_informacion_personal":

            if not asesor_tiene_permiso(
                request.user,
                "editar_informacion"
            ):
                return denegar_permiso(
                    request,
                    "editar_informacion",
                    "admin_perfil_estudiante",
                    estudiante_id=estudiante.id
                )

            nombres = request.POST.get("nombres", "").strip()
            apellidos = request.POST.get("apellidos", "").strip()
            telefono = request.POST.get("telefono", "").strip()
            correo = request.POST.get("correo", "").strip().lower()
            edad_texto = request.POST.get("edad", "").strip()

            # El correo también es el nombre de usuario del estudiante.
            if not correo:
                messages.error(
                    request,
                    "El correo electrónico es obligatorio porque también funciona como nombre de usuario."
                )

            else:
                try:
                    validate_email(correo)
                except ValidationError:
                    messages.error(
                        request,
                        "Escribe una dirección de correo electrónico válida."
                    )
                else:
                    correo_en_uso = User.objects.filter(
                        Q(username__iexact=correo) | Q(email__iexact=correo)
                    ).exclude(
                        id=estudiante.id
                    ).exists()

                    if correo_en_uso:
                        messages.error(
                            request,
                            "Ese correo electrónico ya está asociado a otra cuenta."
                        )
                    else:
                        edad = None
                        edad_valida = True

                        if edad_texto:
                            try:
                                edad = int(edad_texto)
                                if edad < 0:
                                    edad_valida = False
                            except (TypeError, ValueError):
                                edad_valida = False

                        if not edad_valida:
                            messages.error(
                                request,
                                "La edad debe ser un número entero igual o mayor que cero."
                            )
                        else:
                            with transaction.atomic():
                                perfil.nombres = nombres
                                perfil.apellidos = apellidos
                                perfil.edad = edad
                                perfil.telefono = telefono
                                perfil.save(
                                    update_fields=[
                                        "nombres",
                                        "apellidos",
                                        "edad",
                                        "telefono",
                                    ]
                                )

                                estudiante.first_name = nombres
                                estudiante.last_name = apellidos
                                estudiante.email = correo
                                estudiante.username = correo
                                estudiante.save(
                                    update_fields=[
                                        "first_name",
                                        "last_name",
                                        "email",
                                        "username",
                                    ]
                                )

                            messages.success(
                                request,
                                "La información personal del estudiante se actualizó correctamente."
                            )

        # --------------------------------------------------
        # 7. EDITAR PREFERENCIAS ACADÉMICAS
        # Permiso: editar_informacion
        # --------------------------------------------------

        elif accion == "guardar_preferencias":

            if not asesor_tiene_permiso(
                request.user,
                "editar_informacion"
            ):
                return denegar_permiso(
                    request,
                    "editar_informacion",
                    "admin_perfil_estudiante",
                    estudiante_id=estudiante.id
                )

            campos_texto = [
                "carrera_1", "universidad_1", "pais_1",
                "carrera_2", "universidad_2", "pais_2",
                "carrera_3", "universidad_3", "pais_3",
                "carrera_4", "universidad_4", "pais_4",
            ]

            campos_fecha = [
                "intake_1", "deadline_1",
                "intake_2", "deadline_2",
                "intake_3", "deadline_3",
                "intake_4", "deadline_4",
            ]

            fechas_procesadas = {}
            fechas_invalidas = []

            for campo in campos_fecha:

                valor = request.POST.get(
                    campo, ""
                ).strip()

                if valor:

                    fecha = parse_date(valor)

                    if fecha is None:
                        fechas_invalidas.append(campo)
                    else:
                        fechas_procesadas[campo] = fecha

                else:
                    fechas_procesadas[campo] = None

            if fechas_invalidas:

                messages.error(
                    request,
                    "Una o varias fechas no tienen un formato válido. No se guardaron los cambios."
                )

            else:

                for campo in campos_texto:

                    setattr(
                        perfil,
                        campo,
                        request.POST.get(campo, "").strip()
                    )

                for campo, fecha in fechas_procesadas.items():

                    setattr(
                        perfil,
                        campo,
                        fecha
                    )

                perfil.save()

                messages.success(
                    request,
                    "Las preferencias académicas, Intake y Deadline se guardaron correctamente."
                )

        # --------------------------------------------------
        # 8. REVISAR DOCUMENTOS
        # Permiso: revisar_documentos
        # --------------------------------------------------

        elif accion == "actualizar_documento":

            if not asesor_tiene_permiso(
                request.user,
                "revisar_documentos"
            ):
                return denegar_permiso(
                    request,
                    "revisar_documentos",
                    "admin_perfil_estudiante",
                    estudiante_id=estudiante.id
                )

            documento = get_object_or_404(
                Documento,
                id=request.POST.get("documento_id"),
                estudiante=estudiante
            )

            nuevo_estado = request.POST.get(
                "estado", ""
            )

            observaciones = request.POST.get(
                "observaciones", ""
            ).strip()

            estados_validos = [
                "pendiente",
                "aprobado",
                "corregir"
            ]

            if nuevo_estado in estados_validos:

                documento.estado = nuevo_estado
                documento.observaciones = observaciones

                documento.save(
                    update_fields=["estado", "observaciones"]
                )

                messages.success(
                    request,
                    "El documento y sus observaciones se actualizaron correctamente."
                )

            else:

                messages.error(
                    request,
                    "El estado seleccionado no es válido."
                )

        # --------------------------------------------------
        # 9. REGISTRAR NOTAS DE SEGUIMIENTO
        # Permiso: registrar_notas
        # --------------------------------------------------

        elif accion == "guardar_nota":

            if not asesor_tiene_permiso(
                request.user,
                "registrar_notas"
            ):
                return denegar_permiso(
                    request,
                    "registrar_notas",
                    "admin_perfil_estudiante",
                    estudiante_id=estudiante.id
                )

            contenido = request.POST.get(
                "contenido", ""
            ).strip()

            if contenido:

                NotaSeguimiento.objects.create(
                    estudiante=estudiante,
                    administrador=request.user,
                    contenido=contenido
                )

                messages.success(
                    request,
                    "La nota de seguimiento se guardó correctamente."
                )

            else:

                messages.error(
                    request,
                    "Escribe una observación antes de guardar."
                )

        # --------------------------------------------------
        # 10. VALIDAR ACCIONES NO RECONOCIDAS
        # --------------------------------------------------

        else:

            messages.error(
                request,
                "La operación solicitada no es válida."
            )

        # --------------------------------------------------
        # 11. REDIRECCIÓN O MOSTRAR CONTRASEÑA TEMPORAL
        # --------------------------------------------------

        # Si se restableció una contraseña, mostrarla
        # una sola vez en esta respuesta.

        if not (
            accion == "restablecer_contrasena"
            and contraseña_temporal
        ):

            return redirect(
                "admin_perfil_estudiante",
                estudiante_id=estudiante.id
            )

    # ------------------------------------------------------
    # 12. INFORMACIÓN PARA MOSTRAR EN EL PERFIL
    # ------------------------------------------------------

    tipos_documentos_disponibles = TipoDocumento.objects.filter(
        activo=True
    ).order_by("nombre")

    requisitos_seleccionados = list(
        RequisitoDocumento.objects.filter(
            estudiante=estudiante,
            habilitado=True
        ).values_list("tipo_documento_id", flat=True)
    )

    requisitos = RequisitoDocumento.objects.filter(
        estudiante=estudiante,
        habilitado=True
    ).select_related("tipo_documento")

    documentos = Documento.objects.filter(
        estudiante=estudiante
    ).select_related(
        "tipo_documento"
    ).order_by("-fecha_carga")

    documentos_por_tipo = {}

    for documento in documentos:

        if documento.tipo_documento_id not in documentos_por_tipo:

            documentos_por_tipo[documento.tipo_documento_id] = documento

    documentos_unificados = []

    for requisito in requisitos:

        documentos_unificados.append({
            "tipo": requisito.tipo_documento,
            "habilitado": requisito.habilitado,
            "fecha_solicitud": requisito.fecha_solicitud,
            "documento": documentos_por_tipo.get(
                requisito.tipo_documento_id
            ),
        })

    notas = NotaSeguimiento.objects.filter(
        estudiante=estudiante
    ).select_related(
        "administrador"
    )

    # ------------------------------------------------------
    # 13. CONTEXTO DE LA PÁGINA Y PERMISOS DE ACCIÓN
    # ------------------------------------------------------

    contexto = {
        "estudiante": estudiante,
        "perfil": perfil,
        "documentos_unificados": documentos_unificados,
        "notas": notas,
        "tipos_documentos_disponibles": tipos_documentos_disponibles,
        "requisitos_seleccionados": requisitos_seleccionados,
        "contraseña_temporal": contraseña_temporal,

        # Permisos para mostrar u ocultar controles
        "puede_eliminar_estudiante": asesor_tiene_permiso(
            request.user, "eliminar_estudiantes"
        ),
        "puede_restablecer_contrasenas": asesor_tiene_permiso(
            request.user, "restablecer_contrasenas"
        ),
        "puede_gestionar_documentos": asesor_tiene_permiso(
            request.user, "gestionar_documentos"
        ),
        "puede_editar_informacion": asesor_tiene_permiso(
            request.user, "editar_informacion"
        ),
        "puede_revisar_documentos": asesor_tiene_permiso(
            request.user, "revisar_documentos"
        ),
        "puede_registrar_notas": asesor_tiene_permiso(
            request.user, "registrar_notas"
        ),
    }

    # ------------------------------------------------------
    # 14. MOSTRAR PERFIL DEL ESTUDIANTE
    # ------------------------------------------------------

    return render(
        request,
        "portal/admin/perfil_estudiante.html",
        contexto
    )


# ==========================================================
# HISTORIAL DE ESTUDIANTES
# ==========================================================

@staff_member_required(login_url="/admin/login/")
def admin_historial_estudiantes(request):

    # Verificar permiso para consultar el historial
    if not asesor_tiene_permiso(
        request.user,
        "ver_historial"
    ):
        return denegar_permiso(
            request,
            "ver_historial"
        )

    if request.method == "POST":

        # Solamente el administrador principal puede eliminar
        if not request.user.is_superuser:
            messages.error(
                request,
                "No tienes permisos para eliminar registros del historial."
            )
            return redirect("admin_historial_estudiantes")

        accion = request.POST.get("accion", "")

        if accion == "eliminar_historial":

            registro = get_object_or_404(
                HistorialEstudiante,
                id=request.POST.get("historial_id")
            )

            registro.delete()

            messages.success(
                request,
                "El registro del historial fue eliminado correctamente."
            )

        else:
            messages.error(
                request,
                "La acción solicitada no es válida."
            )

        return redirect("admin_historial_estudiantes")

    historial_estudiantes = HistorialEstudiante.objects.all().order_by(
        "-fecha_finalizacion"
    )

    contexto = {
        "historial_estudiantes": historial_estudiantes,
        "es_administrador_principal": request.user.is_superuser,
    }

    return render(
        request,
        "portal/admin/historial_estudiantes.html",
        contexto
    )

# ==========================================================
# GESTIÓN DE ASESORES
# EXCLUSIVA DEL ADMINISTRADOR PRINCIPAL
# ==========================================================

@staff_member_required(login_url="/admin/login/")
def admin_asesores(request):

    if not request.user.is_superuser:
        messages.error(
            request,
            "No tienes permisos para acceder a la gestión de asesores."
        )
        return redirect("admin_inicio")

    asesores = list(
        User.objects.filter(
            is_staff=True,
            is_superuser=False
        ).order_by(
            "first_name",
            "last_name",
            "username"
        )
    )

    for asesor in asesores:
        PermisosAsesor.objects.get_or_create(
            asesor=asesor
        )

    contexto = {
        "asesores": asesores,
    }

    return render(
        request,
        "portal/admin/asesores.html",
        contexto
    )


# ==========================================================
# CREAR ASESOR
# EXCLUSIVO DEL ADMINISTRADOR PRINCIPAL
# ==========================================================

@staff_member_required(login_url="/admin/login/")
def admin_crear_asesor(request):

    if not request.user.is_superuser:
        messages.error(
            request,
            "No tienes permisos para crear asesores."
        )
        return redirect("admin_inicio")

    if request.method == "POST":

        nombres = request.POST.get("nombres", "").strip()
        apellidos = request.POST.get("apellidos", "").strip()
        email = request.POST.get("email", "").strip().lower()
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        password_confirmacion = request.POST.get(
            "password_confirmacion",
            ""
        )

        errores = []

        if not nombres:
            errores.append("Debes ingresar los nombres.")

        if not apellidos:
            errores.append("Debes ingresar los apellidos.")

        if not email:
            errores.append("Debes ingresar el correo electrónico.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                errores.append("El correo electrónico no es válido.")

        if not username:
            errores.append("Debes ingresar un nombre de usuario.")
        elif User.objects.filter(username__iexact=username).exists():
            errores.append("Ese nombre de usuario ya está registrado.")

        if email and User.objects.filter(email__iexact=email).exists():
            errores.append("Ese correo electrónico ya está registrado.")

        if not password:
            errores.append("Debes ingresar una contraseña.")

        if password != password_confirmacion:
            errores.append("Las contraseñas no coinciden.")

        if password:
            try:
                validate_password(password)
            except ValidationError as error:
                errores.extend(error.messages)

        if errores:
            for error in errores:
                messages.error(request, error)

            return render(
                request,
                "portal/admin/crear_asesor.html",
                {
                    "datos": request.POST,
                }
            )

        try:
            with transaction.atomic():

                asesor = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=nombres,
                    last_name=apellidos,
                    is_staff=True,
                    is_superuser=False,
                    is_active=True
                )

                PermisosAsesor.objects.create(
                    asesor=asesor
                )

            messages.success(
                request,
                f"El asesor {nombres} {apellidos} fue creado correctamente."
            )

            return redirect("admin_asesores")

        except Exception:
            messages.error(
                request,
                "No fue posible crear el asesor. Verifica los datos e inténtalo nuevamente."
            )

    return render(
        request,
        "portal/admin/crear_asesor.html",
        {
            "datos": {},
        }
    )


# ==========================================================

# ============================================================
# EDITAR PERMISOS DE ASESORES
# EXCLUSIVO DEL ADMINISTRADOR PRINCIPAL
# ============================================================

@staff_member_required(login_url="/admin/login/")
def admin_editar_permisos_asesor(request, asesor_id):

    # --------------------------------------------------------
    # 1. VALIDAR ACCESO DEL ADMINISTRADOR PRINCIPAL
    # --------------------------------------------------------

    if not request.user.is_superuser:
        messages.error(
            request,
            "No tienes permisos para modificar los permisos de asesores."
        )
        return redirect("admin_inicio")

    # --------------------------------------------------------
    # 2. BUSCAR AL ASESOR
    # --------------------------------------------------------

    asesor = get_object_or_404(
        User,
        id=asesor_id,
        is_staff=True,
        is_superuser=False
    )

    # --------------------------------------------------------
    # 3. OBTENER O CREAR SUS PERMISOS
    # --------------------------------------------------------

    permisos, creado = PermisosAsesor.objects.get_or_create(
        asesor=asesor
    )

    # --------------------------------------------------------
    # 4. LISTA DE LOS DIEZ PERMISOS
    # --------------------------------------------------------

    campos_permisos = [
        ("ver_estudiantes", "Ver estudiantes"),
        ("crear_estudiantes", "Crear estudiantes"),
        ("eliminar_estudiantes", "Eliminar estudiantes"),
        ("editar_informacion", "Editar información"),
        ("gestionar_documentos", "Gestionar documentos"),
        ("revisar_documentos", "Revisar documentos"),
        ("registrar_notas", "Registrar notas"),
        ("gestionar_tipos_documentales", "Gestionar tipos documentales"),
        ("ver_historial", "Ver historial"),
        ("restablecer_contrasenas", "Restablecer contraseñas"),
    ]

    # --------------------------------------------------------
    # 5. PROCESAR LOS CAMBIOS DE PERMISOS
    # --------------------------------------------------------

    if request.method == "POST":

        # Ver estudiantes es un permiso obligatorio.
        # Si se intenta deshabilitar, se rechaza todo el envío.

        if "ver_estudiantes" not in request.POST:

            messages.error(
                request,
                "No se guardaron los cambios. El permiso "
                "'Ver estudiantes' es obligatorio y no puede deshabilitarse. "
                "Si deseas bloquear al asesor, puedes desactivar su cuenta "
                "desde Gestión de asesores."
            )

            return redirect(
                "admin_editar_permisos_asesor",
                asesor_id=asesor.id
            )

        # ----------------------------------------------------
        # 6. MANTENER HABILITADO EL PERMISO OBLIGATORIO
        # ----------------------------------------------------

        permisos.ver_estudiantes = True

        # ----------------------------------------------------
        # 7. GUARDAR LOS OTROS NUEVE PERMISOS
        # ----------------------------------------------------

        for campo, etiqueta in campos_permisos:

            if campo == "ver_estudiantes":
                continue

            setattr(
                permisos,
                campo,
                campo in request.POST
            )

        permisos.save()

        # ----------------------------------------------------
        # 8. CONFIRMAR LA ACTUALIZACIÓN
        # ----------------------------------------------------

        messages.success(
            request,
            f"Los permisos de {asesor.get_full_name() or asesor.username} "
            "fueron actualizados correctamente."
        )

        return redirect("admin_asesores")

    # --------------------------------------------------------
    # 9. PREPARAR LOS PERMISOS PARA MOSTRAR EN PANTALLA
    # --------------------------------------------------------

    lista_permisos = [
        {
            "campo": campo,
            "etiqueta": etiqueta,
            "habilitado": getattr(permisos, campo),
        }
        for campo, etiqueta in campos_permisos
    ]

    # --------------------------------------------------------
    # 10. ENVIAR INFORMACIÓN A LA PLANTILLA
    # --------------------------------------------------------

    contexto = {
        "asesor": asesor,
        "lista_permisos": lista_permisos,
    }

    return render(
        request,
        "portal/admin/editar_permisos_asesor.html",
        contexto
    )


# ==========================================================
# CREAR ESTUDIANTE
# DISPONIBLE PARA ASESORES CON EL PERMISO CORRESPONDIENTE
# CONTRASEÑA TEMPORAL GENERADA AUTOMÁTICAMENTE
# ==========================================================

@staff_member_required(login_url="/admin/login/")
def admin_crear_estudiante(request):

    if not asesor_tiene_permiso(
        request.user,
        "crear_estudiantes"
    ):
        return denegar_permiso(
            request,
            "crear_estudiantes"
        )

    contexto = {
        "errores": [],
        "nombres": "",
        "apellidos": "",
        "email": "",
    }

    if request.method == "POST":

        nombres = request.POST.get("nombres", "").strip()
        apellidos = request.POST.get("apellidos", "").strip()
        email = request.POST.get("email", "").strip().lower()

        contexto.update({
            "nombres": nombres,
            "apellidos": apellidos,
            "email": email,
        })

        errores = []

        if not nombres:
            errores.append("Debes ingresar los nombres.")

        if not apellidos:
            errores.append("Debes ingresar los apellidos.")

        if not email:
            errores.append("Debes ingresar el correo electrónico.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                errores.append("El correo electrónico no es válido.")

        if email and User.objects.filter(
            Q(username__iexact=email) |
            Q(email__iexact=email)
        ).exists():
            errores.append(
                "Ya existe una cuenta registrada con ese correo."
            )

        if errores:
            contexto["errores"] = errores
            return render(
                request,
                "portal/admin/crear_estudiante.html",
                contexto
            )

        contraseña_temporal = get_random_string(16)

        nuevo_usuario = User(
            username=email,
            email=email,
            first_name=nombres,
            last_name=apellidos,
            is_staff=False,
            is_superuser=False,
            is_active=True,
        )

        try:
            validate_password(
                contraseña_temporal,
                user=nuevo_usuario
            )

            with transaction.atomic():

                estudiante = User.objects.create_user(
                    username=email,
                    email=email,
                    password=contraseña_temporal,
                    first_name=nombres,
                    last_name=apellidos,
                    is_staff=False,
                    is_superuser=False,
                    is_active=True,
                )

                PerfilEstudiante.objects.create(
                    estudiante=estudiante,
                    nombres=nombres,
                    apellidos=apellidos,
                )

        except ValidationError as error:
            contexto["errores"] = list(error.messages)
            return render(
                request,
                "portal/admin/crear_estudiante.html",
                contexto
            )

        return render(
            request,
            "portal/admin/crear_estudiante.html",
            {
                "estudiante_creado": estudiante,
                "contraseña_temporal": contraseña_temporal,
            }
        )

    return render(
        request,
        "portal/admin/crear_estudiante.html",
        contexto
    )
