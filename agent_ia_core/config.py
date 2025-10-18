# -*- coding: utf-8 -*-
"""
Configuración centralizada del proyecto Agentic RAG eForms.
Define rutas, modelos, parámetros de recuperación y filtros por defecto.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# ================================================
# RUTAS DEL PROYECTO
# ================================================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
XML_DIR = DATA_DIR / "xml"
RECORDS_DIR = DATA_DIR / "records"
INDEX_DIR = DATA_DIR / "index"
SCHEMA_DIR = PROJECT_ROOT / "schema"
EVAL_DIR = PROJECT_ROOT / "eval"
LOGS_DIR = PROJECT_ROOT / "logs"

# ================================================
# CREDENCIALES Y API KEYS
# ================================================
# IMPORTANTE: Las API keys se configuran por usuario en su perfil
# No se usan API keys globales del .env
# Cada usuario debe tener su propia API key configurada en su perfil

# ================================================
# CONFIGURACIÓN DE PROVEEDOR DE LLM/EMBEDDINGS
# ================================================
# Proveedor por defecto (se usa solo para valores por defecto de modelos)
# El proveedor real se obtiene del perfil del usuario
LLM_PROVIDER = "google"  # Valor por defecto, no se usa directamente

# ================================================
# CONFIGURACIÓN DE MODELOS - OPENAI
# ================================================
OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
OPENAI_EMBEDDING_DIMENSIONS = 3072
OPENAI_LLM_MODEL = "gpt-4o-mini"

# ================================================
# CONFIGURACIÓN DE MODELOS - GOOGLE GEMINI
# ================================================
GOOGLE_EMBEDDING_MODEL = "models/text-embedding-004"
GOOGLE_EMBEDDING_DIMENSIONS = 768
GOOGLE_LLM_MODEL = "gemini-2.5-flash"  # o "gemini-2.5-pro" para mayor calidad

# ================================================
# CONFIGURACIÓN DE MODELOS - NVIDIA NIM
# ================================================
NVIDIA_EMBEDDING_MODEL = "nvidia/nv-embedqa-e5-v5"
NVIDIA_EMBEDDING_DIMENSIONS = 1024
NVIDIA_LLM_MODEL = "meta/llama-3.1-8b-instruct"

# ================================================
# CONFIGURACIÓN ACTIVA POR DEFECTO
# ================================================
# Valores por defecto - el agente recibe el proveedor y API key del usuario
EMBEDDING_MODEL = GOOGLE_EMBEDDING_MODEL
EMBEDDING_DIMENSIONS = GOOGLE_EMBEDDING_DIMENSIONS
LLM_MODEL = GOOGLE_LLM_MODEL

# Temperatura para respuestas (0.0 = determinista, 1.0 = creativo)
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.3'))

# Longitud de contexto para Ollama (tokens)
OLLAMA_CONTEXT_LENGTH = int(os.getenv('OLLAMA_CONTEXT_LENGTH', '2048'))

# Timeout para llamadas al LLM (segundos)
LLM_TIMEOUT = int(os.getenv('LLM_TIMEOUT', '120'))

# ================================================
# PARÁMETROS DE RECUPERACIÓN (RETRIEVER)
# ================================================
# Número de chunks a recuperar (top-k)
DEFAULT_K = int(os.getenv('DEFAULT_K_RETRIEVE', '6'))

# Umbral de similitud mínima para considerar un chunk relevante
MIN_SIMILARITY_SCORE = float(os.getenv('MIN_SIMILARITY_SCORE', '0.5'))

# Re-ranking: aplicar un re-ranker después de la búsqueda vectorial
USE_RERANKING = False
RERANK_TOP_N = 10  # si se usa re-ranking, primero traer más candidatos

# ================================================
# FILTROS PÚBLICOS POR DEFECTO
# ================================================
# Estos filtros se aplicarán por defecto en las consultas
PUBLIC_FILTERS = {
    "country": "ESP",           # España
    "cpv_prefix": "7226",       # Servicios de software (CPV 7226*)
    "date_from": "2024-09-15",  # Fecha desde (publicación)
    "date_to": "2025-10-14",    # Fecha hasta (publicación)
}

# ================================================
# CONFIGURACIÓN DE CHUNKING
# ================================================
# Tamaño máximo de caracteres por chunk de descripción larga
MAX_CHUNK_SIZE = 1000

# Overlap entre chunks consecutivos (si se divide una descripción larga)
CHUNK_OVERLAP = 100

# Secciones que se crearán como chunks individuales
CHUNK_SECTIONS = [
    "title",
    "description",
    "lot",           # habrá un chunk por lote (lot_1, lot_2, etc.)
    "award_criteria",
    "budget",
    "deadline",
    "eligibility",
]

# ================================================
# CONFIGURACIÓN DE INDEXACIÓN
# ================================================
# Tipo de índice vectorial: "faiss", "chromadb" o "pgvector"
INDEX_TYPE = "chromadb"

# Configuración para ChromaDB
CHROMA_COLLECTION_NAME = os.getenv('CHROMA_COLLECTION_NAME', 'eforms_chunks')
CHROMA_PERSIST_DIRECTORY = os.getenv('CHROMA_PERSIST_DIRECTORY', str(INDEX_DIR / "chroma"))

# Configuración para FAISS (si se usa)
FAISS_INDEX_PATH = str(INDEX_DIR / "faiss_index.bin")
FAISS_METADATA_PATH = str(INDEX_DIR / "faiss_metadata.json")

# ================================================
# CONFIGURACIÓN DE VERIFICACIÓN (XmlLookup)
# ================================================
# Campos críticos que requieren verificación directa del XML
CRITICAL_FIELDS = [
    "budget_eur",
    "tender_deadline_date",
    "tender_deadline_time",
    "award_criteria[].weight",
]

# ================================================
# CONFIGURACIÓN DEL AGENTE
# ================================================
# Nodos del grafo LangGraph
AGENT_NODES = ["route", "retrieve", "grade", "verify", "answer"]

# Activar/desactivar nodo de grading (validación de relevancia del contexto)
USE_GRADING = os.getenv('USE_GRADING', 'True').lower() in ('true', '1', 'yes')

# Activar/desactivar nodo de verificación XML (XmlLookup para campos críticos)
USE_XML_VERIFICATION = os.getenv('USE_XML_VERIFICATION', 'True').lower() in ('true', '1', 'yes')

# Número máximo de iteraciones del agente (para evitar loops)
MAX_AGENT_ITERATIONS = int(os.getenv('MAX_AGENT_ITERATIONS', '5'))

# ================================================
# CONFIGURACIÓN DE LOGGING Y AUDITORÍA
# ================================================
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = str(PROJECT_ROOT / "logs" / "rag_system.log")

# Guardar auditoría de consultas (pregunta, respuesta, citas, latencia)
ENABLE_AUDIT = True
AUDIT_FILE = str(PROJECT_ROOT / "logs" / "audit.jsonl")

# ================================================
# CONFIGURACIÓN DE EVALUACIÓN
# ================================================
# Archivo de ground truth para evaluación del retriever
GT_QUERIES_FILE = str(EVAL_DIR / "gt_queries.jsonl")

# Valores de k para evaluar Recall@k y Precision@k
EVAL_K_VALUES = [3, 5, 6, 8, 10]

# ================================================
# NAMESPACES XML eForms (UBL 2.3)
# ================================================
EFORMS_NAMESPACES = {
    "cn": "urn:oasis:names:specification:ubl:schema:xsd:ContractNotice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "efac": "http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1",
    "efbc": "http://data.europa.eu/p27/eforms-ubl-extension-basic-components/1",
    "efext": "http://data.europa.eu/p27/eforms-ubl-extensions/1",
}

# ================================================
# CONFIGURACIÓN DE DESCARGA (TED API)
# ================================================
# Ya está implementado en descarga_xml.py, pero podemos centralizar parámetros
TED_SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"
TED_NOTICE_URL_TEMPLATE = "https://ted.europa.eu/en/notice/{notice_id}/xml"

# Pausa entre requests (segundos)
DOWNLOAD_DELAY = 1.2

# Límite de descargas por ejecución
MAX_DOWNLOADS = 50

# Timeout para requests HTTP (segundos)
HTTP_TIMEOUT = 60

# ================================================
# IDIOMA Y LOCALIZACIÓN
# ================================================
DEFAULT_LANGUAGE = "es"  # español para prompts y respuestas
SUPPORTED_LANGUAGES = ["es", "en", "fr", "de", "it", "pt"]

# ================================================
# VALIDACIÓN Y TESTING
# ================================================
# Modo de validación estricta (lanza excepciones si faltan campos REQUIRED)
STRICT_VALIDATION = True

# Ejecutar smoke tests automáticamente después de ingesta/indexación
AUTO_RUN_TESTS = False
