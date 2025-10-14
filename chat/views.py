from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.contrib import messages
from .models import ChatSession, ChatMessage
from .services import ChatAgentService


class ChatSessionListView(LoginRequiredMixin, ListView):
    """Vista de lista de sesiones de chat del usuario"""
    model = ChatSession
    template_name = 'chat/session_list.html'
    context_object_name = 'sessions'
    paginate_by = 20

    def get_queryset(self):
        return ChatSession.objects.filter(
            user=self.request.user,
            is_archived=False
        ).order_by('-updated_at')


class ChatSessionCreateView(LoginRequiredMixin, View):
    """Vista para crear una nueva sesión de chat"""

    def post(self, request):
        session = ChatSession.objects.create(user=request.user)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'session_id': session.id,
                'redirect_url': f'/chat/{session.id}/'
            })

        return redirect('chat:session_detail', session_id=session.id)


class ChatSessionDetailView(LoginRequiredMixin, DetailView):
    """Vista de detalle de una sesión de chat"""
    model = ChatSession
    template_name = 'chat/session_detail.html'
    context_object_name = 'session'
    pk_url_kwarg = 'session_id'

    def get_queryset(self):
        # Solo permitir acceso a sesiones del usuario actual
        return ChatSession.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener todos los mensajes de la sesión
        context['messages'] = self.object.messages.all().order_by('created_at')
        return context


class ChatMessageCreateView(LoginRequiredMixin, View):
    """Vista para crear un nuevo mensaje en una sesión de chat"""

    def post(self, request, session_id):
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)

        user_message_content = request.POST.get('message', '').strip()

        if not user_message_content:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'El mensaje no puede estar vacío.'})
            messages.error(request, 'El mensaje no puede estar vacío.')
            return redirect('chat:session_detail', session_id=session_id)

        # Crear mensaje del usuario
        user_message = ChatMessage.objects.create(
            session=session,
            role='user',
            content=user_message_content
        )

        # Generar título automáticamente si es el primer mensaje del usuario
        if not session.title:
            session.generate_title()

        # Integrar con Agent_IA para generar la respuesta
        try:
            # Initialize chat service
            chat_service = ChatAgentService(request.user)

            # Get conversation history
            previous_messages = session.messages.filter(
                created_at__lt=user_message.created_at
            ).order_by('created_at')

            conversation_history = [
                {
                    'role': msg.role,
                    'content': msg.content
                }
                for msg in previous_messages
            ]

            # Process message through Agent_IA
            response = chat_service.process_message(
                message=user_message_content,
                conversation_history=conversation_history
            )

            # Create assistant message
            assistant_message = ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=response['content'],
                metadata=response['metadata']
            )

        except Exception as e:
            # Fallback in case of error
            assistant_message = ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=f'Lo siento, ocurrió un error al procesar tu mensaje. Por favor, verifica que tu API key esté configurada correctamente en tu perfil. Error: {str(e)}',
                metadata={
                    'route': 'error',
                    'error': str(e),
                    'documents_used': [],
                    'verified_fields': [],
                    'tokens_used': 0
                }
            )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'user_message': {
                    'id': user_message.id,
                    'content': user_message.content,
                    'created_at': user_message.created_at.isoformat()
                },
                'assistant_message': {
                    'id': assistant_message.id,
                    'content': assistant_message.content,
                    'created_at': assistant_message.created_at.isoformat(),
                    'metadata': assistant_message.metadata
                }
            })

        return redirect('chat:session_detail', session_id=session_id)


class ChatSessionArchiveView(LoginRequiredMixin, View):
    """Vista para archivar una sesión de chat"""

    def post(self, request, session_id):
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)

        session.is_archived = not session.is_archived
        session.save()

        action = 'archivada' if session.is_archived else 'desarchivada'
        messages.success(request, f'Sesión {action} correctamente.')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'is_archived': session.is_archived})

        return redirect('chat:session_list')


class ChatSessionDeleteView(LoginRequiredMixin, View):
    """Vista para eliminar una sesión de chat"""

    def post(self, request, session_id):
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)

        session.delete()
        messages.success(request, 'Sesión eliminada correctamente.')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        return redirect('chat:session_list')
