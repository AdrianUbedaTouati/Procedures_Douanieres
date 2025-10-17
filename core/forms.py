from django import forms
from django.core.exceptions import ValidationError
from authentication.models import User


class EditProfileForm(forms.ModelForm):
    """Formulario para editar el perfil de usuario"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Correo electrónico'
        })
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de usuario'
        })
    )
    first_name = forms.CharField(
        required=False,
        label='Nombre',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre'
        })
    )
    last_name = forms.CharField(
        required=False,
        label='Apellidos',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellidos'
        })
    )
    phone = forms.CharField(
        required=False,
        label='Teléfono',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de teléfono'
        })
    )
    llm_provider = forms.ChoiceField(
        required=False,
        label='Proveedor de IA',
        choices=[
            ('gemini', 'Google Gemini'),
            ('openai', 'OpenAI'),
            ('nvidia', 'NVIDIA NIM'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'llm_provider_select'
        })
    )
    llm_api_key = forms.CharField(
        required=False,
        label='API Key',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tu API key del proveedor seleccionado',
            'type': 'password',
            'id': 'llm_api_key_input'
        })
    )

    # Campos de dirección
    address_line1 = forms.CharField(
        required=False,
        label='Dirección (Línea 1)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Calle y número'
        })
    )
    address_line2 = forms.CharField(
        required=False,
        label='Dirección (Línea 2)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Piso, puerta, edificio (opcional)'
        })
    )
    city = forms.CharField(
        required=False,
        label='Ciudad',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ciudad'
        })
    )
    state_province = forms.CharField(
        required=False,
        label='Provincia/Estado',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Provincia o Estado'
        })
    )
    postal_code = forms.CharField(
        required=False,
        label='Código Postal',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Código Postal'
        })
    )
    country = forms.CharField(
        required=False,
        label='País',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'País'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone',
                 'llm_provider', 'llm_api_key',
                 'address_line1', 'address_line2', 'city', 'state_province',
                 'postal_code', 'country')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Guardar el usuario actual para validaciones
        self.current_user = kwargs.get('instance')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Verificar que el email no esté en uso por otro usuario
        if User.objects.filter(email=email).exclude(pk=self.current_user.pk).exists():
            raise ValidationError('Este correo electrónico ya está registrado.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        # Verificar que el username no esté en uso por otro usuario
        if User.objects.filter(username=username).exclude(pk=self.current_user.pk).exists():
            raise ValidationError('Este nombre de usuario ya está en uso.')
        return username