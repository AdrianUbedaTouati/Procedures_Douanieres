# -*- coding: utf-8 -*-
"""
Tool: get_statistics

Obtiene estadísticas y análisis agregados sobre licitaciones.
"""

from typing import Dict, Any
from .base import ToolDefinition
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="get_statistics",
    description=(
        "Obtiene estadísticas y análisis agregados sobre licitaciones. "
        "Usa esta función cuando el usuario pregunte por números, totales, promedios, o quiera un resumen general. "
        "Ejemplos: '¿cuántas licitaciones hay?', 'presupuesto promedio', 'sectores más comunes', "
        "'licitaciones urgentes', 'distribución por ubicación'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "stat_type": {
                "type": "string",
                "enum": ["general", "budget", "deadline", "cpv", "location", "all"],
                "description": (
                    'Tipo de estadística: '
                    '"general" para totales y contadores básicos, '
                    '"budget" para análisis de presupuestos, '
                    '"deadline" para análisis de fechas límite, '
                    '"cpv" para sectores y categorías, '
                    '"location" para distribución geográfica, '
                    '"all" para todas las estadísticas'
                ),
                "default": "general"
            }
        }
    },
    function=None,
    category="analysis"
)


# ============================================================================
# IMPLEMENTACIÓN
# ============================================================================

def get_statistics(stat_type: str = 'general', db_session=None, **kwargs) -> Dict[str, Any]:
    """
    Obtiene estadísticas agregadas sobre licitaciones.

    Args:
        stat_type: Tipo de estadística ('general', 'budget', 'deadline', 'cpv', 'location', 'all')
        db_session: Sesión de base de datos Django (opcional)
        **kwargs: Argumentos adicionales

    Returns:
        Dict con estadísticas según el tipo solicitado
    """
    try:
        # Setup Django si es necesario
        import django
        if not django.apps.apps.ready:
            import os
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
            django.setup()

        from apps.tenders.models import Tender
        from django.db.models import Count, Avg, Sum, Min, Max
        from datetime import date, timedelta

        logger.info(f"[GET_STATISTICS] Obteniendo estadísticas: {stat_type}")

        stats = {}

        if stat_type in ['general', 'all']:
            # Estadísticas generales
            total_tenders = Tender.objects.count()
            stats['total_tenders'] = total_tenders

            # Con deadline futuro
            active_tenders = Tender.objects.filter(
                tender_deadline_date__gte=date.today()
            ).count()
            stats['active_tenders'] = active_tenders

            # Por tipo de contrato
            contract_types = Tender.objects.values('contract_type').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
            stats['top_contract_types'] = list(contract_types)

            logger.info(f"[GET_STATISTICS] General: {total_tenders} total, {active_tenders} activas")

        if stat_type in ['budget', 'all']:
            # Estadísticas de presupuesto
            budget_stats = Tender.objects.exclude(
                budget_amount__isnull=True
            ).aggregate(
                avg_budget=Avg('budget_amount'),
                total_budget=Sum('budget_amount'),
                min_budget=Min('budget_amount'),
                max_budget=Max('budget_amount'),
                count=Count('id')
            )
            stats['budget'] = {
                'count': budget_stats['count'],
                'average': float(budget_stats['avg_budget'] or 0),
                'total': float(budget_stats['total_budget'] or 0),
                'min': float(budget_stats['min_budget'] or 0),
                'max': float(budget_stats['max_budget'] or 0)
            }

            logger.info(f"[GET_STATISTICS] Budget: {budget_stats['count']} licitaciones con presupuesto")

        if stat_type in ['deadline', 'all']:
            # Estadísticas de deadline
            today = date.today()

            urgent = Tender.objects.filter(
                tender_deadline_date__gte=today,
                tender_deadline_date__lte=today + timedelta(days=7)
            ).count()

            soon = Tender.objects.filter(
                tender_deadline_date__gt=today + timedelta(days=7),
                tender_deadline_date__lte=today + timedelta(days=30)
            ).count()

            later = Tender.objects.filter(
                tender_deadline_date__gt=today + timedelta(days=30)
            ).count()

            stats['deadlines'] = {
                'urgent': urgent,  # <7 días
                'soon': soon,      # 7-30 días
                'later': later     # >30 días
            }

            logger.info(f"[GET_STATISTICS] Deadlines: {urgent} urgentes, {soon} próximas, {later} futuras")

        if stat_type in ['cpv', 'all']:
            # Top sectores CPV
            tenders_with_cpv = Tender.objects.exclude(cpv_codes__isnull=True).exclude(cpv_codes='')

            cpv_counts = {}
            for tender in tenders_with_cpv[:200]:  # Limitar para performance
                if tender.cpv_codes:
                    # Extraer primer código CPV (primeros 2 dígitos)
                    codes = tender.cpv_codes.split(',')
                    if codes and len(codes[0]) >= 2:
                        prefix = codes[0][:2].strip()
                        cpv_counts[prefix] = cpv_counts.get(prefix, 0) + 1

            # Top 5 CPV
            top_cpv = sorted(cpv_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            # Mapeo de códigos CPV a nombres
            cpv_names = {
                '45': 'Construcción',
                '72': 'IT/Tecnología',
                '80': 'Educación',
                '85': 'Salud',
                '90': 'Saneamiento/Medio Ambiente',
                '71': 'Servicios de Ingeniería',
                '79': 'Servicios Empresariales'
            }

            stats['top_cpv_sectors'] = [
                {'code': code, 'name': cpv_names.get(code, 'Otros'), 'count': count}
                for code, count in top_cpv
            ]

            logger.info(f"[GET_STATISTICS] CPV: {len(top_cpv)} sectores analizados")

        if stat_type in ['location', 'all']:
            # Top ubicaciones NUTS
            tenders_with_nuts = Tender.objects.exclude(nuts_regions__isnull=True).exclude(nuts_regions='')

            nuts_counts = {}
            for tender in tenders_with_nuts[:200]:  # Limitar para performance
                if tender.nuts_regions:
                    # Extraer primer código NUTS (país)
                    codes = tender.nuts_regions.split(',')
                    if codes:
                        country = codes[0][:2].strip()
                        nuts_counts[country] = nuts_counts.get(country, 0) + 1

            top_locations = sorted(nuts_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            stats['top_locations'] = [
                {'code': code, 'count': count}
                for code, count in top_locations
            ]

            logger.info(f"[GET_STATISTICS] Locations: {len(top_locations)} ubicaciones analizadas")

        logger.info(f"[GET_STATISTICS] ✓ Estadísticas generadas")

        return {
            'success': True,
            'stat_type': stat_type,
            'statistics': stats,
            'generated_at': date.today().isoformat()
        }

    except Exception as e:
        logger.error(f"[GET_STATISTICS] Error: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


TOOL_DEFINITION.function = get_statistics
