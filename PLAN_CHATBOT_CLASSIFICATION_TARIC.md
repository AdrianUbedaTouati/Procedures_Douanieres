# Plan: Chatbot de Clasificación TARIC (v2)

## Objetivo
Integrar un chatbot especializado en la página de clasificación (`/expeditions/<id>/classification/`) que:
1. Guíe al usuario para subir fotos y fichas técnicas
2. Tenga una **tool para consultar los documentos subidos** (no detección automática)
3. Proponga **5 códigos TARIC con porcentajes de precisión** y razonamiento
4. Muestre **5 botones con código + porcentaje** para que el usuario seleccione
5. Permita seguir conversando si ningún código convence
6. Al validar un código, **bloquee la etapa** (chat y documentos en solo lectura)

---

## Arquitectura Propuesta

### 1. Estructura de Carpetas en `agent_ia_core/`

```
agent_ia_core/
├── chatbots/                              # NUEVA CARPETA - Un chatbot por carpeta
│   └── etapes_classification_taric/       # Chatbot especializado TARIC
│       ├── __init__.py
│       ├── config.py                      # Configuración específica
│       ├── prompts.py                     # Prompts del sistema
│       ├── tools/                         # Tools específicas
│       │   ├── __init__.py
│       │   ├── get_expedition_documents.py  # Consultar docs subidos
│       │   ├── analyze_product_image.py     # Analizar foto con visión IA
│       │   ├── analyze_technical_sheet.py   # Extraer info de PDF
│       │   ├── search_taric_database.py     # Buscar en BD TARIC
│       │   ├── validate_taric_code.py       # Validar código
│       │   └── get_tariff_rates.py          # Obtener aranceles
│       └── service.py                     # Servicio principal
├── tools/                                 # Tools globales existentes
├── prompts/                               # Prompts globales existentes
└── ...
```

---

## 2. Flujo del Chatbot

