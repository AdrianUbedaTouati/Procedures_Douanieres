"""
Token pricing and cost calculation utilities
Handles token counting and cost estimation for different LLM providers
"""
import tiktoken
from typing import Dict, Tuple


# Fixed USD to EUR conversion rate (approximate)
USD_TO_EUR = 0.92

# Pricing in EUR per 1M tokens (converted from USD pricing)
# Source: Official provider pricing as of 2024-10
PRICING_EUR = {
    'google': {
        'name': 'Google Gemini',
        'input': 0.000069,      # ~€0.069 per 1M tokens (Gemini 2.0 Flash)
        'output': 0.000276,     # ~€0.276 per 1M tokens
        'embeddings': 0.0000092,  # ~€0.0092 per 1M tokens (text-embedding-004)
        'note': 'Precios aproximados, conversión USD→EUR fija'
    },
    'openai': {
        'name': 'OpenAI',
        'input': 0.000138,      # ~€0.138 per 1M tokens (GPT-4o mini)
        'output': 0.000552,     # ~€0.552 per 1M tokens
        'embeddings': 0.0001196,  # ~€0.1196 per 1M tokens (text-embedding-3-large)
        'note': 'Precios aproximados, conversión USD→EUR fija'
    },
    'nvidia': {
        'name': 'NVIDIA NIM',
        'input': 0.0,           # GRATIS hasta 10K requests
        'output': 0.0,
        'embeddings': 0.0,
        'free_tier': {
            'requests': 10000,
            'rate_limit_per_min': 40,
            'note': 'Gratis para desarrollo hasta 10,000 requests totales'
        },
        'production': {
            'license_cost_usd_per_gpu_year': 4500,
            'note': 'Requiere licencia NVIDIA AI Enterprise para producción'
        },
        'note': '✅ Gratis hasta 10,000 requests. Después: $4,500/GPU/año o self-hosted'
    },
    'ollama': {
        'name': 'Ollama (Local)',
        'input': 0.0,           # GRATIS - ejecuta localmente
        'output': 0.0,
        'embeddings': 0.0,
        'note': '✅ Completamente GRATIS - Modelo local sin límites. Máxima privacidad'
    }
}


def estimate_tokens(text: str, provider: str = 'google') -> int:
    """
    Estimate the number of tokens in a text

    Args:
        text: Input text
        provider: LLM provider ('google', 'openai', 'nvidia')

    Returns:
        Estimated token count
    """
    if not text:
        return 0

    # For OpenAI, use tiktoken for accurate counting
    if provider == 'openai':
        try:
            encoding = tiktoken.encoding_for_model("gpt-4")
            return len(encoding.encode(text))
        except:
            pass

    # For Google/NVIDIA and fallback: use character-based approximation
    # Rule of thumb: ~4 characters per token in English
    # For technical/Spanish text: ~3.5 characters per token
    return int(len(text) / 3.5)


def calculate_embedding_cost(text: str, provider: str = 'google') -> Tuple[int, float]:
    """
    Calculate cost for generating embeddings

    Args:
        text: Text to embed
        provider: Provider name

    Returns:
        Tuple of (tokens, cost_eur)
    """
    tokens = estimate_tokens(text, provider)

    pricing = PRICING_EUR.get(provider, PRICING_EUR['google'])
    cost_per_token = pricing['embeddings']
    cost_eur = (tokens / 1_000_000) * cost_per_token

    return tokens, cost_eur


def calculate_chat_cost(
    input_text: str,
    output_text: str,
    provider: str = 'google'
) -> Dict:
    """
    Calculate cost for a chat interaction

    Args:
        input_text: User input (prompt)
        output_text: Model output (response)
        provider: Provider name

    Returns:
        Dict with:
            - input_tokens: int
            - output_tokens: int
            - total_tokens: int
            - input_cost_eur: float
            - output_cost_eur: float
            - total_cost_eur: float
    """
    input_tokens = estimate_tokens(input_text, provider)
    output_tokens = estimate_tokens(output_text, provider)

    pricing = PRICING_EUR.get(provider, PRICING_EUR['google'])

    input_cost = (input_tokens / 1_000_000) * pricing['input']
    output_cost = (output_tokens / 1_000_000) * pricing['output']

    return {
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'total_tokens': input_tokens + output_tokens,
        'input_cost_eur': input_cost,
        'output_cost_eur': output_cost,
        'total_cost_eur': input_cost + output_cost
    }


def format_cost(cost_eur: float) -> str:
    """
    Format cost in EUR with appropriate precision

    Args:
        cost_eur: Cost in EUR

    Returns:
        Formatted string (e.g., "€0.0023" or "€1.45")
    """
    if cost_eur == 0:
        return "€0.00 (Gratis)"
    elif cost_eur < 0.01:
        # Show 4 decimals for very small amounts
        return f"€{cost_eur:.4f}"
    elif cost_eur < 1:
        # Show 3 decimals for small amounts
        return f"€{cost_eur:.3f}"
    else:
        # Show 2 decimals for larger amounts
        return f"€{cost_eur:.2f}"


def get_provider_info(provider: str) -> Dict:
    """
    Get pricing information for a provider

    Args:
        provider: Provider name

    Returns:
        Dict with provider pricing info
    """
    return PRICING_EUR.get(provider, PRICING_EUR['google'])


def get_nvidia_limits_info() -> str:
    """
    Get human-readable information about NVIDIA free tier limits

    Returns:
        Formatted string with limits info
    """
    nvidia_info = PRICING_EUR['nvidia']
    free_tier = nvidia_info['free_tier']

    return f"""
    NVIDIA NIM - Limites del Tier Gratuito:

    [OK] {free_tier['requests']:,} requests gratuitos (embeddings + chat)
    [OK] {free_tier['rate_limit_per_min']} requests por minuto (rate limit)
    [OK] Gratis para desarrollo y prototipado

    Despues de agotar los {free_tier['requests']:,} requests:
    [COST] Produccion: ${nvidia_info['production']['license_cost_usd_per_gpu_year']}/GPU/anio
    [SELF] O despliega NIM en tu propia infraestructura (sin limites)

    Estimacion de uso:
    - ~100 licitaciones indexadas (50 chunks c/u) = ~5,000 requests
    - ~5,000 mensajes de chat = ~5,000 requests
    - Total: ~10,000 requests (limite del tier gratuito)
    """.strip()


# Example usage and testing
if __name__ == '__main__':
    # Test embedding cost
    sample_text = "Licitación para suministro de equipos informáticos" * 10
    tokens, cost = calculate_embedding_cost(sample_text, 'nvidia')
    print(f"Embedding: {tokens} tokens, {format_cost(cost)}")

    # Test chat cost
    input_msg = "¿Cuántas licitaciones hay disponibles?"
    output_msg = "Hay 6 licitaciones disponibles en el sistema actualmente."
    chat_cost = calculate_chat_cost(input_msg, output_msg, 'nvidia')
    print(f"Chat: {chat_cost['total_tokens']} tokens, {format_cost(chat_cost['total_cost_eur'])}")

    # Show NVIDIA limits
    print("\n" + get_nvidia_limits_info())
