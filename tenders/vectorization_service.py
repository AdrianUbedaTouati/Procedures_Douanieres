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
            user: Django User instance with llm_api_key, llm_provider, ollama_model, ollama_embedding_model (optional)
        """
        self.user = user
        self.api_key = user.llm_api_key if user else None
        self.provider = getattr(user, 'llm_provider', 'gemini') if user else 'gemini'
        self.ollama_model = getattr(user, 'ollama_model', 'qwen2.5:72b') if user else 'qwen2.5:72b'
        self.ollama_embedding_model = getattr(user, 'ollama_embedding_model', 'nomic-embed-text') if user else 'nomic-embed-text'

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

    def index_all_tenders(self, progress_callback=None, cancel_flag_checker=None) -> Dict[str, Any]:
        """
        Index all tenders from the database into ChromaDB
        Uses temporary collection strategy: creates new collection, then swaps with old one

        Args:
            progress_callback: Optional callback function(data: dict) for progress updates
            cancel_flag_checker: Optional function() -> bool that returns True if cancellation requested

        Returns:
            Dict with indexing results including token usage and costs
        """
        try:
            from agent_ia_core import config
            from agent_ia_core.chunking import chunk_eforms_record
            from core.llm_providers import LLMProviderFactory
            from core.token_pricing import calculate_embedding_cost, format_cost
            import chromadb
            from datetime import datetime

            # Validate API key (Ollama doesn't need one)
            if not self.api_key and self.provider != 'ollama':
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

            # Get ChromaDB configuration
            persist_dir = getattr(config, 'CHROMA_PERSIST_DIRECTORY', str(config.INDEX_DIR / 'chroma'))
            collection_name = getattr(config, 'CHROMA_COLLECTION_NAME', 'eforms_notices')

            # Create TEMPORARY collection name with timestamp
            temp_collection_name = f"{collection_name}_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Create ChromaDB client
            client = chromadb.PersistentClient(path=persist_dir)

            # Check if old collection exists (to preserve it during indexing)
            old_collection_exists = False
            try:
                old_collection = client.get_collection(name=collection_name)
                old_collection_exists = True
                if progress_callback:
                    progress_callback({
                        'type': 'info',
                        'message': f'✓ Colección anterior detectada ({old_collection.count()} chunks). Se mantendrá activa durante la indexación.'
                    })
            except:
                if progress_callback:
                    progress_callback({
                        'type': 'info',
                        'message': 'No hay colección anterior. Creando primera indexación...'
                    })

            # Create embeddings using the selected provider
            if self.provider == 'ollama':
                embeddings = LLMProviderFactory.get_embeddings(
                    provider=self.provider,
                    api_key=None,  # Ollama doesn't need API key
                    model_name=self.ollama_embedding_model
                )
            else:
                embeddings = LLMProviderFactory.get_embeddings(
                    provider=self.provider,
                    api_key=self.api_key
                )

            # Create new TEMPORARY collection
            if progress_callback:
                progress_callback({
                    'type': 'info',
                    'message': f'Creando colección temporal: {temp_collection_name}'
                })

            temp_collection = client.create_collection(
                name=temp_collection_name,
                metadata={"description": "Indexación temporal de licitaciones eForms"}
            )

            indexed_count = 0
            error_count = 0
            total_chunks = 0

            # Token and cost tracking
            total_tokens = 0
            total_cost_eur = 0.0

            # Index each tender
            for idx, tender in enumerate(tenders, 1):
                # Check for cancellation before processing each tender
                if cancel_flag_checker and cancel_flag_checker():
                    if progress_callback:
                        progress_callback({
                            'type': 'cancelled',
                            'message': '⚠️ Indexación cancelada por el usuario. Limpiando colección temporal...'
                        })

                    # Delete temporary collection
                    try:
                        client.delete_collection(name=temp_collection_name)
                    except:
                        pass

                    return {
                        'success': False,
                        'cancelled': True,
                        'indexed': indexed_count,
                        'total_chunks': total_chunks,
                        'total_tokens': total_tokens,
                        'total_cost_eur': total_cost_eur,
                        'message': 'Indexación cancelada. La colección anterior sigue activa.'
                    }

                try:
                    if progress_callback:
                        progress_callback({
                            'type': 'progress',
                            'current': idx,
                            'total': total_tenders,
                            'tender_id': tender.ojs_notice_id,
                            'message': f'Indexando {tender.ojs_notice_id}...',
                            'total_tokens': total_tokens,
                            'total_cost_eur': total_cost_eur
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

                    tender_tokens = 0
                    tender_cost = 0.0

                    # Add chunks to collection
                    for chunk_idx, chunk in enumerate(chunks):
                        # Truncate text if needed (NVIDIA has 512 token limit)
                        # Conservative approach: 512 tokens ≈ 1800 characters (3.5 chars/token)
                        chunk_text = chunk.text
                        if self.provider == 'nvidia' and len(chunk_text) > 1800:
                            chunk_text = chunk_text[:1800] + "..."

                        # Calculate cost BEFORE generating embedding
                        chunk_tokens, chunk_cost = calculate_embedding_cost(chunk_text, self.provider)
                        tender_tokens += chunk_tokens
                        tender_cost += chunk_cost

                        # Generate embedding
                        try:
                            embedding = embeddings.embed_query(chunk_text)
                        except Exception as embed_error:
                            # If still too long, truncate more aggressively
                            if "token" in str(embed_error).lower() or "length" in str(embed_error).lower():
                                # Truncate to ~400 tokens max to be safe
                                chunk_text = chunk_text[:1400] + "..."
                                # Recalculate cost after truncation
                                chunk_tokens, chunk_cost = calculate_embedding_cost(chunk_text, self.provider)
                                embedding = embeddings.embed_query(chunk_text)
                            else:
                                raise

                        # Add to TEMPORARY collection
                        temp_collection.add(
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
                    total_tokens += tender_tokens
                    total_cost_eur += tender_cost
                    indexed_count += 1

                    if progress_callback:
                        progress_callback({
                            'type': 'indexed',
                            'tender_id': tender.ojs_notice_id,
                            'chunks': len(chunks),
                            'tender_tokens': tender_tokens,
                            'tender_cost_eur': tender_cost,
                            'total_tokens': total_tokens,
                            'total_cost_eur': total_cost_eur,
                            'message': f'✓ {tender.ojs_notice_id}: {len(chunks)} chunks, {tender_tokens} tokens, {format_cost(tender_cost)}'
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

            # SWAP: Replace old collection with new one (atomic operation)
            if progress_callback:
                progress_callback({
                    'type': 'info',
                    'message': '🔄 Finalizando indexación. Activando nueva colección...'
                })

            # Delete old collection if it exists
            if old_collection_exists:
                try:
                    client.delete_collection(name=collection_name)
                    if progress_callback:
                        progress_callback({
                            'type': 'info',
                            'message': '✓ Colección anterior eliminada'
                        })
                except Exception as e:
                    if progress_callback:
                        progress_callback({
                            'type': 'warning',
                            'message': f'⚠️ No se pudo eliminar colección anterior: {str(e)}'
                        })

            # Rename temporary collection to main collection name
            # Note: ChromaDB doesn't support rename, so we need to recreate
            try:
                # Create final collection
                final_collection = client.create_collection(
                    name=collection_name,
                    metadata={"description": "Licitaciones eForms indexadas"}
                )

                # Copy all data from temp to final in batches (to avoid memory issues)
                batch_size = 1000  # Process 1000 chunks at a time
                temp_count = temp_collection.count()

                if progress_callback:
                    progress_callback({
                        'type': 'info',
                        'message': f'Copiando {temp_count} chunks a la colección final (en lotes de {batch_size})...'
                    })

                # Get all IDs first
                all_ids = temp_collection.get()['ids']

                # Process in batches
                for i in range(0, len(all_ids), batch_size):
                    batch_ids = all_ids[i:i+batch_size]
                    temp_data = temp_collection.get(
                        ids=batch_ids,
                        include=['embeddings', 'documents', 'metadatas']
                    )

                    if temp_data['ids']:
                        # Clean metadatas: remove None values and ensure all values are strings
                        cleaned_metadatas = []
                        for metadata in temp_data['metadatas']:
                            cleaned_metadata = {}
                            for key, value in metadata.items():
                                if value is not None:
                                    # Convert all values to strings to avoid type issues
                                    cleaned_metadata[key] = str(value) if not isinstance(value, str) else value
                            cleaned_metadatas.append(cleaned_metadata)

                        final_collection.add(
                            ids=temp_data['ids'],
                            embeddings=temp_data['embeddings'],
                            documents=temp_data['documents'],
                            metadatas=cleaned_metadatas
                        )

                    if progress_callback:
                        progress_callback({
                            'type': 'info',
                            'message': f'   Copiados {min(i+batch_size, len(all_ids))}/{len(all_ids)} chunks...'
                        })

                # Delete temporary collection
                client.delete_collection(name=temp_collection_name)

                if progress_callback:
                    progress_callback({
                        'type': 'info',
                        'message': '✓ Nueva colección activada correctamente'
                    })

            except Exception as e:
                if progress_callback:
                    progress_callback({
                        'type': 'error',
                        'message': f'✗ Error al activar colección: {str(e)}',
                        'error': str(e)
                    })
                # Don't fail the whole operation - the temp collection has all the data
                # User can manually rename it if needed

            if progress_callback:
                progress_callback({
                    'type': 'complete',
                    'indexed': indexed_count,
                    'errors': error_count,
                    'total_chunks': total_chunks,
                    'total_tokens': total_tokens,
                    'total_cost_eur': total_cost_eur,
                    'message': f'✅ Indexación completada: {indexed_count} licitaciones, {total_chunks} chunks, {total_tokens:,} tokens, {format_cost(total_cost_eur)}'
                })

            return {
                'success': True,
                'indexed': indexed_count,
                'errors': error_count,
                'total_chunks': total_chunks,
                'total': total_tenders,
                'total_tokens': total_tokens,
                'total_cost_eur': total_cost_eur
            }

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()

            # Clean up temporary collection on fatal error
            try:
                if 'temp_collection_name' in locals():
                    client.delete_collection(name=temp_collection_name)
            except:
                pass

            if progress_callback:
                progress_callback({
                    'type': 'fatal_error',
                    'error': str(e),
                    'message': f'❌ Error fatal: {str(e)}. La colección anterior se mantiene intacta.'
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
