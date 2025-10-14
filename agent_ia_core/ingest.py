# -*- coding: utf-8 -*-
"""
Sistema de ingesta de XMLs eForms.
Orquesta el proceso completo: leer XMLs → parsear → validar → guardar JSONs.
Incluye deduplicación, logging y estadísticas de procesamiento.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
import json
import logging
from datetime import datetime
from collections import defaultdict
import sys

# Importar módulos propios
sys.path.append(str(Path(__file__).parent))
from config import XML_DIR, RECORDS_DIR, STRICT_VALIDATION
from xml_parser import parse_eforms_xml, EFormsXMLParser

# Importar validador
sys.path.append(str(Path(__file__).parent.parent))
from schema.validators import validate_eforms_record, ValidationError

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IngestionStats:
    """Clase para rastrear estadísticas de ingesta."""

    def __init__(self):
        self.total_files = 0
        self.processed = 0
        self.skipped_duplicates = 0
        self.failed_parsing = 0
        self.failed_validation = 0
        self.successful = 0
        self.errors_by_type = defaultdict(int)
        self.start_time = None
        self.end_time = None

    def start(self):
        """Inicia el contador de tiempo."""
        self.start_time = datetime.now()

    def end(self):
        """Finaliza el contador de tiempo."""
        self.end_time = datetime.now()

    def elapsed_time(self) -> float:
        """Retorna el tiempo transcurrido en segundos."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def print_summary(self):
        """Imprime un resumen de las estadísticas."""
        print("\n" + "=" * 60)
        print("RESUMEN DE INGESTA")
        print("=" * 60)
        print(f"Archivos encontrados:     {self.total_files}")
        print(f"Procesados:               {self.processed}")
        print(f"Exitosos:                 {self.successful}")
        print(f"Duplicados (omitidos):    {self.skipped_duplicates}")
        print(f"Errores de parsing:       {self.failed_parsing}")
        print(f"Errores de validación:    {self.failed_validation}")
        print(f"Tiempo transcurrido:      {self.elapsed_time():.2f}s")

        if self.successful > 0:
            avg_time = self.elapsed_time() / self.successful
            print(f"Tiempo promedio por XML:  {avg_time:.3f}s")

        if self.errors_by_type:
            print("\nErrores por tipo:")
            for error_type, count in sorted(self.errors_by_type.items(), key=lambda x: -x[1]):
                print(f"  - {error_type}: {count}")

        print("=" * 60 + "\n")


