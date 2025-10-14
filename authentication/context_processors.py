from django.conf import settings

def email_verification_settings(request):
    """
    Agrega la configuración de verificación de email al contexto de templates.
    """
    return {
        'EMAIL_VERIFICATION_REQUIRED': settings.EMAIL_VERIFICATION_REQUIRED,
        'EMAIL_VERIFICATION_COOLDOWN': settings.EMAIL_VERIFICATION_COOLDOWN_SECONDS,
        'PASSWORD_RESET_COOLDOWN': settings.PASSWORD_RESET_COOLDOWN_SECONDS,
    }