```
┌─────────────────────────────────────────────────────────────────┐
│  INICIO DE CONVERSACIÓN                                         │
├─────────────────────────────────────────────────────────────────┤
│  Bot: "Bonjour! Je suis votre assistant de classification       │
│        douanière TARIC.                                         │
│                                                                 │
│        Pour déterminer le code TARIC de votre produit avec      │
│        précision, merci de télécharger:                         │
│                                                                 │
│        📷 Des PHOTOS du produit (dans la section gauche)        │
│        📄 La FICHE TECHNIQUE si disponible (PDF)                │
│                                                                 │
│        Une fois les documents ajoutés, dites-moi et je          │
│        procéderai à l'analyse."                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  USUARIO SUBE DOCUMENTOS Y ESCRIBE EN EL CHAT                   │
├─────────────────────────────────────────────────────────────────┤
│  Usuario: "J'ai ajouté les photos et la fiche technique"        │
│                                                                 │
│  Bot usa tool: get_expedition_documents()                       │
│  → Retorna lista de fotos y PDFs disponibles                    │
│                                                                 │
│  Bot: "Je vois que vous avez téléchargé:                        │
│        - 2 photos (photo1.jpg, photo2.jpg)                      │
│        - 1 fiche technique (specs.pdf)                          │
│                                                                 │
│        Je procède à l'analyse..."                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  ANÁLISIS CON TOOLS                                             │
├─────────────────────────────────────────────────────────────────┤
│  Bot ejecuta:                                                   │
│  1. analyze_product_image(photo1.jpg) → Descripción visual      │
│  2. analyze_product_image(photo2.jpg) → Más detalles            │
│  3. analyze_technical_sheet(specs.pdf) → Specs técnicas         │
│  4. search_taric_database(keywords) → Códigos candidatos        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PROPUESTA DE 5 CÓDIGOS CON PORCENTAJES                         │
├─────────────────────────────────────────────────────────────────┤
│  Bot: "Basé sur mon analyse, voici les 5 codes TARIC les        │
│        plus probables pour votre produit:                       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 📊 CODES TARIC PROPOSÉS                                 │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │                                                         │    │
│  │ 1. 8471.30.00.00 - Ordinateurs portables               │    │
│  │    Précision: 87%                                       │    │
│  │    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━░░░░░            │    │
│  │                                                         │    │
│  │ 2. 8471.41.00.00 - Autres machines automatiques        │    │
│  │    Précision: 6%                                        │    │
│  │    ━━━░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░            │    │
│  │                                                         │    │
│  │ 3. 8471.49.00.00 - Autres, présentées sous forme       │    │
│  │    Précision: 4%                                        │    │
│  │    ━━░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░            │    │
│  │                                                         │    │
│  │ 4. 8473.30.00.00 - Parties et accessoires              │    │
│  │    Précision: 2%                                        │    │
│  │    ━░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░            │    │
│  │                                                         │    │
│  │ 5. 8542.31.00.00 - Processeurs et contrôleurs          │    │
│  │    Précision: 1%                                        │    │
│  │    ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  RAISONNEMENT:                                                  │
│  Le produit analysé est un ordinateur portable basé sur:        │
│  - Photos: écran intégré, clavier, design compact portable      │
│  - Fiche technique: processeur Intel, RAM 16GB, batterie        │
│  - RGI 1: classé selon fonction principale (traitement données) │
│  - Note chapitre 84: machines automatiques de traitement        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  [8471.30.00.00 - 87%]  [8471.41.00.00 - 6%]           │    │
│  │  [8471.49.00.00 - 4%]   [8473.30.00.00 - 2%]           │    │
│  │  [8542.31.00.00 - 1%]                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Sélectionnez un code ou posez-moi des questions si vous        │
│  souhaitez plus de détails."                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
┌───────────────────────────┐  ┌───────────────────────────────────┐
│  OPCIÓN A: PREGUNTAS      │  │  OPCIÓN B: SELECCIONAR CÓDIGO     │
├───────────────────────────┤  ├───────────────────────────────────┤
│  Usuario: "¿Por qué no    │  │  Usuario hace clic en botón:      │
│  8471.41?"                │  │  [8471.30.00.00 - 87%]            │
│                           │  │                                   │
│  Bot explica diferencias  │  │  Bot: "Vous avez sélectionné:     │
│  y puede re-proponer      │  │        8471.30.00.00              │
│                           │  │                                   │
│  Usuario puede seguir     │  │        Voulez-vous valider ce     │
│  preguntando...           │  │        code et terminer l'étape   │
│                           │  │        de classification?         │
│                           │  │                                   │
│                           │  │        [✓ Valider] [✗ Annuler]"  │
└───────────────────────────┘  └───────────────────────────────────┘
                                              │
                                              ▼
                              ┌───────────────────────────────────┐
                              │  VALIDACIÓN Y BLOQUEO             │
                              ├───────────────────────────────────┤
                              │  Usuario: clic [✓ Valider]        │
                              │                                   │
                              │  Sistema:                         │
                              │  1. Guarda código en expedición   │
                              │  2. Marca etapa como "terminé"    │
                              │  3. Bloquea chat (solo lectura)   │
                              │  4. Bloquea documentos (solo ver) │
                              │                                   │
                              │  Bot: "Code TARIC 8471.30.00.00   │
                              │        validé avec succès!        │
                              │                                   │
                              │        📋 Récapitulatif:          │
                              │        - Code SH: 8471.30         │
                              │        - Code NC: 8471.30.00      │
                              │        - Code TARIC: 8471.30.00.00│
                              │        - Droits: 0% (ITA)         │
                              │        - TVA: 20%                 │
                              │                                   │
                              │        Vous pouvez passer à       │
                              │        l'étape suivante."         │
                              │                                   │
                              │  🔒 Chat et documents en lecture  │
                              │     seule (consultable)           │
                              └───────────────────────────────────┘
```

---

## 3. Tools Específicas

### 3.1 `get_expedition_documents.py`
**Propósito**: Consultar los documentos subidos por el usuario

