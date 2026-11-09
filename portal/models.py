
# ============================================================
# IMPORTACIONES
# ============================================================

from django.db import models
from django.contrib.auth.models import User


# ============================================================
# 1. TIPOS DE DOCUMENTOS
# ============================================================

class TipoDocumento(models.Model):

    nombre = models.CharField(max_length=150, unique=True)
    activo = models.BooleanField(default=True)

    archivo_ejemplo = models.FileField(
        upload_to="ejemplos_documentos/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.nombre


# ============================================================
# 2. DOCUMENTOS DE ESTUDIANTES
# ============================================================

class Documento(models.Model):

    ESTADOS = [
        ("pendiente", "Pendiente de revisión"),
        ("aprobado", "Aprobado"),
        ("corregir", "Requiere corrección"),
    ]

    estudiante = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="documentos"
    )

    tipo_documento = models.ForeignKey(
        TipoDocumento,
        on_delete=models.PROTECT,
        related_name="documentos"
    )

    archivo = models.FileField(
        upload_to="documentos_estudiantes/"
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="pendiente"
    )

    habilitado = models.BooleanField(default=False)
    fecha_carga = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True)

    def __str__(self):
        return f"{self.tipo_documento.nombre} - {self.estudiante.username}"


# ============================================================
# 3. REQUISITOS DOCUMENTALES DE ESTUDIANTES
# ============================================================

class RequisitoDocumento(models.Model):

    estudiante = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="requisitos_documentales"
    )

    tipo_documento = models.ForeignKey(
        TipoDocumento,
        on_delete=models.PROTECT,
        related_name="requisitos_estudiantes"
    )

    habilitado = models.BooleanField(default=False)

    fecha_solicitud = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ("estudiante", "tipo_documento")

    def __str__(self):
        estado = "Habilitado" if self.habilitado else "No habilitado"

        return (
            f"{self.estudiante.username} - "
            f"{self.tipo_documento.nombre} ({estado})"
        )


# ============================================================
# 4. PERFIL DE ESTUDIANTES
# ============================================================

class PerfilEstudiante(models.Model):

    ESTADOS_ACADEMICOS = [
        ("en_curso", "En curso"),
        ("graduado", "Graduado"),
    ]

    estudiante = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil"
    )

    # --------------------------------------------------------
    # INFORMACIÓN PERSONAL
    # --------------------------------------------------------

    nombres = models.CharField(max_length=150, blank=True)
    apellidos = models.CharField(max_length=150, blank=True)
    edad = models.PositiveIntegerField(null=True, blank=True)
    telefono = models.CharField(max_length=30, blank=True)

    # --------------------------------------------------------
    # CONTACTO DE EMERGENCIA
    # --------------------------------------------------------

    contacto_emergencia_nombre = models.CharField(
        max_length=150,
        blank=True
    )

    contacto_emergencia_parentesco = models.CharField(
        max_length=100,
        blank=True
    )

    contacto_emergencia_telefono = models.CharField(
        max_length=30,
        blank=True
    )

    # --------------------------------------------------------
    # FORMACIÓN ACADÉMICA: SECUNDARIA
    # --------------------------------------------------------

    secundaria_institucion = models.CharField(
        max_length=200,
        blank=True
    )

    secundaria_estado = models.CharField(
        max_length=20,
        choices=ESTADOS_ACADEMICOS,
        blank=True
    )

    secundaria_observaciones = models.TextField(blank=True)

    # --------------------------------------------------------
    # FORMACIÓN ACADÉMICA: PREGRADO
    # --------------------------------------------------------

    pregrado_institucion = models.CharField(
        max_length=200,
        blank=True
    )

    pregrado_estado = models.CharField(
        max_length=20,
        choices=ESTADOS_ACADEMICOS,
        blank=True
    )

    pregrado_observaciones = models.TextField(blank=True)

    # --------------------------------------------------------
    # FORMACIÓN ACADÉMICA: POSGRADO
    # --------------------------------------------------------

    posgrado_institucion = models.CharField(
        max_length=200,
        blank=True
    )

    posgrado_estado = models.CharField(
        max_length=20,
        choices=ESTADOS_ACADEMICOS,
        blank=True
    )

    posgrado_observaciones = models.TextField(blank=True)

    # --------------------------------------------------------
    # IDIOMAS
    # --------------------------------------------------------

    idioma_ingles = models.BooleanField(default=False)
    idioma_frances = models.BooleanField(default=False)
    idioma_italiano = models.BooleanField(default=False)
    idioma_mandarin = models.BooleanField(default=False)
    idioma_espanol = models.BooleanField(default=False)

    idiomas_observaciones = models.TextField(blank=True)

    # --------------------------------------------------------
    # PERIODO DE INGRESO ANTIGUO
    # --------------------------------------------------------

    intake = models.CharField(max_length=100, blank=True)

    # --------------------------------------------------------
    # UNIVERSIDAD 1
    # --------------------------------------------------------

    carrera_1 = models.CharField(max_length=200, blank=True)
    universidad_1 = models.CharField(max_length=200, blank=True)
    pais_1 = models.CharField(max_length=100, blank=True)

    intake_1 = models.DateField(null=True, blank=True)
    deadline_1 = models.DateField(null=True, blank=True)

    # --------------------------------------------------------
    # UNIVERSIDAD 2
    # --------------------------------------------------------

    carrera_2 = models.CharField(max_length=200, blank=True)
    universidad_2 = models.CharField(max_length=200, blank=True)
    pais_2 = models.CharField(max_length=100, blank=True)

    intake_2 = models.DateField(null=True, blank=True)
    deadline_2 = models.DateField(null=True, blank=True)

    # --------------------------------------------------------
    # UNIVERSIDAD 3
    # --------------------------------------------------------

    carrera_3 = models.CharField(max_length=200, blank=True)
    universidad_3 = models.CharField(max_length=200, blank=True)
    pais_3 = models.CharField(max_length=100, blank=True)

    intake_3 = models.DateField(null=True, blank=True)
    deadline_3 = models.DateField(null=True, blank=True)

    # --------------------------------------------------------
    # UNIVERSIDAD 4
    # --------------------------------------------------------

    carrera_4 = models.CharField(max_length=200, blank=True)
    universidad_4 = models.CharField(max_length=200, blank=True)
    pais_4 = models.CharField(max_length=100, blank=True)

    intake_4 = models.DateField(null=True, blank=True)
    deadline_4 = models.DateField(null=True, blank=True)

    # --------------------------------------------------------
    # REPRESENTACIÓN DEL PERFIL
    # --------------------------------------------------------

    def __str__(self):
        return f"Perfil de {self.estudiante.username}"


