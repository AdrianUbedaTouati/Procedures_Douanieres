"""
Funciones auxiliares para formateo de resultados.
"""

from typing import Dict, Any, List


def format_tender_summary(tender: Dict[str, Any]) -> str:
    """
    Formatea un resumen legible de una licitación.

    Args:
        tender: Dict con información de la licitación

    Returns:
        String con resumen formateado
    """
    lines = []
    lines.append(f"**ID:** {tender.get('id', 'N/A')}")
    lines.append(f"**Título:** {tender.get('title', 'N/A')}")

    if tender.get('buyer_name'):
        lines.append(f"**Comprador:** {tender.get('buyer_name')}")

    if tender.get('budget'):
        budget = tender['budget']
        lines.append(f"**Presupuesto:** {budget.get('amount', 0):,.2f} {budget.get('currency', 'EUR')}")

    if tender.get('deadline'):
        lines.append(f"**Fecha límite:** {tender.get('deadline')}")

    if tender.get('cpv_codes'):
        lines.append(f"**CPV:** {', '.join(tender.get('cpv_codes', [])[:3])}")

    return "\n".join(lines)


def format_search_results(documents: List[Dict[str, Any]], max_results: int = 5) -> str:
    """
    Formatea una lista de resultados de búsqueda.

    Args:
        documents: Lista de documentos encontrados
        max_results: Máximo de resultados a formatear

    Returns:
        String con resultados formateados
    """
    if not documents:
        return "No se encontraron resultados."

    lines = [f"Se encontraron {len(documents)} licitaciones:\n"]

    for idx, doc in enumerate(documents[:max_results], 1):
        lines.append(f"{idx}. {format_tender_summary(doc)}")
        lines.append("")  # Línea en blanco

    if len(documents) > max_results:
        lines.append(f"... y {len(documents) - max_results} más.")

    return "\n".join(lines)
