
from django import forms
from .models import PerfilEstudiante


class PerfilEstudianteForm(forms.ModelForm):

    # ==========================================================
    # 1. DATOS DE ACCESO DEL ESTUDIANTE
    # ==========================================================

    username = forms.CharField(
        label="Nombre de usuario",
        max_length=150,
        required=False,
        disabled=True
    )

    email = forms.EmailField(
        label="Confirma tu correo",
        required=True
    )

    # ==========================================================
    # 2. CONFIGURACIÓN GENERAL DEL FORMULARIO
    # ==========================================================

    class Meta:
        model = PerfilEstudiante

        fields = [
            "nombres",
            "apellidos",
            "edad",
            "telefono",
            "institucion_educativa",

            "carrera_1",
            "universidad_1",
            "pais_1",

            "carrera_2",
            "universidad_2",
            "pais_2",

            "carrera_3",
            "universidad_3",
            "pais_3",

            "carrera_4",
            "universidad_4",
            "pais_4",
        ]

        labels = {
            "nombres": "Nombres",
            "apellidos": "Apellidos",
            "edad": "Edad",
            "telefono": "Teléfono",
            "institucion_educativa": "Institución educativa",

            "carrera_1": "Carrera o programa",
            "universidad_1": "Universidad",
            "pais_1": "País",

            "carrera_2": "Carrera o programa",
            "universidad_2": "Universidad",
            "pais_2": "País",

            "carrera_3": "Carrera o programa",
            "universidad_3": "Universidad",
            "pais_3": "País",

            "carrera_4": "Carrera o programa",
            "universidad_4": "Universidad",
            "pais_4": "País",
        }

        help_texts = {
            "institucion_educativa": (
                "Escribe el nombre del colegio o universidad donde "
                "estudias actualmente o de la institución de la que "
                "te graduaste."
            ),
        }

    # ==========================================================
    # 3. INICIALIZAR LOS DATOS DEL ESTUDIANTE
    # ==========================================================

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            usuario = self.instance.estudiante

            # El usuario se muestra, pero no se puede modificar.
            self.fields["username"].initial = usuario.username

            # Mostrar el correo actual.
            self.fields["email"].initial = usuario.email

        # ======================================================
        # 4. CAMPOS PERSONALES OBLIGATORIOS
        # ======================================================

        campos_personales = [
            "nombres",
            "apellidos",
            "edad",
            "telefono",
            "institucion_educativa",
        ]

        for campo in campos_personales:
            self.fields[campo].required = True

        self.fields["email"].required = True

        # ======================================================
        # 5. CAMPOS DE PREFERENCIAS UNIVERSITARIAS
        # ======================================================

        campos_preferencias = [
            "carrera_1", "universidad_1", "pais_1",
            "carrera_2", "universidad_2", "pais_2",
            "carrera_3", "universidad_3", "pais_3",
            "carrera_4", "universidad_4", "pais_4",
        ]

        for campo in campos_preferencias:
            self.fields[campo].required = False

    # ==========================================================
    # 6. VALIDAR LAS PREFERENCIAS UNIVERSITARIAS
    # ==========================================================

    def clean(self):
        cleaned_data = super().clean()

        grupos = [
            ("carrera_1", "universidad_1", "pais_1"),
            ("carrera_2", "universidad_2", "pais_2"),
            ("carrera_3", "universidad_3", "pais_3"),
            ("carrera_4", "universidad_4", "pais_4"),
        ]

        hay_preferencia_completa = False

        for grupo in grupos:

            valores = [
                (cleaned_data.get(campo) or "").strip()
                for campo in grupo
            ]

            # Una preferencia completa contiene los tres campos.
            if all(valores):
                hay_preferencia_completa = True

            # Si comenzó a diligenciarla, debe terminarla.
            elif any(valores):

                for campo, valor in zip(grupo, valores):
                    if not valor:
                        self.add_error(
                            campo,
                            "Completa este campo para terminar "
                            "esta preferencia universitaria."
                        )

        # Exigir al menos una preferencia completa.
        if not hay_preferencia_completa:
            self.add_error(
                None,
                "Debes completar al menos una preferencia "
                "universitaria con carrera, universidad y país."
            )

        return cleaned_data

    # ==========================================================
    # 7. GUARDAR EL PERFIL DEL ESTUDIANTE
    # ==========================================================

    def save(self, commit=True):

        perfil = super().save(commit=False)

        # Obtener el usuario desde la instancia existente.
        usuario = perfil.estudiante

        # El nombre de usuario nunca se modifica desde este formulario.
        usuario.email = self.cleaned_data["email"]

        if commit:
            perfil.save()
            usuario.save(update_fields=["email"])

        return perfil


from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm


# ==========================================================
# 8. FORMULARIOS DE RECUPERACIÓN DE CONTRASEÑA
# ==========================================================

Usuario = get_user_model()


class FormularioRecuperacionEstudiante(PasswordResetForm):

    """
    Permite recuperar contraseñas únicamente a estudiantes.
    """

    def get_users(self, email):

        usuarios = Usuario._default_manager.filter(
            email__iexact=email,
            is_active=True,
            is_staff=False
        )

        return (
            usuario
            for usuario in usuarios
            if usuario.has_usable_password()
        )


class FormularioRecuperacionAdministrativa(PasswordResetForm):

    """
    Permite recuperar contraseñas únicamente a asesores
    y administradores.
    """

    def get_users(self, email):

        usuarios = Usuario._default_manager.filter(
            email__iexact=email,
            is_active=True,
            is_staff=True
        )

        return (
            usuario
            for usuario in usuarios
            if usuario.has_usable_password()
        )
