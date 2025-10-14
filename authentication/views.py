from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, JsonResponse

from .forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
    PasswordResetRequestForm,
    SetNewPasswordForm
)
from .models import User, PasswordResetToken
import uuid


def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.verification_token = uuid.uuid4()

            # Verificar si la verificación de email está habilitada
            if not settings.EMAIL_VERIFICATION_REQUIRED:
                user.email_verified = True

            user.save()

            if settings.EMAIL_VERIFICATION_REQUIRED:
                # Enviar email de verificación
                subject = 'Confirma tu cuenta'
                html_message = render_to_string('authentication/email/verify_email.html', {
                    'user': user,
                    'domain': settings.SITE_URL.replace('http://', '').replace('https://', ''),
                    'protocol': 'https' if 'https' in settings.SITE_URL else 'http',
                    'token': user.verification_token,
                })
                plain_message = strip_tags(html_message)

                try:
                    send_mail(
                        subject,
                        plain_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    messages.success(request, 'Registro exitoso! Por favor revisa tu correo para confirmar tu cuenta.')
                except Exception as e:
                    messages.warning(request, 'Registro exitoso pero no se pudo enviar el email de confirmación. Contacta al administrador.')
            else:
                messages.success(request, 'Registro exitoso! Ya puedes iniciar sesión.')

            return redirect('authentication:login')
    else:
        form = CustomUserCreationForm()

    return render(request, 'authentication/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Handle remember me
            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(1209600)  # 2 weeks

            messages.success(request, f'Bienvenido, {user.username}!')
            next_url = request.GET.get('next', 'core:home')
            return redirect(next_url)
        else:
            # Verificar si hay un error de verificación de email
            if form.non_field_errors():
                for error in form.non_field_errors():
                    error_text = str(error)
                    # Detectar si es un error de verificación
                    if 'no ha sido confirmada' in error_text.lower() or 'sin confirmar' in error_text.lower():
                        # Convertir a mensaje para que la modal lo detecte
                        messages.error(request, error_text)
                        # Limpiar los errores del formulario para que no se muestren duplicados
                        form._errors.pop('__all__', None)

                        # Intentar obtener el email/username para la modal
                        username = request.POST.get('username', '')
                        if username:
                            request.session['unverified_user'] = username
    else:
        form = CustomAuthenticationForm(request)

    return render(request, 'authentication/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión exitosamente.')
    return redirect('authentication:login')


def password_reset_request_view(request):
    # Verificar si es una petición AJAX
    is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

    if request.method == 'POST':
        # Si es AJAX, no validar con el form normal
        if is_ajax:
            email = request.POST.get('email', '').strip()

            if not email:
                return JsonResponse({
                    'success': False,
                    'message': 'Por favor proporciona un email.'
                })

            try:
                user = User.objects.get(email__iexact=email)

                # Create password reset token
                reset_token = PasswordResetToken.objects.create(user=user)

                # Send reset email
                subject = 'Restablecer contraseña'
                html_message = render_to_string('authentication/email/password_reset.html', {
                    'user': user,
                    'domain': settings.SITE_URL.replace('http://', '').replace('https://', ''),
                    'protocol': 'https' if 'https' in settings.SITE_URL else 'http',
                    'token': reset_token.token,
                })
                plain_message = strip_tags(html_message)

                send_mail(
                    subject,
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=html_message,
                    fail_silently=False,
                )

                return JsonResponse({
                    'success': True,
                    'message': f'Enlace de recuperación enviado a {user.email}. Por favor revisa tu bandeja de entrada.'
                })

            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'No existe una cuenta con ese correo electrónico.'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': 'Error al enviar el email. Por favor intenta más tarde.'
                })
        else:
            # Formulario normal (sin AJAX)
            form = PasswordResetRequestForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                user = User.objects.get(email=email)

                # Create password reset token
                reset_token = PasswordResetToken.objects.create(user=user)

                # Send reset email
                subject = 'Restablecer contraseña'
                html_message = render_to_string('authentication/email/password_reset.html', {
                    'user': user,
                    'domain': settings.SITE_URL.replace('http://', '').replace('https://', ''),
                    'protocol': 'https' if 'https' in settings.SITE_URL else 'http',
                    'token': reset_token.token,
                })
                plain_message = strip_tags(html_message)

                send_mail(
                    subject,
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=html_message,
                    fail_silently=False,
                )

                messages.success(
                    request,
                    'Se ha enviado un enlace de recuperación a tu correo electrónico.'
                )
                return redirect('authentication:login')
    else:
        form = PasswordResetRequestForm()

    return render(request, 'authentication/password_reset_request.html', {'form': form})


