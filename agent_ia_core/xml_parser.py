# -*- coding: utf-8 -*-
"""
Parser de XML eForms a formato JSON canónico.
Extrae campos REQUIRED/OPTIONAL/META según la plantilla del esquema.
Guarda XPaths usados para trazabilidad y citas exactas.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from lxml import etree
import logging
from datetime import datetime

# Importar configuración y namespaces
import sys
sys.path.append(str(Path(__file__).parent))
from config import EFORMS_NAMESPACES, STRICT_VALIDATION

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EFormsXMLParser:
    """
    Parser de XML eForms (UBL 2.3) a formato JSON canónico.
    Extrae campos REQUIRED, OPTIONAL y META (con XPaths usados).
    """

    def __init__(self, namespaces: Dict[str, str] = None):
        """
        Inicializa el parser con los namespaces de eForms.

        Args:
            namespaces: Diccionario de namespaces XML (por defecto usa EFORMS_NAMESPACES)
        """
        self.namespaces = namespaces or EFORMS_NAMESPACES

    def parse_file(self, xml_path: Path | str) -> Dict[str, Any]:
        """
        Parsea un archivo XML eForms y retorna el registro canónico.

        Args:
            xml_path: Ruta al archivo XML

        Returns:
            Diccionario con estructura {REQUIRED, OPTIONAL, META}

        Raises:
            FileNotFoundError: Si el archivo no existe
            etree.XMLSyntaxError: Si el XML está malformado
        """
        xml_path = Path(xml_path)
        if not xml_path.exists():
            raise FileNotFoundError(f"XML no encontrado: {xml_path}")

        logger.info(f"Parseando XML: {xml_path.name}")

        # Parsear XML con lxml
        tree = etree.parse(str(xml_path))
        root = tree.getroot()

        # Extraer campos
        record = {
            "REQUIRED": self._extract_required_fields(root, xml_path),
            "OPTIONAL": self._extract_optional_fields(root),
            "META": self._extract_meta_fields()
        }

        # Validar campos requeridos si está activado
        if STRICT_VALIDATION:
            self._validate_required_fields(record["REQUIRED"], xml_path)

        return record

    def _extract_required_fields(self, root: etree._Element, xml_path: Path) -> Dict[str, Any]:
        """Extrae campos REQUIRED del XML."""
        fields = {}
        xpaths_used = {}

        # 1. ojs_notice_id
        xpath = ".//efbc:NoticePublicationID[@schemeName='ojs-notice-id']/text()"
        value = self._xpath_text(root, xpath)
        if value:
            fields["ojs_notice_id"] = value
            xpaths_used["ojs_notice_id"] = xpath

        # 2. source_path
        fields["source_path"] = str(xml_path.name)
        xpaths_used["source_path"] = "metadata"

        # 3. publication_date
        xpath = ".//efbc:PublicationDate/text()"
        value = self._xpath_text(root, xpath)
        if value:
            # Convertir a formato ISO-8601
            fields["publication_date"] = self._normalize_date(value)
            xpaths_used["publication_date"] = xpath

        # 4. buyer_name
        xpath = ".//efac:Organization/efac:Company/cac:PartyName/cbc:Name[@languageID='SPA']/text()"
        value = self._xpath_text(root, xpath)
        if not value:
            # Fallback sin languageID
            xpath = ".//efac:Organization/efac:Company/cac:PartyName/cbc:Name/text()"
            value = self._xpath_text(root, xpath)
        if value:
            fields["buyer_name"] = value
            xpaths_used["buyer_name"] = xpath

        # 5. title
        xpath = ".//cac:ProcurementProject/cbc:Name[@languageID='SPA']/text()"
        value = self._xpath_text(root, xpath)
        if not value:
            # Fallback sin languageID
            xpath = ".//cac:ProcurementProject/cbc:Name/text()"
            value = self._xpath_text(root, xpath)
        if value:
            fields["title"] = value
            xpaths_used["title"] = xpath

        # 6. cpv_main
        xpath = ".//cac:ProcurementProject/cac:MainCommodityClassification/cbc:ItemClassificationCode[@listName='cpv']/text()"
        value = self._xpath_text(root, xpath)
        if value:
            fields["cpv_main"] = value
            xpaths_used["cpv_main"] = xpath

        # Guardar XPaths usados en META
        self._xpaths_registry = xpaths_used

        return fields

    def _extract_optional_fields(self, root: etree._Element) -> Dict[str, Any]:
        """Extrae campos OPTIONAL del XML."""
        fields = {}
        xpaths_used = {}

        # 1. description
        xpath = ".//cac:ProcurementProject/cbc:Description[@languageID='SPA']/text()"
        value = self._xpath_text(root, xpath)
        if not value:
            xpath = ".//cac:ProcurementProject/cbc:Description/text()"
            value = self._xpath_text(root, xpath)
        if value:
            fields["description"] = value
            xpaths_used["description"] = xpath

        # 2. cpv_additional
        xpath = ".//cac:ProcurementProject/cac:AdditionalCommodityClassification/cbc:ItemClassificationCode[@listName='cpv']/text()"
        values = self._xpath_list(root, xpath)
        if values:
            fields["cpv_additional"] = values
            xpaths_used["cpv_additional"] = xpath

        # 3. nuts_regions
        xpath = ".//cac:RealizedLocation/cac:Address/cbc:CountrySubentityCode[@listName='nuts']/text()"
        values = self._xpath_list(root, xpath)
        if values:
            fields["nuts_regions"] = values
            xpaths_used["nuts_regions"] = xpath

        # 4. procedure_type
        xpath = ".//cac:TenderingProcess/cbc:ProcedureCode[@listName='procurement-procedure-type']/text()"
        value = self._xpath_text(root, xpath)
        if value:
            fields["procedure_type"] = value
            xpaths_used["procedure_type"] = xpath

        # 5. contract_type
        xpath = ".//cac:ProcurementProject/cbc:ProcurementTypeCode[@listName='contract-nature']/text()"
        value = self._xpath_text(root, xpath)
        if value:
            fields["contract_type"] = value
            xpaths_used["contract_type"] = xpath

        # 6. budget_eur
        xpath = ".//cac:RequestedTenderTotal/cbc:EstimatedOverallContractAmount[@currencyID='EUR']/text()"
        value = self._xpath_text(root, xpath)
        if value:
            try:
                fields["budget_eur"] = float(value)
                xpaths_used["budget_eur"] = xpath
            except ValueError:
                logger.warning(f"No se pudo convertir budget_eur a número: {value}")

        # 7. currency
        xpath = ".//cac:RequestedTenderTotal/cbc:EstimatedOverallContractAmount/@currencyID"
        value = self._xpath_text(root, xpath)
        if value:
            fields["currency"] = value
            xpaths_used["currency"] = xpath

        # 8. tender_deadline_date
        xpath = ".//cac:TenderSubmissionDeadlinePeriod/cbc:EndDate/text()"
        value = self._xpath_text(root, xpath)
        if value:
            fields["tender_deadline_date"] = self._normalize_date(value)
            xpaths_used["tender_deadline_date"] = xpath

        # 9. tender_deadline_time
        xpath = ".//cac:TenderSubmissionDeadlinePeriod/cbc:EndTime/text()"
        value = self._xpath_text(root, xpath)
        if value:
            fields["tender_deadline_time"] = self._normalize_time(value)
            xpaths_used["tender_deadline_time"] = xpath

        # 10. lots (array)
        lots = self._extract_lots(root)
        if lots:
            fields["lots"] = lots
            xpaths_used["lots"] = "multiple_xpaths"

        # 11. award_criteria (array)
        criteria = self._extract_award_criteria(root)
        if criteria:
            fields["award_criteria"] = criteria
            xpaths_used["award_criteria"] = "multiple_xpaths"

        # 12. eligibility_requirements
        xpath = ".//cac:SpecificTendererRequirement/cbc:Description[@languageID='SPA']/text()"
        values = self._xpath_list(root, xpath)
        if values:
            fields["eligibility_requirements"] = " | ".join(values)
            xpaths_used["eligibility_requirements"] = xpath

        # 13. external_references
        xpath = ".//cac:ExternalReference/cbc:URI/text()"
        values = self._xpath_list(root, xpath)
        if values:
            # Deduplicar
            fields["external_references"] = list(set(values))
            xpaths_used["external_references"] = xpath

        # 14. attachments
        attachments = self._extract_attachments(root)
        if attachments:
            fields["attachments"] = attachments
            xpaths_used["attachments"] = "multiple_xpaths"

        # 15. contact_email
        xpath = ".//cac:ContractingParty/cac:Party/cac:Contact/cbc:ElectronicMail/text()"
        value = self._xpath_text(root, xpath)
        if value:
            fields["contact_email"] = value
            xpaths_used["contact_email"] = xpath

        # 16. contact_phone
        xpath = ".//cac:ContractingParty/cac:Party/cac:Contact/cbc:Telephone/text()"
        value = self._xpath_text(root, xpath)
        if value:
            fields["contact_phone"] = value
            xpaths_used["contact_phone"] = xpath

        # 17. contact_url
        xpath = ".//cac:ContractingParty/cac:Party/cac:Contact/cbc:URI/text()"
        value = self._xpath_text(root, xpath)
        if value:
            fields["contact_url"] = value
            xpaths_used["contact_url"] = xpath

        # Agregar XPaths al registro
        self._xpaths_registry.update(xpaths_used)

        return fields

    def _extract_lots(self, root: etree._Element) -> List[Dict[str, Any]]:
        """Extrae información de lotes (si existen)."""
        lots = []

        # Buscar todos los lotes
        lot_elements = root.xpath(".//cac:ProcurementProjectLot", namespaces=self.namespaces)

        for lot_elem in lot_elements:
            lot_id_xpath = "./cbc:ID[@schemeName='Lot']/text()"
            lot_id = self._xpath_text(lot_elem, lot_id_xpath)

            # Solo procesar si es un lote real (no LOT-0000 que es el lote único)
            if lot_id and lot_id != "LOT-0000":
                lot = {"lot_id": lot_id}

                # Nombre del lote
                name_xpath = "./cac:ProcurementProject/cbc:Name/text()"
                name = self._xpath_text(lot_elem, name_xpath)
                if name:
                    lot["name"] = name

                # Descripción del lote
                desc_xpath = "./cac:ProcurementProject/cbc:Description/text()"
                desc = self._xpath_text(lot_elem, desc_xpath)
                if desc:
                    lot["description"] = desc

                # Presupuesto del lote
                budget_xpath = "./cac:ProcurementProject/cac:RequestedTenderTotal/cbc:EstimatedOverallContractAmount/text()"
                budget = self._xpath_text(lot_elem, budget_xpath)
                if budget:
                    try:
                        lot["budget_eur"] = float(budget)
                    except ValueError:
                        pass

                lots.append(lot)

        return lots

    def _extract_award_criteria(self, root: etree._Element) -> List[Dict[str, Any]]:
        """Extrae criterios de adjudicación y sus pesos."""
        criteria = []

        # Buscar todos los criterios
        criterion_elements = root.xpath(
            ".//cac:AwardingCriterion/cac:SubordinateAwardingCriterion",
            namespaces=self.namespaces
        )

        for criterion_elem in criterion_elements:
            criterion = {}

            # Nombre/descripción del criterio
            desc_xpath = "./cbc:Description/text()"
            desc = self._xpath_text(criterion_elem, desc_xpath)
            if desc:
                criterion["name"] = desc.strip()

            # Tipo de criterio (price, quality, etc.)
            type_xpath = "./cbc:AwardingCriterionTypeCode/text()"
            crit_type = self._xpath_text(criterion_elem, type_xpath)
            if crit_type:
                criterion["type"] = crit_type

            # Peso del criterio
            weight_xpath = ".//efbc:ParameterNumeric/text()"
            weight = self._xpath_text(criterion_elem, weight_xpath)
            if weight:
                try:
                    criterion["weight"] = float(weight)
                except ValueError:
                    criterion["weight"] = weight

            if criterion.get("name"):
                criteria.append(criterion)

        return criteria

    def _extract_attachments(self, root: etree._Element) -> List[Dict[str, str]]:
        """Extrae documentos adjuntos con sus URIs."""
        attachments = []

        # Buscar referencias a documentos
        doc_elements = root.xpath(
            ".//cac:CallForTendersDocumentReference",
            namespaces=self.namespaces
        )

        for doc_elem in doc_elements:
            doc_id = self._xpath_text(doc_elem, "./cbc:ID/text()")
            doc_uri = self._xpath_text(doc_elem, "./cac:Attachment/cac:ExternalReference/cbc:URI/text()")

            if doc_id and doc_uri:
                attachments.append({
                    "name": doc_id,
                    "uri": doc_uri
                })

        return attachments

    def _extract_meta_fields(self) -> Dict[str, Any]:
        """Extrae campos META (XPaths usados y namespaces)."""
        return {
            "xpaths": self._xpaths_registry,
            "namespaces": self.namespaces
        }

    def _xpath_text(self, element: etree._Element, xpath: str) -> Optional[str]:
        """
        Ejecuta un XPath y retorna el primer resultado como texto.

        Args:
            element: Elemento raíz para la búsqueda
            xpath: Expresión XPath

        Returns:
            Texto del primer resultado o None
        """
        try:
            result = element.xpath(xpath, namespaces=self.namespaces)
            if result and len(result) > 0:
                text = str(result[0]).strip()
                return text if text else None
            return None
        except Exception as e:
            logger.warning(f"Error en XPath '{xpath}': {e}")
            return None

    def _xpath_list(self, element: etree._Element, xpath: str) -> List[str]:
        """
        Ejecuta un XPath y retorna todos los resultados como lista de strings.

        Args:
            element: Elemento raíz para la búsqueda
            xpath: Expresión XPath

        Returns:
            Lista de strings (puede estar vacía)
        """
        try:
            results = element.xpath(xpath, namespaces=self.namespaces)
            return [str(r).strip() for r in results if str(r).strip()]
        except Exception as e:
            logger.warning(f"Error en XPath '{xpath}': {e}")
            return []

    def _normalize_date(self, date_str: str) -> str:
        """
        Normaliza una fecha a formato ISO-8601 (YYYY-MM-DD).

        Args:
            date_str: Fecha en formato eForms (ej. "2025-10-13+02:00")

        Returns:
            Fecha en formato ISO-8601
        """
        try:
            # Quitar timezone si existe
            date_str = date_str.split("+")[0].split("-", 3)[0:3]
            date_str = "-".join(date_str)
            # Validar formato
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except Exception:
            # Si falla, intentar parsear con más flexibilidad
            try:
                date_str_clean = date_str.split("+")[0].split("T")[0]
                datetime.strptime(date_str_clean, "%Y-%m-%d")
                return date_str_clean
            except Exception:
                logger.warning(f"No se pudo normalizar la fecha: {date_str}")
                return date_str

    def _normalize_time(self, time_str: str) -> str:
        """
        Normaliza una hora a formato ISO-8601 (HH:MM:SS).

        Args:
            time_str: Hora en formato eForms (ej. "15:00:00+01:00")

        Returns:
            Hora en formato ISO-8601
        """
        try:
            # Quitar timezone si existe
            time_str = time_str.split("+")[0]
            # Validar formato
            datetime.strptime(time_str, "%H:%M:%S")
            return time_str
        except Exception:
            logger.warning(f"No se pudo normalizar la hora: {time_str}")
            return time_str

    def _validate_required_fields(self, required_fields: Dict[str, Any], xml_path: Path):
        """
        Valida que todos los campos REQUIRED estén presentes.

        Args:
            required_fields: Diccionario de campos requeridos
            xml_path: Ruta del XML (para logging)

        Raises:
            ValueError: Si falta algún campo requerido
        """
        required_keys = [
            "ojs_notice_id",
            "source_path",
            "publication_date",
            "buyer_name",
            "title",
            "cpv_main"
        ]

        missing = [key for key in required_keys if key not in required_fields or not required_fields[key]]

        if missing:
            error_msg = f"Campos REQUIRED faltantes en {xml_path.name}: {', '.join(missing)}"
            logger.error(error_msg)
            if STRICT_VALIDATION:
                raise ValueError(error_msg)


def parse_eforms_xml(xml_path: Path | str) -> Dict[str, Any]:
    """
    Función de conveniencia para parsear un XML eForms.

    Args:
        xml_path: Ruta al archivo XML

    Returns:
        Diccionario con estructura {REQUIRED, OPTIONAL, META}
    """
    parser = EFormsXMLParser()
    return parser.parse_file(xml_path)


if __name__ == "__main__":
    # Prueba del parser con un XML de ejemplo
    import json

    # Buscar un XML de prueba
    xml_dir = Path(__file__).parent.parent / "ted_xml"
    xml_files = list(xml_dir.glob("*.xml"))

    if xml_files:
        test_xml = xml_files[0]
        print(f"\n=== Parseando {test_xml.name} ===\n")

        try:
            record = parse_eforms_xml(test_xml)
            print(json.dumps(record, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("No se encontraron archivos XML en ted_xml/")
