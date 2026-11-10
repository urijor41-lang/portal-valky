
import os
import zipfile

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm,
    PasswordChangeForm
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.utils import timezone
from django.http import FileResponse, HttpResponseForbidden, Http404


from .models import (
    RequisitoDocumento,
    Documento,
    PerfilEstudiante,
    TipoDocumento

)
from .forms import PerfilEstudianteForm


# ==========================================================
# CONFIGURACIÓN Y VALIDACIÓN DE ARCHIVOS
# ==========================================================

TAMANO_MAXIMO_ARCHIVO = 10 * 1024 * 1024

FORMATOS_PERMITIDOS = {
    ".pdf",
    ".doc",
    ".docx",
}


def validar_archivo_documento(archivo):

    """
    Comprueba el tamaño, extensión y contenido real
    de los documentos cargados por los estudiantes.

    Devuelve None si el archivo es válido.
    Devuelve un mensaje si no cumple los requisitos.
    """

    if not archivo:
        return "Selecciona un archivo para continuar."

    # ------------------------------------------------------
    # 1. VALIDAR TAMAÑO
    # ------------------------------------------------------

    if archivo.size > TAMANO_MAXIMO_ARCHIVO:

        return (
            "El archivo supera el tamaño máximo permitido "
            "de 10 MB."
        )

    # ------------------------------------------------------
    # 2. VALIDAR EXTENSIÓN
    # ------------------------------------------------------

    extension = os.path.splitext(
        archivo.name
    )[1].lower()

    if extension not in FORMATOS_PERMITIDOS:

        return (
            "Formato no permitido. "
            "Solo puedes cargar archivos PDF, DOC o DOCX."
        )

    # ------------------------------------------------------
    # 3. VALIDAR CONTENIDO REAL
    # ------------------------------------------------------

    try:

        archivo.seek(0)

        if extension == ".pdf":

            contenido = archivo.read(1024)

            if b"%PDF-" not in contenido:

                return (
                    "El archivo no parece ser un documento PDF válido."
                )

        elif extension == ".doc":

            contenido = archivo.read(8)

            firma_doc = bytes.fromhex(
                "D0 CF 11 E0 A1 B1 1A E1"
            )

            if contenido != firma_doc:

                return (
                    "El archivo no parece ser un documento DOC válido."
                )

        elif extension == ".docx":

            archivo.seek(0)

            with zipfile.ZipFile(archivo, "r") as documento_zip:

                archivos_internos = documento_zip.namelist()

                if (
                    "[Content_Types].xml" not in archivos_internos
                    or "word/document.xml" not in archivos_internos
                ):

                    return (
                        "El archivo no parece ser un documento DOCX válido."
                    )

    except (
        zipfile.BadZipFile,
        OSError,
        ValueError
    ):

        return (
            "No fue posible reconocer el contenido del archivo. "
            "Comprueba que el documento no esté dañado."
        )

    finally:

        archivo.seek(0)

    return None


# ==========================================================
# 1. INICIO DEL PORTAL DE ESTUDIANTES
# ==========================================================

def inicio(request):

    if not request.user.is_authenticated:
        return render(request, "portal/inicio.html")

    perfil, creado = PerfilEstudiante.objects.get_or_create(
        estudiante=request.user
    )

    nombre_estudiante = (
        perfil.nombres.strip()
        if perfil.nombres and perfil.nombres.strip()
        else request.user.username
    )

    requisitos = list(
        RequisitoDocumento.objects.filter(
            estudiante=request.user,
            habilitado=True
        ).select_related(
            "tipo_documento"
        )
    )

    tipos_habilitados = {
        requisito.tipo_documento_id
        for requisito in requisitos
    }

    documentos = Documento.objects.filter(
        estudiante=request.user,
        tipo_documento_id__in=tipos_habilitados
    ).order_by(
        "-fecha_carga",
        "-id"
    )

    documentos_por_tipo = {}

    for documento in documentos:

        if documento.tipo_documento_id not in documentos_por_tipo:
            documentos_por_tipo[documento.tipo_documento_id] = documento

    documentos_pendientes = 0
    documentos_aprobados = 0
    documentos_corregir = 0

    for tipo_documento_id in tipos_habilitados:

        documento = documentos_por_tipo.get(tipo_documento_id)

        if documento is None:
            documentos_pendientes += 1

        elif documento.estado == "pendiente":
            documentos_pendientes += 1

        elif documento.estado == "aprobado":
            documentos_aprobados += 1

        elif documento.estado == "corregir":
            documentos_corregir += 1

    return render(request, "portal/inicio.html", {
        "nombre_estudiante": nombre_estudiante,
        "documentos_pendientes": documentos_pendientes,
        "documentos_aprobados": documentos_aprobados,
        "documentos_corregir": documentos_corregir,
    })