```python
TOOL_DEFINITION = ToolDefinition(
    name="get_expedition_documents",
    description="Récupérer la liste des documents (photos et fiches techniques) "
                "téléchargés par l'utilisateur pour cette expédition.",
    parameters={
        "type": "object",
        "properties": {
            "type_filter": {
                "type": "string",
                "enum": ["all", "photo", "fiche_technique"],
                "description": "Filtrer par type de document"
            }
        },
        "required": []
    },
    function=get_expedition_documents_impl,
    category="classification"
)

# Retorna:
{
    "photos": [
        {"id": 1, "nom": "photo1.jpg", "url": "/media/...", "uploaded_at": "..."},
        {"id": 2, "nom": "photo2.jpg", "url": "/media/...", "uploaded_at": "..."}
    ],
    "fiches_techniques": [
        {"id": 3, "nom": "specs.pdf", "url": "/media/...", "uploaded_at": "..."}
    ],
    "total": 3
}
```

### 3.2 `analyze_product_image.py`
**Propósito**: Analizar foto con visión IA (GPT-4V, Gemini Vision, LLaVA)

```python
TOOL_DEFINITION = ToolDefinition(
    name="analyze_product_image",
    description="Analyser une photo du produit avec l'IA vision pour identifier "
                "ses caractéristiques: type, matériaux, composants, marques visibles.",
    parameters={
        "type": "object",
        "properties": {
            "document_id": {
                "type": "integer",
                "description": "ID du document photo à analyser"
            }
        },
        "required": ["document_id"]
    },
    function=analyze_product_image_impl,
    category="classification"
)
```

### 3.3 `analyze_technical_sheet.py`
**Propósito**: Extraer información de PDF/fiche technique

```python
TOOL_DEFINITION = ToolDefinition(
    name="analyze_technical_sheet",
    description="Extraire les informations d'une fiche technique PDF: "
                "composition, dimensions, poids, caractéristiques techniques.",
    parameters={
        "type": "object",
        "properties": {
            "document_id": {
                "type": "integer",
                "description": "ID du document PDF à analyser"
            }
        },
        "required": ["document_id"]
    },
    function=analyze_technical_sheet_impl,
    category="classification"
)
```

### 3.4 `search_taric_database.py`
**Propósito**: Buscar códigos TARIC por keywords o descripción

```python
TOOL_DEFINITION = ToolDefinition(
    name="search_taric_database",
    description="Rechercher dans la base TARIC des codes correspondant "
                "à la description du produit.",
    parameters={
        "type": "object",
        "properties": {
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Mots-clés de recherche"
            },
            "product_description": {
                "type": "string",
                "description": "Description complète du produit"
            }
        },
        "required": ["keywords"]
    },
    function=search_taric_database_impl,
    category="classification"
)
```

### 3.5 `validate_taric_code.py`
**Propósito**: Validar que un código TARIC existe y está vigente

```python
TOOL_DEFINITION = ToolDefinition(
    name="validate_taric_code",
    description="Vérifier si un code TARIC est valide et actif.",
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Code TARIC à valider (10 chiffres)"
            }
        },
        "required": ["code"]
    },
    function=validate_taric_code_impl,
    category="classification"
)
```

### 3.6 `get_tariff_rates.py`
**Propósito**: Obtener aranceles para un código TARIC

```python
TOOL_DEFINITION = ToolDefinition(
    name="get_tariff_rates",
    description="Obtenir les droits de douane et TVA pour un code TARIC.",
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Code TARIC"
            },
            "origin_country": {
                "type": "string",
                "description": "Pays d'origine (code ISO)"
            }
        },
        "required": ["code"]
    },
    function=get_tariff_rates_impl,
    category="classification"
)
```

---

## 4. Modelos Django

### 4.1 Nuevos modelos en `apps/expeditions/models.py`

