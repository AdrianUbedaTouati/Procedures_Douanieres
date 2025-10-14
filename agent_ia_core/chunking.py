# -*- coding: utf-8 -*-
"""
Sistema de chunking semántico para registros eForms.
Divide cada registro en chunks por secciones lógicas (title, description, lot_X, etc.).
Cada chunk incluye metadatos completos para filtrado y trazabilidad.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
import sys
from pathlib import Path

# Importar configuración
sys.path.append(str(Path(__file__).parent))
from config import MAX_CHUNK_SIZE, CHUNK_OVERLAP, CHUNK_SECTIONS

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """
    Representa un chunk de texto con sus metadatos.
    """
    # Contenido textual
    text: str

    # Identificación
    chunk_id: str  # formato: {ojs_notice_id}_{section}_{index}
    ojs_notice_id: str
    section: str  # title, description, lot_X, award_criteria, etc.

    # Metadatos estructurados (para filtros)
    source_path: str
    buyer_name: str
    cpv_codes: List[str]  # cpv_main + cpv_additional
    nuts_regions: List[str]
    publication_date: str

    # Metadatos opcionales
    budget_eur: Optional[float] = None
    tender_deadline_date: Optional[str] = None
    contract_type: Optional[str] = None
    procedure_type: Optional[str] = None

    # Trazabilidad
    xpath_section: Optional[str] = None  # XPath del campo original

    # Índice del chunk (para chunks divididos de descripciones largas)
    chunk_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el chunk a diccionario."""
        return asdict(self)