# ==========================================================
# 2. REGISTRO DE ESTUDIANTES
# ==========================================================

def registro(request):

    if request.method == "POST":

        formulario = UserCreationForm(request.POST)

        if formulario.is_valid():

            usuario = formulario.save()

            PerfilEstudiante.objects.create(
                estudiante=usuario
            )

            login(request, usuario)

            return redirect("inicio")

    else:

        formulario = UserCreationForm()

    return render(request, "portal/registro.html", {
        "formulario": formulario
    })


# ==========================================================
# 3. INICIO DE SESIÓN
# ==========================================================

def iniciar_sesion(request):

    if request.method == "POST":

        formulario = AuthenticationForm(
            request,
            data=request.POST
        )

        if formulario.is_valid():

            login(request, formulario.get_user())

            return redirect("inicio")

    else:

        formulario = AuthenticationForm(request)

    return render(request, "portal/iniciar_sesion.html", {
        "formulario": formulario
    })


# ==========================================================
# 4. CERRAR SESIÓN
# ==========================================================

def cerrar_sesion(request):

    if request.method == "POST":

        es_personal_administrativo = (
            request.user.is_authenticated
            and request.user.is_staff
        )

        logout(request)

        if es_personal_administrativo:
            return redirect("/admin/login/")

        return redirect("inicio")

    return redirect("inicio")


# ==========================================================
# 5. CAMBIAR CONTRASEÑA
# ==========================================================

@login_required
def cambiar_contrasena(request):

    if request.method == "POST":

        formulario = PasswordChangeForm(
            user=request.user,
            data=request.POST
        )

        if formulario.is_valid():

            usuario = formulario.save()

            update_session_auth_hash(request, usuario)

            messages.success(
                request,
                "Tu contraseña se actualizó correctamente."
            )

            return redirect("inicio")

        else:

            messages.error(
                request,
                "No fue posible cambiar la contraseña. "
                "Revisa los campos e inténtalo nuevamente."
            )

    else:

        formulario = PasswordChangeForm(
            user=request.user
        )

    return render(request, "portal/cambiar_contrasena.html", {
        "formulario": formulario
    })


# ==========================================================
# 6. PERFIL DEL ESTUDIANTE
# ==========================================================

@login_required
def mi_perfil(request):

    perfil, creado = PerfilEstudiante.objects.get_or_create(
        estudiante=request.user
    )

    if request.method == "POST":

        formulario = PerfilEstudianteForm(
            request.POST,
            instance=perfil
        )

        if formulario.is_valid():

            formulario.save()

            messages.success(
                request,
                "Tu perfil se actualizó correctamente."
            )

            return redirect("mi_perfil")

    else:

        formulario = PerfilEstudianteForm(
            instance=perfil
        )

    formulario.fields["email"].initial = request.user.email

    return render(request, "portal/mi_perfil.html", {
        "formulario": formulario
    })


# ==========================================================
# 7.5. DESCARGA PROTEGIDA DE DOCUMENTOS DEL ESTUDIANTE
# ==========================================================

