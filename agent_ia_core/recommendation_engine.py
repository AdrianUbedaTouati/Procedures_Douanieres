# -*- coding: utf-8 -*-
"""
Motor de recomendación de licitaciones basado en perfil de empresa.
Analiza compatibilidad y genera TOP 5 licitaciones más adecuadas.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime

# Importar módulos propios
sys.path.append(str(Path(__file__).parent))
from config import PROJECT_ROOT, RECORDS_DIR

logger = logging.getLogger(__name__)


@dataclass
class CompatibilityScore:
    """Puntuación de compatibilidad de una licitación."""
    notice_id: str
    title: str
    total_score: float          # 0-100
    category_scores: Dict[str, float]
    match_reasons: List[str]
    warning_factors: List[str]
    recommendation_level: str   # "alta", "media", "baja"
    probability_success: float  # 0-100
    contact_info: Dict[str, Any]


class RecommendationEngine:
    """
    Motor de análisis y recomendación de licitaciones.
    """

    def __init__(self, company_profile_path: Path = None):
        """
        Inicializa el motor.

        Args:
            company_profile_path: Ruta al perfil de empresa
        """
        if company_profile_path is None:
            company_profile_path = PROJECT_ROOT / "company_profile.json"

        self.company_profile = self._load_company_profile(company_profile_path)
        logger.info(f"Perfil de empresa cargado: {self.company_profile['company_info']['name']}")

    def _load_company_profile(self, path: Path) -> Dict[str, Any]:
        """Carga el perfil de empresa desde JSON."""
        if not path.exists():
            raise FileNotFoundError(f"No se encontró company_profile.json en {path}")

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def analyze_all_notices(self) -> List[CompatibilityScore]:
        """
        Analiza todas las licitaciones disponibles.

        Returns:
            Lista de scores ordenada por compatibilidad (descendente)
        """
        records_dir = Path(RECORDS_DIR)
        json_files = list(records_dir.glob("*.json"))

        if not json_files:
            logger.warning(f"No se encontraron JSONs en {records_dir}")
            return []

        scores = []
        for json_path in json_files:
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    notice = json.load(f)

                score = self._calculate_compatibility(notice)
                scores.append(score)

            except Exception as e:
                logger.error(f"Error analizando {json_path.name}: {e}")
                continue

        # Ordenar por score total (descendente)
        scores.sort(key=lambda x: x.total_score, reverse=True)

        logger.info(f"Analizadas {len(scores)} licitaciones")
        return scores

    def get_top_recommendations(self, n: int = 5) -> List[CompatibilityScore]:
        """
        Obtiene las TOP N licitaciones recomendadas.

        Args:
            n: Número de recomendaciones

        Returns:
            Lista de scores
        """
        all_scores = self.analyze_all_notices()
        return all_scores[:n]

    def _calculate_compatibility(self, notice: Dict[str, Any]) -> CompatibilityScore:
        """
        Calcula la compatibilidad de una licitación con el perfil de empresa.

        Args:
            notice: Diccionario de licitación

        Returns:
            Score de compatibilidad
        """
        required = notice.get("REQUIRED", {})
        optional = notice.get("OPTIONAL", {})
        meta = notice.get("META", {})

        category_scores = {}
        match_reasons = []
        warning_factors = []

        # 1. Compatibilidad Técnica (30%)
        tech_score, tech_reasons, tech_warnings = self._score_technical_fit(required, optional)
        category_scores["technical"] = tech_score
        match_reasons.extend(tech_reasons)
        warning_factors.extend(tech_warnings)

        # 2. Compatibilidad Presupuestaria (25%)
        budget_score, budget_reasons, budget_warnings = self._score_budget_fit(required)
        category_scores["budget"] = budget_score
        match_reasons.extend(budget_reasons)
        warning_factors.extend(budget_warnings)

        # 3. Compatibilidad Geográfica (15%)
        geo_score, geo_reasons, geo_warnings = self._score_geographic_fit(required)
        category_scores["geographic"] = geo_score
        match_reasons.extend(geo_reasons)
        warning_factors.extend(geo_warnings)

        # 4. Experiencia y Referencias (20%)
        exp_score, exp_reasons, exp_warnings = self._score_experience_fit(required, optional)
        category_scores["experience"] = exp_score
        match_reasons.extend(exp_reasons)
        warning_factors.extend(exp_warnings)

        # 5. Factores de Competencia (10%)
        comp_score, comp_reasons, comp_warnings = self._score_competitive_factors(required, optional)
        category_scores["competition"] = comp_score
        match_reasons.extend(comp_reasons)
        warning_factors.extend(comp_warnings)

        # Score total ponderado
        total_score = (
            tech_score * 0.30 +
            budget_score * 0.25 +
            geo_score * 0.15 +
            exp_score * 0.20 +
            comp_score * 0.10
        )

        # Nivel de recomendación
        if total_score >= 75:
            recommendation_level = "alta"
        elif total_score >= 50:
            recommendation_level = "media"
        else:
            recommendation_level = "baja"

        # Probabilidad de éxito (ajustada por factores de riesgo)
        probability_success = self._calculate_success_probability(total_score, warning_factors)

        # Extraer información de contacto
        contact_info = self._extract_contact_info(required, optional)

        return CompatibilityScore(
            notice_id=required.get("ojs_notice_id", "unknown"),
            title=required.get("title", "Sin título"),
            total_score=total_score,
            category_scores=category_scores,
            match_reasons=match_reasons,
            warning_factors=warning_factors,
            recommendation_level=recommendation_level,
            probability_success=probability_success,
            contact_info=contact_info
        )

    def _score_technical_fit(
        self,
        required: Dict,
        optional: Dict
    ) -> Tuple[float, List[str], List[str]]:
        """Evalúa compatibilidad técnica (0-100)."""
        score = 0.0
        reasons = []
        warnings = []

        # CPV codes
        cpv_codes = required.get("cpv_codes", [])
        if isinstance(cpv_codes, str):
            cpv_codes = [cpv_codes]

        preferred_cpvs = self.company_profile["bidding_preferences"]["preferred_cpv_codes"]
        cpv_match = any(pref in cpv for cpv in cpv_codes for pref in preferred_cpvs)

        if cpv_match:
            score += 50
            reasons.append(f"CPV code alineado con especialización ({cpv_codes[0] if cpv_codes else 'N/A'})")
        else:
            warnings.append(f"CPV code fuera de especialización principal ({cpv_codes[0] if cpv_codes else 'N/A'})")

        # Keywords en descripción
        description = required.get("description", "").lower()
        title = required.get("title", "").lower()
        combined_text = description + " " + title

        tech_areas = self.company_profile["capabilities"]["technical_areas"]
        tech_keywords = [area.lower() for area in tech_areas]

        matching_keywords = [kw for kw in tech_keywords if kw in combined_text]

        if matching_keywords:
            score += min(30, len(matching_keywords) * 10)
            reasons.append(f"Coincidencia técnica: {', '.join(matching_keywords[:3])}")

        # Avoid keywords
        avoid_keywords = self.company_profile["bidding_preferences"]["avoid_keywords"]
        has_avoid_keywords = any(kw.lower() in combined_text for kw in avoid_keywords)

        if has_avoid_keywords:
            score -= 20
            warnings.append("Contiene palabras clave a evitar")

        # Contract type
        contract_type = required.get("contract_type", "")
        preferred_types = self.company_profile["bidding_preferences"]["preferred_contract_types"]

        if contract_type in preferred_types:
            score += 20
            reasons.append(f"Tipo de contrato preferido ({contract_type})")

        return min(100, max(0, score)), reasons, warnings

    def _score_budget_fit(self, required: Dict) -> Tuple[float, List[str], List[str]]:
        """Evalúa compatibilidad presupuestaria (0-100)."""
        score = 0.0
        reasons = []
        warnings = []

        budget_amount = required.get("budget_amount")
        if not budget_amount:
            warnings.append("Presupuesto no especificado")
            return 50, reasons, warnings

        budget_range = self.company_profile["bidding_preferences"]["budget_range"]
        min_budget = budget_range["min_eur"]
        max_budget = budget_range["max_eur"]

        if min_budget <= budget_amount <= max_budget:
            score = 100
            reasons.append(f"Presupuesto dentro del rango objetivo ({budget_amount:,.0f} EUR)")
        elif budget_amount < min_budget:
            # Demasiado pequeño
            ratio = budget_amount / min_budget
            score = ratio * 50  # Penalización
            warnings.append(f"Presupuesto por debajo del mínimo preferido ({budget_amount:,.0f} EUR)")
        else:
            # Demasiado grande
            ratio = max_budget / budget_amount
            score = ratio * 70  # Penalización menor que si es pequeño
            warnings.append(f"Presupuesto por encima del máximo preferido ({budget_amount:,.0f} EUR)")

        # Comparar con facturación anual
        annual_revenue = self.company_profile["company_info"]["annual_revenue_eur"]
        if budget_amount > annual_revenue * 0.5:
            warnings.append("Presupuesto muy alto vs facturación anual (>50%)")

        return min(100, max(0, score)), reasons, warnings

    def _score_geographic_fit(self, required: Dict) -> Tuple[float, List[str], List[str]]:
        """Evalúa compatibilidad geográfica (0-100)."""
        score = 0.0
        reasons = []
        warnings = []

        nuts_regions = required.get("nuts_regions", [])
        if isinstance(nuts_regions, str):
            nuts_regions = [nuts_regions]

        if not nuts_regions:
            warnings.append("Región NUTS no especificada")
            return 50, reasons, warnings

        preferred_regions = self.company_profile["company_info"]["geographic_presence"]

        # Match directo
        direct_match = any(region in preferred_regions for region in nuts_regions)

        if direct_match:
            score = 100
            reasons.append(f"Presencia geográfica directa ({nuts_regions[0]})")
        else:
            # Match parcial (mismo país)
            country_match = any(
                region[:2] == pref[:2]
                for region in nuts_regions
                for pref in preferred_regions
            )

            if country_match:
                score = 60
                reasons.append(f"Mismo país, región diferente ({nuts_regions[0]})")
            else:
                score = 30
                warnings.append(f"Fuera de presencia geográfica habitual ({nuts_regions[0]})")

        return min(100, max(0, score)), reasons, warnings

    def _score_experience_fit(
        self,
        required: Dict,
        optional: Dict
    ) -> Tuple[float, List[str], List[str]]:
        """Evalúa experiencia y referencias (0-100)."""
        score = 50  # Base score
        reasons = []
        warnings = []

        # Experiencia en sector público
        has_public_experience = self.company_profile["experience"]["public_sector_experience"]

        if has_public_experience:
            score += 30
            reasons.append("Experiencia previa en sector público")

        # Proyectos similares
        relevant_projects = self.company_profile["experience"]["relevant_projects"]
        if relevant_projects:
            score += 20
            reasons.append(f"{len(relevant_projects)} proyectos relevantes en portfolio")
        else:
            warnings.append("Sin proyectos similares en portfolio")

        return min(100, max(0, score)), reasons, warnings

    def _score_competitive_factors(
        self,
        required: Dict,
        optional: Dict
    ) -> Tuple[float, List[str], List[str]]:
        """Evalúa factores competitivos (0-100)."""
        score = 70  # Base score (asumimos competitividad media)
        reasons = []
        warnings = []

        # Procedimiento
        procedure_type = required.get("procedure_type", "")

        if procedure_type == "open":
            score -= 10
            warnings.append("Procedimiento abierto (mayor competencia)")
        elif procedure_type in ["restricted", "negotiated"]:
            score += 10
            reasons.append(f"Procedimiento {procedure_type} (menor competencia)")

        # Deadline proximity
        deadline = required.get("deadline")
        if deadline:
            try:
                deadline_date = datetime.fromisoformat(deadline.split('T')[0])
                days_until_deadline = (deadline_date - datetime.now()).days

                if days_until_deadline < 15:
                    score -= 15
                    warnings.append(f"Deadline muy próximo ({days_until_deadline} días)")
                elif days_until_deadline > 45:
                    score += 10
                    reasons.append(f"Tiempo suficiente para preparar oferta ({days_until_deadline} días)")
            except:
                pass

        # Ventajas competitivas
        competitive_advantages = self.company_profile["competitive_analysis"]["competitive_advantages"]
        if len(competitive_advantages) >= 3:
            score += 20
            reasons.append(f"{len(competitive_advantages)} ventajas competitivas identificadas")

        return min(100, max(0, score)), reasons, warnings

    def _calculate_success_probability(
        self,
        base_score: float,
        warning_factors: List[str]
    ) -> float:
        """
        Calcula la probabilidad de éxito realista.

        Args:
            base_score: Score base (0-100)
            warning_factors: Lista de factores de advertencia

        Returns:
            Probabilidad de éxito (0-100)
        """
        # Partir del score base
        probability = base_score

        # Penalizar por cada warning
        warning_penalty = len(warning_factors) * 5
        probability -= warning_penalty

        # Ajustar por factores de riesgo de empresa
        risk_factors = self.company_profile.get("risk_factors", {})

        if risk_factors.get("financial_capacity") == "baja":
            probability -= 10
        if risk_factors.get("team_availability") == "baja":
            probability -= 15
        if risk_factors.get("overcommitment_risk") == "alto":
            probability -= 10

        # Ajustar por tamaño de empresa (realismo)
        company_size = self.company_profile["company_info"].get("size", "mediana")
        if company_size == "pequeña":
            probability *= 0.85  # Empresas pequeñas tienen menor tasa de éxito

        # Limitar entre 5% y 95% (realismo)
        probability = min(95, max(5, probability))

        return round(probability, 1)

    def _extract_contact_info(
        self,
        required: Dict,
        optional: Dict
    ) -> Dict[str, Any]:
        """
        Extrae información de contacto de la licitación.

        Args:
            required: Campos requeridos
            optional: Campos opcionales

        Returns:
            Diccionario con info de contacto
        """
        contact_info = {
            "buyer_name": required.get("buyer_name", "No especificado"),
            "email": optional.get("contact_email"),
            "phone": optional.get("contact_phone"),
            "ojs_notice_id": required.get("ojs_notice_id"),
            "source_url": f"https://ted.europa.eu/en/notice/{required.get('ojs_notice_id')}/html"
            if required.get("ojs_notice_id") else None
        }

        return contact_info

    def print_recommendations_report(self, top_n: int = 5):
        """
        Imprime un reporte completo de las TOP N recomendaciones.

        Args:
            top_n: Número de recomendaciones
        """
        recommendations = self.get_top_recommendations(n=top_n)

        if not recommendations:
            print("\nNo se encontraron licitaciones para recomendar.")
            return

        print("\n" + "=" * 80)
        print(f"TOP {top_n} LICITACIONES RECOMENDADAS PARA:")
        print(f"{self.company_profile['company_info']['name']}")
        print("=" * 80)
        print()

        for i, rec in enumerate(recommendations, 1):
            self._print_recommendation(i, rec)

        print("=" * 80)
        print()
        print(f"Análisis completado: {len(recommendations)} licitaciones recomendadas")
        print(f"Score promedio: {sum(r.total_score for r in recommendations) / len(recommendations):.1f}/100")
        print()

    def _print_recommendation(self, rank: int, rec: CompatibilityScore):
        """Imprime una recomendación individual."""
        print(f"\n{'#' * 80}")
        print(f"  RECOMENDACION #{rank}")
        print(f"{'#' * 80}")
        print()
        print(f"TITULO: {rec.title}")
        print(f"ID:     {rec.notice_id}")
        print()
        print(f"SCORE TOTAL:             {rec.total_score:.1f}/100")
        print(f"NIVEL:                   {rec.recommendation_level.upper()}")
        print(f"PROBABILIDAD DE EXITO:   {rec.probability_success:.1f}%")
        print()

        print("DESGLOSE DE COMPATIBILIDAD:")
        print(f"  - Técnica:       {rec.category_scores['technical']:.1f}/100")
        print(f"  - Presupuesto:   {rec.category_scores['budget']:.1f}/100")
        print(f"  - Geografía:     {rec.category_scores['geographic']:.1f}/100")
        print(f"  - Experiencia:   {rec.category_scores['experience']:.1f}/100")
        print(f"  - Competencia:   {rec.category_scores['competition']:.1f}/100")
        print()

        if rec.match_reasons:
            print("PUNTOS FUERTES:")
            for reason in rec.match_reasons:
                print(f"  + {reason}")
            print()

        if rec.warning_factors:
            print("FACTORES DE ATENCION:")
            for warning in rec.warning_factors:
                print(f"  ! {warning}")
            print()

        print("INFORMACION DE CONTACTO:")
        print(f"  Organismo:  {rec.contact_info['buyer_name']}")
        if rec.contact_info.get('email'):
            print(f"  Email:      {rec.contact_info['email']}")
        if rec.contact_info.get('phone'):
            print(f"  Teléfono:   {rec.contact_info['phone']}")
        if rec.contact_info.get('source_url'):
            print(f"  URL:        {rec.contact_info['source_url']}")
        print()


def main():
    """Punto de entrada principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Motor de recomendación de licitaciones"
    )
    parser.add_argument(
        "-n", "--top-n",
        type=int,
        default=5,
        help="Número de recomendaciones (default: 5)"
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Ruta a company_profile.json (default: raíz del proyecto)"
    )

    args = parser.parse_args()

    # Crear engine
    profile_path = Path(args.profile) if args.profile else None
    engine = RecommendationEngine(company_profile_path=profile_path)

    # Generar recomendaciones
    engine.print_recommendations_report(top_n=args.top_n)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
