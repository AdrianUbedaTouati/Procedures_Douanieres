# -*- coding: utf-8 -*-
"""
Sistema de tracking de consumo de tokens de API.
Registra todas las llamadas al LLM y calcula costes.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# Precios por 1M tokens (Feb 2025)
PRICING = {
    "google": {
        "gemini-2.5-flash": {
            "input": 0.075,   # USD per 1M tokens
            "output": 0.30
        },
        "gemini-2.5-pro": {
            "input": 1.25,
            "output": 5.00
        }
    },
    "openai": {
        "gpt-4o-mini": {
            "input": 0.15,
            "output": 0.60
        },
        "gpt-4o": {
            "input": 2.50,
            "output": 10.00
        }
    }
}


@dataclass
class TokenUsage:
    """Registro de uso de tokens de una llamada."""
    timestamp: str
    component: str              # "routing", "grading", "answer"
    input_tokens: int
    output_tokens: int
    total_tokens: int
    provider: str               # "google" o "openai"
    model: str                  # "gemini-2.5-flash", etc.
    cost_usd: float
    query_id: Optional[str] = None


@dataclass
class QueryStats:
    """Estadísticas de una consulta completa."""
    query_id: str
    query: str
    timestamp: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    components_used: List[str] = field(default_factory=list)
    num_llm_calls: int = 0
    duration_seconds: Optional[float] = None


class TokenTracker:
    """
    Rastrea el consumo de tokens y costes de API.
    """

    def __init__(self, log_file: Optional[Path] = None):
        """
        Inicializa el tracker.

        Args:
            log_file: Archivo para guardar logs (opcional)
        """
        self.log_file = log_file
        self.usage_history: List[TokenUsage] = []
        self.query_stats: Dict[str, QueryStats] = {}
        self.session_start = datetime.now()

    def log_llm_call(
        self,
        component: str,
        input_tokens: int,
        output_tokens: int,
        provider: str,
        model: str,
        query_id: Optional[str] = None
    ) -> TokenUsage:
        """
        Registra una llamada al LLM.

        Args:
            component: Componente que usa el LLM ("routing", "grading", "answer")
            input_tokens: Tokens de entrada
            output_tokens: Tokens de salida
            provider: Proveedor ("google" o "openai")
            model: Modelo usado
            query_id: ID de la consulta (opcional)

        Returns:
            Registro de uso
        """
        total_tokens = input_tokens + output_tokens
        cost_usd = self._calculate_cost(input_tokens, output_tokens, provider, model)

        usage = TokenUsage(
            timestamp=datetime.now().isoformat(),
            component=component,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            provider=provider,
            model=model,
            cost_usd=cost_usd,
            query_id=query_id
        )

        self.usage_history.append(usage)

        # Actualizar stats de la query
        if query_id:
            if query_id not in self.query_stats:
                self.query_stats[query_id] = QueryStats(
                    query_id=query_id,
                    query="",  # Se actualizará después
                    timestamp=usage.timestamp
                )

            stats = self.query_stats[query_id]
            stats.total_input_tokens += input_tokens
            stats.total_output_tokens += output_tokens
            stats.total_tokens += total_tokens
            stats.total_cost_usd += cost_usd
            stats.num_llm_calls += 1
            if component not in stats.components_used:
                stats.components_used.append(component)

        # Log opcional a archivo
        if self.log_file:
            self._write_to_file(usage)

        logger.debug(
            f"[{component}] Tokens: {input_tokens} in + {output_tokens} out = "
            f"{total_tokens} total | Cost: ${cost_usd:.6f}"
        )

        return usage

    def update_query_info(self, query_id: str, query: str, duration_seconds: float = None):
        """
        Actualiza información de una consulta.

        Args:
            query_id: ID de la consulta
            query: Texto de la consulta
            duration_seconds: Duración en segundos
        """
        if query_id in self.query_stats:
            self.query_stats[query_id].query = query
            if duration_seconds:
                self.query_stats[query_id].duration_seconds = duration_seconds

    def _calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        provider: str,
        model: str
    ) -> float:
        """
        Calcula el coste de una llamada.

        Args:
            input_tokens: Tokens de entrada
            output_tokens: Tokens de salida
            provider: Proveedor
            model: Modelo

        Returns:
            Coste en USD
        """
        try:
            prices = PRICING[provider][model]
            input_cost = (input_tokens / 1_000_000) * prices["input"]
            output_cost = (output_tokens / 1_000_000) * prices["output"]
            return input_cost + output_cost
        except KeyError:
            logger.warning(f"Precio no encontrado para {provider}/{model}, usando 0")
            return 0.0

    def _write_to_file(self, usage: TokenUsage):
        """Escribe un registro al archivo de log."""
        if not self.log_file:
            return

        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.log_file, 'a', encoding='utf-8') as f:
                json.dump(usage.__dict__, f)
                f.write('\n')
        except Exception as e:
            logger.error(f"Error escribiendo log de tokens: {e}")

    def get_session_stats(self) -> Dict:
        """
        Obtiene estadísticas de toda la sesión.

        Returns:
            Diccionario con estadísticas
        """
        total_input = sum(u.input_tokens for u in self.usage_history)
        total_output = sum(u.output_tokens for u in self.usage_history)
        total_cost = sum(u.cost_usd for u in self.usage_history)
        session_duration = (datetime.now() - self.session_start).total_seconds()

        # Agrupar por componente
        by_component = {}
        for usage in self.usage_history:
            comp = usage.component
            if comp not in by_component:
                by_component[comp] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0
                }

            by_component[comp]["calls"] += 1
            by_component[comp]["input_tokens"] += usage.input_tokens
            by_component[comp]["output_tokens"] += usage.output_tokens
            by_component[comp]["total_tokens"] += usage.total_tokens
            by_component[comp]["cost_usd"] += usage.cost_usd

        return {
            "session_duration_seconds": session_duration,
            "total_queries": len(self.query_stats),
            "total_llm_calls": len(self.usage_history),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost_usd": total_cost,
            "by_component": by_component,
            "queries": list(self.query_stats.values())
        }

    def get_query_stats(self, query_id: str) -> Optional[QueryStats]:
        """
        Obtiene estadísticas de una consulta específica.

        Args:
            query_id: ID de la consulta

        Returns:
            Estadísticas o None si no existe
        """
        return self.query_stats.get(query_id)

    def print_session_report(self):
        """Imprime un reporte de la sesión."""
        stats = self.get_session_stats()

        print("\n" + "=" * 70)
        print("REPORTE DE CONSUMO DE TOKENS - SESION")
        print("=" * 70)
        print()
        print(f"Duracion: {stats['session_duration_seconds']:.1f}s")
        print(f"Consultas procesadas: {stats['total_queries']}")
        print(f"Llamadas al LLM: {stats['total_llm_calls']}")
        print()
        print(f"{'Tokens Input:':<25} {stats['total_input_tokens']:>12,}")
        print(f"{'Tokens Output:':<25} {stats['total_output_tokens']:>12,}")
        print(f"{'Tokens Total:':<25} {stats['total_tokens']:>12,}")
        print()
        print(f"{'Coste Total:':<25} ${stats['total_cost_usd']:>11.6f}")
        print()

        if stats['by_component']:
            print("-" * 70)
            print("POR COMPONENTE:")
            print("-" * 70)
            print(f"{'Componente':<15} | {'Llamadas':>10} | {'Tokens':>12} | {'Coste USD':>12}")
            print("-" * 70)

            for comp, data in sorted(stats['by_component'].items()):
                print(
                    f"{comp:<15} | "
                    f"{data['calls']:>10} | "
                    f"{data['total_tokens']:>12,} | "
                    f"${data['cost_usd']:>11.6f}"
                )

        print("=" * 70)
        print()

    def print_query_report(self, query_id: str):
        """
        Imprime reporte de una consulta específica.

        Args:
            query_id: ID de la consulta
        """
        stats = self.get_query_stats(query_id)
        if not stats:
            print(f"No hay estadísticas para query_id={query_id}")
            return

        print("\n" + "=" * 70)
        print(f"REPORTE DE CONSULTA: {query_id}")
        print("=" * 70)
        print()
        print(f"Consulta: \"{stats.query}\"")
        print(f"Timestamp: {stats.timestamp}")
        if stats.duration_seconds:
            print(f"Duracion: {stats.duration_seconds:.2f}s")
        print()
        print(f"Llamadas al LLM: {stats.num_llm_calls}")
        print(f"Componentes usados: {', '.join(stats.components_used)}")
        print()
        print(f"{'Tokens Input:':<25} {stats.total_input_tokens:>12,}")
        print(f"{'Tokens Output:':<25} {stats.total_output_tokens:>12,}")
        print(f"{'Tokens Total:':<25} {stats.total_tokens:>12,}")
        print()
        print(f"{'Coste Total:':<25} ${stats.total_cost_usd:>11.6f}")
        print("=" * 70)
        print()

    def reset(self):
        """Reinicia el tracker (borra historial)."""
        self.usage_history.clear()
        self.query_stats.clear()
        self.session_start = datetime.now()
        logger.info("Token tracker reseteado")

    def export_to_json(self, output_path: Path):
        """
        Exporta estadísticas a JSON.

        Args:
            output_path: Ruta del archivo de salida
        """
        stats = self.get_session_stats()

        # Convertir QueryStats a dict
        stats['queries'] = [
            {
                "query_id": q.query_id,
                "query": q.query,
                "timestamp": q.timestamp,
                "total_input_tokens": q.total_input_tokens,
                "total_output_tokens": q.total_output_tokens,
                "total_tokens": q.total_tokens,
                "total_cost_usd": q.total_cost_usd,
                "components_used": q.components_used,
                "num_llm_calls": q.num_llm_calls,
                "duration_seconds": q.duration_seconds
            }
            for q in stats['queries']
        ]

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

        logger.info(f"Estadísticas exportadas a {output_path}")


# Instancia global (singleton)
_global_tracker: Optional[TokenTracker] = None


def get_global_tracker() -> TokenTracker:
    """
    Obtiene la instancia global del tracker.

    Returns:
        Tracker global
    """
    global _global_tracker
    if _global_tracker is None:
        from config import LOGS_DIR
        log_file = LOGS_DIR / "tokens.jsonl"
        _global_tracker = TokenTracker(log_file=log_file)
    return _global_tracker


def reset_global_tracker():
    """Reinicia el tracker global."""
    global _global_tracker
    _global_tracker = None
