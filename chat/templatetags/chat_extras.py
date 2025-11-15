"""
Custom template tags for chat app
"""
from django import template
from django.utils.safestring import mark_safe
import re
import markdown

register = template.Library()


@register.simple_tag
def calculate_session_totals(messages):
    """
    Calculate total tokens and cost for a chat session

    Args:
        messages: QuerySet or list of ChatMessage objects

    Returns:
        Dict with total_tokens, total_cost, message_count
    """
    total_tokens = 0
    total_cost = 0.0
    message_count = 0

    for msg in messages:
        if msg.role == 'assistant' and hasattr(msg, 'metadata') and msg.metadata:
            total_tokens += msg.metadata.get('total_tokens', 0)
            total_cost += msg.metadata.get('cost_eur', 0.0)
            message_count += 1

    return {
        'total_tokens': total_tokens,
        'total_cost': total_cost,
        'message_count': message_count
    }


@register.filter(name='markdown_to_html')
def markdown_to_html(text):
    """
    Convert markdown text to HTML with support for citations and formatting.

    Supports:
    - Standard markdown (bold, italic, lists, headers, code blocks)
    - Citations in format [ID | section | file] -> styled as badges
    - Line breaks preserved
    """
    if not text:
        return ""

    # Convert citations [ID | section | file] to styled HTML badges
    citation_pattern = r'\[([^\|\]]+)\s*\|\s*([^\|\]]+)\s*\|\s*([^\]]+)\]'

    def replace_citation(match):
        doc_id = match.group(1).strip()
        section = match.group(2).strip()
        filename = match.group(3).strip()
        return (
            f'<span class="citation-badge" title="Fuente: {filename} - Sección: {section}">'
            f'<i class="bi bi-file-earmark-text"></i> {doc_id}'
            f'</span>'
        )

    text = re.sub(citation_pattern, replace_citation, text)

    # PRE-PROCESSING: Arreglar problemas comunes de formato markdown
    # 1. Asegurar líneas en blanco ANTES de títulos (###)
    text = re.sub(r'([^\n])\n(#{1,6} )', r'\1\n\n\2', text)

    # 2. Asegurar líneas en blanco DESPUÉS de títulos
    text = re.sub(r'(#{1,6} [^\n]+)\n([^\n#])', r'\1\n\n\2', text)

    # 3. Asegurar líneas en blanco ANTES de listas
    text = re.sub(r'([^\n])\n([-*+] |\d+\. )', r'\1\n\n\2', text)

    # 4. Asegurar líneas en blanco DESPUÉS de listas (final de lista)
    # Detecta cuando una lista termina y viene texto normal
    text = re.sub(r'((?:[-*+] |\d+\. )[^\n]+)\n([^\n\-*+\d])', r'\1\n\n\2', text)

    # 5. Eliminar múltiples líneas en blanco consecutivas (más de 2)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Convert markdown to HTML
    html = markdown.markdown(
        text,
        extensions=['extra', 'codehilite', 'nl2br', 'md_in_html'],
        extension_configs={
            'codehilite': {
                'css_class': 'highlight',
                'linenums': False
            }
        }
    )

    # POST-PROCESSING: Agregar target="_blank" a todos los enlaces
    # Esto hace que todos los enlaces se abran en una nueva pestaña
    html = re.sub(
        r'<a\s+([^>]*?)href=(["\'])([^"\']+)\2([^>]*?)>',
        r'<a \1href=\2\3\2 target="_blank" rel="noopener noreferrer"\4>',
        html
    )

    return mark_safe(html)
