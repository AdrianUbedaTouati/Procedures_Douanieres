# Index de la Documentation - Procédures Douanières v1.0

**Solution d'Automatisation des Procédures Douanières - Corridor France ↔ Algérie**

---

## Commencer Ici

Si c'est votre première fois, lisez dans cet ordre :

1. **[README.md](../README.md)** - Présentation et installation
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Architecture technique
3. **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** - Schéma de base de données
4. **[Cahier des charges](../Cahier%20des%20charges%20-%20Procédures%20douanières.pdf)** - Spécifications du projet

---

## Documentation Principale

### README.md

**Contenu :**
- Objectifs du projet (5 axes)
- Périmètre Phase 1 (corridor France ↔ Algérie)
- Installation et configuration
- Guide d'utilisation (Expéditions, Classification, Assistant)
- Fournisseurs LLM supportés
- Taux de droits de douane

**Quand le lire :**
- Première utilisation du système
- Installation dans un nouvel environnement
- Configuration d'un nouveau fournisseur LLM

---

### ARCHITECTURE.md

**Contenu :**
- Vue d'ensemble du système
- Architecture haut niveau
- Module Expéditions (structure détaillée)
- Modèles de données (Expedition, ExpeditionEtape, ExpeditionDocument)
- Moteur IA (agent_ia_core)
- Flux de données
- Intégrations externes (DELTA, BADR)

**Quand le lire :**
- Comprendre le fonctionnement interne
- Développer de nouvelles fonctionnalités
- Ajouter une nouvelle étape

---

### DATABASE_SCHEMA.md

**Contenu :**
- Structure hiérarchique des tables (Expedition → ExpeditionEtape → *Data)
- Détail de chaque modèle (ClassificationData, DocumentsData, etc.)
- Relations 1:1 et 1:N
- Structure des fichiers media
- Format des champs JSON (chat_historique, propositions)
- Diagramme entité-relation

**Quand le lire :**
- Comprendre la structure de données
- Développer des fonctionnalités sur les étapes
- Modifier les modèles Django

---

## Structure du Projet

```
Procedures_Douanieres/
├── README.md                    # Documentation principale
├── Cahier des charges.pdf       # Spécifications
│
├── config/                      # Configuration Django
│   ├── settings.py
│   └── urls.py
│
├── apps/                        # Applications Django
│   ├── authentication/          # Authentification
│   ├── core/                    # Configuration, LLM providers
│   ├── chat/                    # Assistant conversationnel
│   └── expeditions/             # Module principal
│       ├── models.py            # Modèles de données
│       ├── views.py             # Vues principales
│       └── etapes/              # Modules par étape
│           ├── classification/  # Étape 1 (Implémentée)
│           ├── documents/       # Étape 2
│           ├── transmission/    # Étape 3
│           ├── paiement/        # Étape 4
│           └── oea/             # Étape 5
│
├── agent_ia_core/               # Moteur IA (voir agent_ia_core/README.md)
│   └── chatbots/                # Chatbots indépendants
│       ├── shared/              # ToolDefinition, ToolRegistry
│       ├── base/                # FunctionCallingAgent + web tools
│       └── etapes_classification_taric/  # Chatbot TARIC
│
├── data/                        # Données
│   ├── db.sqlite3               # Base de données
│   └── media_expediciones/      # Fichiers par expédition
│
├── docs/                        # Documentation
│   ├── DOCS_INDEX.md            # Ce fichier
│   ├── ARCHITECTURE.md          # Architecture
│   └── DATABASE_SCHEMA.md       # Schéma BDD
│
└── tests/                       # Tests
```

---

## Les 5 Étapes du Processus Douanier

### Étape 1 : Classification Douanière (Implémentée)

**Localisation :** `apps/expeditions/etapes/classification/`

**Fonctionnalités :**
- Upload photo ou fiche technique PDF
- Analyse par IA (ClassificationService)
- Proposition des codes SH/NC/TARIC avec confiance
- Validation manuelle ou automatique

**Fichiers :**
- `views.py` - ClassificationView, UploadView, AnalyseView, ValiderView
- `forms.py` - ClassificationUploadForm, ClassificationManuelleForm
- `services.py` - ClassificationService

**Codes de classification :**
| Code | Chiffres | Confiance |
|------|----------|-----------|
| SH | 6 | Haute |
| NC | 8 | Moyenne |
| TARIC | 10 | Variable |

---

### Étape 2 : Génération Documents (En développement)

**Localisation :** `apps/expeditions/etapes/documents/`

**Documents prévus :**
- **France** : DAU, ENS, ICS2
- **Algérie** : D10, D12
- **Annexes** : Certificats d'origine, factures

---

### Étape 3 : Transmission Électronique (Planifié)

**Localisation :** `apps/expeditions/etapes/transmission/`

**Systèmes ciblés :**
- **DELTA** (France) - API REST
- **BADR** (Algérie) - Playwright

---

### Étape 4 : Paiement des Droits (Planifié)

**Localisation :** `apps/expeditions/etapes/paiement/`

**Fonctionnalités prévues :**
- Calcul automatique des droits
- Calcul TVA
- Initiation du paiement

**Formule :** `Droits = (Valeur CIF + Frais) × Taux`

**Taux Algérie :**
| Catégorie | Taux |
|-----------|------|
| Première nécessité | 5% |
| Matières premières | 15% |
| Semi-finis | 30% |
| Produits finis | 60% |

**TVA :** 19% (Algérie), 20% (France)

---

### Étape 5 : Gestion OEA (Planifié)

**Localisation :** `apps/expeditions/etapes/oea/`

**Facilitations OEA :**
- Paiement différé
- Procédures simplifiées
- Réduction des contrôles

---

## Guide par Rôle

### Utilisateurs

1. Se connecter à l'application
2. Créer une nouvelle expédition (menu **Expéditions**)
3. Compléter l'étape 1 (Classification)
4. Utiliser l'**Assistant** pour les questions

### Développeurs

1. Lire [ARCHITECTURE.md](ARCHITECTURE.md)
2. Lire [agent_ia_core/README.md](../agent_ia_core/README.md) pour le moteur IA
3. Structure des étapes : `apps/expeditions/etapes/`
4. Chatbots IA : `agent_ia_core/chatbots/`

**Pour ajouter une nouvelle fonctionnalité à une étape :**
1. Modifier `views.py` de l'étape
2. Ajouter les formulaires dans `forms.py`
3. Créer un service dans `services.py` si nécessaire
4. Mettre à jour les templates

**Pour créer un nouveau chatbot :**
1. Créer dossier dans `agent_ia_core/chatbots/mon_chatbot/`
2. Définir `config.py`, `prompts.py`, `service.py`
3. Créer `tools/` avec les outils spécialisés
4. Voir [agent_ia_core/README.md](../agent_ia_core/README.md) pour les détails

---

## Périmètre Phase 1

**Corridor :** France ↔ Algérie uniquement

**Limitations :**
- Produits de base (articles courants)
- Hors : produits pétroliers, matières dangereuses, licences spéciales

**Ce qui est implémenté :**
- Module Expéditions complet (structure)
- Étape 1 : Classification douanière par IA
- Assistant conversationnel
- Authentification

---

## Contact

**Développeurs :**
- Adrian Ubeda Touati (aubedatouati@gmail.com)
- Juan Manuel Labrador Muñoz (mario.neta.rosario@gmail.com)

---

**Version :** 1.0.0
**Date :** Décembre 2025
**Contexte :** Projet académique