class EFormsIngestor:
    """
    Orquestador de ingesta de XMLs eForms.
    Lee XMLs, parsea, valida y guarda registros en formato JSON.
    """

    def __init__(
        self,
        xml_dir: Path = None,
        records_dir: Path = None,
        strict_validation: bool = None,
        deduplicate: bool = True
    ):
        """
        Inicializa el ingestor.

        Args:
            xml_dir: Directorio con XMLs de entrada (por defecto: config.XML_DIR)
            records_dir: Directorio de salida para JSONs (por defecto: config.RECORDS_DIR)
            strict_validation: Activar validación estricta (por defecto: config.STRICT_VALIDATION)
            deduplicate: Activar deduplicación por ojs_notice_id
        """
        self.xml_dir = Path(xml_dir) if xml_dir else Path(XML_DIR)
        self.records_dir = Path(records_dir) if records_dir else Path(RECORDS_DIR)
        self.strict_validation = strict_validation if strict_validation is not None else STRICT_VALIDATION
        self.deduplicate = deduplicate

        # Crear directorio de salida si no existe
        self.records_dir.mkdir(parents=True, exist_ok=True)

        # Parser y estadísticas
        self.parser = EFormsXMLParser()
        self.stats = IngestionStats()

        # Set de IDs procesados (para deduplicación)
        self.processed_ids: Set[str] = set()

    def run(self, max_files: Optional[int] = None) -> IngestionStats:
        """
        Ejecuta el proceso de ingesta completo.

        Args:
            max_files: Número máximo de archivos a procesar (None = todos)

        Returns:
            Objeto IngestionStats con estadísticas de procesamiento
        """
        logger.info(f"Iniciando ingesta desde {self.xml_dir}")
        logger.info(f"Salida en {self.records_dir}")

        self.stats.start()

        # Buscar archivos XML
        xml_files = list(self.xml_dir.glob("*.xml"))
        self.stats.total_files = len(xml_files)

        if self.stats.total_files == 0:
            logger.warning(f"No se encontraron archivos XML en {self.xml_dir}")
            self.stats.end()
            return self.stats

        logger.info(f"Encontrados {self.stats.total_files} archivos XML")

        # Limitar número de archivos si se especifica
        if max_files:
            xml_files = xml_files[:max_files]
            logger.info(f"Limitando procesamiento a {max_files} archivos")

        # Cargar IDs ya procesados si existe deduplicación
        if self.deduplicate:
            self._load_existing_ids()

        # Procesar cada XML
        for i, xml_path in enumerate(xml_files, 1):
            logger.info(f"[{i}/{len(xml_files)}] Procesando {xml_path.name}")
            self.stats.processed += 1

            try:
                success = self._process_xml(xml_path)
                if success:
                    self.stats.successful += 1

            except Exception as e:
                logger.error(f"Error inesperado procesando {xml_path.name}: {e}")
                self.stats.failed_parsing += 1
                self.stats.errors_by_type["unexpected_error"] += 1

        self.stats.end()
        self.stats.print_summary()

        return self.stats

    def _process_xml(self, xml_path: Path) -> bool:
        """
        Procesa un archivo XML individual.

        Args:
            xml_path: Ruta al archivo XML

        Returns:
            True si se procesó exitosamente, False si hubo error
        """
        try:
            # 1. Parsear XML
            record = self.parser.parse_file(xml_path)

        except FileNotFoundError:
            logger.error(f"Archivo no encontrado: {xml_path}")
            self.stats.failed_parsing += 1
            self.stats.errors_by_type["file_not_found"] += 1
            return False

        except Exception as e:
            logger.error(f"Error parseando {xml_path.name}: {e}")
            self.stats.failed_parsing += 1
            self.stats.errors_by_type["parsing_error"] += 1
            return False

        # 2. Verificar duplicados
        ojs_notice_id = record.get("REQUIRED", {}).get("ojs_notice_id")

        if not ojs_notice_id:
            logger.error(f"No se pudo extraer ojs_notice_id de {xml_path.name}")
            self.stats.failed_parsing += 1
            self.stats.errors_by_type["missing_ojs_id"] += 1
            return False

        if self.deduplicate and ojs_notice_id in self.processed_ids:
            logger.info(f"Duplicado omitido: {ojs_notice_id}")
            self.stats.skipped_duplicates += 1
            return False

        # 3. Validar registro
        try:
            is_valid, errors = validate_eforms_record(record, strict=self.strict_validation)

            if not is_valid:
                logger.warning(f"Registro con errores de validación: {xml_path.name}")
                for error in errors[:5]:  # Mostrar solo primeros 5 errores
                    logger.warning(f"  - {error}")
                self.stats.failed_validation += 1
                self.stats.errors_by_type["validation_error"] += 1

                # Si es strict, no guardamos el registro
                if self.strict_validation:
                    return False

        except ValidationError as e:
            logger.error(f"Error de validación en {xml_path.name}: {e}")
            self.stats.failed_validation += 1
            self.stats.errors_by_type["validation_error"] += 1
            return False

        # 4. Guardar registro en JSON
        try:
            output_path = self._get_output_path(ojs_notice_id)
            self._save_record(record, output_path)

            # Marcar como procesado
            self.processed_ids.add(ojs_notice_id)

            logger.info(f"✓ Guardado: {output_path.name}")
            return True

        except Exception as e:
            logger.error(f"Error guardando {xml_path.name}: {e}")
            self.stats.errors_by_type["save_error"] += 1
            return False

    def _load_existing_ids(self):
        """Carga IDs de registros ya procesados para deduplicación."""
        existing_files = list(self.records_dir.glob("*.json"))

        for json_path in existing_files:
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    record = json.load(f)
                    ojs_id = record.get("REQUIRED", {}).get("ojs_notice_id")
                    if ojs_id:
                        self.processed_ids.add(ojs_id)
            except Exception as e:
                logger.warning(f"No se pudo leer {json_path.name}: {e}")

        if self.processed_ids:
            logger.info(f"Cargados {len(self.processed_ids)} registros existentes (deduplicación activa)")

    def _get_output_path(self, ojs_notice_id: str) -> Path:
        """
        Genera la ruta de salida para un registro.

        Args:
            ojs_notice_id: ID del aviso OJS

        Returns:
            Path al archivo JSON de salida
        """
        # Sanitizar el ID para nombre de archivo
        safe_name = ojs_notice_id.replace("/", "_").replace("\\", "_")
        return self.records_dir / f"{safe_name}.json"

    def _save_record(self, record: Dict[str, Any], output_path: Path):
        """
        Guarda un registro en formato JSON.

        Args:
            record: Diccionario con el registro completo
            output_path: Ruta del archivo de salida
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=2, ensure_ascii=False)


def run_ingestion(
    xml_dir: Optional[Path] = None,
    records_dir: Optional[Path] = None,
    max_files: Optional[int] = None,
    strict_validation: Optional[bool] = None
) -> IngestionStats:
    """
    Función de conveniencia para ejecutar la ingesta.

    Args:
        xml_dir: Directorio con XMLs de entrada
        records_dir: Directorio de salida para JSONs
        max_files: Número máximo de archivos a procesar
        strict_validation: Activar validación estricta

    Returns:
        Objeto IngestionStats con estadísticas
    """
    ingestor = EFormsIngestor(
        xml_dir=xml_dir,
        records_dir=records_dir,
        strict_validation=strict_validation
    )
    return ingestor.run(max_files=max_files)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingesta de XMLs eForms a registros JSON canónicos")
    parser.add_argument(
        "--xml-dir",
        type=Path,
        default=None,
        help="Directorio con XMLs de entrada (por defecto: config.XML_DIR)"
    )
    parser.add_argument(
        "--records-dir",
        type=Path,
        default=None,
        help="Directorio de salida para JSONs (por defecto: config.RECORDS_DIR)"
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Número máximo de archivos a procesar (por defecto: todos)"
    )
    parser.add_argument(
        "--no-strict",
        action="store_true",
        help="Desactivar validación estricta (guardar registros con errores)"
    )

    args = parser.parse_args()

    # Ejecutar ingesta
    stats = run_ingestion(
        xml_dir=args.xml_dir,
        records_dir=args.records_dir,
        max_files=args.max_files,
        strict_validation=not args.no_strict if args.no_strict else None
    )

    # Salir con código de error si hubo fallos
    if stats.failed_parsing > 0 or stats.failed_validation > 0:
        sys.exit(1)