def password_reset_confirm_view(request, token):
    try:
        reset_token = PasswordResetToken.objects.get(token=token)

        if not reset_token.is_valid():
            messages.error(request, 'El enlace de recuperación ha expirado o ya fue usado.')
            return redirect('authentication:password_reset_request')

        if request.method == 'POST':
            form = SetNewPasswordForm(request.POST)
            if form.is_valid():
                user = reset_token.user
                user.set_password(form.cleaned_data['password1'])
                user.save()

                # Mark token as used
                reset_token.used = True
                reset_token.save()

                messages.success(request, 'Tu contraseña ha sido actualizada exitosamente.')
                return redirect('authentication:login')
        else:
            form = SetNewPasswordForm()

        return render(request, 'authentication/password_reset_confirm.html', {
            'form': form,
            'token': token
        })

    except PasswordResetToken.DoesNotExist:
        messages.error(request, 'Enlace de recuperación inválido.')
        return redirect('authentication:password_reset_request')


def verify_email_view(request, token):
    try:
        user = User.objects.get(verification_token=token)

        if not user.email_verified:
            user.email_verified = True
            user.save()
            # Mostrar página de éxito
            return render(request, 'authentication/email_verified_success.html', {
                'user': user,
                'first_time': True
            })
        else:
            # Si ya estaba verificado, también mostrar página de éxito
            messages.info(request, 'Tu correo ya estaba confirmado.')
            return render(request, 'authentication/email_verified_success.html', {
                'user': user,
                'first_time': False
            })

    except User.DoesNotExist:
        # Mostrar página de error
        return render(request, 'authentication/email_verification_error.html')
    except Exception as e:
        print(f"[ERROR] Error inesperado en verify_email_view: {e}")
        # Mostrar página de error
        return render(request, 'authentication/email_verification_error.html')


def resend_verification_view(request):
    """Vista para reenviar el email de verificación"""
    # Verificar si es una petición AJAX
    is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

    if request.method == 'POST':
        email_or_username = None
        user = None

        if request.user.is_authenticated:
            user = request.user
            email_or_username = user.email
        else:
            email_or_username = request.POST.get('email', '').strip()

            if not email_or_username:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': 'Por favor proporciona un email o nombre de usuario.'
                    })
                messages.error(request, 'Por favor proporciona un email o nombre de usuario.')
                return redirect('authentication:resend_verification')

            # Buscar usuario por email O username
            from django.db.models import Q
            try:
                user = User.objects.get(
                    Q(email__iexact=email_or_username) | Q(username__iexact=email_or_username)
                )
            except User.DoesNotExist:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': 'No existe una cuenta con ese email o nombre de usuario.'
                    })
                messages.error(request, 'No existe una cuenta con ese email o nombre de usuario.')
                return redirect('authentication:resend_verification')

        # Si el usuario ya está verificado
        if user.email_verified:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Tu cuenta ya está confirmada.'
                })
            messages.info(request, 'Tu cuenta ya está confirmada.')
            return redirect('authentication:login')

        # Enviar email de verificación
        subject = 'Confirma tu cuenta'
        html_message = render_to_string('authentication/email/verify_email.html', {
            'user': user,
            'domain': settings.SITE_URL.replace('http://', '').replace('https://', ''),
            'protocol': 'https' if 'https' in settings.SITE_URL else 'http',
            'token': user.verification_token,
        })
        plain_message = strip_tags(html_message)

        try:
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Email de confirmación enviado a {user.email}. Por favor revisa tu bandeja de entrada.'
                })

            messages.success(request, f'Email de confirmación enviado a {user.email}')
        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Error al enviar el email. Por favor intenta más tarde.'
                })
            messages.error(request, 'Error al enviar el email. Por favor intenta más tarde.')

        return redirect('authentication:login')

    return render(request, 'authentication/resend_verification.html')


