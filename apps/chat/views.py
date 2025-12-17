from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.template.loader import render_to_string
from django.db.models import Count, Prefetch
from .models import ChatSession, ChatMessage
from .services import ChatAgentService
import logging

logger = logging.getLogger(__name__)


class ChatSessionListView(LoginRequiredMixin, ListView):
    """Vista de lista de sesiones de chat del usuario"""
    model = ChatSession
    template_name = 'chat/session_list.html'
    context_object_name = 'sessions'
    paginate_by = 20

    def get_queryset(self):
        # Prefetch último mensaje para evitar N+1 queries
        last_message_prefetch = Prefetch(
            'messages',
            queryset=ChatMessage.objects.order_by('-created_at')[:1],
            to_attr='last_message_cached'
        )

        return ChatSession.objects.filter(
            user=self.request.user,
            is_archived=False
        ).annotate(
            message_count=Count('messages')
        ).prefetch_related(
            last_message_prefetch
        ).order_by('-updated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # El chat siempre está disponible (ya no depende de ChromaDB)
        context['can_use_chat'] = True
        return context


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

        return redirect('apps_chat:session_detail', session_id=session.id)


class ChatSessionDetailView(LoginRequiredMixin, DetailView):
    """Vista de detalle de una sesión de chat"""
    model = ChatSession
    template_name = 'chat/session_detail.html'
    context_object_name = 'session'
    pk_url_kwarg = 'session_id'

    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['messages'] = self.object.messages.all().order_by('created_at')
        return context


class ChatMessageCreateView(LoginRequiredMixin, View):
    """Vista para crear un nuevo mensaje en una sesión de chat"""

    def post(self, request, session_id):
        import sys

        session = get_object_or_404(ChatSession, id=session_id, user=request.user)

        user_message_content = request.POST.get('message', '').strip()

        if not user_message_content:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'El mensaje no puede estar vacío.'})
            messages.error(request, 'El mensaje no puede estar vacío.')
            return redirect('apps_chat:session_detail', session_id=session_id)

        # Log de inicio de proceso
        print("\n" + "="*70, file=sys.stderr)
        print(f"[CHAT REQUEST] Usuario: {request.user.username} ({request.user.llm_provider.upper()})", file=sys.stderr)
        print(f"[CHAT REQUEST] Sesión ID: {session_id} | Título: {session.title or 'Nueva'}", file=sys.stderr)
        print(f"[CHAT REQUEST] Mensaje: {user_message_content[:80]}{'...' if len(user_message_content) > 80 else ''}", file=sys.stderr)
        print("="*70, file=sys.stderr)

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
            # Initialize chat service with session_id for logging
            print(f"[CHAT] Inicializando servicio de chat...", file=sys.stderr)
            chat_service = ChatAgentService(request.user, session_id=session.id)

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
            print(f"[CHAT] Procesando mensaje a través del agente...", file=sys.stderr)
            response = chat_service.process_message(
                message=user_message_content,
                conversation_history=conversation_history
            )

            # Create assistant message
            print(f"[CHAT] Respuesta generada: {len(response['content'])} caracteres", file=sys.stderr)
            print(f"[CHAT] Metadata: tokens={response['metadata'].get('total_tokens', 0)}", file=sys.stderr)
            print("="*70 + "\n", file=sys.stderr)

            assistant_message = ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=response['content'],
                metadata=response['metadata']
            )

        except Exception as e:
            # Log completo del error para debugging
            import traceback
            error_trace = traceback.format_exc()
            print(f"[CHAT ERROR] {error_trace}")

            # Mensaje de error más descriptivo según el tipo
            error_msg = str(e)
            if 'ollama' in error_msg.lower() or 'connection' in error_msg.lower():
                assistant_content = (
                    "**Error de conexión con Ollama**\n\n"
                    "Por favor verifica:\n"
                    "1. Ollama está ejecutándose: `ollama serve`\n"
                    "2. El modelo está descargado: `ollama list`\n"
                    "3. Si no está, descárgalo: `ollama pull qwen2.5:72b`\n\n"
                    f"Error técnico: {error_msg}"
                )
            elif 'API key' in error_msg or 'api_key' in error_msg:
                assistant_content = (
                    "**Falta configurar tu API key**\n\n"
                    "Ve a tu perfil y configura tu API key del proveedor que estás usando."
                )
            else:
                assistant_content = f"Lo siento, ocurrió un error al procesar tu mensaje: {error_msg}"

            # Fallback in case of error
            assistant_message = ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=assistant_content,
                metadata={
                    'route': 'error',
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'documents_used': [],
                    'tokens_used': 0
                }
            )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Renderizar HTML del mensaje del usuario
            user_html = render_to_string('chat/partials/_message_bubble.html', {
                'msg': user_message
            })

            # Renderizar HTML del mensaje del asistente
            assistant_html = render_to_string('chat/partials/_message_bubble.html', {
                'msg': assistant_message
            })

            logger.info(f"AJAX Response Debug:")
            logger.info(f"  - User message length: {len(user_html)} chars")
            logger.info(f"  - Assistant message length: {len(assistant_html)} chars")
            logger.info(f"  - Tools used: {assistant_message.metadata.get('tools_used', [])}")
            logger.info(f"  - Total tokens: {assistant_message.metadata.get('total_tokens', 0)}")

            return JsonResponse({
                'success': True,
                'user_message': {
                    'id': user_message.id,
                    'content': user_message.content,
                    'created_at': user_message.created_at.isoformat(),
                    'rendered_html': user_html
                },
                'assistant_message': {
                    'id': assistant_message.id,
                    'content': assistant_message.content,
                    'created_at': assistant_message.created_at.isoformat(),
                    'metadata': assistant_message.metadata,
                    'rendered_html': assistant_html
                }
            })

        return redirect('apps_chat:session_detail', session_id=session_id)


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

        return redirect('apps_chat:session_list')


class ChatSessionDeleteView(LoginRequiredMixin, View):
    """Vista para eliminar una sesión de chat"""

    def post(self, request, session_id):
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)

        session.delete()
        messages.success(request, 'Sesión eliminada correctamente.')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        return redirect('apps_chat:session_list')