# ============================================================
# 5. NOTAS DE SEGUIMIENTO
# ============================================================

class NotaSeguimiento(models.Model):

    estudiante = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notas_seguimiento"
    )

    administrador = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notas_registradas"
    )

    contenido = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Nota de seguimiento - {self.estudiante.username}"


# ============================================================
# 6. HISTORIAL DE ESTUDIANTES
# ============================================================

class HistorialEstudiante(models.Model):

    RESULTADOS = [
        ("completado", "Completado"),
        ("desistio", "Desistió del proceso"),
        ("otra_agencia", "Se fue con otra agencia"),
        ("otro", "Otro motivo"),
    ]

    nombre_estudiante = models.CharField(max_length=300)

    resultado = models.CharField(
        max_length=30,
        choices=RESULTADOS
    )

    observacion = models.TextField(blank=True)

    fecha_finalizacion = models.DateTimeField(auto_now_add=True)

    responsable_nombre = models.CharField(max_length=200)

    class Meta:
        ordering = ["-fecha_finalizacion"]

        verbose_name = "Historial de estudiante"
        verbose_name_plural = "Historial de estudiantes"

    def __str__(self):
        return (
            f"{self.nombre_estudiante} - "
            f"{self.get_resultado_display()}"
        )


# ============================================================
# 7. PERMISOS DE ASESORES
# ============================================================

class PermisosAsesor(models.Model):

    asesor = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="permisos_asesor"
    )

    # --------------------------------------------------------
    # PERMISOS GENERALES DE ESTUDIANTES
    # --------------------------------------------------------

    ver_estudiantes = models.BooleanField(default=True)
    crear_estudiantes = models.BooleanField(default=True)
    eliminar_estudiantes = models.BooleanField(default=True)
    editar_informacion = models.BooleanField(default=True)

    # --------------------------------------------------------
    # PERMISOS DOCUMENTALES
    # --------------------------------------------------------

    gestionar_documentos = models.BooleanField(default=True)
    revisar_documentos = models.BooleanField(default=True)
    gestionar_tipos_documentales = models.BooleanField(default=True)

    # --------------------------------------------------------
    # NOTAS E HISTORIAL
    # --------------------------------------------------------

    registrar_notas = models.BooleanField(default=True)
    ver_historial = models.BooleanField(default=True)

    # --------------------------------------------------------
    # SEGURIDAD Y ACCESO
    # --------------------------------------------------------

    restablecer_contrasenas = models.BooleanField(default=True)

    # --------------------------------------------------------
    # CONFIGURACIÓN DEL MODELO
    # --------------------------------------------------------

    class Meta:
        verbose_name = "Permisos de asesor"
        verbose_name_plural = "Permisos de asesores"

    def __str__(self):
        return f"Permisos de {self.asesor.username}"
