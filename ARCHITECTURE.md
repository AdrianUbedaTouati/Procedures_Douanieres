# TenderAI Platform - Arquitectura del Sistema

## Índice
1. [Visión General](#visión-general)
2. [Stack Tecnológico](#stack-tecnológico)
3. [Arquitectura de API Keys](#arquitectura-de-api-keys)
4. [Aplicaciones Django](#aplicaciones-django)
5. [Módulo Agent_IA Core](#módulo-agent_ia-core)
6. [Flujo de Datos Principal](#flujo-de-datos-principal)
7. [Sistema de Chat RAG](#sistema-de-chat-rag)
8. [Vectorización y ChromaDB](#vectorización-y-chromadb)
9. [Modelos de Datos](#modelos-de-datos)
10. [Integraciones Externas](#integraciones-externas)

---

## Visión General

**TenderAI Platform** es una plataforma web completa para el análisis inteligente de licitaciones públicas que integra:

- Sistema de autenticación y gestión de usuarios
- Perfiles empresariales personalizables
- Motor de recomendaciones con IA multicriteria
- Chat conversacional con RAG (Retrieval-Augmented Generation)
- Descarga automática desde TED API
- Vectorización y búsqueda semántica
- Soporte multi-proveedor LLM (Google Gemini, OpenAI, NVIDIA NIM)

### Principio Fundamental: API Keys por Usuario

**IMPORTANTE**: El sistema utiliza **exclusivamente API keys configuradas por cada usuario** en su perfil. No existen API keys globales en archivos `.env`. Cada usuario debe configurar su propia API key del proveedor LLM que desee usar (Google, OpenAI o NVIDIA).

---

## Stack Tecnológico

### Backend
- **Django 5.2.6**: Framework web principal
- **Python 3.12+**: Lenguaje de programación
- **SQLite/PostgreSQL**: Base de datos relacional
- **ChromaDB**: Base de datos vectorial para embeddings

### IA y Machine Learning
- **LangChain 0.3.14**: Framework para aplicaciones LLM
- **LangGraph 0.2.63**: Orquestación de agentes con grafos
- **Google Gemini 2.5 Flash**: LLM principal (via API del usuario)
- **OpenAI GPT-4**: Soporte alternativo
- **NVIDIA NIM**: Modelos open-source (Llama 3.1)

### Frontend
- **Bootstrap 5.3**: Framework CSS
- **HTMX**: Interactividad dinámica
- **JavaScript**: Lógica cliente

### APIs Externas
- **TED API**: Descarga de licitaciones europeas
- **Google Gemini API**: Generación de texto y embeddings
- **OpenAI API**: Alternativa LLM
- **NVIDIA API**: Modelos open-source

---

## Arquitectura de API Keys

### Diseño Actual (Usuario-Céntrico)

```
┌─────────────────────────────────────────────────────────────┐
│                     USUARIO (Base de Datos)                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ User Model                                            │   │
│  │  - username                                           │   │
│  │  - llm_provider: "gemini" | "openai" | "nvidia"      │   │
│  │  - llm_api_key: "AIzaSyC..." (API key del usuario)   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
                            ↓ API Key fluye desde el usuario
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   CHAT SERVICE (Django)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ChatAgentService(user)                               │   │
│  │   self.api_key = user.llm_api_key  ← De la DB       │   │
│  │   self.provider = user.llm_provider                  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
                            ↓ Pasa API key al agente
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  AGENT_IA CORE (LangGraph)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ EFormsRAGAgent(api_key, llm_provider)                │   │
│  │   self.api_key = api_key  ← REQUERIDO               │   │
│  │   self.llm = ChatNVIDIA(nvidia_api_key=api_key)      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
                            ↓ Usa misma API key para embeddings
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  RETRIEVER (ChromaDB)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ create_retriever(provider, api_key)                  │   │
│  │   embeddings = NVIDIAEmbeddings(                     │   │
│  │       nvidia_api_key=api_key  ← Mismo key del LLM   │   │
│  │   )                                                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Cambios Arquitectónicos (Octubre 2024)

**ANTES** (Sistema híbrido - eliminado):
```python
# ❌ ANTIGUO: Fallback a .env
API_KEY = os.getenv('GOOGLE_API_KEY')  # En config.py
api_key = user.llm_api_key or API_KEY  # Fallback
```

**AHORA** (Solo usuario - actual):
```python
# ✅ NUEVO: Solo API key del usuario
def __init__(self, api_key: str, llm_provider: str):
    if not api_key:
        raise ValueError("API key es requerida. Configura tu API key en tu perfil.")
    self.api_key = api_key
```

**Archivos Modificados**:
1. `agent_ia_core/agent_graph.py`: `api_key` es parámetro **requerido**
2. `chat/services.py`: Pasa `api_key=user.llm_api_key` directamente
3. `agent_ia_core/config.py`: Eliminadas todas las asignaciones de `API_KEY`
4. `agent_ia_core/index_build.py`: Eliminado import de `API_KEY`
5. `.env`: Eliminadas todas las líneas de API keys
6. `tenders/vectorization_service.py`: Eliminado `config.API_KEY = ...`

---

## Aplicaciones Django

### 1. **authentication**
Gestión completa de autenticación de usuarios.

**Funcionalidades**:
- Login/Logout
- Registro de usuarios
- Recuperación de contraseña
- Validación de emails

**Archivos clave**:
- `views.py`: Vistas de autenticación
- `forms.py`: Formularios de login/registro
- `templates/`: Templates de autenticación

### 2. **core**
Núcleo de la aplicación y configuración base.

**Funcionalidades**:
- Dashboard principal
- Perfil de usuario
- Configuración de API keys (llm_provider, llm_api_key)

**Archivos clave**:
- `views.py`: Vista home y perfil
- `models.py`: Extensión del modelo User

### 3. **company**
Gestión de perfiles empresariales.

**Funcionalidades**:
- Creación/edición de perfil empresarial
- 20+ campos configurables:
  - Datos básicos (nombre, CIF, sector)
  - Capacidades técnicas
  - Experiencia previa
  - Certificaciones
  - Recursos disponibles

**Archivos clave**:
- `models.py`: Modelo CompanyProfile
- `views.py`: CRUD de perfiles
- `forms.py`: Formulario de perfil

### 4. **tenders**
Gestión completa de licitaciones.

**Funcionalidades**:
- CRUD de licitaciones
- Descarga desde TED API
- Búsqueda y filtros avanzados
- Sistema de guardado (interesado, aplicado, ganado, perdido)
- Recomendaciones con IA multicriteria
- Vectorización para RAG

**Archivos clave**:
- `models.py`: Modelos Tender, SavedTender, TenderRecommendation
- `views.py`: Vistas de licitaciones
- `services/download_service.py`: Descarga desde TED
- `services/recommendation_service.py`: Motor de recomendaciones
- `vectorization_service.py`: Indexación en ChromaDB

**Sistema de Recomendaciones** (5 dimensiones):
1. **Compatibilidad técnica**: Match entre capacidades empresa y requisitos
2. **Experiencia previa**: Proyectos similares realizados
3. **Capacidad financiera**: Presupuesto vs capacidad empresa
4. **Ubicación geográfica**: Proximidad a la licitación
5. **Plazo**: Tiempo disponible vs complejidad

### 5. **chat**
Sistema de chat conversacional con RAG.

**Funcionalidades**:
- Sesiones de chat por usuario
- Integración con agent_graph (LangGraph)
- Historial de conversaciones
- Streaming de respuestas (futuro)

**Archivos clave**:
- `models.py`: ChatSession, ChatMessage
- `views.py`: API endpoints de chat
- `services.py`: ChatAgentService (integración con Agent_IA)

---

## Módulo Agent_IA Core

Módulo Python independiente que implementa el agente RAG usando LangGraph.

### Estructura
```
agent_ia_core/
├── agent_graph.py        # Grafo principal del agente
├── config.py             # Configuración (sin API keys)
├── index_build.py        # Construcción de índice ChromaDB
├── prompts.py            # Prompts del sistema
├── retriever.py          # Retriever semántico
├── llm_factory.py        # Factory para LLMs multi-proveedor
└── utils/
    ├── logging_config.py
    └── helpers.py
```

### Componentes Principales

#### 1. **EFormsRAGAgent** (`agent_graph.py`)

Agente principal que implementa el flujo RAG con LangGraph.

**Grafo de Estados**:
```
START → route → retrieve → grade → verify → answer → END
          ↑         ↓         ↓
          └─────────┴─────────┘
           (retry si no hay docs relevantes)
```

**Nodos**:
- `route`: Clasifica la pregunta (licitación vs general)
- `retrieve`: Busca documentos en ChromaDB
- `grade`: Evalúa relevancia de documentos (opcional)
- `verify`: Verifica hallucinations (opcional)
- `answer`: Genera respuesta final

**Parámetros**:
```python
EFormsRAGAgent(
    api_key: str,              # ← REQUERIDO (del usuario)
    llm_provider: str,         # ← REQUERIDO ("google"|"openai"|"nvidia")
    llm_model: str = None,     # Modelo específico
    temperature: float = 0.3,  # Creatividad
    k_retrieve: int = 6,       # Documentos a recuperar
    use_grading: bool = False, # Evaluación de relevancia
    use_verification: bool = False  # Verificación de hallucinations
)
```

**Estado Actual del Grading**:
- **Desactivado** (`use_grading=False`) por defecto
- **Razón**: NVIDIA LLM es muy estricto, marcaba 0/6 documentos como relevantes
- **Mejora implementada**: Lógica de decisión más permisiva (1 doc es suficiente, solo 1 retry)
- **Futuro**: Re-activar con prompts ajustados por proveedor

#### 2. **Retriever** (`retriever.py`)

Recupera documentos semánticamente similares desde ChromaDB.

**Flujo**:
```python
query → embeddings → ChromaDB search → top-k documentos
```

**Configuración por Proveedor**:
- **Google**: `text-embedding-004` (768D)
- **OpenAI**: `text-embedding-3-large` (3072D)
- **NVIDIA**: `nvidia/nv-embedqa-e5-v5` (1024D)

#### 3. **LLM Factory** (`llm_factory.py`)

Patrón Factory para instanciar LLMs según proveedor.

```python
class LLMProviderFactory:
    @staticmethod
    def get_chat_model(provider: str, api_key: str, model: str = None, temperature: float = 0.3):
        if provider == "google":
            return ChatGoogleGenerativeAI(
                model=model or "gemini-2.0-flash-exp",
                google_api_key=api_key,
                temperature=temperature
            )
        elif provider == "openai":
            return ChatOpenAI(
                model=model or "gpt-4o-mini",
                api_key=api_key,
                temperature=temperature
            )
        elif provider == "nvidia":
            return ChatNVIDIA(
                model=model or "meta/llama-3.1-8b-instruct",
                nvidia_api_key=api_key,
                temperature=temperature
            )
```

#### 4. **Index Builder** (`index_build.py`)

Construye el índice de ChromaDB a partir de XMLs de licitaciones.

**Proceso**:
1. Lee XMLs desde `data/records/`
2. Parsea con `RecordExtractor`
3. Chunking con `RecursiveCharacterTextSplitter`
4. Genera embeddings (usando API key del usuario)
5. Persiste en ChromaDB (`chroma_db/`)

**Configuración**:
```python
TenderIndexBuilder(
    api_key: str,              # API key del usuario
    provider: str = "nvidia",  # Proveedor de embeddings
    embedding_model: str = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
)
```

---

## Flujo de Datos Principal

### 1. Usuario configura API Key
```
Usuario → Perfil → Editar → llm_provider="nvidia" + llm_api_key="nvapi-xxx"
                                                    ↓
                                            Guardado en DB (User model)
```

### 2. Usuario envía pregunta al chat
```
Frontend → POST /chat/send/
              ↓
         ChatView (views.py)
              ↓
         ChatAgentService(user)  ← Carga api_key de DB
              ↓
         agent = EFormsRAGAgent(
             api_key=user.llm_api_key,
             llm_provider=user.llm_provider
         )
              ↓
         response = agent.process(question)
              ↓
         Guarda en ChatMessage
              ↓
         Retorna JSON con respuesta
```

### 3. Flujo dentro del Agente RAG
```
question → route_node
             ↓
             ↓ (si pregunta sobre licitaciones)
             ↓
         retrieve_node
             ↓ (usa api_key del usuario)
             ↓
         NVIDIAEmbeddings(nvidia_api_key=api_key)
             ↓
         query_embedding = embed(question)
             ↓
         ChromaDB.similarity_search(query_embedding, k=6)
             ↓
         [doc1, doc2, ..., doc6]
             ↓
         grade_node (opcional, actualmente desactivado)
             ↓
         answer_node
             ↓
         ChatNVIDIA(nvidia_api_key=api_key).invoke(prompt + docs)
             ↓
         Respuesta final con citas
```

---

## Sistema de Chat RAG

### Arquitectura del Chat

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (HTMX)                         │
│  Usuario escribe pregunta → POST /chat/send/                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   DJANGO VIEW LAYER                          │
│  chat/views.py → ChatSendView                               │
│    - Valida usuario autenticado                             │
│    - Obtiene/crea ChatSession                               │
│    - Llama a ChatAgentService                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   SERVICE LAYER                              │
│  chat/services.py → ChatAgentService                        │
│    - Inicializa con user.llm_api_key                        │
│    - Mapea provider ("gemini"→"google")                     │
│    - Crea EFormsRAGAgent con parámetros del usuario         │
│    - Procesa mensaje y retorna respuesta                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              AGENT_IA CORE (LangGraph)                       │
│  agent_graph.py → EFormsRAGAgent                            │
│    - Ejecuta grafo: route→retrieve→answer                   │
│    - Usa api_key para LLM y embeddings                      │
│    - Retorna respuesta estructurada                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     CHROMADB                                 │
│  chroma_db/ → Colección "eforms_collection"                 │
│    - 22 chunks de 6 licitaciones                            │
│    - Embeddings 1024D (NVIDIA)                              │
│    - Metadata: tender_id, source, chunk_id                  │
└─────────────────────────────────────────────────────────────┘
```

### Mapeo de Proveedores

El usuario configura `llm_provider` en su perfil con valores user-friendly que se mapean internamente:

```python
# En chat/services.py
provider_map = {
    'gemini': ('google', 'gemini-2.0-flash-exp'),
    'openai': ('openai', 'gpt-4o-mini'),
    'nvidia': ('nvidia', 'meta/llama-3.1-8b-instruct')
}
```

### Ejemplo de Conversación

**Pregunta**: "¿Cuántas licitaciones hay disponibles?"

**Flujo**:
1. `route_node`: Clasifica como pregunta sobre licitaciones → "retrieve"
2. `retrieve_node`:
   - Embedding de pregunta con NVIDIA
   - Búsqueda en ChromaDB → 6 documentos
3. `grade_node`: ⏭️ **Desactivado** (saltado)
4. `answer_node`:
   - Prompt + 6 documentos contexto
   - LLM genera: "Hay 6 licitaciones disponibles en el sistema..."
5. Respuesta guardada en `ChatMessage`

**Tiempo de respuesta**: ~2-3 segundos

---

## Vectorización y ChromaDB

### Proceso de Vectorización

#### 1. Descarga de Licitaciones (TED API)
```
Usuario → Búsqueda TED → Selecciona licitaciones → Descarga XMLs
                                                         ↓
                                            data/records/*.xml
```

#### 2. Indexación Manual
```python
# tenders/vectorization_service.py
service = TenderVectorizationService(
    user=request.user  # Usa api_key del usuario
)
service.vectorize_all_tenders()
```

**Flujo de vectorización**:
```
XMLs → RecordExtractor.parse(xml)
         ↓
     {title, description, budget, deadline, ...}
         ↓
     text = f"{title}\n{description}\n..."
         ↓
     RecursiveCharacterTextSplitter(chunk_size=1000)
         ↓
     [chunk1, chunk2, chunk3, ...]
         ↓
     NVIDIAEmbeddings(api_key).embed_documents(chunks)
         ↓
     [[0.1, 0.2, ...], [0.3, 0.4, ...], ...]  # 1024D cada uno
         ↓
     ChromaDB.add(
         documents=chunks,
         embeddings=embeddings,
         metadatas=[{tender_id, source, chunk_id}, ...]
     )
```

#### 3. Estructura de ChromaDB

**Ubicación**: `chroma_db/`

**Colección**: `eforms_collection`

**Esquema de documento**:
```python
{
    "id": "tender_123_chunk_0",
    "document": "Suministro de equipos informáticos para administración pública...",
    "embedding": [0.123, 0.456, ...],  # 1024 dimensiones
    "metadata": {
        "tender_id": "123",
        "source": "data/records/tender_123.xml",
        "chunk_id": 0,
        "timestamp": "2024-10-17T12:00:00"
    }
}
```

**Estadísticas actuales**:
- **Total documentos**: 22 chunks
- **Licitaciones indexadas**: 6
- **Dimensiones**: 1024 (NVIDIA NV-Embed-QA)
- **Chunks por licitación**: ~3-4 (varía según longitud)

### Consulta Semántica

```python
# En retriever.py
def create_retriever(k=6, provider="nvidia", api_key=None):
    embeddings = NVIDIAEmbeddings(
        model="nvidia/nv-embedqa-e5-v5",
        nvidia_api_key=api_key
    )

    vectorstore = Chroma(
        collection_name="eforms_collection",
        embedding_function=embeddings,
        persist_directory="chroma_db"
    )

    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k}
    )
```

**Búsqueda**:
1. Pregunta del usuario → Embedding (1024D)
2. Similarity search en ChromaDB
3. Retorna top-k documentos más similares
4. Documentos se pasan al LLM como contexto

---

## Modelos de Datos

### User (Django Auth + Extensión)
```python
class User(AbstractUser):
    # Campos estándar de Django
    username = CharField(max_length=150, unique=True)
    email = EmailField()

    # Extensiones para LLM
    llm_provider = CharField(
        max_length=20,
        choices=[('gemini', 'Google Gemini'),
                 ('openai', 'OpenAI'),
                 ('nvidia', 'NVIDIA NIM')],
        default='nvidia'
    )
    llm_api_key = CharField(max_length=255, blank=True)
```

### CompanyProfile (company/models.py)
```python
class CompanyProfile(models.Model):
    user = OneToOneField(User)
    company_name = CharField(max_length=255)
    cif = CharField(max_length=20)
    sector = CharField(max_length=100)

    # Capacidades
    technical_capabilities = TextField()
    certifications = TextField()
    previous_experience = TextField()

    # Recursos
    number_of_employees = IntegerField()
    annual_revenue = DecimalField()

    # Ubicación
    country = CharField(max_length=100)
    city = CharField(max_length=100)

    # ... (20+ campos totales)
```

### Tender (tenders/models.py)
```python
class Tender(models.Model):
    # Identificación
    tender_id = CharField(max_length=255, unique=True)
    title = CharField(max_length=500)
    description = TextField()

    # TED API
    publication_date = DateField()
    deadline = DateField()
    notice_type = CharField(max_length=100)

    # Detalles
    budget = DecimalField(max_digits=15, decimal_places=2, null=True)
    currency = CharField(max_length=10, default='EUR')
    cpv_codes = JSONField(default=list)  # ["45000000", ...]

    # Ubicación
    country = CharField(max_length=100)
    city = CharField(max_length=200)

    # Datos
    xml_file = FileField(upload_to='tenders/xml/', null=True)
    data_json = JSONField(default=dict)

    # Vectorización
    is_vectorized = BooleanField(default=False)
    vectorized_at = DateTimeField(null=True)
```

### SavedTender (tenders/models.py)
```python
class SavedTender(models.Model):
    user = ForeignKey(User)
    tender = ForeignKey(Tender)
    status = CharField(
        max_length=20,
        choices=[
            ('interested', 'Interesado'),
            ('applied', 'Aplicado'),
            ('won', 'Ganado'),
            ('lost', 'Perdido')
        ]
    )
    notes = TextField(blank=True)
    saved_at = DateTimeField(auto_now_add=True)
```

### TenderRecommendation (tenders/models.py)
```python
class TenderRecommendation(models.Model):
    user = ForeignKey(User)
    tender = ForeignKey(Tender)

    # Puntuaciones (0-100)
    score_technical = FloatField()
    score_experience = FloatField()
    score_financial = FloatField()
    score_geographic = FloatField()
    score_timing = FloatField()

    # Puntuación total
    total_score = FloatField()

    # Análisis
    recommendation_text = TextField()
    created_at = DateTimeField(auto_now_add=True)
```

### ChatSession (chat/models.py)
```python
class ChatSession(models.Model):
    user = ForeignKey(User)
    title = CharField(max_length=255, default="Nueva conversación")
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### ChatMessage (chat/models.py)
```python
class ChatMessage(models.Model):
    session = ForeignKey(ChatSession)
    role = CharField(
        max_length=10,
        choices=[('user', 'Usuario'), ('assistant', 'Asistente')]
    )
    content = TextField()
    timestamp = DateTimeField(auto_now_add=True)

    # Metadata
    tokens_used = IntegerField(null=True)  # Futuro
    cost_eur = DecimalField(max_digits=10, decimal_places=6, null=True)  # Futuro
```

---

## Integraciones Externas

### 1. TED API (Tenders Electronic Daily)

**Endpoint**: `https://api.ted.europa.eu/v3/notices/search`

**Autenticación**: API Key (pública, sin límites estrictos)

**Flujo de descarga**:
```python
# tenders/services/download_service.py
class TEDDownloadService:
    def search_and_download(self, query_params, download_xml=True):
        # 1. Búsqueda
        response = requests.post(
            "https://api.ted.europa.eu/v3/notices/search",
            json={"q": query, "fields": [...]}
        )

        # 2. Por cada resultado
        for notice in results:
            # 3. Descargar XML
            xml_url = notice['_links']['xml']['href']
            xml_content = requests.get(xml_url)

            # 4. Guardar localmente
            save_to_file(xml_content, f"data/records/{notice_id}.xml")

            # 5. Crear registro en DB
            Tender.objects.create(
                tender_id=notice_id,
                title=notice['title'],
                xml_file=xml_path,
                ...
            )
```

**Campos descargados**:
- Identificación (notice_id, publication_date)
- Título y descripción
- Datos del comprador (buyer_name, buyer_country)
- CPV codes (clasificación de productos/servicios)
- Presupuesto y moneda
- Plazos (deadline)
- XML completo del formulario eForms

### 2. Google Gemini API

**Modelos usados**:
- `gemini-2.0-flash-exp`: Chat/generación
- `text-embedding-004`: Embeddings (768D)

**Configuración**:
```python
ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    google_api_key=user.llm_api_key,  # API key del usuario
    temperature=0.3
)
```

**Uso**:
- Generación de respuestas en chat
- Embeddings para vectorización
- Grading de documentos (cuando está activado)

### 3. OpenAI API

**Modelos usados**:
- `gpt-4o-mini`: Chat/generación
- `text-embedding-3-large`: Embeddings (3072D)

**Configuración**:
```python
ChatOpenAI(
    model="gpt-4o-mini",
    api_key=user.llm_api_key,
    temperature=0.3
)
```

### 4. NVIDIA NIM API

**Modelos usados**:
- `meta/llama-3.1-8b-instruct`: Chat/generación
- `nvidia/nv-embedqa-e5-v5`: Embeddings (1024D)

**Configuración**:
```python
ChatNVIDIA(
    model="meta/llama-3.1-8b-instruct",
    nvidia_api_key=user.llm_api_key,
    temperature=0.3
)
```

**Particularidades**:
- Requiere `os.environ['NVIDIA_API_KEY']` además del parámetro
- Embeddings de 1024 dimensiones (más eficiente que OpenAI)
- Modelos open-source (Llama, Mistral, etc.)

---

## Diagrama de Arquitectura Completo

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USUARIO (Navegador)                          │
│                     Bootstrap 5 + HTMX Frontend                      │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
                                  ↓ HTTP Requests
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│                        DJANGO APPLICATION                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │authentication│  │     core      │  │   company    │             │
│  │              │  │               │  │              │             │
│  │ - Login      │  │ - Dashboard   │  │ - Perfil     │             │
│  │ - Register   │  │ - User Profile│  │   Empresa    │             │
│  │ - Password   │  │ - API Keys    │  │ - Capacidades│             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                      │
│  ┌──────────────────────────────┐  ┌──────────────────────────┐   │
│  │         tenders               │  │         chat             │   │
│  │                               │  │                          │   │
│  │ - CRUD Licitaciones          │  │ - ChatSession            │   │
│  │ - Descarga TED API           │  │ - ChatMessage            │   │
│  │ - Búsqueda/Filtros           │  │ - ChatAgentService       │   │
│  │ - Recomendaciones IA         │  │                          │   │
│  │ - Vectorización ChromaDB     │  │                          │   │
│  └──────────────────────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
                                  ↓ API Key del Usuario (DB)
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│                       AGENT_IA_CORE MODULE                           │
│                        (LangGraph + LangChain)                       │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              EFormsRAGAgent (LangGraph)                      │   │
│  │                                                               │   │
│  │   START → route → retrieve → grade → verify → answer → END  │   │
│  │             ↓         ↓         ↓                             │   │
│  │             └─────────┴─────────┘                             │   │
│  │                (retry loop)                                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ LLM Factory  │  │  Retriever   │  │ Index Builder│             │
│  │              │  │              │  │              │             │
│  │ - Google     │  │ - Embeddings │  │ - XML Parser │             │
│  │ - OpenAI     │  │ - ChromaDB   │  │ - Chunking   │             │
│  │ - NVIDIA     │  │ - Similarity │  │ - Persist    │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
                                  ↓ API Calls (con api_key del usuario)
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      SERVICIOS EXTERNOS                              │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  Google API  │  │  OpenAI API  │  │  NVIDIA NIM  │             │
│  │              │  │              │  │              │             │
│  │ - Gemini 2.0 │  │ - GPT-4o     │  │ - Llama 3.1  │             │
│  │ - Embeddings │  │ - Embeddings │  │ - Embeddings │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                        TED API                                │  │
│  │  - Búsqueda de licitaciones europeas                         │  │
│  │  - Descarga de XMLs eForms                                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
                                  ↓ Almacenamiento local
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│                        ALMACENAMIENTO                                │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  SQLite/     │  │  ChromaDB    │  │  Filesystem  │             │
│  │  PostgreSQL  │  │              │  │              │             │
│  │              │  │ - Embeddings │  │ - XMLs       │             │
│  │ - Users      │  │ - 1024D      │  │ - Logs       │             │
│  │ - Tenders    │  │ - 22 chunks  │  │              │             │
│  │ - Chat       │  │              │  │              │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Notas de Desarrollo

### Issues Conocidos

1. **Grading Desactivado**:
   - NVIDIA LLM es muy estricto evaluando relevancia
   - Causa recursión infinita (retry loop)
   - Solución temporal: `use_grading=False`
   - Mejora futura: Ajustar prompts o usar structured output

2. **Token Tracking Pendiente**:
   - Campo `tokens_used` en ChatMessage no se calcula aún
   - Requiere integración con callbacks de LangChain

3. **Cost Tracking Pendiente**:
   - Campo `cost_eur` en ChatMessage no se calcula aún
   - Requiere tabla de precios por modelo y tracking de tokens

### Roadmap Futuro

- [ ] Re-activar grading con prompts optimizados
- [ ] Implementar token tracking por mensaje
- [ ] Calcular costos en EUR por conversación
- [ ] Streaming de respuestas (SSE o WebSockets)
- [ ] Indicador de estado de vectorización por XML
- [ ] Re-vectorización automática al descargar nuevos XMLs
- [ ] Toggle de grading opcional al vectorizar (ahorro de tokens)
- [ ] Soporte multi-idioma (actualmente solo español)
- [ ] Verificación de hallucinations (actualmente desactivado)
- [ ] Dashboard de analytics de uso de API

---

## Cambios Recientes (Octubre 2024)

### Commit: `77d1c7f` - Refactor: API Keys exclusivas por usuario

**Archivos modificados**:
1. `agent_ia_core/agent_graph.py`: api_key como parámetro requerido
2. `chat/services.py`: Pasa api_key directamente desde usuario
3. `agent_ia_core/config.py`: Eliminadas asignaciones de API_KEY
4. `agent_ia_core/index_build.py`: Eliminado import de API_KEY
5. `.env`: Eliminadas todas las líneas de API keys
6. `tenders/vectorization_service.py`: Eliminado `config.API_KEY = ...`

**Impacto**:
- ✅ Sistema 100% usuario-céntrico
- ✅ Cada usuario usa su propia API key
- ✅ No hay fallbacks a .env
- ✅ Errores claros si falta API key
- ⚠️ Testing requiere usuario con API key configurada (ej. pepe2012)

### Commit: `5235ca4` - Fix: Grading ajustado + Chat funcionando perfectamente

**Archivos modificados**:
1. `agent_ia_core/agent_graph.py`: Lógica de decisión más permisiva
2. `chat/services.py`: `use_grading=False` por defecto

**Cambios en lógica**:
```python
# ANTES: Muy estricto
if len(relevant_docs) < 2 and iteration < 2:
    return "retrieve"  # Infinitos retries

# AHORA: Más permisivo
if not relevant_docs and iteration == 1:
    return "retrieve"  # Solo 1 retry
if len(relevant_docs) >= 1:
    return "answer"  # 1 doc es suficiente
```

**Impacto**:
- ✅ Chat funciona perfectamente con NVIDIA
- ✅ No más recursion limits
- ✅ Respuestas coherentes con citas
- ✅ Tiempo de respuesta: 2-3s
- ⚠️ Grading desactivado (futuro: re-activar con ajustes)

---

## Conclusión

TenderAI Platform es una aplicación Django completa que integra IA avanzada para análisis de licitaciones públicas. Su arquitectura modular separa claramente:

1. **Capa Web (Django)**: Autenticación, CRUD, UX
2. **Capa IA (Agent_IA Core)**: RAG, LangGraph, multi-provider LLM
3. **Capa Datos**: SQLite + ChromaDB + Filesystem

**Principio fundamental**: API keys por usuario, sin claves globales en .env.

El sistema está producción-ready con funcionalidades core completadas:
- ✅ Autenticación y perfiles
- ✅ Descarga desde TED API
- ✅ Vectorización y búsqueda semántica
- ✅ Chat RAG funcional
- ✅ Recomendaciones IA multicriteria

Próximos pasos se enfocan en analytics (tokens, costos) y optimizaciones (grading, streaming).

---

**Última actualización**: Octubre 2024
**Versión**: 1.3.1
