# -*- coding: utf-8 -*-
"""
Validadores para registros eForms normalizados.
Valida campos REQUIRED, tipos de datos y formatos ISO-8601.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Excepción para errores de validación."""
    pass


class EFormsValidator:
    """
    Validador de registros eForms normalizados.
    Verifica campos REQUIRED, tipos y formatos.
    """

    # Campos requeridos mínimos
    REQUIRED_FIELDS = [
        "ojs_notice_id",
        "source_path",
        "publication_date",
        "buyer_name",
        "title",
        "cpv_main"
    ]

    def validate_record(self, record: Dict[str, Any], strict: bool = True) -> Tuple[bool, List[str]]:
        """
        Valida un registro completo (REQUIRED + OPTIONAL + META).

        Args:
            record: Diccionario con estructura {REQUIRED, OPTIONAL, META}
            strict: Si es True, lanza excepción en caso de error

        Returns:
            Tupla (es_válido, lista_de_errores)

        Raises:
            ValidationError: Si strict=True y hay errores
        """
        errors = []

        # Verificar estructura básica
        if not isinstance(record, dict):
            errors.append("El registro debe ser un diccionario")
            if strict:
                raise ValidationError("; ".join(errors))
            return False, errors

        if "REQUIRED" not in record:
            errors.append("Falta la sección REQUIRED")

        if "OPTIONAL" not in record:
            errors.append("Falta la sección OPTIONAL")

        if "META" not in record:
            errors.append("Falta la sección META")

        if errors:
            if strict:
                raise ValidationError("; ".join(errors))
            return False, errors

        # Validar REQUIRED
        req_errors = self.validate_required_fields(record["REQUIRED"])
        errors.extend(req_errors)

        # Validar OPTIONAL (solo si existen los campos)
        opt_errors = self.validate_optional_fields(record["OPTIONAL"])
        errors.extend(opt_errors)

        # Validar META
        meta_errors = self.validate_meta_fields(record["META"])
        errors.extend(meta_errors)

        if errors and strict:
            raise ValidationError("; ".join(errors))

        return len(errors) == 0, errors

    def validate_required_fields(self, required: Dict[str, Any]) -> List[str]:
        """
        Valida campos REQUIRED.

        Args:
            required: Diccionario de campos requeridos

        Returns:
            Lista de errores encontrados (vacía si no hay errores)
        """
        errors = []

        # Verificar presencia de campos
        for field in self.REQUIRED_FIELDS:
            if field not in required:
                errors.append(f"Campo REQUIRED faltante: {field}")
            elif not required[field]:
                errors.append(f"Campo REQUIRED vacío: {field}")

        if errors:
            return errors

        # Validar tipos y formatos
        # 1. ojs_notice_id (string, formato: XXXXXXXX-YYYY)
        ojs_id = required.get("ojs_notice_id", "")
        if not isinstance(ojs_id, str):
            errors.append(f"ojs_notice_id debe ser string, es {type(ojs_id).__name__}")
        elif not self._is_valid_ojs_notice_id(ojs_id):
            errors.append(f"ojs_notice_id con formato inválido: {ojs_id}")

        # 2. source_path (string)
        source_path = required.get("source_path", "")
        if not isinstance(source_path, str):
            errors.append(f"source_path debe ser string, es {type(source_path).__name__}")

        # 3. publication_date (string, formato ISO-8601 date-time)
        pub_date = required.get("publication_date", "")
        if not isinstance(pub_date, str):
            errors.append(f"publication_date debe ser string, es {type(pub_date).__name__}")
        elif not self._is_valid_date(pub_date):
            errors.append(f"publication_date con formato inválido: {pub_date}")

        # 4. buyer_name (string, no vacío)
        buyer_name = required.get("buyer_name", "")
        if not isinstance(buyer_name, str):
            errors.append(f"buyer_name debe ser string, es {type(buyer_name).__name__}")
        elif len(buyer_name.strip()) < 3:
            errors.append(f"buyer_name demasiado corto: '{buyer_name}'")

        # 5. title (string, no vacío)
        title = required.get("title", "")
        if not isinstance(title, str):
            errors.append(f"title debe ser string, es {type(title).__name__}")
        elif len(title.strip()) < 5:
            errors.append(f"title demasiado corto: '{title}'")

        # 6. cpv_main (string, formato: 8 dígitos)
        cpv_main = required.get("cpv_main", "")
        if not isinstance(cpv_main, str):
            errors.append(f"cpv_main debe ser string, es {type(cpv_main).__name__}")
        elif not self._is_valid_cpv(cpv_main):
            errors.append(f"cpv_main con formato inválido: {cpv_main}")

        return errors

    def validate_optional_fields(self, optional: Dict[str, Any]) -> List[str]:
        """
        Valida campos OPTIONAL (solo los que existen).

        Args:
            optional: Diccionario de campos opcionales

        Returns:
            Lista de errores encontrados (vacía si no hay errores)
        """
        errors = []

        # 1. description (string o null)
        if "description" in optional:
            desc = optional["description"]
            if desc is not None and not isinstance(desc, str):
                errors.append(f"description debe ser string o null, es {type(desc).__name__}")

        # 2. cpv_additional (array de strings)
        if "cpv_additional" in optional:
            cpv_add = optional["cpv_additional"]
            if not isinstance(cpv_add, list):
                errors.append(f"cpv_additional debe ser array, es {type(cpv_add).__name__}")
            else:
                for i, cpv in enumerate(cpv_add):
                    if not isinstance(cpv, str):
                        errors.append(f"cpv_additional[{i}] debe ser string")
                    elif not self._is_valid_cpv(cpv):
                        errors.append(f"cpv_additional[{i}] con formato inválido: {cpv}")

        # 3. nuts_regions (array de strings)
        if "nuts_regions" in optional:
            nuts = optional["nuts_regions"]
            if not isinstance(nuts, list):
                errors.append(f"nuts_regions debe ser array, es {type(nuts).__name__}")
            else:
                for i, nut in enumerate(nuts):
                    if not isinstance(nut, str):
                        errors.append(f"nuts_regions[{i}] debe ser string")

        # 4. budget_eur (number o null)
        if "budget_eur" in optional:
            budget = optional["budget_eur"]
            if budget is not None and not isinstance(budget, (int, float)):
                errors.append(f"budget_eur debe ser number o null, es {type(budget).__name__}")
            elif budget is not None and budget < 0:
                errors.append(f"budget_eur no puede ser negativo: {budget}")

        # 5. tender_deadline_date (string ISO date o null)
        if "tender_deadline_date" in optional:
            deadline = optional["tender_deadline_date"]
            if deadline is not None:
                if not isinstance(deadline, str):
                    errors.append(f"tender_deadline_date debe ser string o null")
                elif not self._is_valid_date(deadline):
                    errors.append(f"tender_deadline_date con formato inválido: {deadline}")

        # 6. tender_deadline_time (string ISO time o null)
        if "tender_deadline_time" in optional:
            time = optional["tender_deadline_time"]
            if time is not None:
                if not isinstance(time, str):
                    errors.append(f"tender_deadline_time debe ser string o null")
                elif not self._is_valid_time(time):
                    errors.append(f"tender_deadline_time con formato inválido: {time}")

        # 7. lots (array de objetos)
        if "lots" in optional:
            lots = optional["lots"]
            if not isinstance(lots, list):
                errors.append(f"lots debe ser array, es {type(lots).__name__}")
            else:
                for i, lot in enumerate(lots):
                    if not isinstance(lot, dict):
                        errors.append(f"lots[{i}] debe ser objeto")
                    elif "lot_id" not in lot:
                        errors.append(f"lots[{i}] debe tener 'lot_id'")

        # 8. award_criteria (array de objetos)
        if "award_criteria" in optional:
            criteria = optional["award_criteria"]
            if not isinstance(criteria, list):
                errors.append(f"award_criteria debe ser array, es {type(criteria).__name__}")
            else:
                for i, crit in enumerate(criteria):
                    if not isinstance(crit, dict):
                        errors.append(f"award_criteria[{i}] debe ser objeto")
                    elif "name" not in crit:
                        errors.append(f"award_criteria[{i}] debe tener 'name'")

        # 9. external_references (array de strings)
        if "external_references" in optional:
            refs = optional["external_references"]
            if not isinstance(refs, list):
                errors.append(f"external_references debe ser array")
            else:
                for i, ref in enumerate(refs):
                    if not isinstance(ref, str):
                        errors.append(f"external_references[{i}] debe ser string")
                    elif not ref.startswith("http"):
                        errors.append(f"external_references[{i}] debe ser URL válida")

        return errors

    def validate_meta_fields(self, meta: Dict[str, Any]) -> List[str]:
        """
        Valida campos META.

        Args:
            meta: Diccionario de metadatos

        Returns:
            Lista de errores encontrados (vacía si no hay errores)
        """
        errors = []

        # 1. xpaths (objeto)
        if "xpaths" not in meta:
            errors.append("META debe contener 'xpaths'")
        elif not isinstance(meta["xpaths"], dict):
            errors.append(f"META.xpaths debe ser objeto, es {type(meta['xpaths']).__name__}")

        # 2. namespaces (objeto)
        if "namespaces" not in meta:
            errors.append("META debe contener 'namespaces'")
        elif not isinstance(meta["namespaces"], dict):
            errors.append(f"META.namespaces debe ser objeto, es {type(meta['namespaces']).__name__}")

        return errors

    # ===== Métodos auxiliares de validación =====

    def _is_valid_ojs_notice_id(self, ojs_id: str) -> bool:
        """Valida formato de ojs_notice_id (ej: 00668461-2025)."""
        if not ojs_id:
            return False
        parts = ojs_id.split("-")
        if len(parts) != 2:
            return False
        # Primera parte: 6-8 dígitos, segunda parte: 4 dígitos (año)
        return parts[0].isdigit() and len(parts[0]) >= 6 and parts[1].isdigit() and len(parts[1]) == 4

    def _is_valid_cpv(self, cpv: str) -> bool:
        """Valida formato de código CPV (8 dígitos)."""
        return cpv.isdigit() and len(cpv) == 8

    def _is_valid_date(self, date_str: str) -> bool:
        """Valida formato de fecha ISO-8601 (YYYY-MM-DD)."""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _is_valid_time(self, time_str: str) -> bool:
        """Valida formato de hora ISO-8601 (HH:MM:SS)."""
        try:
            datetime.strptime(time_str, "%H:%M:%S")
            return True
        except ValueError:
            return False