```python
class ClassificationChat(models.Model):
    """Sesión de chat para clasificación TARIC de una expedición."""
    expedition = models.OneToOneField(
        Expedition,
        on_delete=models.CASCADE,
        related_name='classification_chat'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Chat de classification"
        verbose_name_plural = "Chats de classification"


class ClassificationMessage(models.Model):
    """Mensaje en el chat de clasificación."""
    ROLE_CHOICES = [
        ('user', 'Utilisateur'),
        ('assistant', 'Assistant'),
        ('system', 'Système'),
    ]

    chat = models.ForeignKey(
        ClassificationChat,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    # metadata puede contener:
    # - tools_used: lista de tools ejecutadas
    # - tokens: tokens consumidos
    # - proposals: propuestas de códigos TARIC (si las hay)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class TARICProposal(models.Model):
    """Propuesta de código TARIC generada por el chatbot."""
    message = models.ForeignKey(
        ClassificationMessage,
        on_delete=models.CASCADE,
        related_name='proposals'
    )
    code_sh = models.CharField(max_length=6)
    code_nc = models.CharField(max_length=8)
    code_taric = models.CharField(max_length=10)
    probability = models.FloatField()  # 0-100
    description = models.CharField(max_length=255)
    justification = models.TextField()
    ordre = models.IntegerField(default=0)
    is_selected = models.BooleanField(default=False)

    class Meta:
        ordering = ['-probability']
```

---

## 5. Vistas API

### 5.1 Nuevas vistas en `apps/expeditions/etapes/classification/views.py`

```python
class ClassificationChatView(LoginRequiredMixin, View):
    """Vista principal del chat - obtener historial."""

    def get(self, request, pk):
        expedition = get_object_or_404(...)
        chat, created = ClassificationChat.objects.get_or_create(expedition=expedition)

        messages = chat.messages.all()
        # Si es nuevo chat, añadir mensaje de bienvenida
        if created or not messages.exists():
            welcome_msg = create_welcome_message(chat)

        return JsonResponse({
            'success': True,
            'messages': [...],
            'etape_terminee': etape.statut == 'termine'
        })


class ClassificationChatMessageView(LoginRequiredMixin, View):
    """Enviar mensaje al chatbot."""

    def post(self, request, pk):
        # Verificar que etapa no está terminada
        if etape.statut == 'termine':
            return JsonResponse({'error': 'Étape terminée'}, status=403)

        # Crear mensaje del usuario
        user_message = ClassificationMessage.objects.create(
            chat=chat,
            role='user',
            content=request.POST['message']
        )

        # Procesar con el chatbot TARIC
        service = TARICClassificationService(user, expedition)
        response = service.process_message(user_message.content)

        # Crear mensaje del asistente
        assistant_message = ClassificationMessage.objects.create(
            chat=chat,
            role='assistant',
            content=response['content'],
            metadata=response['metadata']
        )

        # Si hay propuestas, crearlas
        if response.get('proposals'):
            for i, prop in enumerate(response['proposals']):
                TARICProposal.objects.create(
                    message=assistant_message,
                    code_sh=prop['code_sh'],
                    code_nc=prop['code_nc'],
                    code_taric=prop['code_taric'],
                    probability=prop['probability'],
                    description=prop['description'],
                    justification=prop['justification'],
                    ordre=i
                )

        return JsonResponse({
            'success': True,
            'user_message': {...},
            'assistant_message': {...},
            'proposals': [...]  # Si hay botones para mostrar
        })


class SelectTARICProposalView(LoginRequiredMixin, View):
    """Seleccionar una propuesta de código TARIC."""

    def post(self, request, pk, proposal_id):
        # Verificar que etapa no está terminada
        proposal = get_object_or_404(TARICProposal, pk=proposal_id)

        # Marcar como seleccionada
        proposal.is_selected = True
        proposal.save()

        return JsonResponse({
            'success': True,
            'selected_code': proposal.code_taric,
            'message': f'Code {proposal.code_taric} sélectionné'
        })


class ValidateTARICCodeView(LoginRequiredMixin, View):
    """Validar código TARIC y cerrar etapa."""

    def post(self, request, pk):
        expedition = get_object_or_404(...)
        etape = expedition.get_etape(1)

        # Obtener propuesta seleccionada
        proposal = TARICProposal.objects.filter(
            message__chat__expedition=expedition,
            is_selected=True
        ).first()

        if not proposal:
            return JsonResponse({'error': 'Aucun code sélectionné'}, status=400)

        # Guardar en la etapa
        etape.donnees = {
            'code_sh': proposal.code_sh,
            'code_nc': proposal.code_nc,
            'code_taric': proposal.code_taric,
            'probability': proposal.probability,
            'justification': proposal.justification,
            'mode': 'chatbot',
            'valide': True
        }
        etape.marquer_termine(etape.donnees)

        # Añadir mensaje de confirmación al chat
        chat = expedition.classification_chat
        ClassificationMessage.objects.create(
            chat=chat,
            role='assistant',
            content=f"✅ Code TARIC {proposal.code_taric} validé avec succès!\n\n"
                   f"Cette étape est maintenant terminée et verrouillée."
        )

        return JsonResponse({
            'success': True,
            'message': 'Classification validée',
            'redirect': reverse('apps_expeditions:detail', kwargs={'pk': pk})
        })
```

