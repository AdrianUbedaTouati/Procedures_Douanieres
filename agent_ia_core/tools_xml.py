# -*- coding: utf-8 -*-
"""
Herramientas para verificación determinista de valores en XMLs eForms.
XmlLookup permite extraer valores exactos por XPath desde el XML original.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional, List
from lxml import etree
import logging
import sys

# Importar configuración
sys.path.append(str(Path(__file__).parent))
from config import XML_DIR, EFORMS_NAMESPACES

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class XmlLookupTool:
    """
    Herramienta para extraer valores exactos de XMLs eForms usando XPath.
    Útil para verificar campos críticos (importes, fechas, pesos) antes de responder.
    """

    def __init__(self, xml_dir: Path = None, namespaces: Dict[str, str] = None):
        """
        Inicializa la herramienta.

        Args:
            xml_dir: Directorio con XMLs originales
            namespaces: Namespaces XML de eForms
        """
        self.xml_dir = Path(xml_dir) if xml_dir else Path(XML_DIR)
        self.namespaces = namespaces or EFORMS_NAMESPACES
        self._xml_cache = {}  # Cache de XMLs parseados

    def lookup(
        self,
        source_path: str,
        xpath: str,
        return_all: bool = False
    ) -> Optional[str | List[str]]:
        """
        Extrae un valor del XML usando XPath.

        Args:
            source_path: Nombre del archivo XML (ej: "668461-2025.xml")
            xpath: Expresión XPath para el campo
            return_all: Si True, retorna todos los resultados, sino solo el primero

        Returns:
            Valor extraído como string, lista de strings, o None si no se encuentra
        """
        try:
            # Cargar XML (desde cache si existe)
            tree = self._load_xml(source_path)
            if tree is None:
                return None

            # Ejecutar XPath
            results = tree.xpath(xpath, namespaces=self.namespaces)

            if not results:
                logger.warning(f"XPath no encontró resultados: {xpath} en {source_path}")
                return None

            # Convertir a strings
            str_results = [str(r).strip() for r in results if str(r).strip()]

            if not str_results:
                return None

            if return_all:
                return str_results
            else:
                return str_results[0]

        except Exception as e:
            logger.error(f"Error ejecutando XPath lookup: {e}")
            return None

    def lookup_budget(self, source_path: str) -> Optional[Dict[str, Any]]:
        """
        Extrae información completa del presupuesto.

        Args:
            source_path: Nombre del archivo XML

        Returns:
            Diccionario con budget_eur, currency y xpath, o None
        """
        xpath_amount = ".//cac:RequestedTenderTotal/cbc:EstimatedOverallContractAmount[@currencyID='EUR']/text()"
        xpath_currency = ".//cac:RequestedTenderTotal/cbc:EstimatedOverallContractAmount/@currencyID"

        amount_str = self.lookup(source_path, xpath_amount)
        currency = self.lookup(source_path, xpath_currency)

        if amount_str:
            try:
                return {
                    "budget_eur": float(amount_str),
                    "currency": currency or "EUR",
                    "xpath": xpath_amount
                }
            except ValueError:
                logger.error(f"No se pudo convertir presupuesto a float: {amount_str}")
                return None

        return None

    def lookup_deadline(self, source_path: str) -> Optional[Dict[str, Any]]:
        """
        Extrae información completa del deadline.

        Args:
            source_path: Nombre del archivo XML

        Returns:
            Diccionario con fecha, hora y xpaths, o None
        """
        xpath_date = ".//cac:TenderSubmissionDeadlinePeriod/cbc:EndDate/text()"
        xpath_time = ".//cac:TenderSubmissionDeadlinePeriod/cbc:EndTime/text()"

        date_str = self.lookup(source_path, xpath_date)
        time_str = self.lookup(source_path, xpath_time)

        if date_str:
            return {
                "tender_deadline_date": date_str,
                "tender_deadline_time": time_str,
                "xpath_date": xpath_date,
                "xpath_time": xpath_time
            }

        return None

    def lookup_award_criteria(self, source_path: str) -> Optional[List[Dict[str, Any]]]:
        """
        Extrae todos los criterios de adjudicación con sus pesos.

        Args:
            source_path: Nombre del archivo XML

        Returns:
            Lista de criterios con name, weight, type y xpath
        """
        try:
            tree = self._load_xml(source_path)
            if tree is None:
                return None

            criteria = []

            # Buscar todos los criterios
            criterion_elements = tree.xpath(
                ".//cac:AwardingCriterion/cac:SubordinateAwardingCriterion",
                namespaces=self.namespaces
            )

            for i, criterion_elem in enumerate(criterion_elements):
                criterion = {}

                # Nombre/descripción
                desc = criterion_elem.xpath("./cbc:Description/text()", namespaces=self.namespaces)
                if desc:
                    criterion["name"] = str(desc[0]).strip()

                # Tipo
                crit_type = criterion_elem.xpath(
                    "./cbc:AwardingCriterionTypeCode/text()",
                    namespaces=self.namespaces
                )
                if crit_type:
                    criterion["type"] = str(crit_type[0]).strip()

                # Peso
                weight = criterion_elem.xpath(
                    ".//efbc:ParameterNumeric/text()",
                    namespaces=self.namespaces
                )
                if weight:
                    try:
                        criterion["weight"] = float(weight[0])
                    except ValueError:
                        criterion["weight"] = str(weight[0]).strip()

                    criterion["xpath_weight"] = ".//cac:AwardingCriterion/cac:SubordinateAwardingCriterion[" + str(i+1) + "]//efbc:ParameterNumeric/text()"

                if criterion.get("name"):
                    criteria.append(criterion)

            return criteria if criteria else None

        except Exception as e:
            logger.error(f"Error extrayendo criterios de adjudicación: {e}")
            return None

    def verify_field(
        self,
        source_path: str,
        xpath: str,
        expected_value: Any
    ) -> bool:
        """
        Verifica que un campo tenga el valor esperado.

        Args:
            source_path: Nombre del archivo XML
            xpath: XPath del campo
            expected_value: Valor esperado

        Returns:
            True si coincide, False si no
        """
        actual_value = self.lookup(source_path, xpath)

        if actual_value is None:
            return False

        # Convertir ambos a string para comparar
        return str(actual_value).strip() == str(expected_value).strip()

    def _load_xml(self, source_path: str) -> Optional[etree._ElementTree]:
        """
        Carga un XML desde disco o cache.

        Args:
            source_path: Nombre del archivo XML

        Returns:
            Árbol XML parseado o None
        """
        # Verificar cache
        if source_path in self._xml_cache:
            return self._xml_cache[source_path]

        # Buscar archivo
        xml_path = self.xml_dir / source_path
        if not xml_path.exists():
            logger.error(f"XML no encontrado: {xml_path}")
            return None

        try:
            # Parsear y cachear
            tree = etree.parse(str(xml_path))
            self._xml_cache[source_path] = tree
            return tree

        except Exception as e:
            logger.error(f"Error parseando XML {source_path}: {e}")
            return None

    def clear_cache(self):
        """Limpia el cache de XMLs."""
        self._xml_cache.clear()


# Instancia global para uso como tool
xml_lookup_tool = XmlLookupTool()


def xml_lookup(source_path: str, xpath: str) -> Optional[str]:
    """
    Función de conveniencia para usar como tool en LangChain.

    Args:
        source_path: Nombre del archivo XML
        xpath: Expresión XPath

    Returns:
        Valor extraído o None
    """
    return xml_lookup_tool.lookup(source_path, xpath)


if __name__ == "__main__":
    # Prueba de la herramienta
    print("\n=== PRUEBA DE XML LOOKUP TOOL ===\n")

    tool = XmlLookupTool()

    # Usar un XML de ejemplo
    test_xml = "668461-2025.xml"

    print(f"Probando con {test_xml}\n")

    # 1. Lookup de presupuesto
    print("1. Lookup de presupuesto:")
    budget = tool.lookup_budget(test_xml)
    if budget:
        print(f"   Budget: {budget['budget_eur']} {budget['currency']}")
        print(f"   XPath: {budget['xpath']}")
    print()

    # 2. Lookup de deadline
    print("2. Lookup de deadline:")
    deadline = tool.lookup_deadline(test_xml)
    if deadline:
        print(f"   Fecha: {deadline['tender_deadline_date']}")
        print(f"   Hora: {deadline['tender_deadline_time']}")
        print(f"   XPath fecha: {deadline['xpath_date']}")
    print()

    # 3. Lookup de criterios de adjudicación
    print("3. Lookup de criterios de adjudicación:")
    criteria = tool.lookup_award_criteria(test_xml)
    if criteria:
        for i, crit in enumerate(criteria, 1):
            print(f"   {i}. {crit['name']}")
            print(f"      Peso: {crit.get('weight', 'N/A')}%")
            print(f"      Tipo: {crit.get('type', 'N/A')}")
    print()

    # 4. Lookup genérico con XPath
    print("4. Lookup genérico - Título:")
    xpath_title = ".//cac:ProcurementProject/cbc:Name[@languageID='SPA']/text()"
    title = tool.lookup(test_xml, xpath_title)
    if title:
        print(f"   {title[:100]}...")
    print()

    # 5. Verificación de campo
    print("5. Verificación de campo:")
    if budget:
        is_correct = tool.verify_field(
            test_xml,
            budget['xpath'],
            budget['budget_eur']
        )
        print(f"   ¿Presupuesto verificado? {is_correct}")
    print()