def validate_eforms_record(record: Dict[str, Any], strict: bool = True) -> Tuple[bool, List[str]]:
    """
    Función de conveniencia para validar un registro eForms.

    Args:
        record: Diccionario con estructura {REQUIRED, OPTIONAL, META}
        strict: Si es True, lanza excepción en caso de error

    Returns:
        Tupla (es_válido, lista_de_errores)
    """
    validator = EFormsValidator()
    return validator.validate_record(record, strict=strict)


if __name__ == "__main__":
    # Prueba del validador
    import json

    # Registro de prueba válido
    valid_record = {
        "REQUIRED": {
            "ojs_notice_id": "00668461-2025",
            "source_path": "668461-2025.xml",
            "publication_date": "2025-10-13",
            "buyer_name": "Fundación Estatal para la Formación en el Empleo",
            "title": "Servicios informáticos SAP",
            "cpv_main": "72600000"
        },
        "OPTIONAL": {
            "description": "Servicios de desarrollo y mantenimiento",
            "budget_eur": 961200.0,
            "cpv_additional": ["72267100"],
            "nuts_regions": ["ES300"]
        },
        "META": {
            "xpaths": {"title": "//cac:ProcurementProject/cbc:Name/text()"},
            "namespaces": {"cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"}
        }
    }

    print("\n=== Validando registro válido ===")
    is_valid, errors = validate_eforms_record(valid_record, strict=False)
    print(f"Válido: {is_valid}")
    if errors:
        print("Errores:", errors)

    # Registro de prueba inválido
    invalid_record = {
        "REQUIRED": {
            "ojs_notice_id": "INVALID",  # formato incorrecto
            "source_path": "test.xml",
            # falta publication_date
            "buyer_name": "AB",  # demasiado corto
            "title": "X",  # demasiado corto
            "cpv_main": "123"  # formato incorrecto
        },
        "OPTIONAL": {},
        "META": {}
    }

    print("\n=== Validando registro inválido ===")
    is_valid, errors = validate_eforms_record(invalid_record, strict=False)
    print(f"Válido: {is_valid}")
    if errors:
        print("Errores encontrados:")
        for error in errors:
            print(f"  - {error}")
