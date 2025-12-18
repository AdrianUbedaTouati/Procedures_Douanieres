# Architecture du Système - Procédures Douanières v1.0

**Solution d'Automatisation des Procédures Douanières - Corridor France ↔ Algérie**

---

## Table des Matières

1. [Vue d'Ensemble](#vue-densemble)
2. [Architecture Haut Niveau](#architecture-haut-niveau)
3. [Module Expéditions](#module-expéditions)
4. [Moteur IA](#moteur-ia)
5. [Flux de Données](#flux-de-données)
6. [Intégrations Externes](#intégrations-externes)

---

## Vue d'Ensemble

### Objectif

Plateforme Django utilisant l'IA avec **Function Calling** pour automatiser le parcours douanier France ↔ Algérie.

### Les 5 Axes du Cahier des Charges

| Axe | Étape | Description | Statut |
|-----|-------|-------------|--------|
| 1 | Classification | Classification SH/NC/TARIC par IA | Implémenté |
| 2 | Documents | Génération automatique DAU, D10, D12 | En développement |
| 3 | Transmission | Connexion DELTA, BADR | Planifié |
| 4 | Paiement | Calcul et règlement des droits | Planifié |
| 5 | OEA | Gestion du statut Opérateur Économique Agréé | Planifié |

### Technologies

| Couche | Technologie |
|--------|-------------|
| Backend | Django 5.1.6 + Python 3.10+ |
| IA/ML | LangChain + ChromaDB |
| LLMs | Ollama (local) / OpenAI / Google Gemini |
| Frontend | Bootstrap 5 + JavaScript |
| Base de données | SQLite |

---

## Architecture Haut Niveau

```
┌─────────────────────────────────────────────────────────────────┐
│                      INTERFACE UTILISATEUR                       │
│                    Bootstrap 5 + JavaScript                      │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │
│  │  Accueil  │  │Expéditions│  │ Assistant │  │  Profil   │    │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/AJAX
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATIONS DJANGO                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                         apps/                                ││
│  │  ├─ authentication/    # Authentification utilisateurs      ││
│  │  ├─ core/              # Configuration, providers LLM       ││
│  │  ├─ chat/              # Assistant conversationnel          ││
│  │  └─ expeditions/       # Module principal (5 étapes)        ││
│  │       └─ etapes/                                            ││
│  │           ├─ classification/   # Étape 1                    ││
│  │           ├─ documents/        # Étape 2                    ││
│  │           ├─ transmission/     # Étape 3                    ││
│  │           ├─ paiement/         # Étape 4                    ││
│  │           └─ oea/              # Étape 5                    ││
│  └─────────────────────────────────────────────────────────────┘│
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                      MOTEUR IA (agent_ia_core)                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  FunctionCallingAgent                                        ││
│  │  ├─ prompts/prompts.py     # Prompts en français            ││
│  │  └─ agent_function_calling.py  # Agent principal            ││
│  └─────────────────────────────────────────────────────────────┘│
└────────────────────────────┬────────────────────────────────────┘
                             │
             ┌───────────────┼───────────────┐
             ↓               ↓               ↓
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│    ChromaDB     │ │   LLM Provider  │ │ Systèmes Ext.   │
│                 │ │                 │ │                 │
│ Base SH/NC/TARIC│ │ Ollama (local)  │ │ DELTA (France)  │
│                 │ │ OpenAI          │ │ BADR (Algérie)  │
│                 │ │ Google Gemini   │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Module Expéditions

### Structure du Module

Le module `apps/expeditions/` est le cœur de l'application. Il gère les expéditions avec **5 étapes** du processus douanier.

```
apps/expeditions/
├── __init__.py              # Documentation de la structure
├── apps.py                  # Configuration Django
├── models.py                # Modèles de données
├── views.py                 # Vues principales
├── urls.py                  # Routes
├── forms.py                 # Formulaires
├── admin.py                 # Administration
│
├── templates/expeditions/   # Templates
│   ├── expedition_list.html
│   ├── expedition_detail.html
│   ├── expedition_form.html
│   └── etapes/
│       ├── classification.html
│       ├── documents.html
│       ├── transmission.html
│       ├── paiement.html
│       └── oea.html
│
└── etapes/                  # Modules par étape
    ├── __init__.py
    │
    ├── classification/      # Étape 1: Classification Douanière
    │   ├── __init__.py
    │   ├── views.py         # ClassificationView, Upload, Analyse, Valider
    │   ├── forms.py         # ClassificationUploadForm, ManuelleForm
    │   ├── services.py      # ClassificationService (IA)
    │   └── urls.py
    │
    ├── documents/           # Étape 2: Génération Documents
    │   ├── __init__.py
    │   ├── views.py
    │   └── urls.py
    │
    ├── transmission/        # Étape 3: Transmission Électronique
    │   ├── __init__.py
    │   ├── views.py
    │   └── urls.py
    │
    ├── paiement/            # Étape 4: Paiement des Droits
    │   ├── __init__.py
    │   ├── views.py
    │   └── urls.py
    │
    └── oea/                 # Étape 5: Gestion OEA
        ├── __init__.py
        ├── views.py
        └── urls.py
```

### Modèles de Données

#### Expedition

```python
class Expedition(models.Model):
    """Un article/envoi en cours de traitement douanier."""

    DIRECTIONS = [
        ('FR_DZ', 'France → Algérie'),
        ('DZ_FR', 'Algérie → France'),
    ]
    STATUTS = [
        ('brouillon', 'Brouillon'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('erreur', 'Erreur'),
    ]

    reference = models.CharField(max_length=50, unique=True)  # EXP-2025-001
    nom_article = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    direction = models.CharField(max_length=10, choices=DIRECTIONS)
    statut = models.CharField(max_length=20, choices=STATUTS)
    etape_courante = models.IntegerField(default=1)  # 1-5
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### ExpeditionEtape

```python
class ExpeditionEtape(models.Model):
    """Une étape du processus douanier (5 étapes fixes)."""

    ETAPES = [
        (1, 'Classification Douanière'),
        (2, 'Génération Documents'),
        (3, 'Transmission Électronique'),
        (4, 'Paiement des Droits'),
        (5, 'Gestion OEA'),
    ]
    STATUTS = [
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('erreur', 'Erreur'),
    ]

    expedition = models.ForeignKey(Expedition, on_delete=models.CASCADE)
    numero = models.IntegerField(choices=ETAPES)
    statut = models.CharField(max_length=20, choices=STATUTS)
    donnees = models.JSONField(default=dict)  # Résultats de l'étape
    completed_at = models.DateTimeField(null=True, blank=True)
```

#### ExpeditionDocument

```python
class ExpeditionDocument(models.Model):
    """Document associé à une expédition."""

    TYPES = [
        ('photo', 'Photo du produit'),
        ('fiche_technique', 'Fiche technique'),
        ('dau', 'DAU'),
        ('d10', 'Formulaire D10'),
        ('d12', 'Formulaire D12'),
    ]

    expedition = models.ForeignKey(Expedition, on_delete=models.CASCADE)
    type = models.CharField(max_length=30, choices=TYPES)
    fichier = models.FileField(upload_to='expeditions/documents/')
    nom_original = models.CharField(max_length=255)
    etape = models.ForeignKey(ExpeditionEtape, null=True)
```

### Workflow des 5 Étapes

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSUS DOUANIER                            │
│                                                                  │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  │ ÉTAPE 1 │───→│ ÉTAPE 2 │───→│ ÉTAPE 3 │───→│ ÉTAPE 4 │───→│ ÉTAPE 5 │
│  │Classif. │    │Documents│    │Transmis.│    │Paiement │    │   OEA   │
│  └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘
│       │              │              │              │              │
│       ↓              ↓              ↓              ↓              ↓
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  │Upload   │    │Génère   │    │Envoi    │    │Calcul   │    │Vérif.   │
│  │Photo/PDF│    │DAU, D10 │    │DELTA    │    │Droits   │    │Statut   │
│  │         │    │D12      │    │BADR     │    │TVA      │    │OEA      │
│  │Analyse  │    │         │    │         │    │         │    │         │
│  │IA       │    │         │    │         │    │         │    │         │
│  │         │    │         │    │         │    │         │    │         │
│  │Codes    │    │         │    │         │    │         │    │         │
│  │SH/NC/   │    │         │    │         │    │         │    │         │
│  │TARIC    │    │         │    │         │    │         │    │         │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
│                                                                  │
│  Statut: [Implémenté] [En dev]    [Planifié]  [Planifié]  [Planifié]
└─────────────────────────────────────────────────────────────────┘
```

---

## Moteur IA (agent_ia_core)

### Philosophie

**Chaque chatbot est complètement indépendant** avec son propre:
- `config.py` - Configuration spécifique
- `prompts.py` - System prompts et templates
- `tools/` - Outils spécialisés

Seule l'infrastructure de base est partagée dans `shared/`.

### Structure

```
agent_ia_core/
├── __init__.py                 # Re-export de FunctionCallingAgent
└── chatbots/
    ├── __init__.py
    │
    ├── shared/                 # Infrastructure partagée UNIQUEMENT
    │   ├── base.py             # ToolDefinition (dataclass)
    │   └── registry.py         # ToolRegistry (gestion des tools)
    │
    ├── base/                   # Chatbot Base (générique)
    │   ├── agent.py            # FunctionCallingAgent
    │   ├── config.py           # Configuration
    │   ├── prompts.py          # System prompts génériques
    │   └── tools/
    │       ├── web_search.py       # Recherche web Google
    │       └── browse_webpage.py   # Navigation et extraction
    │
    └── etapes_classification_taric/  # Chatbot Classification TARIC
        ├── config.py           # Configuration spécifique TARIC
        ├── prompts.py          # Prompts de classification
        ├── service.py          # TARICClassificationService
        └── tools/
            ├── get_expedition_documents.py  # Récupérer docs expédition
            └── search_taric_database.py     # Recherche base TARIC
```

### Chatbots Disponibles

| Chatbot | Localisation | Utilisation |
|---------|--------------|-------------|
| Base | `chatbots/base/` | Agent générique avec web search |
| Classification TARIC | `chatbots/etapes_classification_taric/` | Classification douanière |

### Créer un Nouveau Chatbot

1. Créer dossier dans `chatbots/mon_chatbot/`
2. Définir `config.py` avec `CHATBOT_CONFIG`
3. Définir `prompts.py` avec `SYSTEM_PROMPT`
4. Créer `tools/` avec fichiers `.py` contenant `TOOL_DEFINITION`
5. Créer `service.py` avec la logique métier

### Service de Classification

```python
# agent_ia_core/chatbots/etapes_classification_taric/service.py

class TARICClassificationService:
    """Service pour classifier un produit via l'IA."""

    def get_welcome_message(self) -> str:
        """Retourne le message de bienvenue."""

    def process_message(self, user_message: str) -> dict:
        """Traite un message utilisateur et retourne la réponse."""

    def generate_conversation_summary(self) -> str:
        """Génère un résumé de la conversation."""
```

### ToolDefinition

Chaque tool est définie avec:

```python
from agent_ia_core.chatbots.shared import ToolDefinition

TOOL_DEFINITION = ToolDefinition(
    name='ma_tool',           # Nom unique
    description='...',        # Description pour le LLM
    parameters={...},         # JSON Schema des paramètres
    function=ma_fonction,     # Fonction Python à exécuter
    category='classification' # Catégorie
)
```

---

## Flux de Données

### Flux Classification (Étape 1)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Utilisateur │────→│   Upload    │────→│  Document   │
│             │     │  Photo/PDF  │     │   Créé      │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ↓
                                    ┌─────────────────┐
                                    │Classification   │
                                    │   Service       │
                                    └────────┬────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ↓                          ↓                          ↓
            ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
            │  Extraction │          │     LLM     │          │  ChromaDB   │
            │    Texte    │          │   Analyse   │          │  (futur)    │
            └─────────────┘          └─────────────┘          └─────────────┘
                    │                          │                          │
                    └──────────────────────────┼──────────────────────────┘
                                               │
                                               ↓
                                    ┌─────────────────┐
                                    │ Codes Proposés  │
                                    │ SH / NC / TARIC │
                                    │ + Confiance     │
                                    └────────┬────────┘
                                               │
                                               ↓
                                    ┌─────────────────┐
                                    │   Validation    │
                                    │   Utilisateur   │
                                    └─────────────────┘
```

### Flux Complet d'une Expédition

```
┌─────────────────────────────────────────────────────────────────┐
│                    CRÉATION EXPÉDITION                           │
│                                                                  │
│  1. Utilisateur crée une expédition                             │
│     └─ nom_article, direction (FR→DZ ou DZ→FR)                  │
│                                                                  │
│  2. Système crée automatiquement 5 étapes                       │
│     └─ Étape 1 en "en_cours", autres "en_attente"               │
│                                                                  │
│  3. Utilisateur complète chaque étape séquentiellement          │
│     └─ Chaque étape validée passe la suivante en "en_cours"     │
│                                                                  │
│  4. À la fin de l'étape 5, expédition marquée "terminé"         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Intégrations Externes

### DELTA (France) - Planifié

- **Type** : API REST
- **Authentification** : Certificat numérique
- **Documents** : DAU, ENS, ICS2
- **Format** : XML CUSDEC

### BADR (Algérie) - Planifié

- **Type** : Portail web (automatisation Playwright)
- **Authentification** : Login/password
- **Documents** : D10, D12
- **Format** : Formulaires en ligne

---

## Taux de Droits de Douane

### Algérie (Importation)

| Catégorie | Taux |
|-----------|------|
| Produits de première nécessité | 5% |
| Matières premières industrielles | 15% |
| Produits semi-finis | 30% |
| Produits finis de consommation | 60% |

### TVA

- Algérie : 19%
- France : 20%

### Formule

```
Droits = (Valeur CIF + Frais) × Taux applicable
Total = Valeur CIF + Droits + TVA
```

---

**Version** : 1.0.0
**Date** : Décembre 2025
**Corridor** : France ↔ Algérie
