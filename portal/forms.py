
from django import forms
from django.contrib.auth.models import User
from .models import PerfilEstudiante


class PerfilEstudianteForm(forms.ModelForm):

    username = forms.CharField(
        label="Nombre de usuario",
        max_length=150,
        required=True
    )

    email = forms.EmailField(
        label="Correo electrónico",
        required=False
    )

    class Meta:
        model = PerfilEstudiante

        fields = [
            "nombres",
            "apellidos",
            "edad",
            "telefono",

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
            "telefono": "Teléfono de contacto",

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            usuario = self.instance.estudiante
            self.fields["username"].initial = usuario.username
            self.fields["email"].initial = usuario.email

    def clean_username(self):
        username = self.cleaned_data["username"].strip()

        usuarios = User.objects.filter(username=username)

        if self.instance and self.instance.pk:
            usuarios = usuarios.exclude(
                pk=self.instance.estudiante.pk
            )

        if usuarios.exists():
            raise forms.ValidationError(
                "Este nombre de usuario ya está en uso."
            )

        return username

    def save(self, commit=True):
        perfil = super().save(commit=False)

        usuario = perfil.estudiante
        usuario.username = self.cleaned_data["username"]
        usuario.email = self.cleaned_data["email"]

        if commit:
            usuario.save()
            perfil.save()

        return perfil