### 5.2 URLs

```python
# apps/expeditions/etapes/classification/urls.py

urlpatterns = [
    # ... URLs existentes ...

    # Chat de clasificación
    path('chat/', views.ClassificationChatView.as_view(), name='classification_chat'),
    path('chat/message/', views.ClassificationChatMessageView.as_view(), name='classification_chat_message'),
    path('chat/proposal/<int:proposal_id>/select/', views.SelectTARICProposalView.as_view(), name='select_proposal'),
    path('chat/validate/', views.ValidateTARICCodeView.as_view(), name='validate_taric'),
]
```

---

## 6. Frontend - Template

### 6.1 Estructura del template `classification.html`

```html
<div class="row">
    <!-- Columna izquierda: Upload de documentos (sin cambios) -->
    <div class="col-lg-5 mb-4">
        <!-- Sección Photos -->
        <!-- Sección Fiches Techniques -->
        <!-- (código existente) -->
    </div>

    <!-- Columna derecha: CHAT (reemplaza resultados) -->
    <div class="col-lg-7 mb-4">
        <div class="card h-100">
            <div class="card-header bg-success text-white d-flex justify-content-between align-items-center">
                <span><i class="bi bi-robot"></i> Assistant Classification TARIC</span>
                {% if etape_terminee %}
                <span class="badge bg-light text-dark"><i class="bi bi-lock"></i> Lecture seule</span>
                {% endif %}
            </div>

            <div class="card-body d-flex flex-column" style="height: 600px;">
                <!-- Área de mensajes -->
                <div id="chatMessages" class="flex-grow-1 overflow-auto mb-3">
                    <!-- Mensajes se cargan aquí -->
                </div>

                <!-- Área de propuestas TARIC (cuando hay) -->
                <div id="taricProposals" class="d-none mb-3">
                    <!-- Botones de códigos TARIC -->
                </div>

                <!-- Input de mensaje -->
                {% if not etape_terminee %}
                <div class="chat-input-area">
                    <form id="chatForm" class="d-flex gap-2">
                        <textarea id="chatInput" class="form-control"
                                  placeholder="Tapez votre message..."
                                  rows="1"></textarea>
                        <button type="submit" class="btn btn-success" id="sendBtn">
                            <i class="bi bi-send"></i>
                        </button>
                    </form>
                </div>
                {% else %}
                <div class="alert alert-info mb-0">
                    <i class="bi bi-lock"></i> Cette conversation est en lecture seule.
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
```

### 6.2 Componente de Propuestas TARIC

```html
<!-- Botones de propuestas -->
<div id="taricProposals" class="taric-proposals">
    <p class="text-muted small mb-2">Sélectionnez un code TARIC:</p>
    <div class="d-flex flex-wrap gap-2">
        <!-- Generado dinámicamente -->
        <button class="btn btn-outline-primary taric-btn" data-proposal-id="1">
            <span class="code">8471.30.00.00</span>
            <span class="badge bg-success">87%</span>
        </button>
        <button class="btn btn-outline-secondary taric-btn" data-proposal-id="2">
            <span class="code">8471.41.00.00</span>
            <span class="badge bg-warning">6%</span>
        </button>
        <!-- ... más botones ... -->
    </div>
</div>

<!-- Modal de confirmación -->
<div class="modal" id="confirmTaricModal">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5>Confirmer la sélection</h5>
            </div>
            <div class="modal-body">
                <p>Vous avez sélectionné le code:</p>
                <h3 class="text-center text-primary" id="selectedCode">8471.30.00.00</h3>
                <p class="text-center">
                    <span class="badge bg-success fs-5" id="selectedProbability">87%</span>
                </p>
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle"></i>
                    Cette action validera l'étape et verrouillera le chat et les documents.
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                <button class="btn btn-success" id="confirmValidateBtn">
                    <i class="bi bi-check-lg"></i> Valider
                </button>
            </div>
        </div>
    </div>
</div>
```

