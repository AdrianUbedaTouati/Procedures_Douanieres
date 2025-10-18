"""
Custom template tags for chat app
"""
from django import template

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
