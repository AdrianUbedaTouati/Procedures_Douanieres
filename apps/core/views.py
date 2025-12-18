from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.http import JsonResponse
from .forms import EditProfileForm
from .ollama_checker import OllamaHealthChecker
import uuid


def home_view(request):
    """Vista principal de la aplicación"""
    print(f"[HOME DEBUG] Usuario autenticado: {request.user.is_authenticated}")
    if request.user.is_authenticated:
        print(f"[HOME DEBUG] Usuario: {request.user.username} (ID: {request.user.id})")
        print(f"[HOME DEBUG] Session key: {request.session.session_key}")
        print(f"[HOME DEBUG] User ID en sesión: {request.session.get('_auth_user_id')}")
    else:
        print(f"[HOME DEBUG] Usuario NO autenticado (AnonymousUser)")
        print(f"[HOME DEBUG] Session key: {request.session.session_key}")
        print(f"[HOME DEBUG] Contenido de sesión: {dict(request.session.items())}")

    context = {
        'total_users': 0,  # Placeholder for future statistics
    }
    return render(request, 'core/home.html', context)


def about_view(request):
    """Vista de información sobre la aplicación"""
    return render(request, 'core/about.html')


def contact_view(request):
    """Vista de contacto"""
    return render(request, 'core/contact.html')


@login_required
def dashboard_view(request):
    """Dashboard para usuarios autenticados"""
    context = {
        'user': request.user,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def profile_view(request):
    """Vista del perfil del usuario"""
    return render(request, 'core/profile.html', {'user': request.user})


@login_required
def edit_profile_view(request):
    """Vista para editar el perfil del usuario"""
    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            # Si el email cambió, marcar como no verificado
            old_email = request.user.email
            user = form.save(commit=False)

            # Si el email cambió y la verificación está habilitada
            if old_email != user.email and settings.EMAIL_VERIFICATION_REQUIRED:
                user.email_verified = False
                user.verification_token = uuid.uuid4()

                # Enviar nuevo email de verificación
                subject = 'Confirma tu nuevo correo'
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
                    messages.warning(request, 'Tu correo ha cambiado. Por favor revisa tu bandeja de entrada para confirmar el nuevo correo.')
                except Exception as e:
                    messages.warning(request, 'Perfil actualizado pero no se pudo enviar el email de confirmación.')

            user.save()
            messages.success(request, 'Tu perfil ha sido actualizado exitosamente.')
            return redirect('apps_core:profile')
    else:
        form = EditProfileForm(instance=request.user)

    return render(request, 'core/edit_profile.html', {'form': form})


@login_required
def ollama_check_view(request):
    """
    Página de verificación de Ollama
    Muestra el estado de instalación, servidor y modelos
    """
    # Get user's configured models (use empty string check instead of 'or')
    user_chat_model = request.user.ollama_model if request.user.ollama_model else "qwen2.5:72b"
    user_embedding_model = request.user.ollama_embedding_model if request.user.ollama_embedding_model else "nomic-embed-text"

    # Debug info
    print(f"[OLLAMA CHECK] Usuario: {request.user.username}")
    print(f"[OLLAMA CHECK] Chat model DB: [{request.user.ollama_model}]")
    print(f"[OLLAMA CHECK] Chat model usado: [{user_chat_model}]")
    print(f"[OLLAMA CHECK] Embed model DB: [{request.user.ollama_embedding_model}]")
    print(f"[OLLAMA CHECK] Embed model usado: [{user_embedding_model}]")

    # Perform full health check
    health_status = OllamaHealthChecker.full_health_check(
        user_chat_model=user_chat_model,
        user_embedding_model=user_embedding_model
    )

    # Get recommendations
    recommendations = OllamaHealthChecker.get_recommendations()

    context = {
        'health_status': health_status,
        'recommendations': recommendations,
        'user_chat_model': user_chat_model,
        'user_embedding_model': user_embedding_model,
        'user': request.user,
        'debug_info': {
            'username': request.user.username,
            'db_chat_model': request.user.ollama_model,
            'db_embed_model': request.user.ollama_embedding_model,
        }
    }

    return render(request, 'core/ollama_check.html', context)


@login_required
def ollama_test_api(request):
    """
    API endpoint to test Ollama model
    """
    if request.method == 'POST':
        model_name = request.POST.get('model', 'qwen2.5:72b')
        test_prompt = request.POST.get('prompt', '¿Cuál es la capital de España?')

        # Test the model
        test_result = OllamaHealthChecker.test_model(model_name, test_prompt)

        return JsonResponse(test_result)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def ollama_models_api(request):
    """
    API endpoint to get installed Ollama models
    Returns list of available models for dropdowns
    """
    try:
        models_info = OllamaHealthChecker.get_installed_models()

        if models_info["success"]:
            # Separate models into chat and embedding categories
            chat_models = []
            embedding_models = []

            for model in models_info["models"]:
                model_name = model["name"]

                # Check if it's an embedding model (usually contains 'embed' in name)
                if 'embed' in model_name.lower():
                    embedding_models.append({
                        'name': model_name,
                        'size': model.get('size', ''),
                        'modified': model.get('modified', '')
                    })
                else:
                    chat_models.append({
                        'name': model_name,
                        'size': model.get('size', ''),
                        'modified': model.get('modified', '')
                    })

            return JsonResponse({
                'success': True,
                'chat_models': chat_models,
                'embedding_models': embedding_models,
                'total_count': models_info['count'],
                'recommended_chat': 'qwen2.5:72b',
                'recommended_embedding': 'nomic-embed-text',
                'message': models_info['message']
            })
        else:
            return JsonResponse({
                'success': False,
                'chat_models': [],
                'embedding_models': [],
                'message': models_info['message']
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'chat_models': [],
            'embedding_models': [],
            'message': f'Error obteniendo modelos: {str(e)}'
        })