"""
Service for managing vectorization and indexing of tenders in ChromaDB
Integrates with agent_ia_core modules
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from django.conf import settings
from .models import Tender

# Add agent_ia_core to Python path
agent_ia_path = os.path.join(settings.BASE_DIR, 'agent_ia_core')
if agent_ia_path not in sys.path:
    sys.path.insert(0, agent_ia_path)


class VectorizationService:
    """
    Service for vectorizing and indexing tenders in ChromaDB
    Uses agent_ia_core modules: ingest.py, index_build.py, chunking.py
    """

    def __init__(self, user=None):
        """
        Initialize vectorization service

        Args:
            user: Django User instance with llm_api_key and llm_provider (optional)
        """
        self.user = user
        self.api_key = user.llm_api_key if user else None
        self.provider = user.llm_provider if user else 'gemini'

    def get_vectorstore_status(self) -> Dict[str, Any]:
        """
        Get current status of the ChromaDB vectorstore

        Returns:
            Dict with:
                - is_initialized: bool
                - num_documents: int
                - num_chunks: int (estimated)
                - collection_name: str
                - persist_directory: str
                - last_indexed: datetime or None
        """
        try:
            from agent_ia_core import config
            from agent_ia_core.retriever import create_retriever
            import chromadb

            # Get ChromaDB configuration (usar la misma ubicación que agent_ia_core)
            persist_dir = getattr(config, 'CHROMA_PERSIST_DIRECTORY', str(config.INDEX_DIR / 'chroma'))
            collection_name = getattr(config, 'CHROMA_COLLECTION_NAME', 'eforms_notices')

            # Try to connect to ChromaDB
            try:
                client = chromadb.PersistentClient(path=persist_dir)
                collection = client.get_collection(name=collection_name)

                # Get collection stats
                count = collection.count()

                return {
                    'is_initialized': True,
                    'num_documents': count,
                    'num_chunks': count,  # Each chunk is a document in ChromaDB
                    'collection_name': collection_name,
                    'persist_directory': str(Path(persist_dir).absolute()),
                    'status': 'ready',
                    'message': f'Vectorstore inicializado con {count} chunks'
                }

            except Exception as e:
                # Collection doesn't exist or other error
                return {
                    'is_initialized': False,
                    'num_documents': 0,
                    'num_chunks': 0,
                    'collection_name': collection_name,
                    'persist_directory': str(Path(persist_dir).absolute()),
                    'status': 'not_initialized',
                    'message': 'Vectorstore no inicializado. Necesitas indexar licitaciones primero.',
                    'error': str(e)
                }

        except ImportError as e:
            return {
                'is_initialized': False,
                'num_documents': 0,
                'num_chunks': 0,
                'status': 'error',
                'message': f'Error importando módulos: {str(e)}',
                'error': str(e)
            }

    def index_all_tenders(self, progress_callback=None) -> Dict[str, Any]:
        """
        Index all tenders from the database into ChromaDB

        Args:
            progress_callback: Optional callback function(data: dict) for progress updates

        Returns:
            Dict with indexing results
        """
        try:
            from agent_ia_core import config
            from agent_ia_core.chunking import chunk_eforms_record
            from core.llm_providers import LLMProviderFactory
            import chromadb

            # Validate API key
            if not self.api_key:
                provider_info = LLMProviderFactory.get_provider_info(self.provider)
                provider_name = provider_info.get('name', self.provider)
                return {
                    'success': False,
                    'error': f'No API key configured. Please set your {provider_name} API key in your profile.'
                }

            # Get all tenders with XMLs
            tenders = Tender.objects.exclude(xml_content='').exclude(xml_content__isnull=True)
            total_tenders = tenders.count()

            if total_tenders == 0:
                return {
                    'success': False,
                    'error': 'No hay licitaciones con XMLs para indexar. Descarga algunas primero.'
                }

            if progress_callback:
                progress_callback({
                    'type': 'start',
                    'total': total_tenders,
                    'message': f'Iniciando indexación de {total_tenders} licitaciones...'
                })

            # Get ChromaDB configuration (usar la misma ubicación que agent_ia_core)
            persist_dir = getattr(config, 'CHROMA_PERSIST_DIRECTORY', str(config.INDEX_DIR / 'chroma'))
            collection_name = getattr(config, 'CHROMA_COLLECTION_NAME', 'eforms_notices')

            # Create ChromaDB client and collection
            client = chromadb.PersistentClient(path=persist_dir)

            # Delete existing collection if it exists
            try:
                client.delete_collection(name=collection_name)
                if progress_callback:
                    progress_callback({
                        'type': 'info',
                        'message': 'Colección anterior eliminada. Creando nueva...'
                    })
            except:
                pass

            # Create embeddings using the selected provider
            embeddings = LLMProviderFactory.get_embeddings(
                provider=self.provider,
                api_key=self.api_key
            )

            # Create new collection
            collection = client.create_collection(
                name=collection_name,
                metadata={"description": "Licitaciones eForms indexadas"}
            )

            indexed_count = 0
            error_count = 0
            total_chunks = 0

            # Index each tender
            for idx, tender in enumerate(tenders, 1):
                try:
                    if progress_callback:
                        progress_callback({
                            'type': 'progress',
                            'current': idx,
                            'total': total_tenders,
                            'tender_id': tender.ojs_notice_id,
                            'message': f'Indexando {tender.ojs_notice_id}...'
                        })

                    # Parse and chunk the XML
                    from agent_ia_core.xml_parser import EFormsXMLParser
                    from lxml import etree
                    import io

                    # Parse XML content from string
                    parser_instance = EFormsXMLParser()
                    tree = etree.parse(io.BytesIO(tender.xml_content.encode('utf-8')))
                    root = tree.getroot()

                    # Extract fields using parser methods
                    parsed_data = {
                        "REQUIRED": parser_instance._extract_required_fields(root, Path(f"{tender.ojs_notice_id}.xml")),
                        "OPTIONAL": parser_instance._extract_optional_fields(root),
                        "META": parser_instance._extract_meta_fields()
                    }

                    # Chunk the tender (returns list of Chunk dataclass objects)
                    chunks = chunk_eforms_record(parsed_data)

                    # Add chunks to collection
                    for chunk_idx, chunk in enumerate(chunks):
                        # Truncate text if needed (NVIDIA has 512 token limit ≈ 2000 chars)
                        chunk_text = chunk.text
                        if self.provider == 'nvidia' and len(chunk_text) > 2000:
                            chunk_text = chunk_text[:2000] + "..."

                        # Generate embedding
                        try:
                            embedding = embeddings.embed_query(chunk_text)
                        except Exception as embed_error:
                            # If still too long, truncate more aggressively
                            if "token" in str(embed_error).lower() or "length" in str(embed_error).lower():
                                chunk_text = chunk_text[:1500] + "..."
                                embedding = embeddings.embed_query(chunk_text)
                            else:
                                raise

                        # Add to collection
                        collection.add(
                            ids=[chunk.chunk_id],
                            embeddings=[embedding],
                            documents=[chunk_text],
                            metadatas=[{
                                'ojs_notice_id': chunk.ojs_notice_id,
                                'section': chunk.section,
                                'chunk_index': chunk.chunk_index,
                                'source_path': chunk.source_path,
                                'buyer_name': chunk.buyer_name,
                                'cpv_codes': ','.join(chunk.cpv_codes),
                                'nuts_regions': ','.join(chunk.nuts_regions),
                                'publication_date': chunk.publication_date
                            }]
                        )

                    total_chunks += len(chunks)
                    indexed_count += 1

                    if progress_callback:
                        progress_callback({
                            'type': 'indexed',
                            'tender_id': tender.ojs_notice_id,
                            'chunks': len(chunks),
                            'message': f'✓ {tender.ojs_notice_id} indexado ({len(chunks)} chunks)'
                        })

                except Exception as e:
                    error_count += 1
                    if progress_callback:
                        progress_callback({
                            'type': 'error',
                            'tender_id': tender.ojs_notice_id,
                            'error': str(e),
                            'message': f'✗ Error en {tender.ojs_notice_id}: {str(e)}'
                        })

            if progress_callback:
                progress_callback({
                    'type': 'complete',
                    'indexed': indexed_count,
                    'errors': error_count,
                    'total_chunks': total_chunks,
                    'message': f'Indexación completada: {indexed_count} licitaciones, {total_chunks} chunks'
                })

            return {
                'success': True,
                'indexed': indexed_count,
                'errors': error_count,
                'total_chunks': total_chunks,
                'total': total_tenders
            }

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()

            if progress_callback:
                progress_callback({
                    'type': 'fatal_error',
                    'error': str(e),
                    'message': f'Error fatal: {str(e)}'
                })

            return {
                'success': False,
                'error': str(e),
                'traceback': error_trace
            }

    def clear_vectorstore(self) -> Dict[str, Any]:
        """
        Clear the entire vectorstore (delete collection)

        Returns:
            Dict with operation results
        """
        try:
            from agent_ia_core import config
            import chromadb

            persist_dir = getattr(config, 'CHROMA_PERSIST_DIR', './chroma_db')
            collection_name = getattr(config, 'CHROMA_COLLECTION_NAME', 'licitaciones')

            client = chromadb.PersistentClient(path=persist_dir)

            try:
                client.delete_collection(name=collection_name)
                return {
                    'success': True,
                    'message': f'Colección "{collection_name}" eliminada exitosamente'
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Error eliminando colección: {str(e)}'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def reindex_tender(self, ojs_notice_id: str) -> Dict[str, Any]:
        """
        Reindex a specific tender

        Args:
            ojs_notice_id: OJS notice ID of the tender to reindex

        Returns:
            Dict with operation results
        """
        try:
            tender = Tender.objects.get(ojs_notice_id=ojs_notice_id)

            if not tender.xml_content:
                return {
                    'success': False,
                    'error': f'Tender {ojs_notice_id} does not have XML content'
                }

            # Use the full indexing method with a filter
            # For now, just use the full index (can be optimized later)
            return {
                'success': True,
                'message': f'Use "Indexar Todo" to reindex. Individual reindexing not yet implemented.'
            }

        except Tender.DoesNotExist:
            return {
                'success': False,
                'error': f'Tender {ojs_notice_id} not found'
            }