### 6.3 CSS Específico

```css
/* Chat container */
#chatMessages {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
}

/* Burbujas de mensaje */
.chat-message {
    max-width: 85%;
    padding: 12px 16px;
    border-radius: 16px;
}

.chat-message.user {
    align-self: flex-end;
    background: linear-gradient(135deg, #0d6efd, #0a58ca);
    color: white;
}

.chat-message.assistant {
    align-self: flex-start;
    background: #f8f9fa;
    border: 1px solid #dee2e6;
}

/* Propuestas TARIC */
.taric-proposals {
    background: #f0f7ff;
    border-radius: 12px;
    padding: 16px;
    border: 2px solid #0d6efd;
}

.taric-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
}

.taric-btn .code {
    font-family: monospace;
    font-weight: bold;
}

.taric-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

/* Barra de probabilidad en mensajes */
.probability-bar {
    height: 8px;
    background: #e9ecef;
    border-radius: 4px;
    overflow: hidden;
}

.probability-bar .fill {
    height: 100%;
    background: linear-gradient(90deg, #198754, #20c997);
}
```

---

## 7. Tareas de Implementación

### Fase 1: Infraestructura Base
- [ ] Crear estructura `agent_ia_core/chatbots/etapes_classification_taric/`
- [ ] Implementar `config.py` con configuración del chatbot
- [ ] Implementar `prompts.py` con prompts especializados
- [ ] Crear `service.py` con `TARICClassificationService`

### Fase 2: Tools Específicas
- [ ] Implementar `get_expedition_documents.py`
- [ ] Implementar `analyze_product_image.py` (visión IA)
- [ ] Implementar `analyze_technical_sheet.py` (extracción PDF)
- [ ] Implementar `search_taric_database.py`
- [ ] Implementar `validate_taric_code.py`
- [ ] Implementar `get_tariff_rates.py`

### Fase 3: Modelos Django
- [ ] Añadir modelos `ClassificationChat`, `ClassificationMessage`, `TARICProposal`
- [ ] Crear y aplicar migración
- [ ] Configurar admin

### Fase 4: Vistas API
- [ ] Implementar `ClassificationChatView` (GET historial)
- [ ] Implementar `ClassificationChatMessageView` (POST mensaje)
- [ ] Implementar `SelectTARICProposalView` (seleccionar código)
- [ ] Implementar `ValidateTARICCodeView` (validar y cerrar etapa)
- [ ] Actualizar URLs

### Fase 5: Frontend
- [ ] Actualizar `classification.html` con chat integrado
- [ ] Crear CSS para el chat
- [ ] Implementar JavaScript para:
  - Cargar historial de mensajes
  - Enviar mensajes AJAX
  - Renderizar propuestas con botones
  - Modal de confirmación
  - Manejar estado de lectura seule

### Fase 6: Integración y Testing
- [ ] Integrar chatbot con documentos de expedición
- [ ] Probar flujo completo
- [ ] Ajustar prompts según resultados
- [ ] Testing de bloqueo de etapa

---

## 8. Resumen de Comportamiento

| Estado | Chat | Documentos | Botones TARIC |
|--------|------|------------|---------------|
| Etapa en curso | ✅ Editable | ✅ Editable | ✅ Activos |
| Código seleccionado (sin validar) | ✅ Editable | ✅ Editable | ✅ Activos |
| Código validado (etapa terminée) | 🔒 Solo lectura | 🔒 Solo lectura | 🔒 Deshabilitados |

---

¿Procedo con la implementación?