@login_required(login_url="/iniciar-sesion/")
def descargar_documento(request, documento_id):

    documento = get_object_or_404(
        Documento,
        id=documento_id
    )

    # Verificar permisos del personal administrativo
    if request.user.is_staff:

        if request.user.is_superuser:
            autorizado = True
        else:
            from .admin_views import asesor_tiene_permiso

            autorizado = asesor_tiene_permiso(
                request.user,
                "ver_estudiantes"
            )

        if not autorizado:
            return HttpResponseForbidden(
                "No tienes permiso para consultar este documento."
            )

    # El estudiante solo puede consultar sus propios documentos
    else:

        if documento.estudiante_id != request.user.id:
            raise Http404(
                "El documento solicitado no existe."
            )

    if not documento.archivo:
        raise Http404("El documento no tiene un archivo disponible.")

    try:
        archivo_abierto = documento.archivo.open("rb")
    except (FileNotFoundError, OSError):
        raise Http404("El archivo no está disponible.")

    nombre_archivo = os.path.basename(
        documento.archivo.name
    )

    extension = os.path.splitext(
        nombre_archivo
    )[1].lower()

    tipos_mime = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    tipo_contenido = tipos_mime.get(
        extension,
        "application/octet-stream"
    )

    respuesta = FileResponse(
        archivo_abierto,
        as_attachment=False,
        filename=nombre_archivo,
        content_type=tipo_contenido
    )

    respuesta["X-Content-Type-Options"] = "nosniff"
    respuesta["Cache-Control"] = "private, no-store"

    return respuesta

# ==========================================================
# 7.6. DESCARGA PROTEGIDA DE ARCHIVOS DE EJEMPLO
# ==========================================================

@login_required(login_url="/iniciar-sesion/")
def descargar_ejemplo_documento(request, tipo_id):

    tipo = get_object_or_404(
        TipoDocumento,
        id=tipo_id
    )

    # ------------------------------------------------------
    # 7.6.1 VERIFICAR QUE EXISTA UN ARCHIVO DE EJEMPLO
    # ------------------------------------------------------

    if not tipo.archivo_ejemplo:

        raise Http404(
            "Este tipo de documento no tiene un ejemplo disponible."
        )

    try:

        archivo_abierto = tipo.archivo_ejemplo.open("rb")

    except (FileNotFoundError, OSError):

        raise Http404(
            "El archivo de ejemplo no está disponible."
        )

    # ------------------------------------------------------
    # 7.6.2 IDENTIFICAR EL FORMATO DEL ARCHIVO
    # ------------------------------------------------------

    nombre_archivo = os.path.basename(
        tipo.archivo_ejemplo.name
    )

    extension = os.path.splitext(
        nombre_archivo
    )[1].lower()

    tipos_mime = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }

    tipo_contenido = tipos_mime.get(
        extension,
        "application/octet-stream"
    )

    # ------------------------------------------------------
    # 7.6.3 ENTREGAR EL ARCHIVO
    # ------------------------------------------------------

    respuesta = FileResponse(
        archivo_abierto,
        as_attachment=False,
        filename=nombre_archivo,
        content_type=tipo_contenido
    )

    respuesta["X-Content-Type-Options"] = "nosniff"
    respuesta["Cache-Control"] = "private, no-store"

    return respuesta


# ==========================================================
# 8. DOCUMENTOS DEL ESTUDIANTE
# ==========================================================

