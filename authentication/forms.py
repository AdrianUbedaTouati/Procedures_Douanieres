from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from .models import User
from .validators import CustomPasswordValidator


class CustomUserCreationForm(UserCreationForm):
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
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control password-input',
            'placeholder': 'Contraseña',
            'id': 'password1'
        })
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control password-input',
            'placeholder': 'Confirmar contraseña',
            'id': 'password2'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        validator = CustomPasswordValidator()
        validator.validate(password1)
        return password1

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Este correo electrónico ya está registrado.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='Email o Usuario',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email o nombre de usuario',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control password-input',
            'placeholder': 'Contraseña',
            'id': 'login-password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Recordarme'
    )

    error_messages = {
        'invalid_login': 'Usuario/email o contraseña incorrectos.',
        'inactive': 'Esta cuenta está inactiva.',
        'blocked': 'Tu cuenta ha sido bloqueada temporalmente debido a múltiples intentos fallidos. Por favor, intenta más tarde.',
        'not_verified': 'Tu cuenta aún no ha sido confirmada. Por favor revisa tu correo electrónico.',
    }

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            # Buscar usuario por email O username
            from django.db.models import Q
            try:
                user = User.objects.get(
                    Q(email__iexact=username) | Q(username__iexact=username)
                )

                # Check if user is blocked
                if user.is_login_blocked():
                    raise ValidationError(
                        self.error_messages['blocked'],
                        code='blocked',
                    )

                # Check if email verification is required
                from django.conf import settings
                if settings.EMAIL_VERIFICATION_REQUIRED and not user.email_verified:
                    # Guardar el email del usuario para usarlo en el modal
                    self.unverified_email = user.email
                    raise ValidationError(
                        self.error_messages['not_verified'],
                        code='not_verified',
                    )

                # Attempt authentication with the value entered by user (email or username)
                # The EmailOrUsernameBackend will handle finding the user
                self.user_cache = authenticate(
                    self.request,
                    username=username,  # Use what user typed (email or username)
                    password=password
                )

                if self.user_cache is None:
                    user.increment_login_attempts()
                    raise ValidationError(
                        self.error_messages['invalid_login'],
                        code='invalid_login',
                    )
                else:
                    user.reset_login_attempts()
                    self.confirm_login_allowed(self.user_cache)

            except User.DoesNotExist:
                raise ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                )
            except User.MultipleObjectsReturned:
                raise ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                )

        return self.cleaned_data


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu correo electrónico'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise ValidationError('No existe una cuenta con este correo electrónico.')
        return email


class SetNewPasswordForm(forms.Form):
    password1 = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control password-input',
            'placeholder': 'Nueva contraseña',
            'id': 'new-password1'
        })
    )
    password2 = forms.CharField(
        label='Confirmar nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control password-input',
            'placeholder': 'Confirmar nueva contraseña',
            'id': 'new-password2'
        })
    )

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        validator = CustomPasswordValidator()
        validator.validate(password1)
        return password1

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise ValidationError('Las contraseñas no coinciden.')

        return cleaned_data