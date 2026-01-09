# Documentation - Procedures Douanieres

**Solution d'Automatisation des Procedures Douanieres - Corridor France <-> Algerie**

## Index de la Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architecture technique du systeme |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Schema de base de donnees |
| [DOCS_INDEX.md](DOCS_INDEX.md) | Index detaille et guide par role |
| [../agent_ia_core/README.md](../agent_ia_core/README.md) | Documentation du moteur IA |

## Commencer Ici

Si c'est votre premiere fois, lisez dans cet ordre :

1. **[../README.md](../README.md)** - Presentation et installation
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Architecture technique
3. **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** - Schema de base de donnees

## Resume du Projet

### Les 5 Etapes du Processus Douanier

| Etape | Nom | Statut | Description |
|-------|-----|--------|-------------|
| 1 | **Classification** | Implemente | Chatbot IA avec 4 tools pour classifier les produits |
| 2 | **Documents** | Implemente | Generation PDF (DAU, D10) via WeasyPrint |
| 3 | Transmission | Planifie | Envoi vers DELTA (France) / BADR (Algerie) |
| 4 | Paiement | Planifie | Calcul et paiement des droits |
| 5 | OEA | Planifie | Gestion du statut Operateur Economique Agree |

### Technologies Principales

| Composant | Technologie |
|-----------|-------------|
| Backend | Django 5.x, Python 3.12 |
| IA | OpenAI GPT-4o, Function Calling |
| Vision | GPT-4o Vision |
| PDF | WeasyPrint |
| Frontend | Bootstrap 5, Alpine.js, HTMX |

### Les 4 Outils du Chatbot (Etape 1)

| Outil | Fonction |
|-------|----------|
| `web_search` | Recherche Google Custom Search API |
| `browse_webpage` | Extraction progressive avec early stopping |
| `analyze_documents` | Analyse Vision GPT-4o (photos/PDF) |
| `fetch_pdf` | Telechargement de fiches techniques |

## Contact

**Developpeurs** :
- Adrian Ubeda Touati (aubedatouati@gmail.com)
- Juan Manuel Labrador Munoz (mario.neta.rosario@gmail.com)

---

**Version** : 2.0.0
**Date** : Janvier 2026
