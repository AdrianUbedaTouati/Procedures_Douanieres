"""
Middleware personalizado para forzar la persistencia de sesión
"""
from django.utils.deprecation import MiddlewareMixin


class ForceSessionMiddleware(MiddlewareMixin):
    """
    Middleware que fuerza la sesión a guardarse y enviarse en CADA respuesta.
    Soluciona problemas de navegadores que no guardan/envían cookies correctamente.
    """

    def process_request(self, request):
        """
        Antes de procesar el request, asegura que la sesión esté accesible.
        """
        # Acceder a la sesión para forzar su carga
        if hasattr(request, 'session'):
            _ = request.session.session_key
        return None

    def process_response(self, request, response):
        """
        Después de procesar el request, fuerza que la sesión se guarde.
        """
        if hasattr(request, 'session'):
            # Si hay usuario autenticado, forzar guardado
            if request.user.is_authenticated:
                # Marcar sesión como modificada
                request.session.modified = True

                # Forzar guardado explícito
                try:
                    request.session.save()
                except Exception as e:
                    print(f"[FORCE SESSION] Error guardando sesión: {e}")

                # Log para debugging
                print(f"[FORCE SESSION] User: {request.user.username}, Session key: {request.session.session_key}")

        return response
