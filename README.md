# Solution d'Automatisation des Procédures Douanières

Plateforme intelligente d'automatisation du parcours douanier utilisant l'Intelligence Artificielle avec **Function Calling**, **Classification automatique SH/NC/TARIC**, et génération documentaire automatisée.

## Objectifs du Projet

Cette solution répond aux **5 axes majeurs** définis dans le cahier des charges :

| Axe | Fonctionnalité | Statut |
|-----|----------------|--------|
| 1 | **Classification douanière par IA** - Identification des codes SH/NC/TARIC | Implémenté |
| 2 | **Automatisation documentaire** - Génération DAU, D10, D12, ENS/ICS2 | En développement |
| 3 | **Transmission électronique** - Connexion DELTA, BADR | Planifié |
| 4 | **Paiement automatisé** - Calcul et règlement des droits | Planifié |
| 5 | **Gestion OEA** - Statut Opérateur Économique Agréé | Planifié |

## Périmètre Phase 1

- **Corridor** : France ↔ Algérie (export France → import Algérie et vice-versa)
- **Articles** : Produits de base (hors produits pétroliers, matières dangereuses, licences)
- **Contexte** : Projet académique

## Caractéristiques Principales

### 1. Classification Douanière par IA (Implémentée)

- **Code SH (6 chiffres)** : Identifiable dans la quasi-totalité des cas
- **Code NC (8 chiffres, UE)** : Identifiable dans la majorité des cas
- **Code TARIC (10 chiffres)** : Identifiable avec informations contextuelles

**Méthode** :
- Upload d'une photo du produit ou d'une fiche technique PDF
- Analyse par Intelligence Artificielle
- Proposition de codes candidats avec niveaux de confiance
- Validation manuelle ou automatique

### 2. Module Expéditions (Implémenté)

Le module central de l'application avec **5 étapes du processus douanier** :

| Étape | Nom | Description | Statut |
|-------|-----|-------------|--------|
| 1 | Classification | Codes SH/NC/TARIC par IA | Fonctionnel |
| 2 | Documents | Génération DAU, D10, D12 | En développement |
| 3 | Transmission | Envoi vers DELTA/BADR | Planifié |
| 4 | Paiement | Calcul et paiement des droits | Planifié |
| 5 | OEA | Gestion statut OEA | Planifié |

### 3. Assistant Conversationnel

- Chatbot IA spécialisé en procédures douanières
- Répond aux questions sur la réglementation
- Aide à la classification et au calcul des droits

## Prérequis

- Python 3.10+
- Django 5.1.6
- **Option 1** : Ollama installé localement (100% gratuit, sans API key)
- **Option 2** : Google Gemini / OpenAI / NVIDIA API Key
- ChromaDB pour la vectorisation

## Installation

### 1. Cloner le dépôt

```bash
git clone <repo-url>
cd Procedures_Douanieres
```

### 2. Créer l'environnement virtuel

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

Créer un fichier `.env` à la racine :

```env
# Django
SECRET_KEY=votre-clé-secrète
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Configuration IA
LLM_PROVIDER=ollama              # ollama | google | openai | nvidia
GOOGLE_API_KEY=                  # Si google
OPENAI_API_KEY=                  # Si openai
```

### 5. Appliquer les migrations

```bash
python manage.py migrate
```

### 6. Créer un superutilisateur

```bash
python manage.py createsuperuser
```

### 7. Lancer le serveur

```bash
python manage.py runserver
```

