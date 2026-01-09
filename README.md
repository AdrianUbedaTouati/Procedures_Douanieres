# Solution d'Automatisation des Procedures Douanieres

Plateforme intelligente d'automatisation du parcours douanier utilisant l'Intelligence Artificielle avec **Function Calling**, **Classification automatique SH/NC/TARIC**, et generation documentaire automatisee.

**Projet de Fin de Master** - Janvier 2026

## Objectifs du Projet

Cette solution repond aux **5 axes majeurs** definis dans le cahier des charges :

| Axe | Fonctionnalite | Statut |
|-----|----------------|--------|
| 1 | **Classification douaniere par IA** - Identification des codes SH/NC/TARIC | Implemente |
| 2 | **Automatisation documentaire** - Generation DAU, D10 | Implemente |
| 3 | **Transmission electronique** - Connexion DELTA, BADR | Planifie |
| 4 | **Paiement automatise** - Calcul et reglement des droits | Planifie |
| 5 | **Gestion OEA** - Statut Operateur Economique Agree | Planifie |

## Perimetre Phase 1

- **Corridor** : France <-> Algerie (export France -> import Algerie et vice-versa)
- **Articles** : Produits de base (hors produits petroliers, matieres dangereuses, licences)
- **Contexte** : Projet academique

## Caracteristiques Principales

### Etape 1 : Classification Douaniere par Chatbot IA

Chatbot intelligent avec **4 outils (tools)** pour classifier les produits :

| Outil | Fonction |
|-------|----------|
| `web_search` | Recherche Google Custom Search API |
| `browse_webpage` | Extraction progressive avec early stopping |
| `analyze_documents` | Analyse Vision GPT-4o (photos/PDF) |
| `fetch_pdf` | Telechargement de fiches techniques |

**Fonctionnement** :
- Upload d'une photo du produit ou d'une fiche technique PDF
- Chatbot IA avec Function Calling (agent autonome)
- Proposition de codes candidats avec niveaux de confiance
- Extraction structuree avec OpenAI Structured Output (JSON Schema strict)
- Validation par selection de bouton

### Etape 2 : Generation de Documents Douaniers

Generation automatique des documents officiels :

| Direction | Document | Description |
|-----------|----------|-------------|
| France -> Algerie | **DAU** | Document Administratif Unique (exportation UE) |
| Algerie -> France | **D10** | Declaration de mise a la consommation |

**Processus** :
1. Formulaire avec 50+ champs (destinataire, transport, valeurs, marchandises)
2. Template Django HTML/CSS
3. Conversion PDF via WeasyPrint
4. Stockage et telechargement

### Module Expeditions

Le module central de l'application avec **5 etapes du processus douanier** :

| Etape | Nom | Description | Statut |
|-------|-----|-------------|--------|
| 1 | Classification | Codes SH/NC/TARIC par IA | Fonctionnel |
| 2 | Documents | Generation DAU, D10 | Fonctionnel |
| 3 | Transmission | Envoi vers DELTA/BADR | Planifie |
| 4 | Paiement | Calcul et paiement des droits | Planifie |
| 5 | OEA | Gestion statut OEA | Planifie |

## Stack Technique

| Couche | Technologies | Justification |
|--------|--------------|---------------|
| **Backend** | Django 5.x, Python 3.12 | Framework robuste, ORM puissant |
| **IA** | OpenAI GPT-4o, Function Calling | Meilleur rapport qualite/prix pour le tool-calling |
| **Vision** | GPT-4o Vision | Analyse d'images et PDFs scannes |
| **PDF** | WeasyPrint | Generation PDF depuis HTML/CSS, open-source |
| **Frontend** | Bootstrap 5, Alpine.js, HTMX | Leger, reactif, sans build complexe |
| **Base de donnees** | SQLite | Simple pour developpement |

## Prerequis

- Python 3.10+
- Django 5.1.6
- OpenAI API Key (pour GPT-4o et Function Calling)
- Google Custom Search API Key (optionnel, pour web_search)

## Installation

### 1. Cloner le depot

```bash
git clone <repo-url>
cd Procedures_Douanieres
```

### 2. Creer l'environnement virtuel

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

### 3. Installer les dependances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

Creer un fichier `.env` a la racine :

