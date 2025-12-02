# -*- coding: utf-8 -*-
"""
Sistema de indexación vectorial híbrida para chunks eForms.
Construye y actualiza el índice ChromaDB con embeddings y metadatos.
Soporta filtros estructurados (CPV, NUTS, fechas, presupuesto).
Soporta OpenAI y Google Gemini como proveedores de embeddings.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import logging
from datetime import datetime
import sys

# Importar configuración
sys.path.append(str(Path(__file__).parent))
from agent_ia_core.config import (
    RECORDS_DIR, INDEX_DIR, CHROMA_PERSIST_DIRECTORY,
    CHROMA_COLLECTION_NAME, EMBEDDING_MODEL, LLM_PROVIDER
)
from chunking import chunk_eforms_record, Chunk

# Imports de LangChain y ChromaDB
try:
    from langchain_core.documents import Document
    from langchain_chroma import Chroma

    # Importar embeddings según el proveedor
    if LLM_PROVIDER == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        EMBEDDINGS_CLASS = GoogleGenerativeAIEmbeddings
    elif LLM_PROVIDER == "nvidia":
        from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
        EMBEDDINGS_CLASS = NVIDIAEmbeddings
    else:  # openai
        from langchain_openai import OpenAIEmbeddings
        EMBEDDINGS_CLASS = OpenAIEmbeddings

except ImportError as e:
    print(f"Error importing dependencies: {e}")
    print("\nPor favor instala las dependencias necesarias:")
    print("  pip install langchain-chroma langchain-core")
    if LLM_PROVIDER == "google":
        print("  pip install langchain-google-genai google-generativeai")
    else:
        print("  pip install langchain-openai openai")
    sys.exit(1)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IndexBuilder:
    """
    Constructor de índice vectorial híbrido con ChromaDB.
    Indexa chunks con embeddings y metadatos para filtros estructurados.
    Soporta OpenAI y Google Gemini.
    """

    def __init__(
        self,
        records_dir: Path = None,
        persist_directory: str = None,
        collection_name: str = None,
        embedding_model: str = None,
        api_key: str = None,
        provider: str = None
    ):
        """
        Inicializa el constructor de índice.

        Args:
            records_dir: Directorio con registros JSON
            persist_directory: Directorio para persistir ChromaDB
            collection_name: Nombre de la colección
            embedding_model: Modelo de embeddings
            api_key: API key del proveedor
            provider: "openai" o "google"
        """
        self.records_dir = Path(records_dir) if records_dir else Path(RECORDS_DIR)
        self.persist_directory = persist_directory or CHROMA_PERSIST_DIRECTORY
        self.collection_name = collection_name or CHROMA_COLLECTION_NAME
        self.embedding_model = embedding_model or EMBEDDING_MODEL
        self.api_key = api_key
        self.provider = provider or LLM_PROVIDER

        # Verificar API key (no necesaria para Ollama)
        if not self.api_key and self.provider != 'ollama':
            raise ValueError(
                f"API key no configurada para {self.provider}. "
                f"Por favor, configura tu API key en tu perfil de usuario."
            )

        # Crear directorio de persistencia
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        # Inicializar embeddings según el proveedor
        logger.info(f"Inicializando embeddings con {self.provider} - Modelo: {self.embedding_model}")
        if self.provider != 'ollama':
            logger.info(f"API Key (primeros 20 chars): {self.api_key[:20] if self.api_key else 'None'}...")

        try:
            import os
            if self.provider == "google":
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                os.environ['GOOGLE_API_KEY'] = self.api_key
                self.embeddings = GoogleGenerativeAIEmbeddings(
                    model=self.embedding_model,
                    google_api_key=self.api_key
                )
            elif self.provider == "nvidia":
                from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
                os.environ['NVIDIA_API_KEY'] = self.api_key
                logger.info(f"Setting NVIDIA_API_KEY environment variable")
                self.embeddings = NVIDIAEmbeddings(
                    model=self.embedding_model,
                    nvidia_api_key=self.api_key
                )
            elif self.provider == "ollama":
                from langchain_ollama import OllamaEmbeddings
                logger.info(f"Inicializando Ollama embeddings locales")
                self.embeddings = OllamaEmbeddings(
                    model=self.embedding_model,
                    base_url="http://localhost:11434"
                )
            else:  # openai
                from langchain_openai import OpenAIEmbeddings
                os.environ['OPENAI_API_KEY'] = self.api_key
                self.embeddings = OpenAIEmbeddings(
                    model=self.embedding_model,
                    openai_api_key=self.api_key
                )
        except Exception as e:
            logger.error(f"Error inicializando embeddings: {e}")
            raise

        # Inicializar vectorstore (se crea/carga en build)
        self.vectorstore: Optional[Chroma] = None

    def build(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """
        Construye o actualiza el índice desde los registros.

        Args:
            force_rebuild: Si True, reconstruye el índice desde cero

        Returns:
            Diccionario con estadísticas de indexación
        """
        logger.info(f"Iniciando construcción del índice desde {self.records_dir}")
        start_time = datetime.now()

        stats = {
            "total_records": 0,
            "total_chunks": 0,
            "total_documents": 0,
            "errors": 0,
            "provider": self.provider,
            "embedding_model": self.embedding_model,
            "start_time": start_time.isoformat(),
        }

        # Cargar registros JSON
        json_files = list(self.records_dir.glob("*.json"))
        stats["total_records"] = len(json_files)

        if stats["total_records"] == 0:
            logger.warning(f"No se encontraron registros JSON en {self.records_dir}")
            return stats

        logger.info(f"Encontrados {stats['total_records']} registros")

        # Convertir registros a chunks y luego a documentos
        all_documents: List[Document] = []

        for json_file in json_files:
            try:
                # Leer registro
                with open(json_file, 'r', encoding='utf-8') as f:
                    record = json.load(f)

                # Chunkear registro
                chunks = chunk_eforms_record(record)
                stats["total_chunks"] += len(chunks)

                # Convertir chunks a Documents de LangChain
                documents = self._chunks_to_documents(chunks)
                all_documents.extend(documents)

                logger.debug(f"Procesado {json_file.name}: {len(chunks)} chunks")

            except Exception as e:
                logger.error(f"Error procesando {json_file.name}: {e}")
                stats["errors"] += 1

        stats["total_documents"] = len(all_documents)
        logger.info(f"Generados {stats['total_documents']} documentos para indexar")

        # Crear o actualizar vectorstore
        if force_rebuild or self.vectorstore is None:
            logger.info("Creando nuevo índice ChromaDB...")
            self.vectorstore = Chroma.from_documents(
                documents=all_documents,
                embedding=self.embeddings,
                collection_name=self.collection_name,
                persist_directory=self.persist_directory
            )
            logger.info("✓ Índice creado y persistido")
        else:
            logger.info("Actualizando índice existente...")
            # ChromaDB permite añadir documentos incrementalmente
            self.vectorstore.add_documents(all_documents)
            logger.info("✓ Índice actualizado")

        # Estadísticas finales
        end_time = datetime.now()
        stats["end_time"] = end_time.isoformat()
        stats["elapsed_seconds"] = (end_time - start_time).total_seconds()

        self._print_stats(stats)
        return stats

    def load_existing(self) -> bool:
        """
        Carga un índice existente desde disco.

        Returns:
            True si se cargó correctamente, False si no existe
        """
        try:
            logger.info(f"Cargando índice existente desde {self.persist_directory}")
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )

            # Verificar que el índice tenga contenido
            collection = self.vectorstore._collection
            count = collection.count()

            if count > 0:
                logger.info(f"✓ Índice cargado: {count} documentos")
                return True
            else:
                logger.warning("El índice está vacío")
                return False

        except Exception as e:
            logger.warning(f"No se pudo cargar índice existente: {e}")
            return False

    def get_vectorstore(self) -> Chroma:
        """
        Obtiene el vectorstore (carga si existe, lanza error si no).

        IMPORTANTE: Este método SOLO CARGA índices existentes, NO construye nuevos.
        Para indexar licitaciones, usa la UI de Django en /licitaciones/vectorizacion/

        Returns:
            Instancia de Chroma vectorstore

        Raises:
            RuntimeError: Si el índice no existe o está vacío
        """
        if self.vectorstore is None:
            if not self.load_existing():
                # NO intentar construir automáticamente desde data/records/
                # En su lugar, lanzar un error claro indicando qué hacer
                raise RuntimeError(
                    f"❌ El índice vectorial no existe o está vacío.\n\n"
                    f"📁 Ubicación esperada: {self.persist_directory}\n"
                    f"📦 Colección: {self.collection_name}\n\n"
                    f"🔧 SOLUCIÓN:\n"
                    f"1. Ve a http://localhost:8001/licitaciones/obtener/\n"
                    f"2. Descarga algunas licitaciones desde TED\n"
                    f"3. Ve a http://localhost:8001/licitaciones/vectorizacion/\n"
                    f"4. Haz clic en 'Indexar Todas las Licitaciones'\n"
                    f"5. Espera a que termine la indexación\n\n"
                    f"Después de indexar, el chat podrá consultar documentos."
                )
        return self.vectorstore

    def _chunks_to_documents(self, chunks: List[Chunk]) -> List[Document]:
        """
        Convierte chunks a documentos de LangChain con metadatos.

        Args:
            chunks: Lista de objetos Chunk

        Returns:
            Lista de Documents para indexar
        """
        documents = []

        for chunk in chunks:
            # Crear metadatos estructurados
            metadata = {
                "chunk_id": chunk.chunk_id,
                "ojs_notice_id": chunk.ojs_notice_id,
                "section": chunk.section,
                "source_path": chunk.source_path,
                "buyer_name": chunk.buyer_name,
                "publication_date": chunk.publication_date,
                "xpath_section": chunk.xpath_section or "",
                "chunk_index": chunk.chunk_index,

                # Metadatos para filtros (como strings para ChromaDB)
                "cpv_codes": ",".join(chunk.cpv_codes),
                "nuts_regions": ",".join(chunk.nuts_regions),
                "contract_type": chunk.contract_type or "",
                "procedure_type": chunk.procedure_type or "",
            }

            # Añadir metadatos opcionales
            if chunk.budget_eur is not None:
                metadata["budget_eur"] = chunk.budget_eur

            if chunk.tender_deadline_date:
                metadata["tender_deadline_date"] = chunk.tender_deadline_date

            # ✅ AÑADIR: Extraer campos de contacto del objeto Chunk
            # Si chunking.py los incluyó, ahora se indexarán en ChromaDB
            if hasattr(chunk, 'contact_email') and chunk.contact_email:
                metadata["contact_email"] = chunk.contact_email

            if hasattr(chunk, 'contact_phone') and chunk.contact_phone:
                metadata["contact_phone"] = chunk.contact_phone

            if hasattr(chunk, 'contact_url') and chunk.contact_url:
                metadata["contact_url"] = chunk.contact_url

            if hasattr(chunk, 'contact_fax') and chunk.contact_fax:
                metadata["contact_fax"] = chunk.contact_fax

            # Crear documento
            doc = Document(
                page_content=chunk.text,
                metadata=metadata
            )
            documents.append(doc)

        return documents

    def _print_stats(self, stats: Dict[str, Any]):
        """Imprime estadísticas de indexación."""
        print("\n" + "=" * 60)
        print("RESUMEN DE INDEXACIÓN")
        print("=" * 60)
        print(f"Proveedor:                {stats['provider'].upper()}")
        print(f"Modelo de embeddings:     {stats['embedding_model']}")
        print(f"Registros procesados:     {stats['total_records']}")
        print(f"Chunks generados:         {stats['total_chunks']}")
        print(f"Documentos indexados:     {stats['total_documents']}")
        print(f"Errores:                  {stats['errors']}")
        print(f"Tiempo transcurrido:      {stats['elapsed_seconds']:.2f}s")

        if stats['total_documents'] > 0:
            avg_time = stats['elapsed_seconds'] / stats['total_documents']
            print(f"Tiempo promedio/doc:      {avg_time:.4f}s")

        print("=" * 60 + "\n")


def build_index(
    records_dir: Optional[Path] = None,
    force_rebuild: bool = False
) -> Dict[str, Any]:
    """
    Función de conveniencia para construir el índice.

    Args:
        records_dir: Directorio con registros JSON
        force_rebuild: Reconstruir índice desde cero

    Returns:
        Estadísticas de indexación
    """
    builder = IndexBuilder(records_dir=records_dir)
    return builder.build(force_rebuild=force_rebuild)


def get_vectorstore(provider: str = None, api_key: str = None, embedding_model: str = None) -> Chroma:
    """
    Función de conveniencia para obtener el vectorstore.
    SOLO CARGA índices existentes, NO construye nuevos.

    IMPORTANTE: Para indexar licitaciones en Django, usa la UI en /licitaciones/vectorizacion/

    Args:
        provider: Provider name ('google', 'openai', 'nvidia', 'ollama'). If None, uses config default.
        api_key: API key for the provider. If None, uses config default (not needed for ollama).
        embedding_model: Model name. If None, uses config default.

    Returns:
        Instancia de Chroma vectorstore

    Raises:
        RuntimeError: Si el índice no existe o está vacío
    """
    builder = IndexBuilder(provider=provider, api_key=api_key, embedding_model=embedding_model)
    return builder.get_vectorstore()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Construye índice vectorial híbrido desde registros eForms"
    )
    parser.add_argument(
        "--records-dir",
        type=Path,
        default=None,
        help="Directorio con registros JSON (por defecto: config.RECORDS_DIR)"
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Reconstruir índice desde cero (elimina índice existente)"
    )

    args = parser.parse_args()

    # Construir índice
    try:
        stats = build_index(
            records_dir=args.records_dir,
            force_rebuild=args.force_rebuild
        )

        # Salir con código de error si hubo fallos
        if stats["errors"] > 0:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