@login_required
def mis_documentos(request):

    requisitos = list(
        RequisitoDocumento.objects.filter(
            estudiante=request.user,
            habilitado=True
        ).select_related(
            "tipo_documento"
        ).order_by(
            "tipo_documento__nombre"
        )
    )

    # ------------------------------------------------------
    # 8.1 PROCESAR CARGA DE DOCUMENTOS
    # ------------------------------------------------------

    if request.method == "POST":

        requisito_id = request.POST.get("requisito_id")
        archivo = request.FILES.get("archivo")

        if not requisito_id or not requisito_id.isdigit() or not archivo:

            messages.error(
                request,
                "Selecciona un documento y un archivo para continuar."
            )

            return redirect("mis_documentos")

        requisito = get_object_or_404(
            RequisitoDocumento,
            id=int(requisito_id),
            estudiante=request.user,
            habilitado=True
        )

        # --------------------------------------------------
        # 8.1.1 VALIDAR ARCHIVO
        # --------------------------------------------------

        error_archivo = validar_archivo_documento(
            archivo
        )

        if error_archivo:

            messages.error(
                request,
                error_archivo
            )

            return redirect("mis_documentos")

        documento = Documento.objects.filter(
            estudiante=request.user,
            tipo_documento=requisito.tipo_documento
        ).order_by(
            "-fecha_carga",
            "-id"
        ).first()

        # --------------------------------------------------
        # 8.1.2 CREAR PRIMER DOCUMENTO
        # --------------------------------------------------

        if documento is None:

            Documento.objects.create(
                estudiante=request.user,
                tipo_documento=requisito.tipo_documento,
                archivo=archivo
            )

            messages.success(
                request,
                "Tu documento se cargó correctamente y quedó pendiente de revisión."
            )

            return redirect("mis_documentos")

        # --------------------------------------------------
        # 8.1.3 REEMPLAZAR DOCUMENTO POR CORREGIR
        # --------------------------------------------------

        if documento.estado == "corregir":

            archivo_anterior = (
                documento.archivo.name
                if documento.archivo
                else None
            )

            documento.archivo = archivo
            documento.estado = "pendiente"
            documento.observaciones = ""
            documento.fecha_carga = timezone.now()

            documento.save(update_fields=[
                "archivo",
                "estado",
                "observaciones",
                "fecha_carga"
            ])

            if (
                archivo_anterior
                and archivo_anterior != documento.archivo.name
            ):

                documento.archivo.storage.delete(
                    archivo_anterior
                )

            messages.success(
                request,
                "El documento fue reemplazado correctamente y quedó pendiente de una nueva revisión."
            )

            return redirect("mis_documentos")

        # --------------------------------------------------
        # 8.1.4 DOCUMENTO EN REVISIÓN
        # --------------------------------------------------

        if documento.estado == "pendiente":

            messages.error(
                request,
                "Tu documento ya está en revisión. Espera la respuesta del administrador."
            )

            return redirect("mis_documentos")

        # --------------------------------------------------
        # 8.1.5 DOCUMENTO APROBADO
        # --------------------------------------------------

        if documento.estado == "aprobado":

            messages.error(
                request,
                "Este documento ya fue aprobado. No necesitas cargarlo nuevamente."
            )

            return redirect("mis_documentos")

        messages.error(
            request,
            "No fue posible procesar el documento. Comunícate con el administrador."
        )

        return redirect("mis_documentos")

    # ------------------------------------------------------
    # 8.2 CONSULTAR DOCUMENTOS HABILITADOS
    # ------------------------------------------------------

    tipos_habilitados = [
        requisito.tipo_documento_id
        for requisito in requisitos
    ]

    documentos = Documento.objects.filter(
        estudiante=request.user,
        tipo_documento_id__in=tipos_habilitados
    ).select_related(
        "tipo_documento"
    ).order_by(
        "-fecha_carga",
        "-id"
    )

    # ------------------------------------------------------
    # 8.3 ASOCIAR DOCUMENTO MÁS RECIENTE A CADA REQUISITO
    # ------------------------------------------------------

    documentos_por_tipo = {}

    for documento in documentos:

        if documento.tipo_documento_id not in documentos_por_tipo:

            documentos_por_tipo[
                documento.tipo_documento_id
            ] = documento

    for requisito in requisitos:

        requisito.documento_actual = documentos_por_tipo.get(
            requisito.tipo_documento_id
        )
        
        requisito.archivo_ejemplo = (
            requisito.tipo_documento.archivo_ejemplo
        )

    return render(request, "portal/mis_documentos.html", {
        "requisitos": requisitos,
        "documentos": documentos
    })
