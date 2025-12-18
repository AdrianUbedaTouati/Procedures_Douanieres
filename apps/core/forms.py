from django import forms
from django.core.exceptions import ValidationError
from apps.authentication.models import User


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
            ('ollama', 'Ollama (Local)'),
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
            'placeholder': 'Tu API key del proveedor seleccionado (no necesaria para Ollama)',
            'type': 'password',
            'id': 'llm_api_key_input'
        }),
        help_text='No es necesaria para Ollama (modelo local)'
    )
    openai_model = forms.ChoiceField(
        required=False,
        label='Modelo OpenAI',
        choices=[
            ('gpt-4o', 'GPT-4o (Más potente, más caro)'),
            ('gpt-4o-mini', 'GPT-4o-mini (Balance calidad/precio) - Recomendado'),
            ('gpt-4-turbo', 'GPT-4 Turbo (Anterior generación)'),
            ('gpt-3.5-turbo', 'GPT-3.5 Turbo (Económico, menos capaz)'),
        ],
        initial='gpt-4o-mini',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'openai_model_select'
        }),
        help_text='Solo se usa si seleccionas OpenAI como proveedor'
    )
    ollama_model = forms.CharField(
        required=False,
        label='Modelo Ollama',
        initial='qwen2.5:72b',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: qwen2.5:72b, llama3.3:70b, mistral:7b',
            'id': 'ollama_model_input'
        }),
        help_text='Solo se usa si seleccionas Ollama como proveedor'
    )
    ollama_embedding_model = forms.CharField(
        required=False,
        label='Modelo de Embeddings Ollama',
        initial='nomic-embed-text',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: nomic-embed-text, mxbai-embed-large',
            'id': 'ollama_embedding_input'
        }),
        help_text='Modelo para vectorización (solo para Ollama)'
    )

    # Chat agent settings
    use_grading = forms.BooleanField(
        required=False,
        label='Activar Grading de Documentos',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Filtra documentos irrelevantes del chat (más preciso pero más lento)'
    )
    use_verification = forms.BooleanField(
        required=False,
        label='Activar Verificación XML',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Valida campos críticos con el XML original (más preciso pero más lento)'
    )

    # Google Search API settings
    use_web_search = forms.BooleanField(
        required=False,
        label='Activar Búsqueda Web',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'use_web_search_checkbox'
        }),
        help_text='Permite al agente buscar información actualizada en internet'
    )
    google_search_api_key = forms.CharField(
        required=False,
        label='Google Search API Key',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'AIza...',
            'type': 'password',
            'id': 'google_search_api_key_input'
        }),
        help_text='API key de Google Custom Search API (100 búsquedas/día gratis)'
    )
    google_search_engine_id = forms.CharField(
        required=False,
        label='Google Custom Search Engine ID',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'a1b2c3d4e5f6g7h8i',
            'id': 'google_search_engine_id_input'
        }),
        help_text='ID del motor de búsqueda personalizado (cx parameter)'
    )
    browse_max_chars = forms.IntegerField(
        required=False,
        label='Máximo de caracteres por página web',
        initial=10000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '10000',
            'min': 1000,
            'max': 50000,
            'step': 1000,
            'id': 'browse_max_chars_input'
        }),
        help_text='Máximo de caracteres a extraer de cada página web (1,000 - 50,000). Aproximadamente 1 token = 4 caracteres. Por defecto 10,000 (≈2,500 tokens)'
    )
    browse_chunk_size = forms.IntegerField(
        required=False,
        label='Tamaño de fragmento de página',
        initial=1250,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '1250',
            'min': 500,
            'max': 50000,
            'step': 250,
            'id': 'browse_chunk_size_input'
        }),
        help_text='Tamaño de cada fragmento al analizar páginas (500 - 50,000). Fragmentos más pequeños = mayor precisión pero más llamadas. Por defecto 1,250 (≈312 tokens). DEBE ser menor que "Máximo de caracteres".'
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
                 'llm_provider', 'llm_api_key', 'openai_model', 'ollama_model', 'ollama_embedding_model',
                 'use_grading', 'use_verification',
                 'use_web_search', 'google_search_api_key', 'google_search_engine_id', 'browse_max_chars', 'browse_chunk_size',
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

    def clean(self):
        cleaned_data = super().clean()
        browse_max_chars = cleaned_data.get('browse_max_chars')
        browse_chunk_size = cleaned_data.get('browse_chunk_size')

        # Validar que browse_chunk_size sea menor que browse_max_chars
        if browse_max_chars and browse_chunk_size:
            if browse_chunk_size >= browse_max_chars:
                raise ValidationError({
                    'browse_chunk_size': 'El tamaño de fragmento debe ser menor que el máximo de caracteres por página.'
                })

        return cleaned_data