```env
# Django
SECRET_KEY=votre-cle-secrete
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# OpenAI (requis)
OPENAI_API_KEY=sk-...

# Google Custom Search (optionnel, pour web_search)
GOOGLE_API_KEY=...
GOOGLE_ENGINE_ID=...
```

### 5. Appliquer les migrations

```bash
python manage.py migrate
```

### 6. Creer un superutilisateur

```bash
python manage.py createsuperuser
```

### 7. Lancer le serveur

```bash
python manage.py runserver
```

Acceder a http://127.0.0.1:8000

## Structure du Projet

```
Procedures_Douanieres/
├── config/                         # Configuration Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── apps/                           # Applications Django
│   ├── authentication/             # Authentification et profils
│   ├── core/                       # Configuration, fournisseurs LLM
│   ├── chat/                       # Assistant conversationnel
│   └── expeditions/                # Module expeditions (principal)
│       ├── models.py               # Expedition, ExpeditionEtape, Documents
│       ├── views.py                # Vues principales
│       └── etapes/                 # Modules par etape
│           ├── classification/     # Etape 1: Classification IA
│           │   └── services.py     # TARICClassificationService
│           └── documents/          # Etape 2: Generation PDF
│               └── services.py     # DocumentGenerationService
│
├── agent_ia_core/                  # Moteur IA
│   └── chatbots/
│       ├── shared/                 # ToolDefinition, ToolRegistry
│       └── etapes_classification_taric/
│           ├── service.py          # TARICClassificationService
│           └── tools/              # 4 outils du chatbot
│               ├── web_search.py
│               ├── browse_webpage.py
│               ├── analyze_documents.py
│               └── fetch_pdf.py
│
├── data/                           # Donnees
│   ├── db.sqlite3                  # Base de donnees
│   └── media_expediciones/         # Fichiers uploades
│
├── docs/                           # Documentation
│   ├── ARCHITECTURE.md
│   ├── DATABASE_SCHEMA.md
│   └── DOCS_INDEX.md
│
├── presentation/                   # Presentation academique
│   └── Procedures_Douanieres_Presentation.ipynb
│
└── tests/                          # Tests
```

## Guide d'Utilisation

### 1. Creer une Expedition

1. Se connecter a l'application
2. Cliquer sur **Expeditions** dans la navbar
3. Cliquer sur **Nouvelle Expedition**
4. Remplir le nom de l'article et la direction (FR->DZ ou DZ->FR)
5. L'expedition est creee avec 5 etapes

### 2. Classification d'un Produit (Etape 1)

1. Ouvrir une expedition
2. Cliquer sur **Continuer** sur l'etape "Classification"
3. Telecharger une **photo** ou une **fiche technique PDF**
4. Discuter avec le chatbot IA
5. Le chatbot analyse, recherche sur le web, et propose des codes TARIC
6. Selectionner le code en cliquant sur le bouton correspondant
7. L'etape passe a "termine"

### 3. Generation de Documents (Etape 2)

1. Ouvrir l'etape "Documents"
2. Remplir le formulaire (destinataire, transport, valeurs...)
3. Cliquer sur **Generer DAU** ou **Generer D10**
4. Telecharger le PDF genere

## Modele de Donnees

```
User (1) ──► (N) Expedition (1) ──► (5) ExpeditionEtape
                                          │
                                    ┌─────┼─────┐
                                    ▼     ▼     ▼
                              Classification  Documents  Expedition
                              Data (1:1)      Data (1:1) Document (1:N)
```

**ClassificationData** : code_taric, code_nc, code_sh, chat_historique, propositions
**DocumentsData** : 50+ champs (consignee, transport, valeurs, incoterms...)
**ExpeditionDocument** : fichiers (photos, PDFs, documents generes)

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Architecture technique detaillee
- [DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) - Schema de base de donnees
- [DOCS_INDEX.md](docs/DOCS_INDEX.md) - Index de la documentation
- [agent_ia_core/README.md](agent_ia_core/README.md) - Documentation du moteur IA

## Licence

Projet academique - Tous droits reserves

## Equipe

**Developpeurs** :
- Adrian Ubeda Touati (aubedatouati@gmail.com)
- Juan Manuel Labrador Munoz (mario.neta.rosario@gmail.com)

---

**Solution d'Automatisation des Procedures Douanieres** - Corridor France <-> Algerie
