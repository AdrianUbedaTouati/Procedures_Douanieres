# Architecture du Systeme - Procedures Douanieres v2.0

**Solution d'Automatisation des Procedures Douanieres - Corridor France <-> Algerie**

---

## Table des Matieres

1. [Vue d'Ensemble](#vue-densemble)
2. [Architecture Haut Niveau](#architecture-haut-niveau)
3. [Module Expeditions](#module-expeditions)
4. [Moteur IA - Etape 1](#moteur-ia---etape-1)
5. [Generation Documents - Etape 2](#generation-documents---etape-2)
6. [Flux de Donnees](#flux-de-donnees)
7. [Integrations Externes](#integrations-externes)

---

## Vue d'Ensemble

### Objectif

Plateforme Django utilisant l'IA avec **Function Calling** pour automatiser le parcours douanier France <-> Algerie.

### Les 5 Axes du Cahier des Charges

| Axe | Etape | Description | Statut |
|-----|-------|-------------|--------|
| 1 | Classification | Classification SH/NC/TARIC par IA | Implemente |
| 2 | Documents | Generation automatique DAU, D10 | Implemente |
| 3 | Transmission | Connexion DELTA, BADR | Planifie |
| 4 | Paiement | Calcul et reglement des droits | Planifie |
| 5 | OEA | Gestion du statut Operateur Economique Agree | Planifie |

### Technologies

| Couche | Technologie | Justification |
|--------|-------------|---------------|
| Backend | Django 5.x, Python 3.12 | Framework robuste, ORM puissant |
| IA | OpenAI GPT-4o, Function Calling | Meilleur rapport qualite/prix pour le tool-calling |
| Vision | GPT-4o Vision | Analyse d'images et PDFs scannes |
| PDF | WeasyPrint | Generation PDF depuis HTML/CSS, open-source |
| Frontend | Bootstrap 5, Alpine.js, HTMX | Leger, reactif, sans build complexe |
| Base de donnees | SQLite | Simple pour developpement |

---

## Architecture Haut Niveau

```
+------------------------------------------------------------------+
|                      INTERFACE UTILISATEUR                        |
|                    Bootstrap 5 + Alpine.js + HTMX                 |
|  +------------+  +------------+  +------------+  +------------+   |
|  |  Accueil   |  |Expeditions |  | Assistant  |  |  Profil    |   |
|  +------------+  +------------+  +------------+  +------------+   |
+--------------------------------+---------------------------------+
                                 | HTTP/AJAX/HTMX
                                 v
+------------------------------------------------------------------+
|                      APPLICATIONS DJANGO                          |
|  +--------------------------------------------------------------+|
|  |                         apps/                                 ||
|  |  +- authentication/    # Authentification utilisateurs        ||
|  |  +- core/              # Configuration, providers LLM         ||
|  |  +- chat/              # Assistant conversationnel            ||
|  |  +- expeditions/       # Module principal (5 etapes)          ||
|  |       +- etapes/                                              ||
|  |           +- classification/   # Etape 1: Chatbot IA          ||
|  |           +- documents/        # Etape 2: Generation PDF      ||
|  |           +- transmission/     # Etape 3: DELTA/BADR          ||
|  |           +- paiement/         # Etape 4: Droits              ||
|  |           +- oea/              # Etape 5: OEA                 ||
|  +--------------------------------------------------------------+|
+--------------------------------+---------------------------------+
                                 |
                                 v
+------------------------------------------------------------------+
|                      MOTEUR IA (agent_ia_core)                    |
|  +--------------------------------------------------------------+|
|  |  chatbots/etapes_classification_taric/                        ||
|  |  +- service.py         # TARICClassificationService           ||
|  |  +- tools/             # 4 outils du chatbot                  ||
|  |      +- web_search.py                                         ||
|  |      +- browse_webpage.py                                     ||
|  |      +- analyze_documents.py                                  ||
|  |      +- fetch_pdf.py                                          ||
|  +--------------------------------------------------------------+|
+--------------------------------+---------------------------------+
                                 |
             +-------------------+-------------------+
             v                   v                   v
+----------------+ +----------------+ +----------------+
|   OpenAI API   | |  Google Search | | Systemes Ext.  |
|                | |       API      | |                |
| GPT-4o         | | Custom Search  | | DELTA (France) |
| GPT-4o Vision  | |                | | BADR (Algerie) |
| Structured Out.| |                | |                |
+----------------+ +----------------+ +----------------+
```

---

## Module Expeditions

### Structure du Module

Le module apps/expeditions/ est le coeur de l'application.

```
apps/expeditions/
+-- models.py                # Expedition, ExpeditionEtape, *Data
+-- views.py                 # Vues principales
+-- urls.py
+-- forms.py
|
+-- templates/expeditions/
|   +-- expedition_list.html
|   +-- expedition_detail.html
|   +-- etapes/
|       +-- classification.html    # Chat interface
|       +-- documents.html         # Formulaire + PDF
|
+-- etapes/
    +-- classification/            # Etape 1
    |   +-- views.py
    |   +-- services.py
    |
    +-- documents/                 # Etape 2
        +-- views.py
        +-- forms.py               # 50+ champs
        +-- services.py            # DocumentGenerationService
```

### Workflow des 5 Etapes

| Etape | Nom | Fonction | Statut |
|-------|-----|----------|--------|
| 1 | Classification | Upload + Chatbot IA -> Codes TARIC | Implemente |
| 2 | Documents | Formulaire + Generation PDF DAU/D10 | Implemente |
| 3 | Transmission | Envoi vers DELTA/BADR | Planifie |
| 4 | Paiement | Calcul droits + TVA | Planifie |
| 5 | OEA | Verification statut OEA | Planifie |

---

## Moteur IA - Etape 1

### Les 4 Outils (Tools)

| Outil | Description | Innovation |
|-------|-------------|------------|
| web_search | Recherche Google | Informations actualisees sur les codes TARIC |
| browse_webpage | Lecture de pages web | Early stopping : economie de 92% des tokens |
| analyze_documents | Analyse Vision | Strategie intelligente PDF : texte vs image |
| fetch_pdf | Telechargement PDF | Sauvegarde automatique dans l'expedition |

### Extraction Structuree

Utilisation de OpenAI Structured Output (JSON Schema strict) pour garantir un format valide:

```json
{
  "proposals": [
    {
      "code_taric": "8471300000",
      "description": "Ordinateurs portables",
      "probability": 95,
      "droits_douane": "0%",
      "tva": "20%",
      "justification": "..."
    }
  ]
}
```

---

## Generation Documents - Etape 2

### DocumentGenerationService

Processus de generation:

1. Donnees d'entree (Expedition + ClassificationData + DocumentsData)
2. Template HTML Django
3. WeasyPrint (HTML -> PDF)
4. Sauvegarde ExpeditionDocument

### DocumentsData

Plus de 50 champs pour les informations commerciales :

| Categorie | Exemples de champs |
|-----------|-------------------|
| Destinataire | Nom, adresse, ville, pays, numero fiscal |
| Transport | Mode (mer/air/route), nom du navire, ports |
| Valeurs | FOB, fret, assurance, CIF (calcule auto) |
| Marchandises | Nombre de colis, poids brut/net, origine |
| Incoterms | EXW, FOB, CIF, DAP... |

---

## Integrations Externes

### DELTA (France) - Planifie

- Type : API REST
- Documents : DAU, ENS, ICS2
- Approche : Prestataires agrees (Conex, CCS)

### BADR (Algerie) - Planifie

- Type : Portail web (pas d'API publique)
- Documents : D10, D12
- Approche : RPA (Selenium/Playwright) si autorise

---

**Version** : 2.0.0
**Date** : Janvier 2026