Accéder à http://127.0.0.1:8000

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
│   └── expeditions/                # Module expéditions (principal)
│       ├── models.py               # Expedition, ExpeditionEtape, ExpeditionDocument
│       ├── views.py                # Vues principales
│       ├── forms.py                # Formulaires
│       ├── urls.py                 # Routes
│       └── etapes/                 # Modules par étape
│           ├── classification/     # Étape 1: Classification IA
│           │   ├── views.py
│           │   ├── forms.py
│           │   └── services.py     # ClassificationService
│           ├── documents/          # Étape 2: Documents
│           ├── transmission/       # Étape 3: Transmission
│           ├── paiement/           # Étape 4: Paiement
│           └── oea/                # Étape 5: OEA
│
├── agent_ia_core/                  # Moteur IA (voir agent_ia_core/README.md)
│   └── chatbots/                   # Chatbots indépendants
│       ├── shared/                 # Infrastructure partagée (ToolDefinition, ToolRegistry)
│       ├── base/                   # Chatbot Base (FunctionCallingAgent, web_search)
│       └── etapes_classification_taric/  # Chatbot Classification TARIC
│
├── data/                           # Données
│   ├── db.sqlite3                  # Base de données
│   └── media_expediciones/         # Fichiers uploadés par expédition
│       └── {expedition_id}/        # Dossier par expédition
│           └── etape_{n}_{type}/   # Sous-dossiers par étape
│               ├── images/         # Photos
│               └── documents/      # PDF, fiches techniques
│
├── docs/                           # Documentation
│   ├── ARCHITECTURE.md             # Architecture technique
│   ├── DOCS_INDEX.md               # Index documentation
│   └── ...
│
└── tests/                          # Tests
```

## Guide d'Utilisation

### 1. Créer une Expédition

1. Se connecter à l'application
2. Cliquer sur **Expéditions** dans la navbar
3. Cliquer sur **Nouvelle Expédition**
4. Remplir le nom de l'article et la direction (FR→DZ ou DZ→FR)
5. L'expédition est créée avec 5 étapes

### 2. Classification d'un Produit (Étape 1)

1. Ouvrir une expédition
2. Cliquer sur **Continuer** sur l'étape "Classification"
3. Télécharger une **photo** ou une **fiche technique PDF**
4. Cliquer sur **Lancer la classification IA**
5. Vérifier les codes proposés (SH, NC, TARIC)
6. Modifier manuellement si nécessaire
7. Cliquer sur **Valider** pour passer à l'étape suivante

### 3. Utiliser l'Assistant IA

1. Cliquer sur **Assistant** dans la navbar
2. Créer une nouvelle session de chat
3. Poser des questions sur :
   - La classification douanière
   - Les documents requis
   - Le calcul des droits
   - La réglementation France-Algérie

## Fournisseurs LLM Supportés

| Fournisseur | Modèles | API Key | Coût | Confidentialité |
|-------------|---------|---------|------|-----------------|
| **Ollama** | llama3.2, qwen2.5, mistral | Non | Gratuit | 100% Local |
| Google Gemini | gemini-2.0-flash-exp | Oui | Payant | Cloud |
| OpenAI | gpt-4o, gpt-4o-mini | Oui | Payant | Cloud |
| NVIDIA | mixtral, llama | Oui | Payant | Cloud |

**Recommandation** : Ollama pour la confidentialité maximale et le coût nul.

## Taux de Droits de Douane

### Algérie (Importation)

| Catégorie | Taux |
|-----------|------|
| Produits de première nécessité | 5% |
| Matières premières industrielles | 15% |
| Produits semi-finis | 30% |
| Produits finis de consommation | 60% |

### TVA

- **Algérie** : 19%
- **France** : 20%

### Formule de Calcul

```
Droits = (Valeur CIF + Frais) × Taux applicable
Total = Valeur CIF + Droits + TVA
```

## Tests

```bash
# Exécuter tous les tests
python manage.py test

# Tests spécifiques
python manage.py test tests.test_agent
python manage.py test tests.test_chat
```

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Architecture technique détaillée
- [DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) - Schéma de base de données (modèles, relations, structure fichiers)
- [DOCS_INDEX.md](docs/DOCS_INDEX.md) - Index de la documentation
- [Cahier des charges](Cahier%20des%20charges%20-%20Procédures%20douanières.pdf) - Spécifications du projet

## Licence

Projet académique - Tous droits réservés

## Équipe

**Développeurs** :
- Adrian Ubeda Touati (aubedatouati@gmail.com)
- Juan Manuel Labrador Muñoz (mario.neta.rosario@gmail.com)

**Technologies** :
- Backend : Django 5.1.6 + Python 3.10+
- IA/ML : LangChain + ChromaDB
- LLMs : Ollama (local) | Google Gemini | OpenAI | NVIDIA
- Frontend : Bootstrap 5 + JavaScript
- Base de données : SQLite

---

**Solution d'Automatisation des Procédures Douanières** - Corridor France ↔ Algérie
