from django.db import models
from django.conf import settings


class ChatSession(models.Model):
    """Sesión de chat del usuario con el agente"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        verbose_name='Usuario'
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Título',
        help_text='Auto-generado del primer mensaje'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado en')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado en')
    is_archived = models.BooleanField(default=False, verbose_name='Archivada')

    class Meta:
        verbose_name = 'Sesión de chat'
        verbose_name_plural = 'Sesiones de chat'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.email} - {self.title or 'Nueva conversación'} ({self.created_at.strftime('%Y-%m-%d')})"

    def get_message_count(self):
        """Retorna el número de mensajes en la sesión"""
        return self.messages.count()

    def generate_title(self):
        """Genera un título basado en el primer mensaje del usuario"""
        first_message = self.messages.filter(role='user').first()
        if first_message:
            # Tomar las primeras 50 caracteres del contenido
            self.title = first_message.content[:50]
            if len(first_message.content) > 50:
                self.title += '...'
            self.save(update_fields=['title'])


class ChatMessage(models.Model):
    """Mensaje individual en una sesión de chat"""

    ROLE_CHOICES = [
        ('user', 'Usuario'),
        ('assistant', 'Asistente'),
        ('system', 'Sistema'),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Sesión'
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        verbose_name='Rol'
    )
    content = models.TextField(verbose_name='Contenido')
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Metadatos',
        help_text='Documentos usados, campos verificados, tokens, etc.'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado en')

    class Meta:
        verbose_name = 'Mensaje de chat'
        verbose_name_plural = 'Mensajes de chat'
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.get_role_display()}] {self.content[:50]}..."

    @property
    def documents_used(self):
        """Retorna los documentos utilizados en la respuesta"""
        return self.metadata.get('documents_used', [])

    @property
    def verified_fields(self):
        """Retorna los campos verificados con XPath"""
        return self.metadata.get('verified_fields', [])

    @property
    def route_used(self):
        """Retorna la ruta utilizada por el agente"""
        return self.metadata.get('route', 'unknown')

    @property
    def tokens_used(self):
        """Retorna el número de tokens utilizados"""
        return self.metadata.get('tokens_used', 0)