class EFormsChunker:
    """
    Divide registros eForms en chunks semánticos.
    Cada chunk representa una sección lógica del aviso.
    """

    def __init__(
        self,
        max_chunk_size: int = None,
        chunk_overlap: int = None,
        sections: List[str] = None
    ):
        """
        Inicializa el chunker.

        Args:
            max_chunk_size: Tamaño máximo de caracteres por chunk
            chunk_overlap: Overlap entre chunks consecutivos
            sections: Lista de secciones a crear como chunks
        """
        self.max_chunk_size = max_chunk_size or MAX_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or CHUNK_OVERLAP
        self.sections = sections or CHUNK_SECTIONS

    def chunk_record(self, record: Dict[str, Any]) -> List[Chunk]:
        """
        Divide un registro en chunks semánticos.

        Args:
            record: Registro con estructura {REQUIRED, OPTIONAL, META}

        Returns:
            Lista de objetos Chunk
        """
        required = record.get("REQUIRED", {})
        optional = record.get("OPTIONAL", {})
        meta = record.get("META", {})
        xpaths = meta.get("xpaths", {})

        # Extraer metadatos comunes para todos los chunks
        common_metadata = self._extract_common_metadata(required, optional)

        chunks = []

        # 1. Chunk de título (siempre presente)
        if "title" in self.sections:
            title_chunk = self._create_title_chunk(
                title=required.get("title", ""),
                metadata=common_metadata,
                xpath=xpaths.get("title")
            )
            if title_chunk:
                chunks.append(title_chunk)

        # 2. Chunks de descripción (puede dividirse si es larga)
        if "description" in self.sections and optional.get("description"):
            desc_chunks = self._create_description_chunks(
                description=optional["description"],
                metadata=common_metadata,
                xpath=xpaths.get("description")
            )
            chunks.extend(desc_chunks)

        # 3. Chunks de lotes (uno por lote)
        if "lot" in self.sections and optional.get("lots"):
            lot_chunks = self._create_lot_chunks(
                lots=optional["lots"],
                metadata=common_metadata
            )
            chunks.extend(lot_chunks)

        # 4. Chunk de criterios de adjudicación
        if "award_criteria" in self.sections and optional.get("award_criteria"):
            criteria_chunk = self._create_award_criteria_chunk(
                criteria=optional["award_criteria"],
                metadata=common_metadata,
                xpath=xpaths.get("award_criteria")
            )
            if criteria_chunk:
                chunks.append(criteria_chunk)

        # 5. Chunk de presupuesto
        if "budget" in self.sections and optional.get("budget_eur"):
            budget_chunk = self._create_budget_chunk(
                budget_eur=optional["budget_eur"],
                currency=optional.get("currency", "EUR"),
                metadata=common_metadata,
                xpath=xpaths.get("budget_eur")
            )
            if budget_chunk:
                chunks.append(budget_chunk)

        # 6. Chunk de deadline
        if "deadline" in self.sections and optional.get("tender_deadline_date"):
            deadline_chunk = self._create_deadline_chunk(
                deadline_date=optional["tender_deadline_date"],
                deadline_time=optional.get("tender_deadline_time"),
                metadata=common_metadata,
                xpath=xpaths.get("tender_deadline_date")
            )
            if deadline_chunk:
                chunks.append(deadline_chunk)

        # 7. Chunk de requisitos de elegibilidad
        if "eligibility" in self.sections and optional.get("eligibility_requirements"):
            eligibility_chunk = self._create_eligibility_chunk(
                requirements=optional["eligibility_requirements"],
                metadata=common_metadata,
                xpath=xpaths.get("eligibility_requirements")
            )
            if eligibility_chunk:
                chunks.append(eligibility_chunk)

        logger.debug(f"Generados {len(chunks)} chunks para {common_metadata['ojs_notice_id']}")
        return chunks

    def _extract_common_metadata(
        self,
        required: Dict[str, Any],
        optional: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extrae metadatos comunes para todos los chunks."""
        # CPV codes (main + additional)
        cpv_codes = [required.get("cpv_main", "")]
        if optional.get("cpv_additional"):
            cpv_codes.extend(optional["cpv_additional"])
        cpv_codes = [c for c in cpv_codes if c]  # Filtrar vacíos

        return {
            "ojs_notice_id": required.get("ojs_notice_id", ""),
            "source_path": required.get("source_path", ""),
            "buyer_name": required.get("buyer_name", ""),
            "cpv_codes": list(set(cpv_codes)),  # Deduplicar
            "nuts_regions": optional.get("nuts_regions", []),
            "publication_date": required.get("publication_date", ""),
            "budget_eur": optional.get("budget_eur"),
            "tender_deadline_date": optional.get("tender_deadline_date"),
            "contract_type": optional.get("contract_type"),
            "procedure_type": optional.get("procedure_type"),
        }

    def _create_title_chunk(
        self,
        title: str,
        metadata: Dict[str, Any],
        xpath: Optional[str] = None
    ) -> Optional[Chunk]:
        """Crea un chunk para el título."""
        if not title or not title.strip():
            return None

        chunk_id = f"{metadata['ojs_notice_id']}_title_0"

        return Chunk(
            text=title.strip(),
            chunk_id=chunk_id,
            ojs_notice_id=metadata["ojs_notice_id"],
            section="title",
            source_path=metadata["source_path"],
            buyer_name=metadata["buyer_name"],
            cpv_codes=metadata["cpv_codes"],
            nuts_regions=metadata["nuts_regions"],
            publication_date=metadata["publication_date"],
            budget_eur=metadata["budget_eur"],
            tender_deadline_date=metadata["tender_deadline_date"],
            contract_type=metadata["contract_type"],
            procedure_type=metadata["procedure_type"],
            xpath_section=xpath,
            chunk_index=0
        )

    def _create_description_chunks(
        self,
        description: str,
        metadata: Dict[str, Any],
        xpath: Optional[str] = None
    ) -> List[Chunk]:
        """
        Crea chunks para la descripción.
        Si la descripción es muy larga, la divide en múltiples chunks con overlap.
        """
        if not description or not description.strip():
            return []

        description = description.strip()
        chunks = []

        # Si la descripción cabe en un chunk, crear uno solo
        if len(description) <= self.max_chunk_size:
            chunk_id = f"{metadata['ojs_notice_id']}_description_0"
            chunk = Chunk(
                text=description,
                chunk_id=chunk_id,
                ojs_notice_id=metadata["ojs_notice_id"],
                section="description",
                source_path=metadata["source_path"],
                buyer_name=metadata["buyer_name"],
                cpv_codes=metadata["cpv_codes"],
                nuts_regions=metadata["nuts_regions"],
                publication_date=metadata["publication_date"],
                budget_eur=metadata["budget_eur"],
                tender_deadline_date=metadata["tender_deadline_date"],
                contract_type=metadata["contract_type"],
                procedure_type=metadata["procedure_type"],
                xpath_section=xpath,
                chunk_index=0
            )
            chunks.append(chunk)
        else:
            # Dividir en múltiples chunks con overlap
            chunks.extend(self._split_text_into_chunks(
                text=description,
                section="description",
                metadata=metadata,
                xpath=xpath
            ))

        return chunks

    def _split_text_into_chunks(
        self,
        text: str,
        section: str,
        metadata: Dict[str, Any],
        xpath: Optional[str] = None
    ) -> List[Chunk]:
        """Divide un texto largo en múltiples chunks con overlap."""
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            # Calcular el final del chunk
            end = start + self.max_chunk_size

            # Si no es el último chunk, buscar un punto de corte natural (espacio)
            if end < len(text):
                # Buscar el último espacio antes del límite
                last_space = text.rfind(" ", start, end)
                if last_space > start:
                    end = last_space

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunk_id = f"{metadata['ojs_notice_id']}_{section}_{chunk_index}"
                chunk = Chunk(
                    text=chunk_text,
                    chunk_id=chunk_id,
                    ojs_notice_id=metadata["ojs_notice_id"],
                    section=section,
                    source_path=metadata["source_path"],
                    buyer_name=metadata["buyer_name"],
                    cpv_codes=metadata["cpv_codes"],
                    nuts_regions=metadata["nuts_regions"],
                    publication_date=metadata["publication_date"],
                    budget_eur=metadata["budget_eur"],
                    tender_deadline_date=metadata["tender_deadline_date"],
                    contract_type=metadata["contract_type"],
                    procedure_type=metadata["procedure_type"],
                    xpath_section=xpath,
                    chunk_index=chunk_index
                )
                chunks.append(chunk)
                chunk_index += 1

            # Avanzar con overlap
            start = end - self.chunk_overlap if end < len(text) else len(text)

        return chunks

    def _create_lot_chunks(
        self,
        lots: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """Crea un chunk por cada lote."""
        chunks = []

        for i, lot in enumerate(lots):
            lot_id = lot.get("lot_id", i)
            lot_text_parts = []

            # Construir texto descriptivo del lote
            if lot.get("name"):
                lot_text_parts.append(f"Lote {lot_id}: {lot['name']}")

            if lot.get("description"):
                lot_text_parts.append(lot["description"])

            if lot.get("budget_eur"):
                lot_text_parts.append(f"Presupuesto: {lot['budget_eur']} EUR")

            if not lot_text_parts:
                continue

            lot_text = "\n".join(lot_text_parts)
            chunk_id = f"{metadata['ojs_notice_id']}_lot_{lot_id}"

            chunk = Chunk(
                text=lot_text,
                chunk_id=chunk_id,
                ojs_notice_id=metadata["ojs_notice_id"],
                section=f"lot_{lot_id}",
                source_path=metadata["source_path"],
                buyer_name=metadata["buyer_name"],
                cpv_codes=metadata["cpv_codes"],
                nuts_regions=metadata["nuts_regions"],
                publication_date=metadata["publication_date"],
                budget_eur=lot.get("budget_eur") or metadata["budget_eur"],
                tender_deadline_date=metadata["tender_deadline_date"],
                contract_type=metadata["contract_type"],
                procedure_type=metadata["procedure_type"],
                xpath_section=f"lot[{i}]",
                chunk_index=i
            )
            chunks.append(chunk)

        return chunks

    def _create_award_criteria_chunk(
        self,
        criteria: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        xpath: Optional[str] = None
    ) -> Optional[Chunk]:
        """Crea un chunk con los criterios de adjudicación."""
        if not criteria:
            return None

        # Construir texto descriptivo de los criterios
        criteria_lines = ["Criterios de adjudicación:"]

        for i, crit in enumerate(criteria, 1):
            name = crit.get("name", f"Criterio {i}")
            weight = crit.get("weight")
            crit_type = crit.get("type")

            line = f"{i}. {name}"
            if weight is not None:
                line += f" - Peso: {weight}%"
            if crit_type:
                line += f" (Tipo: {crit_type})"

            criteria_lines.append(line)

        criteria_text = "\n".join(criteria_lines)
        chunk_id = f"{metadata['ojs_notice_id']}_award_criteria_0"

        return Chunk(
            text=criteria_text,
            chunk_id=chunk_id,
            ojs_notice_id=metadata["ojs_notice_id"],
            section="award_criteria",
            source_path=metadata["source_path"],
            buyer_name=metadata["buyer_name"],
            cpv_codes=metadata["cpv_codes"],
            nuts_regions=metadata["nuts_regions"],
            publication_date=metadata["publication_date"],
            budget_eur=metadata["budget_eur"],
            tender_deadline_date=metadata["tender_deadline_date"],
            contract_type=metadata["contract_type"],
            procedure_type=metadata["procedure_type"],
            xpath_section=xpath,
            chunk_index=0
        )

    def _create_budget_chunk(
        self,
        budget_eur: float,
        currency: str,
        metadata: Dict[str, Any],
        xpath: Optional[str] = None
    ) -> Optional[Chunk]:
        """Crea un chunk para el presupuesto."""
        budget_text = f"Presupuesto estimado: {budget_eur:,.2f} {currency}"
        chunk_id = f"{metadata['ojs_notice_id']}_budget_0"

        return Chunk(
            text=budget_text,
            chunk_id=chunk_id,
            ojs_notice_id=metadata["ojs_notice_id"],
            section="budget",
            source_path=metadata["source_path"],
            buyer_name=metadata["buyer_name"],
            cpv_codes=metadata["cpv_codes"],
            nuts_regions=metadata["nuts_regions"],
            publication_date=metadata["publication_date"],
            budget_eur=budget_eur,
            tender_deadline_date=metadata["tender_deadline_date"],
            contract_type=metadata["contract_type"],
            procedure_type=metadata["procedure_type"],
            xpath_section=xpath,
            chunk_index=0
        )

    def _create_deadline_chunk(
        self,
        deadline_date: str,
        deadline_time: Optional[str],
        metadata: Dict[str, Any],
        xpath: Optional[str] = None
    ) -> Optional[Chunk]:
        """Crea un chunk para el plazo de presentación."""
        deadline_text = f"Fecha límite de presentación de ofertas: {deadline_date}"
        if deadline_time:
            deadline_text += f" a las {deadline_time}"

        chunk_id = f"{metadata['ojs_notice_id']}_deadline_0"

        return Chunk(
            text=deadline_text,
            chunk_id=chunk_id,
            ojs_notice_id=metadata["ojs_notice_id"],
            section="deadline",
            source_path=metadata["source_path"],
            buyer_name=metadata["buyer_name"],
            cpv_codes=metadata["cpv_codes"],
            nuts_regions=metadata["nuts_regions"],
            publication_date=metadata["publication_date"],
            budget_eur=metadata["budget_eur"],
            tender_deadline_date=deadline_date,
            contract_type=metadata["contract_type"],
            procedure_type=metadata["procedure_type"],
            xpath_section=xpath,
            chunk_index=0
        )

    def _create_eligibility_chunk(
        self,
        requirements: str,
        metadata: Dict[str, Any],
        xpath: Optional[str] = None
    ) -> Optional[Chunk]:
        """Crea un chunk para los requisitos de elegibilidad."""
        if not requirements or not requirements.strip():
            return None

        chunk_id = f"{metadata['ojs_notice_id']}_eligibility_0"

        return Chunk(
            text=f"Requisitos de elegibilidad: {requirements.strip()}",
            chunk_id=chunk_id,
            ojs_notice_id=metadata["ojs_notice_id"],
            section="eligibility",
            source_path=metadata["source_path"],
            buyer_name=metadata["buyer_name"],
            cpv_codes=metadata["cpv_codes"],
            nuts_regions=metadata["nuts_regions"],
            publication_date=metadata["publication_date"],
            budget_eur=metadata["budget_eur"],
            tender_deadline_date=metadata["tender_deadline_date"],
            contract_type=metadata["contract_type"],
            procedure_type=metadata["procedure_type"],
            xpath_section=xpath,
            chunk_index=0
        )


def chunk_eforms_record(record: Dict[str, Any]) -> List[Chunk]:
    """
    Función de conveniencia para chunkear un registro.

    Args:
        record: Registro con estructura {REQUIRED, OPTIONAL, META}

    Returns:
        Lista de objetos Chunk
    """
    chunker = EFormsChunker()
    return chunker.chunk_record(record)


if __name__ == "__main__":
    # Prueba del chunker con un registro de ejemplo
    import json
    from pathlib import Path

    # Leer un registro de prueba
    records_dir = Path(__file__).parent.parent / "data" / "records"
    json_files = list(records_dir.glob("*.json"))

    if json_files:
        test_file = json_files[0]
        print(f"\n=== Chunking {test_file.name} ===\n")

        with open(test_file, 'r', encoding='utf-8') as f:
            record = json.load(f)

        chunks = chunk_eforms_record(record)

        print(f"Generados {len(chunks)} chunks:\n")
        for i, chunk in enumerate(chunks, 1):
            print(f"{i}. [{chunk.section}] {chunk.chunk_id}")
            print(f"   Texto: {chunk.text[:100]}...")
            print(f"   Metadatos: CPV={chunk.cpv_codes}, NUTS={chunk.nuts_regions}")
            print(f"   XPath: {chunk.xpath_section}")
            print()
    else:
        print("No se encontraron registros JSON en data/records/")
        print("Ejecuta primero: python -m src.ingest")
