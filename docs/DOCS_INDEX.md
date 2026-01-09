# Index de la Documentation - Procedures Douanieres v2.0

**Solution d'Automatisation des Procedures Douanieres - Corridor France <-> Algerie**

---

## Commencer Ici

Si c'est votre premiere fois, lisez dans cet ordre :

1. **[README.md](../README.md)** - Presentation et installation
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Architecture technique
3. **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** - Schema de base de donnees

---

## Documentation Principale

### README.md (racine)

**Contenu :**
- Objectifs du projet (5 axes)
- Perimetre Phase 1 (corridor France <-> Algerie)
- Stack technique avec justifications
- Installation et configuration
- Guide d'utilisation (Expeditions, Classification, Documents)
- Modele de donnees

**Quand le lire :**
- Premiere utilisation du systeme
- Installation dans un nouvel environnement

---

### ARCHITECTURE.md

**Contenu :**
- Vue d'ensemble du systeme
- Architecture haut niveau (diagramme)
- Module Expeditions (structure detaillee)
- Moteur IA - Etape 1 (4 outils du chatbot)
- Generation Documents - Etape 2 (WeasyPrint)
- Flux de donnees
- Integrations externes (DELTA, BADR)

**Quand le lire :**
- Comprendre le fonctionnement interne
- Developper de nouvelles fonctionnalites

---

### DATABASE_SCHEMA.md

**Contenu :**
- Structure hierarchique des tables
- Detail de chaque modele (ClassificationData, DocumentsData, etc.)
- Relations 1:1 et 1:N
- Structure des fichiers media
- Format des champs JSON

**Quand le lire :**
- Comprendre la structure de donnees
- Modifier les modeles Django

---

### agent_ia_core/README.md

**Contenu :**
- Structure du moteur IA
- Philosophie (chatbots independants)
- Les 4 outils du chatbot TARIC
- Comment creer un nouveau chatbot
- ToolDefinition et ToolRegistry

**Quand le lire :**
- Travailler sur le chatbot IA
- Ajouter de nouveaux outils

---

## Les 5 Etapes du Processus Douanier

### Etape 1 : Classification Douaniere (Implemente)

**Localisation :** apps/expeditions/etapes/classification/

**Fonctionnalites :**
- Upload photo ou fiche technique PDF
- Chatbot IA avec Function Calling
- 4 outils : web_search, browse_webpage, analyze_documents, fetch_pdf
- Proposition des codes SH/NC/TARIC avec confiance
- Extraction structuree avec OpenAI Structured Output
- Selection par bouton

**Fichiers cles :**
- agent_ia_core/chatbots/etapes_classification_taric/service.py
- agent_ia_core/chatbots/etapes_classification_taric/tools/*.py

---

### Etape 2 : Generation Documents (Implemente)

**Localisation :** apps/expeditions/etapes/documents/

**Fonctionnalites :**
- Formulaire 50+ champs (destinataire, transport, valeurs)
- Generation PDF via WeasyPrint
- Documents : DAU (FR->DZ), D10 (DZ->FR)
- Telechargement ZIP

**Fichiers cles :**
- apps/expeditions/etapes/documents/services.py (DocumentGenerationService)
- apps/expeditions/etapes/documents/forms.py (DocumentsDataForm)

---

### Etape 3 : Transmission Electronique (Planifie)

**Localisation :** apps/expeditions/etapes/transmission/

**Systemes cibles :**
- DELTA (France) - API REST via prestataires
- BADR (Algerie) - RPA si autorise

---

### Etape 4 : Paiement des Droits (Planifie)

**Localisation :** apps/expeditions/etapes/paiement/

**Fonctionnalites prevues :**
- Calcul automatique des droits
- Calcul TVA
- Initiation du paiement

**Formule :** Droits = (Valeur CIF + Frais) x Taux

**Taux Algerie :**
| Categorie | Taux |
|-----------|------|
| Premiere necessite | 5% |
| Matieres premieres | 15% |
| Semi-finis | 30% |
| Produits finis | 60% |

---

### Etape 5 : Gestion OEA (Planifie)

**Localisation :** apps/expeditions/etapes/oea/

**Facilitations OEA :**
- Paiement differe
- Procedures simplifiees
- Reduction des controles

---

## Guide par Role

### Utilisateurs

1. Se connecter a l'application
2. Creer une nouvelle expedition (menu Expeditions)
3. Completer l'etape 1 (Classification via chatbot)
4. Completer l'etape 2 (Formulaire + Generation PDF)

### Developpeurs

1. Lire ARCHITECTURE.md
2. Lire agent_ia_core/README.md pour le moteur IA
3. Structure des etapes : apps/expeditions/etapes/
4. Chatbots IA : agent_ia_core/chatbots/

**Pour ajouter un nouvel outil au chatbot :**
1. Creer fichier dans agent_ia_core/chatbots/etapes_classification_taric/tools/
2. Definir TOOL_DEFINITION avec ToolDefinition
3. L'outil sera autodecouvert au demarrage

**Pour creer un nouveau chatbot :**
1. Creer dossier dans agent_ia_core/chatbots/mon_chatbot/
2. Definir config.py, prompts.py, service.py
3. Creer tools/ avec les outils specialises
4. Voir agent_ia_core/README.md pour les details

---

## Perimetre Phase 1

**Corridor :** France <-> Algerie uniquement

**Limitations :**
- Produits de base (articles courants)
- Hors : produits petroliers, matieres dangereuses, licences speciales

**Ce qui est implemente :**
- Module Expeditions complet (structure)
- Etape 1 : Classification douaniere par chatbot IA
- Etape 2 : Generation documents PDF (DAU, D10)
- Authentification

---

## Contact

**Developpeurs :**
- Adrian Ubeda Touati (aubedatouati@gmail.com)
- Juan Manuel Labrador Munoz (mario.neta.rosario@gmail.com)

---

**Version :** 2.0.0
**Date :** Janvier 2026
**Contexte :** Projet academique - Fin de Master
